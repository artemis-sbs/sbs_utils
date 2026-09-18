"""A mission reset drops MISSION routes but keeps the LIBRARY's own handlers.

`reset_mission_state()` clears every dispatcher so a recompiled story starts without the
previous story's routes. But the library registers handlers of its own at IMPORT time -
comms/science/popup selection, task purging on destroy, mount and orbit cleanup, the grid
move-role - and a module is imported once per process. Cleared, they were never put back,
so in the dev runner's in-process reload (`--runs`, the /debug restart) run 2 had no comms,
no science selection and leaked tasks for every destroyed object. The engine forks a fresh
process per mission and never saw it.
"""
import sys
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import cosmos_dev.mock.sbs as _mock_sbs
sys.modules.setdefault("sbs", _mock_sbs)          # some procedural modules `import sbs`

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  (import order)
from sbs_utils.consoledispatcher import ConsoleDispatcher
from sbs_utils.griddispatcher import GridDispatcher
from sbs_utils.lifetimedispatcher import LifetimeDispatcher
from sbs_utils.handlerhooks import reset_mission_state
from sbs_utils.procedural import comms, science, popup, grid, mount, orbit  # noqa: F401
from sbs_utils.mast_sbs import mast_sbs_procedural


def _selects(console):
    return ConsoleDispatcher._dispatch_select.get((0, console), [])


def _messages(console):
    return ConsoleDispatcher._dispatch_messages.get((0, console), [])


class TestLibraryHandlersSurviveReset(unittest.TestCase):

    def setUp(self):
        reset_mission_state()

    def test_COMMS_SELECTION_SURVIVES(self):
        self.assertIn(comms.start_comms_selected, _selects("comms_target_UID"))
        self.assertIn(comms.start_comms_selected, _messages("comms_target_UID"))

    def test_grid_comms_selection_survives(self):
        self.assertIn(comms.start_grid_comms_selected, _selects("grid_selected_UID"))
        self.assertIn(comms.start_grid_comms_selected, _messages("grid_selected_UID"))

    def test_science_selection_survives(self):
        self.assertIn(science.start_science_selected, _selects("science_target_UID"))
        self.assertIn(science.start_science_message, _messages("science_target_UID"))

    def test_popups_survive(self):
        for console in ("science_popup", "comms_popup", "comms2d_popup", "weapons_popup"):
            self.assertIn(popup.start_popup_selected, _selects(console), console)

    def test_TASK_PURGE_ON_DESTROY_SURVIVES(self):
        self.assertIn(mast_sbs_procedural.handle_purge_tasks, LifetimeDispatcher._dispatch_destroy)

    def test_mount_and_orbit_cleanup_survive(self):
        self.assertIn(mount._mount_on_destroy, LifetimeDispatcher._dispatch_destroy)
        self.assertIn(orbit._orbit_on_destroy, LifetimeDispatcher._dispatch_destroy)

    def test_grid_move_role_survives(self):
        self.assertIn(grid.grid_remove_move_role, GridDispatcher._dispatch_any_object)

    def test_a_MISSION_route_is_still_dropped(self):
        """The point of the reset: a story's own route must not outlive it."""
        route = lambda event: None          # noqa: E731 - stands in for a route handler
        ConsoleDispatcher.add_default_select("comms_target_UID", route)
        LifetimeDispatcher.add_destroy(route)
        reset_mission_state()
        self.assertNotIn(route, _selects("comms_target_UID"))
        self.assertNotIn(route, LifetimeDispatcher._dispatch_destroy)

    def test_twice_is_the_same_as_once(self):
        reset_mission_state()
        self.assertEqual(1, _selects("comms_target_UID").count(comms.start_comms_selected))


if __name__ == "__main__":
    unittest.main()
