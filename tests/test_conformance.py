"""`test=<seconds>` leaves a verdict the real engine can be judged by.

The engine exposes no quit/exit/shutdown, so a mission cannot fail a build directly - it
can only leave evidence, and the launcher turns that into an exit code.

The tests that matter most are the ones about what the verdict does NOT claim. A run that
executed nothing at all still reaches 30 seconds without a runtime error, so `errors: 0`
alone is not a pass - `reached` and `errors` are separate fields and the verdict needs
both. This session produced a real instance of that failure: a launch argument matched
nothing, the mission spawned nothing, and the run reported success.
"""

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import json
import logging
import os
import unittest

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  (settle node import order)
import cosmos_dev.mock.sbs as mock
from sbs_utils.helpers import FrameContext
from sbs_utils.procedural import conformance as C


class _Sim:
    """Only what FrameContext.sim_seconds reads: ticks at 30 Hz."""
    def __init__(self, seconds=0):
        self.time_tick_counter = int(seconds * 30)


class _Ctx:
    sbs = mock

    def __init__(self, seconds=None):
        if seconds is not None:
            self.sim = _Sim(seconds)


class _Base(unittest.TestCase):
    def setUp(self):
        self._saved = FrameContext.context
        FrameContext.context = _Ctx()
        C.conformance_reset()
        mock.set_command_line([])
        self._path = None

    def tearDown(self):
        C.conformance_reset()
        FrameContext.context = self._saved
        mock.set_command_line([])
        from sbs_utils.fs import get_mission_dir
        p = os.path.join(get_mission_dir(), "records", "verdict.json")
        if os.path.exists(p):
            os.remove(p)

    def _verdict(self):
        from sbs_utils.fs import get_mission_dir
        p = os.path.join(get_mission_dir(), "records", "verdict.json")
        if not os.path.exists(p):
            return None
        with open(p, encoding="utf-8") as f:
            return json.load(f)


class TestNotRequested(_Base):
    def test_no_argument_means_no_verdict(self):
        self.assertEqual(C.conformance_seconds(), 0)
        C.conformance_tick()
        self.assertIsNone(self._verdict())

    def test_a_bad_value_warns_rather_than_guessing(self):
        from sbs_utils.procedural import execution
        said, real = [], execution.log
        execution.log = lambda m, *a, **k: said.append(m)
        try:
            mock.set_command_line(["test=soon"])
            self.assertEqual(C.conformance_seconds(), 0)
        finally:
            execution.log = real
        self.assertTrue(any("soon" in m for m in said), said)


class TestVerdict(_Base):
    def setUp(self):
        super().setUp()
        mock.set_command_line(["test=10", "run=ci", "map=sandbox"])

    def test_nothing_is_written_before_the_time_is_up(self):
        C.conformance_seconds()
        FrameContext.context = _Ctx(3)
        C.conformance_tick()
        self.assertIsNone(self._verdict(),
                          "a verdict written early would describe a run that never finished")

    def test_a_clean_run_passes(self):
        C.conformance_seconds()
        C.conformance_write(sim_seconds=12)
        v = self._verdict()
        self.assertEqual(v["verdict"], "PASS")
        self.assertEqual(v["errors"], 0)
        self.assertTrue(v["reached"])
        self.assertEqual(v["run"], "ci")
        self.assertEqual(v["map"], "sandbox")

    def test_a_runtime_error_fails_it(self):
        C.conformance_seconds()
        logging.getLogger("mast.runtime").error("boom in a label")
        C.conformance_write(sim_seconds=12)
        v = self._verdict()
        self.assertEqual(v["verdict"], "FAIL")
        self.assertEqual(v["errors"], 1)
        self.assertIn("boom", v["first_error"])

    def test_falling_short_of_the_time_fails_even_with_no_errors(self):
        """The case that matters: a mission that died at second 2 has no runtime errors
        either. Zero errors is not a pass on its own."""
        C.conformance_seconds()
        C.conformance_write(sim_seconds=2)
        v = self._verdict()
        self.assertEqual(v["errors"], 0)
        self.assertFalse(v["reached"])
        self.assertEqual(v["verdict"], "FAIL")

    def test_the_runtime_is_stamped(self):
        """An engine report and a mock report otherwise look identical, and one has already
        been mistaken for the other."""
        C.conformance_seconds()
        C.conformance_write(sim_seconds=12)
        self.assertEqual(self._verdict()["runtime"], "mock")

    def test_it_says_what_it_did_not_check(self):
        """A verdict claiming more than it measured is worse than none."""
        C.conformance_seconds()
        C.conformance_write(sim_seconds=12)
        self.assertIn("coverage", self._verdict()["note"])

    def test_written_once(self):
        C.conformance_seconds()
        FrameContext.context = _Ctx(12)
        C.conformance_tick()
        first = self._verdict()["sim_seconds"]
        FrameContext.context = _Ctx(99)
        C.conformance_tick()
        self.assertEqual(self._verdict()["sim_seconds"], first,
                         "the verdict describes when the run finished, not the last tick")


class TestTickIsSafe(_Base):
    """`conformance_tick` runs on every tick of the shipped library, so it must never raise.

    `FrameContext.sim_seconds` reads `context.sim.time_tick_counter` and RAISES when there
    is no sim - which happens before one is created. An unguarded read here would take down
    every mission, whether or not anyone asked for a conformance pass.
    """

    def test_no_sim_does_not_raise(self):
        mock.set_command_line(["test=10"])
        FrameContext.context = _Ctx()          # no .sim at all
        C.conformance_tick()                   # must simply do nothing
        self.assertIsNone(self._verdict())

    def test_no_context_does_not_raise(self):
        mock.set_command_line(["test=10"])
        C.conformance_seconds()
        FrameContext.context = None
        C.conformance_tick()


class TestReset(_Base):
    def test_reset_detaches_the_counter(self):
        mock.set_command_line(["test=10"])
        C.conformance_seconds()
        logging.getLogger("mast.runtime").error("one")
        self.assertEqual(C.conformance_error_count(), 1)
        C.conformance_reset()
        self.assertEqual(C.conformance_error_count(), 0)
        logging.getLogger("mast.runtime").error("after the reset")
        self.assertEqual(C.conformance_error_count(), 0,
                         "a detached handler must not keep counting into the next mission")

    def test_registered_in_the_reset_ledger(self):
        from sbs_utils.handlerhooks import _RESET_PROBES
        self.assertIn("conformance", _RESET_PROBES)


if __name__ == "__main__":
    unittest.main()
