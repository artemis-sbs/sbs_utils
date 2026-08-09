"""The parsed-document cache, and why it hands out clones.

Parsing is linear and cheap. What was expensive was doing it AGAIN: the Library
tab re-read and re-parsed every registered .amd on every open, help_tab did the
same, and a hail re-parsed its scene body. The cost was never one parse.

The clone is not defensive habit, it is required. Callers MUTATE the tree they are
given: `amd_doc.amd_splice` extends a section's children in place, and
`quest_grant_amd` hands `node["data"]` to `quest_add` as the quest's LIVE dict,
which `_quest_swap_in_armed` then pops and updates. A shared tree would let one
console's granted quest rewrite the document another console is reading. Cloning
keeps the contract exactly as it was: every call returns a fresh tree.
"""
import os
import shutil
import tempfile
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural import amd_doc
from sbs_utils.procedural.amd_quest import amd_quest_data
from sbs_utils.procedural.quest import (document_get_amd_file, amd_doc_cache_clear,
                                        amd_doc_cache_size)

SRC = ("# [Root](root)\n"
       "## [A job](a_job)\n---\nJob\nDone when: destroy 3 raiders\nReward: 5 credits\n---\nbody\n")
OTHER = "# [Other](other)\n---\nJob\nReward: 1 credits\n---\n"


class CacheBase(unittest.TestCase):
    def setUp(self):
        amd_doc_cache_clear()

    def tearDown(self):
        amd_doc_cache_clear()


class TestItCaches(CacheBase):
    def test_a_second_parse_hits(self):
        document_get_amd_file(None, "r", content=SRC)
        self.assertEqual(amd_doc_cache_size(), 1)
        document_get_amd_file(None, "r", content=SRC)
        self.assertEqual(amd_doc_cache_size(), 1)

    def test_equal_but_never_the_same_object(self):
        a = document_get_amd_file(None, "r", content=SRC)
        b = document_get_amd_file(None, "r", content=SRC)
        self.assertEqual(a, b)
        self.assertIsNot(a, b)
        self.assertIsNot(a["children"][0], b["children"][0])
        self.assertIsNot(a["children"][0]["children"][0]["data"],
                         b["children"][0]["children"][0]["data"])

    def test_different_content_is_a_different_entry(self):
        document_get_amd_file(None, "r", content=SRC)
        document_get_amd_file(None, "r", content=OTHER)
        self.assertEqual(amd_doc_cache_size(), 2)

    def test_the_reader_options_are_part_of_the_key(self):
        # Each of these changes which lines become records, so none may share a hit.
        document_get_amd_file(None, "r", content=SRC)
        document_get_amd_file(None, "r", content=SRC, allow_bare_headings=True)
        document_get_amd_file(None, "r", content=SRC, strip_comments=False)
        document_get_amd_file(None, "r", content=SRC, data_parser=amd_quest_data)
        document_get_amd_file(None, "OTHER TITLE", content=SRC)
        self.assertEqual(amd_doc_cache_size(), 5)

    def test_a_different_data_parser_really_parses_differently(self):
        plain = document_get_amd_file(None, "r", content=SRC)
        quest = document_get_amd_file(None, "r", content=SRC, data_parser=amd_quest_data)
        self.assertNotEqual(plain["children"][0]["children"][0].get("data"),
                            quest["children"][0]["children"][0].get("data"))

    def test_it_is_bounded(self):
        for i in range(200):
            document_get_amd_file(None, "r", content=f"# [K{i}](k{i})\nbody\n")
        self.assertLessEqual(amd_doc_cache_size(), 64)


class TestMutationDoesNotLeak(CacheBase):
    def test_editing_a_returned_tree_leaves_the_next_caller_clean(self):
        a = document_get_amd_file(None, "r", content=SRC)
        a["children"][0]["children"][0]["data"]["reward"] = "MUTATED"
        a["children"][0]["display_text"] = "MUTATED"
        b = document_get_amd_file(None, "r", content=SRC)
        self.assertNotEqual(b["children"][0]["display_text"], "MUTATED")
        self.assertNotEqual(b["children"][0]["children"][0]["data"].get("reward"),
                            "MUTATED")

    def test_amd_splice_does_not_grow_the_cached_tree(self):
        # The real mutator: OpenUniverse splices every declared include into its doc.
        host = amd_doc.amd_document(SRC)
        inc = amd_doc.amd_document(OTHER)
        before = len(amd_doc.amd_root_node(host)["children"])
        amd_doc.amd_splice(host, "a_job", inc)
        again = amd_doc.amd_document(SRC)
        self.assertEqual(len(amd_doc.amd_root_node(again)["children"]), before,
                         "a splice into one copy grew the cached document")


class TestFilesAreKeyedOnTheirBytes(CacheBase):
    def setUp(self):
        super().setUp()
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "d.amd")
        self._write(SRC)

    def tearDown(self):
        super().tearDown()
        shutil.rmtree(self.dir, ignore_errors=True)

    def _write(self, text):
        with open(self.path, "w", encoding="utf-8", newline="") as f:
            f.write(text)

    def test_an_edited_file_is_not_a_stale_hit(self):
        first = document_get_amd_file(self.path, "r")
        self._write(SRC + "## [Added](added)\nmore\n")
        second = document_get_amd_file(self.path, "r")
        self.assertNotEqual(first, second,
                            "an edited file served the previous parse")

    def test_file_and_content_doors_agree(self):
        by_path = document_get_amd_file(self.path, "r")
        by_text = document_get_amd_file(None, "r", content=SRC)
        self.assertEqual(by_path["children"], by_text["children"])

    def test_a_missing_file_is_not_cached_as_empty(self):
        gone = os.path.join(self.dir, "nope.amd")
        document_get_amd_file(gone, "r")
        self._write(SRC)
        shutil.copyfile(self.path, gone)
        tree = document_get_amd_file(gone, "r")
        self.assertEqual(len(tree["children"]), 1,
                         "the failed read was cached and the file never appeared")


class TestContentResolutionCache(unittest.TestCase):
    def test_has_content_and_read_content_share_one_probe(self):
        amd_doc.amd_content_cache_clear()
        self.assertFalse(amd_doc.amd_has_content("no_such_file_xyz.amd"))
        n = amd_doc.amd_content_cache_size()
        self.assertGreater(n, 0, "a miss must be cached: amd_has_content asks it per "
                                 "lore source on every tab open")
        self.assertIsNone(amd_doc.amd_read_content("no_such_file_xyz.amd", quiet=True))
        self.assertEqual(amd_doc.amd_content_cache_size(), n)

    def test_clearing_the_addon_list_clears_the_resolutions(self):
        amd_doc.amd_has_content("no_such_file_xyz.amd")
        self.assertGreater(amd_doc.amd_content_cache_size(), 0)
        amd_doc.amd_declared_addons_clear()
        self.assertEqual(amd_doc.amd_content_cache_size(), 0)


if __name__ == "__main__":
    unittest.main()


class TestTheContentKeyUsesTheRealSourceMap(unittest.TestCase):
    """Two addons may resolve the same filename to different content, so the key
    must carry the calling label's source map. Getting the accessor wrong does not
    slow the cache down - it returns the WRONG FILE."""

    class _SM:
        def __init__(self, basedir, is_lib):
            self.basedir, self.is_lib = basedir, is_lib

    class _Task:
        def __init__(self, sm):
            self._sm = sm

        def get_active_node_source_map(self):
            return self._sm

    def test_two_addons_do_not_share_a_key(self):
        from sbs_utils.helpers import FrameContext
        prev = getattr(FrameContext, "task", None)
        try:
            FrameContext.task = self._Task(self._SM("addon_a", False))
            a = amd_doc._content_key("lore.amd")
            FrameContext.task = self._Task(self._SM("addon_b", True))
            b = amd_doc._content_key("lore.amd")
        finally:
            FrameContext.task = prev
        self.assertNotEqual(a, b)
        self.assertEqual(a[1], "addon_a")
        self.assertEqual(b[1], "addon_b")
        self.assertTrue(b[2])

    def test_no_running_label_is_its_own_key(self):
        from sbs_utils.helpers import FrameContext
        prev = getattr(FrameContext, "task", None)
        try:
            FrameContext.task = None
            self.assertEqual(amd_doc._content_key("lore.amd"), ("lore.amd", None, False))
        finally:
            FrameContext.task = prev
