"""Everything a boarding mission names must actually be reachable from MAST.

THE FAILURE THIS GUARDS IS INVISIBLE TO EVERY OTHER CHECK. `MastGlobals` registers
FUNCTIONS only - a module-level string, list or dict is never a MAST global - so a
mission writing `any_role(ROOM_ROLES)` compiles clean, lints clean, and raises
`NameError: name 'ROOM_ROLES' is not defined` at runtime on the line that uses it.

It happened. `boarding_site.ROOM_ROLES` was written as a constant and used from a probe's
`.mast`, and:

* `sbs lint` has no rule for an unknown MAST global.
* `python -m unittest` proved only that the library agrees with itself.
* `--test` reported **PASS** - the room code only runs once a console has boarded, and
  headless has no consoles, so the line never executed.

It took an engine run with two clients connected. This file is the cheap version of that
run, and it is why the rule "every .mast touchpoint must be an accessor function" is
tested rather than merely written down.
"""
import inspect
import unittest

from sbs_utils.fs import test_set_exe_dir

test_set_exe_dir()

# The mock must be bound as `sbs` BEFORE the library imports it, exactly as
# LandingParty's own content test does - registering the MAST globals walks the
# procedural package, and several of those modules import `sbs` at module scope.
import sys
from cosmos_dev.mock import sbs as _mock_sbs
sys.modules.setdefault("sbs", _mock_sbs)

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
import sbs_utils.mast_sbs.mast_sbs_procedural  # noqa: F401  registers the globals
from sbs_utils.mast.mast_globals import MastGlobals

# Every boarding name a mission is expected to write in a `.mast` file. Add to this when
# a mission starts using something new - the point is that the list is what missions
# actually reach for, not what happens to be public.
CALLED_FROM_MAST = [
    # the party
    "boarding_invite", "boarding_invite_crew", "boarding_open_roster",
    "boarding_beam_down", "boarding_beam_up", "boarding_team", "boarding_me",
    "boarding_held", "boarding_clients", "boarding_job_text", "boarding_is_open",
    # the scene
    "boarding_scene_begin", "boarding_scene", "boarding_scene_end", "boarding_line",
    "boarding_choices", "boarding_choices_for", "boarding_answer", "boarding_seq",
    "boarding_learned", "boarding_metric_install",
    # the bodies and the interior
    "boarding_site_build", "boarding_site_is", "boarding_figure_spawn",
    "boarding_figure_of", "boarding_lifeform_of", "boarding_take", "boarding_release",
    "boarding_my_figure", "boarding_my_host", "boarding_walk", "boarding_click",
    "boarding_where", "boarding_room_at", "boarding_figures",
    # rooms that notice you
    "boarding_rooms_watch", "boarding_rooms_unwatch", "boarding_rooms_occupied",
    "boarding_room_of", "boarding_room_name_of", "boarding_room_name",
    "boarding_client_of_figure",
    # the console
    "boarding_go_down", "boarding_go_up", "boarding_home_ship", "boarding_relevant",
    "boarding_who", "boarding_set_who", "boarding_label", "gui_boarding_screen",
    "gui_boarding_console", "gui_boarding_console_tick",
    "boarding_console_revision",
    # THE ACCESSORS. These exist only because MAST cannot see a constant.
    "boarding_room_roles", "boarding_console_type", "boarding_figure_role",
    "boarding_site_role",
]

# Names that are CONSTANTS in the library and therefore must NOT be written in a .mast
# file. Each one has an accessor above; this pins the pairing so a mission author who
# reaches for the constant is answered by a test rather than by a runtime NameError.
CONSTANTS_WITH_ACCESSORS = {
    "ROOM_ROLES": "boarding_room_roles",
    "FIGURE_ROLE": "boarding_figure_role",
    "SITE_ROLE": "boarding_site_role",
    "BOARDING_CONSOLE": "boarding_console_type",
}


class EveryNameAMissionWritesIsReachable(unittest.TestCase):
    def test_each_one_is_a_mast_global(self):
        missing = [n for n in CALLED_FROM_MAST if n not in MastGlobals.globals]
        self.assertEqual([], missing,
                         "not reachable from MAST - a mission naming these gets a "
                         "runtime NameError: %s" % missing)

    def test_and_each_one_is_actually_a_function(self):
        """Being in the table is not enough - only a callable is usable, and a name
        rebound to something else would still be present."""
        bad = [n for n in CALLED_FROM_MAST
               if n in MastGlobals.globals
               and not (inspect.isfunction(MastGlobals.globals[n])
                        or inspect.isbuiltin(MastGlobals.globals[n]))]
        self.assertEqual([], bad, "present but not callable: %s" % bad)


class ConstantsAreNotReachableAndDoNotNeedToBe(unittest.TestCase):
    def test_the_constants_really_are_invisible(self):
        """Pins WHY the accessors exist. If MAST ever learns to export constants this
        fails, and the accessors can be reconsidered rather than carried forever."""
        for const in CONSTANTS_WITH_ACCESSORS:
            self.assertNotIn(const, MastGlobals.globals,
                             "%s is reachable now - the reason for its accessor is "
                             "gone" % const)

    def test_but_each_has_an_accessor_that_answers(self):
        from sbs_utils.procedural import boarding_site as B
        for const, accessor in CONSTANTS_WITH_ACCESSORS.items():
            self.assertIn(accessor, MastGlobals.globals)
            self.assertTrue(MastGlobals.globals[accessor](),
                            "%s answered nothing" % accessor)


if __name__ == "__main__":
    unittest.main()
