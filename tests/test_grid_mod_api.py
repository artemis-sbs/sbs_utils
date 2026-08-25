"""An addon can ship ship interiors, a theme, and more than one layout per hull.

WHY THIS WAS MISSING. `grid_get_grid_data()` read exactly two places - the engine's
`grid_data.json` and the *mission directory's* `extra_grid_data.json` - so an addon inside
a `.mastlib` could not contribute an interior at all, and neither could a mod. Ship data
already had a runtime merge (`merge_mod_ship_yaml`); this is its missing half.

Unlike ship data, interiors need NO build step: grid objects are not engine content -
`grid_rebuild_grid_objects` creates every one at runtime through `grid_spawn` - so the
engine never has to pre-know one. See `SHIP_MOD_PLAN.md` s3.

Also covers the three theme defects that made per-race vocabulary impossible, and the
layout support that lets one hull have a full interior, a cheap systems-only one, and a
jump-drive refit.
"""

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

# Explicitly, and BEFORE anything that reaches procedural.comms. comms imports
# story_nodes which imports back into comms, so whichever gets there first wins - import
# this file alone and internal_damage -> comms -> story_nodes -> comms explodes on a
# partially initialized module. Importing story_nodes up front settles the order instead
# of depending on which other test happened to run first.
import sbs_utils.mast_sbs.story_nodes  # noqa: F401
from sbs_utils.procedural import grid as g


_MOD = """
{
  "pirate_brigantine": {
    "grid_objects": [
      {"x": 5, "y": 7, "name": "plunder-hold", "roles": "room,bay,cargo"},
      {"x": 6, "y": 7, "name": "plunder-hold", "roles": "room,bay,cargo"}
    ]
  }
}
"""

_LAYOUTS = """
{
  "pirate_longbow": {
    "theme": "cosmos",
    "layouts": {
      "default": {"grid_objects": [{"x": 7, "y": 7, "name": "hold", "roles": "room"}]},
      "systems": {"grid_objects": [{"x": 7, "y": 8, "name": "impulse",
                                    "roles": "system,engine,impulse"}]},
      "jump":    {"theme": "Retro",
                  "grid_objects": [{"x": 7, "y": 9, "name": "jump",
                                    "roles": "system,engine,jump"}]}
    }
  }
}
"""

_THEME = """
[{"name": "PirateTest",
  "primary_roles": ["room"],
  "colors": {"default": "orange", "room": "orange"},
  "damage_colors": {"default": "crimson"},
  "icons": {"plunder": {"icon": 126, "scale": 1.0}}}]
"""


class TestGridModData(unittest.TestCase):
    def setUp(self):
        g.grid_reset_caches()

    def tearDown(self):
        g.grid_reset_caches()

    def test_an_addon_can_supply_an_interior(self):
        self.assertFalse(g.grid_get_layout("pirate_brigantine"),
                         "pirate_brigantine should start as an empty stub")
        g.grid_merge_mod_data(_MOD, "PirateMod")
        objs = g.grid_get_layout("pirate_brigantine")
        self.assertEqual(len(objs), 2)
        self.assertEqual(g.grid_get_mod("pirate_brigantine"), "PirateMod")

    def test_built_in_hulls_are_untouched(self):
        g.grid_merge_mod_data(_MOD, "PirateMod")
        self.assertGreater(len(g.grid_get_layout("tsn_light_cruiser")), 60)
        self.assertIsNone(g.grid_get_mod("tsn_light_cruiser"))

    def test_a_mod_replaces_a_whole_interior(self):
        """Whole-entry replace: a mod supplies a hull's interior, it does not add a room
        to someone else's. Layout variants are how one hull has more than one."""
        g.grid_merge_mod_data(
            '{"tsn_light_cruiser": {"grid_objects": [{"x":1,"y":1,"name":"a","roles":"room"}]}}',
            "OverrideMod")
        self.assertEqual(len(g.grid_get_layout("tsn_light_cruiser")), 1)

    def test_a_collision_between_two_mods_is_reported(self):
        from sbs_utils.procedural import execution
        said = []
        real = execution.log
        execution.log = lambda msg, *a, **k: said.append(msg)
        try:
            g.grid_merge_mod_data(_MOD, "PirateMod")
            g.grid_merge_mod_data(_MOD, "OtherMod")
        finally:
            execution.log = real
        self.assertTrue(any("collision" in m and "PirateMod" in m and "OtherMod" in m
                            for m in said),
                        f"the clash was not reported by name: {said}")

    def test_junk_input_is_ignored_not_fatal(self):
        for bad in (None, "", "[]", "not: [valid"):
            g.grid_merge_mod_data(bad, "BadMod")
        self.assertGreater(len(g.grid_get_layout("tsn_light_cruiser")), 60)


class TestLayouts(unittest.TestCase):
    def setUp(self):
        g.grid_reset_caches()
        g.grid_merge_mod_data(_LAYOUTS, "LayoutMod")

    def tearDown(self):
        g.grid_reset_caches()

    def test_named_layouts_select(self):
        self.assertEqual(g.grid_get_layout("pirate_longbow")[0]["name"], "hold")
        self.assertEqual(g.grid_get_layout("pirate_longbow", "systems")[0]["name"],
                         "impulse")
        self.assertEqual(g.grid_get_layout("pirate_longbow", "jump")[0]["name"], "jump")

    def test_an_unknown_layout_falls_back_to_default(self):
        """A mission asking for a layout a hull does not have should still get a ship."""
        self.assertEqual(g.grid_get_layout("pirate_longbow", "no_such")[0]["name"],
                         "hold")

    def test_plain_grid_objects_still_read_as_the_default(self):
        """Every existing entry keeps working - this is the backward-compat guarantee."""
        self.assertGreater(len(g.grid_get_layout("tsn_light_cruiser")), 60)

    def test_theme_is_per_hull_and_per_layout(self):
        self.assertEqual(g.grid_get_theme_name("pirate_longbow"), "cosmos")
        self.assertEqual(g.grid_get_theme_name("pirate_longbow", "jump"), "Retro")
        self.assertIsNone(g.grid_get_theme_name("tsn_light_cruiser"))


class TestThemeDefects(unittest.TestCase):
    def setUp(self):
        g.grid_reset_caches()

    def tearDown(self):
        g.grid_reset_caches()

    def test_named_theme_lookup_does_not_raise(self):
        """Defect 3: both lookups called `name.lower.strip()` - missing parens, so every
        call raised AttributeError. Named theme lookup had never worked at all."""
        self.assertEqual(g.grid_get_grid_named_theme("Retro")["name"], "Retro")
        self.assertEqual(g.grid_get_grid_named_theme("  rEtRo  ")["name"], "Retro")

    def test_an_unknown_theme_name_falls_back(self):
        """Callers subscript the result, so None would raise far from the typo."""
        theme = g.grid_get_grid_named_theme("no_such_theme")
        self.assertIsInstance(theme, dict)
        self.assertIn("colors", theme)

    def test_none_means_the_current_theme(self):
        self.assertEqual(g.grid_get_grid_named_theme(None),
                         g.grid_get_grid_current_theme())

    def test_out_of_range_selection_returns_a_theme_not_an_int(self):
        """Defect 5: returned the integer INDEX into callers that subscript it as a dict,
        so a bad selection raised TypeError somewhere unrelated."""
        g.grid_get_grid_theme()
        g._grid_theme_current = 99
        try:
            theme = g.grid_get_grid_current_theme()
            self.assertIsInstance(theme, dict)
            self.assertIn("colors", theme)
        finally:
            g._grid_theme_current = 0

    def test_set_named_theme_works(self):
        g.grid_set_grid_named_theme("Retro")
        try:
            self.assertEqual(g.grid_get_grid_current_theme()["name"], "Retro")
        finally:
            g.grid_set_grid_current_theme(0)

    def test_an_addon_can_supply_a_theme(self):
        g.grid_merge_mod_theme(_THEME)
        self.assertEqual(g.grid_get_grid_named_theme("PirateTest")["colors"]["room"],
                         "orange")

    def test_a_mod_theme_can_reskin_a_built_in_one(self):
        before = g.grid_get_grid_named_theme("Retro")["colors"].get("room")
        g.grid_merge_mod_theme(
            '[{"name":"Retro","colors":{"room":"hotpink","default":"hotpink"},'
            '"damage_colors":{"default":"red"},"icons":{}}]')
        self.assertNotEqual(before, "hotpink")
        self.assertEqual(g.grid_get_grid_named_theme("Retro")["colors"]["room"],
                         "hotpink")

    def test_item_theme_data_honors_a_named_theme(self):
        g.grid_merge_mod_theme(_THEME)
        r = g.grid_get_item_theme_data("room,bay,cargo", "PirateTest")
        self.assertEqual(r.color, "orange")


class TestSensorCoefficientRole(unittest.TestCase):
    def test_the_role_matched_is_the_one_the_data_uses(self):
        """Defect 2: the coefficient table matched "sensors" (plural) while every ship
        carries "sensor" (singular, 92 uses, zero plural), so sensor_damage_coeff was
        permanently 1.0 and sensor damage never degraded sensors."""
        import inspect
        from sbs_utils.procedural import internal_damage
        src = inspect.getsource(internal_damage.set_damage_coefficients)
        self.assertIn('("sensor", "sensor_damage_coeff"', src)
        self.assertNotIn('("sensors", "sensor_damage_coeff"', src)

    def test_no_shipped_hull_uses_the_plural_role(self):
        from sbs_utils.procedural.grid import grid_get_grid_data
        plural = 0
        for entry in grid_get_grid_data().values():
            for o in entry.get("grid_objects") or []:
                if "sensors" in [t.strip().lower() for t in o["roles"].split(",")]:
                    plural += 1
        self.assertEqual(plural, 0,
                         "a hull uses the plural role - the singular fix would miss it")


class TestPlayableRaces(unittest.TestCase):
    """PLAYABLE_RACES gates which race addons load their floor plans.

    An interior is only ever built for a PLAYER ship, so floor plans for a race nobody can
    fly are parsed at load and never used.
    """

    def setUp(self):
        from sbs_utils.procedural import settings
        self.settings = settings
        settings.setting_defaults = None
        settings.settings_get_defaults()

    def tearDown(self):
        self.settings.setting_defaults = None

    def _set(self, value):
        self.settings.settings_get_defaults()["PLAYABLE_RACES"] = value

    def test_matching_ignores_case_and_spacing(self):
        """Both sides are normalized. A setting written 'tsn' or ' TSN ' must match a
        shipData side of 'TSN', or the gate silently hides a whole race's interiors."""
        self._set("  tsn ,  PIRATE  ")
        for race in ("TSN", "tsn", "Tsn", "  tSn  ", "PIRATE", "pirate", "Pirate"):
            self.assertTrue(self.settings.settings_race_is_playable(race), race)

    def test_a_race_not_listed_is_not_playable(self):
        self._set("TSN")
        self.assertFalse(self.settings.settings_race_is_playable("Pirate"))
        self.assertFalse(self.settings.settings_race_is_playable("Klingon"))

    def test_empty_means_no_restriction_not_nothing(self):
        """A mission that clears the setting should get every race, not a game where no
        ship has an interior."""
        for empty in ("", "   ", None):
            self._set(empty)
            self.assertTrue(self.settings.settings_race_is_playable("Pirate"))

    def test_a_list_works_too(self):
        """A mission may reasonably write a YAML list instead of a string."""
        self._set(["TSN", "Pirate"])
        self.assertTrue(self.settings.settings_race_is_playable("pirate"))
        self.assertFalse(self.settings.settings_race_is_playable("Ximni"))

    def test_the_default_covers_every_race_that_has_interiors(self):
        """The default must not silently drop interiors that ship today."""
        for race in ("TSN", "USFP", "Ximni", "Arvonian", "Torgoth", "Skaraan",
                     "Kralien", "Biomech", "Pirate"):
            self.assertTrue(self.settings.settings_race_is_playable(race),
                            f"{race} is not in the default PLAYABLE_RACES")


class TestAddRaces(unittest.TestCase):
    """A MOD widens the race lists rather than replacing them.

    Every mod shipping player-flyable hulls had to hand-roll this against the live
    settings dict - the TNG pack's `tng_register_races` is 30 lines of exactly it. The
    fiddly parts are all silent when wrong: case-insensitive dedupe, a value that may be a
    YAML list instead of a string, and not putting a stray comma in front of the first
    entry when the setting starts empty.
    """

    def setUp(self):
        from sbs_utils.procedural import settings
        self.settings = settings
        settings.setting_defaults = None
        settings.settings_get_defaults()

    def tearDown(self):
        self.settings.setting_defaults = None

    def _set(self, value):
        self.settings.settings_get_defaults()["PLAYABLE_RACES"] = value

    def test_it_adds_without_taking_away(self):
        """The whole point: a Galaxy alongside a TSN crew, not instead of one."""
        self._set("TSN, Ximni")
        added = self.settings.settings_add_playable_races("Federation", "Klingon")
        self.assertEqual(["Federation", "Klingon"], added)
        for race in ("TSN", "Ximni", "Federation", "Klingon"):
            self.assertTrue(self.settings.settings_race_is_playable(race), race)

    def test_it_works_even_when_the_MISSION_named_the_key(self):
        """The reason this is not `settings_set_mod_default`, which returns False once the
        mission has spoken. A mission listing `TSN, Ximni` has said nothing at all about
        the Federation, so widening the list is not overriding its choice."""
        self.settings.settings_get_defaults()["PLAYABLE_RACES"] = "TSN, Ximni"
        self.settings._explicit_keys.add("PLAYABLE_RACES")
        try:
            self.assertFalse(
                self.settings.settings_set_mod_default("PLAYABLE_RACES", "Federation"),
                "precondition: the mod tier is refused once the mission set the key")
            self.settings.settings_add_playable_races("Federation")
            self.assertTrue(self.settings.settings_race_is_playable("Federation"))
            self.assertTrue(self.settings.settings_race_is_playable("TSN"))
        finally:
            self.settings._explicit_keys.discard("PLAYABLE_RACES")

    def test_a_race_already_listed_is_not_duplicated(self):
        self._set("TSN, Ximni")
        self.assertEqual([], self.settings.settings_add_playable_races("tsn", "  XIMNI "))
        self.assertEqual(
            2, len(self.settings.settings_playable_races()),
            "a case variant was appended as a second entry")

    def test_it_dedupes_within_one_call_too(self):
        self._set("TSN")
        self.assertEqual(["Federation"],
                         self.settings.settings_add_playable_races("Federation", "federation"))

    def test_it_takes_a_string_or_a_list(self):
        self._set("TSN")
        self.settings.settings_add_playable_races("Federation, Klingon")
        self.settings.settings_add_playable_races(["Romulan", "Orion"])
        for race in ("Federation", "Klingon", "Romulan", "Orion"):
            self.assertTrue(self.settings.settings_race_is_playable(race), race)

    def test_adding_to_an_empty_setting_leaves_no_leading_comma(self):
        """An empty setting means NO RESTRICTION, so this is also the case where a stray
        comma would turn one race into a phantom empty entry."""
        self._set("")
        self.settings.settings_add_playable_races("Federation")
        self.assertEqual({"federation"}, self.settings.settings_playable_races())

    def test_the_npc_twin(self):
        self.settings.settings_get_defaults()["NPC_RACES"] = "Kralien"
        self.settings.settings_add_npc_races("Klingon")
        self.assertTrue(self.settings.settings_race_is_npc("Klingon"))
        self.assertTrue(self.settings.settings_race_is_npc("Kralien"))
        self.assertFalse(self.settings.settings_race_is_playable("Klingon"),
                         "the NPC list must not widen the PLAYABLE list")

    def test_it_is_callable_from_MAST(self):
        """A mod calls this from its __init__.mast, so it has to be a MAST global."""
        import sys
        import cosmos_dev.mock.sbs as mock
        sys.modules.setdefault("sbs", mock)
        import sbs_utils.mast_sbs.mast_sbs_procedural  # noqa: F401
        from sbs_utils.mast.mast_globals import MastGlobals
        for name in ("settings_add_playable_races", "settings_add_npc_races"):
            self.assertIn(name, MastGlobals.globals,
                          f"{name} is not callable from MAST - add its module to the "
                          "import list in mast_sbs/mast_sbs_procedural.py")


if __name__ == "__main__":
    unittest.main()
