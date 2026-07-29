"""MastVerdict.sweep_runtime_log -- the log has the last word.

The on_runtime_error / on_compile_error seams only see errors that travel through
them. Library code that catches its own exception and logs it does not, so a run
could report "PASS - no runtime errors" with errors sitting in mast.runtime.log.
The sweep closes that by treating a non-empty log as a failure.

These are unit tests on the sweep itself; the end-to-end mutation check (inject a
swallow-and-log into a mission, confirm --test flips to FAIL and back) was run
against the real runner.
"""
import os
import tempfile
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from cosmos_dev.verdict import MastVerdict


class TestVerdictLogSweep(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.log = os.path.join(self.dir, "mast.runtime.log")

    def _write(self, text):
        with open(self.log, "w", encoding="utf-8") as f:
            f.write(text)

    def test_clean_log_leaves_the_verdict_passing(self):
        self._write("")
        v = MastVerdict()
        self.assertEqual(v.sweep_runtime_log(self.log), 0)
        self.assertTrue(v.ok)

    def test_whitespace_only_log_is_still_clean(self):
        # The handler is opened per run; an empty-but-touched file is the norm.
        self._write("\n\n   \n")
        v = MastVerdict()
        self.assertEqual(v.sweep_runtime_log(self.log), 0)
        self.assertTrue(v.ok)

    def test_missing_log_is_not_an_error(self):
        # A mission that never compiled MAST never opens the handler.
        v = MastVerdict()
        self.assertEqual(v.sweep_runtime_log(os.path.join(self.dir, "nope.log")), 0)
        self.assertTrue(v.ok)

    def test_logged_only_error_fails_the_verdict(self):
        # The case the seams cannot see: nothing recorded, but the log has content.
        self._write("ValueError: swallowed and logged\n  more detail\n")
        v = MastVerdict()
        found = v.sweep_runtime_log(self.log)
        self.assertGreater(found, 0)
        self.assertFalse(v.ok)
        self.assertEqual(v.errors[0]["source"], "log")
        # The FIRST log line is what identifies it -- a report that only said
        # "check the log" would not be worth failing over.
        self.assertIn("swallowed and logged", v.errors[0]["message"])
        self.assertIn("mast.runtime.log", v.errors[0]["message"])

    def test_does_not_double_report_an_already_recorded_error(self):
        # Recorded errors are logged too, so an unconditional append would make
        # every genuine failure report twice.
        v = MastVerdict()
        v.record_exception(ValueError("already seen"), where="mission_tick")
        self._write("ValueError: already seen\n")
        v.sweep_runtime_log(self.log)
        self.assertEqual(len(v.errors), 1)
        self.assertEqual(v.errors[0]["source"], "python")

    def test_report_names_the_log_source(self):
        self._write("RuntimeError: no seam saw this\n")
        v = MastVerdict()
        v.sweep_runtime_log(self.log)
        report = v.report()
        self.assertTrue(report.startswith("FAIL"))
        self.assertIn("(log)", report)


if __name__ == "__main__":
    unittest.main()
