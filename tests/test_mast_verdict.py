"""Tests for the MastScheduler.on_runtime_error verdict seam and collector."""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from sbs_utils.mast.mastscheduler import MastScheduler
from cosmos_dev.verdict import MastVerdict


class TestVerdictSeam(unittest.TestCase):
    def tearDown(self):
        MastScheduler.on_runtime_error = None   # never leak the hook between tests

    def test_seam_defaults_off(self):
        self.assertIsNone(MastScheduler.on_runtime_error)

    def test_install_sets_and_uninstall_restores(self):
        v = MastVerdict().install()
        self.assertIsNotNone(MastScheduler.on_runtime_error)
        self.assertEqual(MastScheduler.on_runtime_error.__self__, v)
        v.uninstall()
        self.assertIsNone(MastScheduler.on_runtime_error)

    def test_clean_run_is_ok(self):
        v = MastVerdict().install()
        v.uninstall()
        self.assertTrue(v.ok)
        self.assertIn("PASS", v.report())

    def test_runtime_error_fires_seam_and_fails(self):
        v = MastVerdict().install()
        # Simulate the scheduler reporting a runtime error.
        MastScheduler.on_runtime_error("boom at line 7")
        v.uninstall()
        self.assertFalse(v.ok)
        self.assertEqual(len(v.errors), 1)
        self.assertEqual(v.errors[0]["source"], "mast")
        self.assertIn("boom", v.report())

    def test_record_exception(self):
        v = MastVerdict()
        try:
            raise ValueError("bad thing")
        except ValueError as e:
            v.record_exception(e, where="tick")
        self.assertFalse(v.ok)
        self.assertEqual(v.errors[0]["source"], "python")
        self.assertIn("ValueError: bad thing", v.errors[0]["message"])
        self.assertIn("tick", v.report())

    def test_seam_failure_does_not_break_runtime_error(self):
        # A throwing hook must not break the scheduler's error path (it's guarded).
        def boom(_m):
            raise RuntimeError("hook blew up")
        MastScheduler.on_runtime_error = boom
        # Base MastScheduler.runtime_error should swallow the hook error and still print.
        sched = MastScheduler.__new__(MastScheduler)   # avoid full init
        sched.runtime_error("some mast error")          # must not raise


if __name__ == "__main__":
    unittest.main()
