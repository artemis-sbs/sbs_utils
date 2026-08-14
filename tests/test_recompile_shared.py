"""Recompiling a story in one process needs a fresh shared/agent state.

LABELS NO LONGER TAKE PART IN THIS (LM #544). A label used to register its name
into Agent.SHARED -- it WAS a shared variable named after itself -- so a second
in-process compile hit "Label conflicts with shared name" from the FIRST compile's
leftovers, and `watcher = 0` could destroy `=== watcher`. Labels now live in the
per-story `Mast.label_symbols`, which dies with its Mast, so an in-process
recompile is clean by construction rather than by remembering to reset.

The reset contract still matters for everything else Agent.SHARED holds (shared
variables, agents, dispatchers) -- that is what the rest of this file pins.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest
import sbs_utils.mast_sbs.story_nodes  # register node types
from sbs_utils.mast.mast import Mast
from sbs_utils.mast.mast_globals import MastGlobals
from sbs_utils.agent import Agent, clear_shared


def _compile_label():
    m = Mast()
    return m.compile("== admiral_move_camera_sync ==\n    ->END\n", "<test>", m)


class TestRecompileSharedReset(unittest.TestCase):
    def setUp(self):
        Agent.clear()
        clear_shared()

    def test_recompile_without_reset_is_clean(self):
        """The second-run trap this file was written for, now closed at the source.

        A label lives in its own Mast, so nothing of the first compile is left to
        collide with -- no reset required, and none of the "works once, fails on
        run 2" class that a process-global namespace invites.
        """
        self.assertEqual(_compile_label(), [])                 # first compile clean
        self.assertEqual(_compile_label(), [])                 # ...and again, no reset

    def test_a_label_is_not_a_shared_variable(self):
        """The mechanism behind LM #544: while the label was IN Agent.SHARED, an
        unscoped `watcher = 0` resolved to Scope.SHARED and overwrote it."""
        self.assertEqual(_compile_label(), [])
        self.assertIsNone(
            Agent.SHARED.get_inventory_value("admiral_move_camera_sync"),
            "a label must not occupy the shared variable namespace")

    def test_recompile_after_reset_is_clean(self):
        self.assertEqual(_compile_label(), [])
        Agent.clear()                                          # what the runner reload does
        clear_shared()
        self.assertEqual(_compile_label(), [])                 # clean again


class TestDefaultAssignToGlobal(unittest.TestCase):
    """A `default name = ...` to a global/keyword is a legitimate fallback (debug.mast's
    `default elite_get_all_abilities = None`) and must NOT error - including on an
    in-process recompile where the name is still a global from the prior compile. A hard
    `name = ...` to a global is still an error."""

    def setUp(self):
        Agent.clear()
        clear_shared()
        self._added = []

    def tearDown(self):
        for k in self._added:
            MastGlobals.globals.pop(k, None)

    def _register_global(self, name):
        MastGlobals.globals[name] = (lambda: None)
        self._added.append(name)

    def test_default_to_global_is_allowed(self):
        self._register_global("helper_fn_x")                    # as if an import added it
        m = Mast()
        errs = m.compile("== top_x ==\n    default helper_fn_x = None\n    ->END\n", "<t>", m)
        self.assertEqual(errs, [])                              # default is exempt

    def test_hard_assign_to_global_still_errors(self):
        self._register_global("helper_fn_y")
        m = Mast()
        errs = m.compile("== top_y ==\n    helper_fn_y = None\n    ->END\n", "<t>", m)
        self.assertTrue(any("keyword" in e for e in errs))      # hard assign still guarded


class TestResetMissionState(unittest.TestCase):
    """The single source of truth that wipes per-mission runtime state for a fresh
    mission / in-process recompile (handlerhooks.reset_mission_state)."""

    def test_clears_route_dispatchers_and_shared(self):
        from sbs_utils.handlerhooks import reset_mission_state
        from sbs_utils.lifetimedispatcher import LifetimeDispatcher
        from sbs_utils.damagedispatcher import DamageDispatcher, CollisionDispatcher
        from sbs_utils.tickdispatcher import TickDispatcher

        from sbs_utils.mast_sbs.story_nodes.media import MediaLabel
        from sbs_utils.mast_sbs.story_nodes.gui_tab_decorator_label import GuiTabDecoratorLabel

        LifetimeDispatcher._dispatch_spawn.add(lambda e: None)   # a //spawn route
        DamageDispatcher._dispatch_any.add(lambda e: None)
        CollisionDispatcher._dispatch_interactive.add(lambda e: None)
        TickDispatcher._dispatch_tick.add(object())
        MediaLabel.folders["music"] = [object()]                 # an @media label
        GuiTabDecoratorLabel.all["mytab"] = object()             # a //gui/tab label
        Agent.SHARED.set_inventory_value("some_label_name", object())

        reset_mission_state()

        self.assertEqual(LifetimeDispatcher._dispatch_spawn, set())
        self.assertEqual(DamageDispatcher._dispatch_any, set())
        self.assertEqual(CollisionDispatcher._dispatch_interactive, set())
        self.assertEqual(TickDispatcher._dispatch_tick, set())
        self.assertEqual(MediaLabel.folders, {})
        self.assertEqual(GuiTabDecoratorLabel.all, {})
        self.assertIsNone(Agent.SHARED.get_inventory_value("some_label_name"))


if __name__ == "__main__":
    unittest.main()
