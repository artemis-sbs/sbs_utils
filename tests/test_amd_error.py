"""AMD failures must be loud enough to fail a run.

Before this, a broken .amd could not fail anything:

  * document_get_amd_file caught EVERY exception and returned a tree whose
    display_text was the exception OBJECT and whose children were empty -- so the
    panel rendered blank, nothing was logged, and the run reported PASS;
  * a missing file printed "no file" to stdout;
  * the runtime never passed an `errors=` collector to amd_parse_facts, so every
    fence problem the parser found was discarded;
  * the warnings that WERE logged went to loggers `quest`/`action`/`cutscene`/
    `media`, and Mast only attaches a FileHandler to `mast.compile` and
    `mast.runtime` -- so they reached no file the harness reads.

.amd has no compile step, so there was no equivalent of Mast.on_compile_error for
a verdict to hang off. amd_error.on_amd_error is that seam.
"""
import logging
import os
import tempfile
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural import amd_error as amd_err
from sbs_utils.procedural.amd_error import amd_error, amd_warn
from sbs_utils.procedural.quest import document_get_amd_file
import sbs_utils.procedural.amd_quest  # registers the quest vocabulary


BAD_STRUCTURE = "# [a](a)\n#### [jumps two levels](d)\n"
BAD_FENCE = "# [A](a)\n---\nJob\nthis line has no colon\nReward: 10 credits\n---\nbody\n"


class Seam:
    """Capture on_amd_error for the duration of a block."""
    def __enter__(self):
        self.seen = []
        self._prev = amd_err.on_amd_error
        amd_err.on_amd_error = lambda m, f=None, l=None, s="error": \
            self.seen.append({"message": str(m), "file": f, "line": l, "severity": s})
        return self

    def __exit__(self, *a):
        amd_err.on_amd_error = self._prev

    def errors(self):
        return [e for e in self.seen if e["severity"] == "error"]

    def warnings(self):
        return [e for e in self.seen if e["severity"] == "warning"]


class TestTheSeamFires(unittest.TestCase):
    def test_a_structure_error_reaches_the_seam_once(self):
        with Seam() as s:
            document_get_amd_file(None, "Quests", content=BAD_STRUCTURE)
        self.assertEqual(len(s.errors()), 1, s.seen)
        self.assertIn("could not parse", s.errors()[0]["message"])

    def test_the_returned_tree_says_what_broke(self):
        tree = document_get_amd_file(None, "Quests", content=BAD_STRUCTURE)
        # It used to hand back the EXCEPTION OBJECT as display_text and no children.
        self.assertIsInstance(tree["display_text"], str)
        self.assertEqual(len(tree["children"]), 1)
        self.assertIn("Could not read", tree["children"][0]["display_text"])
        self.assertIn("Document structure error",
                      tree["children"][0]["description"])

    def test_a_missing_file_reports_rather_than_printing(self):
        with Seam() as s:
            tree = document_get_amd_file(os.path.join(tempfile.gettempdir(),
                                                      "definitely_not_here_9f3.amd"))
        self.assertTrue(any("not found or unreadable" in e["message"]
                            for e in s.errors()), s.seen)
        self.assertEqual(tree["children"], [])

    def test_fence_problems_are_warnings_with_a_file_line(self):
        with Seam() as s:
            document_get_amd_file(None, "r", content=BAD_FENCE)
        warns = s.warnings()
        self.assertTrue(warns, "the runtime discarded the fence errors again")
        # Line 4 of the FILE, not line 3 of a block the author cannot see.
        self.assertEqual(warns[0]["line"], 4)
        self.assertEqual(s.errors(), [], "a bad fence line is not a failed document")

    def test_a_good_document_is_silent(self):
        with Seam() as s:
            document_get_amd_file(None, "r", content="# [A](a)\n---\nJob\nReward: 5 credits\n---\n")
        self.assertEqual(s.seen, [])

    def test_a_broken_listener_cannot_crash_the_parse(self):
        def explode(*a, **k):
            raise RuntimeError("listener is broken")
        prev = amd_err.on_amd_error
        amd_err.on_amd_error = explode
        try:
            tree = document_get_amd_file(None, "Q", content=BAD_STRUCTURE)
        finally:
            amd_err.on_amd_error = prev
        self.assertEqual(len(tree["children"]), 1)


class TestStrict(unittest.TestCase):
    def tearDown(self):
        amd_err.strict = False

    def test_strict_re_raises(self):
        amd_err.strict = True
        with self.assertRaises(Exception):
            document_get_amd_file(None, "Q", content=BAD_STRUCTURE)

    def test_default_is_not_strict(self):
        # The game must never raise here: this is called from GUI build code and a
        # raise inside a present takes the frame down for every console.
        self.assertFalse(amd_err.strict)


class TestSeverityRouting(unittest.TestCase):
    def test_errors_go_to_the_one_logger_the_harness_reads(self):
        with self.assertLogs("mast.runtime", level="ERROR") as cm:
            amd_error("boom", "x.amd", 3)
        self.assertIn("boom", cm.output[0])

    def test_warnings_stay_out_of_mast_runtime(self):
        # sweep_runtime_log treats ANY content in mast.runtime.log as a failed run,
        # and the shipped corpus has legitimate warnings -- so they must not land there.
        with self.assertLogs("amd", level="WARNING") as cm:
            amd_warn("just a field", "x.amd", 3)
        self.assertIn("just a field", cm.output[0])
        logger = logging.getLogger("mast.runtime")
        with self.assertRaises(AssertionError):
            with self.assertLogs("mast.runtime", level="ERROR"):
                amd_warn("also just a field")

    def test_a_line_without_a_path_still_names_the_line(self):
        self.assertIn("line 7", amd_error("m", None, 7))
        self.assertIn("x.amd:7", amd_error("m", "x.amd", 7))
        self.assertIn("x.amd", amd_error("m", "x.amd"))


class TestVerdictWiring(unittest.TestCase):
    def _verdict(self):
        from cosmos_dev.verdict import MastVerdict
        return MastVerdict()

    def test_a_broken_amd_fails_the_verdict(self):
        v = self._verdict().install()
        try:
            self.assertTrue(v.ok)
            document_get_amd_file(None, "Q", content=BAD_STRUCTURE)
            self.assertFalse(v.ok, "a document that does not parse still passed")
            self.assertEqual(v.errors[0]["source"], "amd")
        finally:
            v.uninstall()

    def test_warnings_do_not_fail_the_verdict(self):
        v = self._verdict().install()
        try:
            document_get_amd_file(None, "r", content=BAD_FENCE)
            self.assertTrue(v.ok, "a mistyped field must not fail a whole run")
        finally:
            v.uninstall()

    def test_uninstall_restores_the_previous_listener(self):
        sentinel = lambda *a, **k: None
        amd_err.on_amd_error = sentinel
        try:
            v = self._verdict().install()
            self.assertIsNot(amd_err.on_amd_error, sentinel)
            v.uninstall()
            self.assertIs(amd_err.on_amd_error, sentinel)
        finally:
            amd_err.on_amd_error = None


if __name__ == "__main__":
    unittest.main()
