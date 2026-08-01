"""Brains and objectives must still TICK after a mission restart.

The bug this locks down cost real debugging time and produced no error at all:

    objective_schedule() latches "already scheduled" in three module globals.
    reset_mission_state() calls TickDispatcher.clear(), throwing the tasks away -
    but the latches stayed set, so the next mission re-registered nothing.

Every mission after the first then ran with dead AI. NPCs spawned, brains were
attached, and nothing ever thought or moved. Cosmos forks a fresh process per
mission so it never sees this; the dev runner reuses the interpreter, so there it
is every run but the first - which is exactly the shape of bug that gets reported
as "it works, then later it doesn't" and looks unreproducible from one run.

A --runs soak shows it as `moving` collapsing while `npcs` and `brains` hold.
"""

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import cosmos_dev.mock.sbs as sbs
from sbs_utils.handlerhooks import reset_mission_audit, reset_mission_state
from sbs_utils.procedural import brain as brain_mod
from sbs_utils.procedural.objective import objective_schedule, objective_ticks_stale
from sbs_utils.tickdispatcher import TickDispatcher
from tests.reset_helper import reset_mock


def _scheduled() -> int:
    """Tick tasks the dispatcher holds. A newly scheduled one waits in
    _new_this_tick until the next dispatch, so both sets count."""
    return len(TickDispatcher._dispatch_tick) + len(TickDispatcher._new_this_tick)


class TestAiTicksSurviveRestart(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)

    def test_ticks_are_rescheduled_after_a_restart(self):
        objective_schedule()
        first = _scheduled()
        self.assertGreater(first, 0, "objective_schedule registered nothing")

        reset_mission_state()          # the restart
        sbs.create_new_sim()
        self.assertEqual(_scheduled(), 0)

        objective_schedule()           # the next mission asks again
        self.assertEqual(_scheduled(), first,
                         "the second mission got no brain/objective tick tasks - "
                         "its NPCs would never think or move")

    def test_stale_tick_latch_is_reported_by_the_ledger(self):
        objective_schedule()
        TickDispatcher.clear()         # dispatcher loses the tasks, latches stay set
        self.assertTrue(objective_ticks_stale())
        self.assertIn("objective.ticks_stale", reset_mission_audit())
        reset_mission_state()
        self.assertFalse(objective_ticks_stale())

    def test_brain_guard_is_released_when_a_brain_pass_raises(self):
        """One exception must not switch the AI off for the rest of the process."""
        original = brain_mod._brains_run_all

        def _boom(tick_task, pass_seconds=None):
            raise RuntimeError("brain pass blew up")

        brain_mod._brains_run_all = _boom
        try:
            with self.assertRaises(RuntimeError):
                brain_mod.brains_run_all(None)
        finally:
            brain_mod._brains_run_all = original

        self.assertFalse(brain_mod.brains_is_stalled(),
                         "the re-entrancy guard stayed latched - every brain in the "
                         "game is now permanently skipped")
        brain_mod.brains_run_all(None)      # and the next pass runs normally


if __name__ == "__main__":
    unittest.main()
