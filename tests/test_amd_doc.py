"""Multi-file AMD document machinery (sbs_utils.procedural.amd_doc): section navigation
and the File:-splice, promoted out of Open Universe.

Run: python -m unittest tests.test_amd_doc
"""
import unittest
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from sbs_utils.procedural.amd_doc import (
    amd_document, amd_root_node, amd_root_data, amd_section, amd_includes, amd_splice)


def _doc(text):
    return amd_document(text)   # default coercion is fine for structure tests


TOC = (
    "# [World](world)\n"
    "---\n"
    "reputation: { axis: honor }\n"
    "---\n"
    "## [Clans](clans)\n"
    "---\n"
    "File: clans_a.amd\n"
    "Files: clans_b.amd, clans_c.amd\n"
    "---\n"
    "## [Jobs](jobs)\n"
    "### [Patrol](patrol)\n"
)


class AmdDocTests(unittest.TestCase):
    def test_root_and_sections(self):
        doc = _doc(TOC)
        self.assertEqual(amd_root_node(doc).get("key"), "world")
        self.assertEqual(amd_section(doc, "clans").get("key"), "clans")
        self.assertEqual(amd_section(doc, "jobs").get("key"), "jobs")
        self.assertIsNone(amd_section(doc, "nope"))

    def test_root_data_config_block(self):
        # a document-wide config block on the root fence is reachable
        self.assertEqual(amd_root_data(_doc(TOC)).get("reputation"), {"axis": "honor"})

    def test_includes_collects_file_and_files(self):
        incs = amd_includes(_doc(TOC))
        pairs = [(i.get("key"), i.get("file")) for i in incs]
        self.assertEqual(pairs, [
            ("clans", "clans_a.amd"), ("clans", "clans_b.amd"), ("clans", "clans_c.amd")])

    def test_splice_appends_into_section(self):
        doc = _doc(TOC)
        inc = _doc("# [Ashfang](ashfang)\n# [Verdant](verdant)\n")
        amd_splice(doc, "clans", inc)
        keys = [c.get("key") for c in amd_section(doc, "clans").get("children", [])]
        self.assertIn("ashfang", keys)
        self.assertIn("verdant", keys)

    def test_splice_missing_section_is_safe(self):
        doc = _doc(TOC)
        amd_splice(doc, "nope", _doc("# [X](x)\n"))   # no crash
        amd_splice(doc, "clans", None)                # no crash


if __name__ == "__main__":
    unittest.main()
