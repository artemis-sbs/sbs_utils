"""The pre-flight gate: lint a mission's .amd BEFORE the sim starts.

Until this existed the runner had no AMD import at all -- a document that did not
parse rendered a blank panel and the run reported PASS. Phase 2 made a failed
PARSE fail the run; this catches the errors the parser TOLERATES, of which the
unclosed data fence is the sharpest: the parser silently swallows the rest of
the file as data, so every record below it just is not there.

Two properties matter more than the linting itself:

  * the gate must not KEEP the mission's vocabulary. It runs in the same process
    that then runs the mission, and pre-registering fields changes the order they
    are declared in -- measured, that turned a passing LegendaryMissions run into
    "AMD field 'call sign' is already declared ... with a different meaning".
  * warnings must not fail a run by default. The shipped corpus carries
    legitimate ones, and a gate that fails on those is a gate people route around.
"""
import json
import os
import shutil
import tempfile
import unittest
import zipfile

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural import amd_schema as S
from sbs_utils.procedural.amd_lint import amd_lint_mission
from sbs_utils.procedural.amd_stamp import (STAMP_NAME, amd_digest, amd_stamp_read_zip,
                                            amd_clean_digests, amd_stamp_for_folder)

GOOD = "# [A job](a_job)\n---\nJob\nDone when: destroy 3 raiders\nReward: 5 credits\n---\nbody\n"
UNCLOSED = "# [A job](b_job)\n---\nJob\nReward: 5 credits\n"
JUMP = "# [A](a)\n#### [too deep](d)\n"


class GateBase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def write(self, name, text):
        path = os.path.join(self.dir, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        return path


class TestTheGateFinds(GateBase):
    def test_a_clean_mission_is_silent(self):
        self.write("good.amd", GOOD)
        self.assertEqual(amd_lint_mission(self.dir), [])

    def test_an_unclosed_fence_is_an_error(self):
        # The parser does NOT raise on this -- it swallows the rest of the file --
        # so the Phase 2 seam cannot see it. This is what the gate adds.
        self.write("bad.amd", UNCLOSED)
        codes = [f.code for _p, f in amd_lint_mission(self.dir) if f.is_error()]
        self.assertIn("unclosed-data-fence", codes)

    def test_a_heading_jump_is_an_error(self):
        self.write("bad.amd", JUMP)
        codes = [f.code for _p, f in amd_lint_mission(self.dir) if f.is_error()]
        self.assertIn("heading-level-jump", codes)

    def test_it_walks_subfolders(self):
        self.write(os.path.join("addon", "deep", "bad.amd"), UNCLOSED)
        self.assertTrue(amd_lint_mission(self.dir))

    def test_a_cross_file_reference_is_not_dangling(self):
        # A record referenced from another FILE in the same mission is defined; the
        # mission-wide symbol table is what stops 33 false findings on OpenUniverse.
        self.write("one.amd", "# [Parent](parent)\n---\nJob\nReward: 1 credits\n---\n")
        self.write("two.amd", "# [Child](child)\n---\nJob\nParent: parent\nReward: 1 credits\n---\n")
        codes = [f.code for _p, f in amd_lint_mission(self.dir)]
        self.assertNotIn("dangling-parent", codes)


class TestTheGateDoesNotMutate(GateBase):
    def test_mission_vocabulary_is_borrowed_not_kept(self):
        self.write("good.amd", GOOD)
        self.write("probe_amd.py",
                   "from sbs_utils.procedural.amd_schema import amd_register_fields, text\n"
                   "amd_register_fields('quest', {'gate probe field': text()}, domain='probe')\n")
        before = dict(S.ARCHETYPES.get("quest", {}))
        amd_lint_mission(self.dir)
        self.assertEqual(dict(S.ARCHETYPES.get("quest", {})), before,
                         "the gate kept the mission's vocabulary; running the mission "
                         "next would re-register it in a different order")

    def test_one_mission_does_not_inherit_anothers_words(self):
        other = tempfile.mkdtemp()
        try:
            with open(os.path.join(other, "x_amd.py"), "w", encoding="utf-8") as f:
                f.write("from sbs_utils.procedural.amd_schema import amd_register_fields, text\n"
                        "amd_register_fields('quest', {'only mine': text()}, domain='other')\n")
            with open(os.path.join(other, "a.amd"), "w", encoding="utf-8") as f:
                f.write(GOOD)
            amd_lint_mission(other)
            self.write("mine.amd",
                       "# [B](b)\n---\nJob\nOnly mine: 3\nReward: 1 credits\n---\n")
            codes = [f.code for _p, f in amd_lint_mission(self.dir)]
            self.assertIn("unknown-field", codes,
                          "the previous mission's vocabulary leaked into this one")
        finally:
            shutil.rmtree(other, ignore_errors=True)


class TestTheStamp(GateBase):
    def _zip_with_stamp(self, name, text):
        folder = os.path.join(self.dir, "addon")
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, name), "w", encoding="utf-8", newline="") as f:
            f.write(text)
        stamp, findings = amd_stamp_for_folder(folder, self.dir, "vtest")
        zpath = os.path.join(self.dir, "pack.mastlib")
        with zipfile.ZipFile(zpath, "w") as z:
            z.write(os.path.join(folder, name), name)
            z.writestr(STAMP_NAME, json.dumps(stamp))
        return zpath, stamp, findings

    def test_round_trip(self):
        zpath, stamp, findings = self._zip_with_stamp("good.amd", GOOD)
        self.assertEqual(findings, [])
        self.assertEqual(amd_stamp_read_zip(zpath), stamp)
        self.assertIn(amd_digest(GOOD), amd_clean_digests([zpath]))

    def test_a_file_with_errors_is_not_marked_clean(self):
        zpath, stamp, findings = self._zip_with_stamp("bad.amd", UNCLOSED)
        self.assertTrue(findings)
        self.assertNotIn(amd_digest(UNCLOSED), amd_clean_digests([zpath]))

    def test_line_endings_do_not_invalidate_the_stamp(self):
        # A mastlib holds the build machine's bytes and autocrlf rewrites a working
        # tree's. A raw hash would call every file dirty on the other platform and
        # silently turn the cache off.
        self.assertEqual(amd_digest(GOOD), amd_digest(GOOD.replace("\n", "\r\n")))

    def test_an_edited_byte_invalidates_it(self):
        self.assertNotEqual(amd_digest(GOOD), amd_digest(GOOD + "# [C](c)\n"))

    def test_a_zip_without_a_stamp_contributes_nothing(self):
        zpath = os.path.join(self.dir, "nostamp.mastlib")
        with zipfile.ZipFile(zpath, "w") as z:
            z.writestr("x.amd", GOOD)
        self.assertEqual(amd_stamp_read_zip(zpath), {})
        self.assertEqual(amd_clean_digests([zpath]), set())

    def test_a_missing_or_corrupt_zip_never_raises(self):
        self.assertEqual(amd_clean_digests(["/no/such/file.mastlib"]), set())
        bad = os.path.join(self.dir, "corrupt.mastlib")
        with open(bad, "wb") as f:
            f.write(b"not a zip at all")
        self.assertEqual(amd_clean_digests([bad]), set())

    def test_a_folder_with_no_amd_gets_no_stamp(self):
        empty = os.path.join(self.dir, "empty")
        os.makedirs(empty)
        stamp, findings = amd_stamp_for_folder(empty, self.dir)
        self.assertIsNone(stamp)


if __name__ == "__main__":
    unittest.main()
