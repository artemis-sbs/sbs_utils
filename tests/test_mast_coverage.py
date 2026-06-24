"""Tests for the MastTicker.on_enter_node coverage seam and the dev collector."""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from sbs_utils.mast.mastscheduler import MastTicker
from cosmos_dev.coverage import MastCoverage, label_kind


class TestCoverageSeam(unittest.TestCase):
    def tearDown(self):
        MastTicker.on_enter_node = None   # never leak the hook between tests

    def test_seam_defaults_off(self):
        self.assertIsNone(MastTicker.on_enter_node)

    def test_install_sets_and_uninstall_restores(self):
        cov = MastCoverage().install()
        # Bound methods don't compare equal under `is`; check it's wired to this
        # collector instead.
        self.assertIsNotNone(MastTicker.on_enter_node)
        self.assertEqual(MastTicker.on_enter_node.__self__, cov)
        cov.uninstall()
        self.assertIsNone(MastTicker.on_enter_node)

    def test_records_entered_nodes(self):
        cov = MastCoverage().install()

        class _Cmd:
            file_num = 2
            line_num = 7
        # Simulate the seam firing as next() would.
        MastTicker.on_enter_node("setup", _Cmd())
        MastTicker.on_enter_node("setup", _Cmd())          # same node -> count 2
        MastTicker.on_enter_node("__route__comms/hail__3__", _Cmd())
        cov.uninstall()

        self.assertEqual(cov.nodes[("setup", 2, 7, "_Cmd")], 2)
        self.assertIn("setup", cov.labels_hit)
        self.assertIn("__route__comms/hail__3__", cov.labels_hit)
        self.assertEqual(cov.summary()["labels_hit"], 2)

    def test_label_kind_classification(self):
        self.assertEqual(label_kind("setup"), "label")
        self.assertEqual(label_kind("__route__comms/hail__3__"), "comms")
        self.assertEqual(label_kind("__route__signal/go__1__"), "signal")
        self.assertEqual(label_kind("__route__shared/signal/go__1__"), "shared/signal")
        self.assertEqual(label_kind("__route__damage/destroy__9__"), "damage")

    def test_uncovered_filters_by_kind(self):
        class _FakeMast:
            labels = {"setup": 0, "__route__comms/a__1__": 0,
                      "__route__comms/b__2__": 0, "__route__signal/x__3__": 0}
        cov = MastCoverage()
        cov.nodes = {("__route__comms/a__1__", 1, 1, "X"): 1}   # only this hit
        missing_comms = cov.uncovered(_FakeMast, kinds=("comms",))
        self.assertEqual(missing_comms, ["__route__comms/b__2__"])


if __name__ == "__main__":
    unittest.main()
