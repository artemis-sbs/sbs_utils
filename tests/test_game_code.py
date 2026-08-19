"""Reusable game_code: encode a map's seed + key option values into a shareable
string, decode it back into the shared scope. See procedural/maps.py."""
import os
import tempfile
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural import maps
from sbs_utils.procedural.maps import (
    game_code_encode, game_code_decode, game_code_vars,
    _map_property_vars, _coerce_like, game_code_label,
    game_code_presets_load, game_code_presets_for_map, game_code_presets_save_code,
    game_code_last_save, game_code_last_code, game_code_last_apply,
    player_loadout_apply_to_ships,
    player_loadout_encode, player_loadout_decode, player_loadout_from_ships,
)
from sbs_utils.procedural.execution import get_shared_variable, set_shared_variable


# Mirrors the real siege metadata: grouped Main/Map, with the world-flavor
# selects (Terrain) and the kept ones (Friendly Ships, Time Limit, Seed).
SIEGE_PROPS = {
    "Main": {
        "Player Ships": 'gui_int_slider("$text:int;low: 1.0;high:8.0;", var= "PLAYER_COUNT")',
        "Difficulty":   'gui_int_slider("$text:int;low: 1.0;high:11.0;", var= "DIFFICULTY")',
    },
    "Map": {
        "Terrain":        'gui_drop_down("$text: {TERRAIN_SELECT};list: none, max", var="TERRAIN_SELECT")',
        "Friendly Ships": 'gui_drop_down("$text: {FRIENDLY_SELECT};list: none, max", var="FRIENDLY_SELECT")',
        "Time Limit":     'gui_input("desc: Minutes;", var="GAME_TIME_LIMIT")',
        "Seed":           'gui_input("desc: Integer (0 = random);", var="seed_value")',
    },
}


class FakeMap:
    def __init__(self, path, props, game_code=None):
        self.path = path
        self._inv = {"Properties": props}
        if game_code is not None:
            self._inv["GameCode"] = game_code

    def get_inventory_value(self, key, default=None):
        return self._inv.get(key, default)


class TestGameCode(unittest.TestCase):
    def setUp(self):
        self.map = FakeMap("siege", SIEGE_PROPS)
        # Live shared vars with realistic types (ints for sliders/seed, strings
        # for dropdowns and the minute input -- matching server_console).
        set_shared_variable("PLAYER_COUNT", 2)
        set_shared_variable("DIFFICULTY", 5)
        set_shared_variable("TERRAIN_SELECT", "some")
        set_shared_variable("FRIENDLY_SELECT", "few")
        set_shared_variable("GAME_TIME_LIMIT", "20")
        set_shared_variable("seed_value", 4242)
        self._orig_list = maps.maps_get_list
        # **kw: maps_get_list now takes include_hidden, and game_code_decode passes
        # it - resolving a saved code is a lookup by path, not a menu.
        maps.maps_get_list = lambda **kw: [self.map]

    def tearDown(self):
        maps.maps_get_list = self._orig_list

    def test_property_vars_in_declaration_order(self):
        self.assertEqual(
            _map_property_vars(self.map),
            ["PLAYER_COUNT", "DIFFICULTY", "TERRAIN_SELECT",
             "FRIENDLY_SELECT", "GAME_TIME_LIMIT", "seed_value"])

    def test_a_shared_code_is_options_only(self):
        # The default is the SHAREABLE code: a code pasted to another host has no
        # business carrying this crew's ship names, and they would be several times
        # longer than everything else in it put together.
        self.assertEqual(
            game_code_vars(self.map),
            ["PLAYER_COUNT", "DIFFICULTY", "TERRAIN_SELECT",
             "FRIENDLY_SELECT", "GAME_TIME_LIMIT", "seed_value"])

    def test_a_saved_code_also_carries_the_ships(self):
        self.assertEqual(
            game_code_vars(self.map, with_loadout=True),
            ["PLAYER_COUNT", "DIFFICULTY", "TERRAIN_SELECT",
             "FRIENDLY_SELECT", "GAME_TIME_LIMIT", "seed_value", "SHIP_LOADOUT"])

    def test_metadata_gamecode_overrides_default(self):
        m = FakeMap("siege", SIEGE_PROPS, game_code=["DIFFICULTY", "seed_value"])
        self.assertEqual(game_code_vars(m), ["DIFFICULTY", "seed_value"])
        self.assertNotIn("SHIP_LOADOUT", game_code_encode(m))

    def test_a_pinned_map_still_saves_its_ships(self):
        # An explicit GameCode list pins the OPTIONS; it does not opt out of saving the
        # crew, which is orthogonal to it.
        m = FakeMap("siege", SIEGE_PROPS, game_code=["DIFFICULTY"])
        self.assertEqual(game_code_vars(m, with_loadout=True), ["DIFFICULTY", "SHIP_LOADOUT"])

    def test_declared_loadout_is_not_duplicated(self):
        m = FakeMap("siege", SIEGE_PROPS, game_code=["DIFFICULTY", "SHIP_LOADOUT"])
        self.assertEqual(game_code_vars(m, with_loadout=True), ["DIFFICULTY", "SHIP_LOADOUT"])

    def test_unset_loadout_is_skipped(self):
        # Listing a var costs nothing when it has no value - encode skips None.
        set_shared_variable("SHIP_LOADOUT", None)
        self.assertNotIn("SHIP_LOADOUT", game_code_encode(self.map))

    def test_set_loadout_rides_a_SAVED_code_and_round_trips(self):
        token = player_loadout_encode([{"name": "Artemis", "hull": "tsn_light_cruiser"}])
        set_shared_variable("SHIP_LOADOUT", token)
        self.assertNotIn("SHIP_LOADOUT", game_code_encode(self.map))   # shared: no
        code = game_code_encode(self.map, with_loadout=True)           # saved: yes
        self.assertIn(f"SHIP_LOADOUT={token}", code)
        set_shared_variable("SHIP_LOADOUT", "")
        game_code_decode(code)
        self.assertEqual(get_shared_variable("SHIP_LOADOUT"), token)

    def test_encode_format(self):
        self.assertEqual(
            game_code_encode(self.map),
            "siege;PLAYER_COUNT=2;DIFFICULTY=5;TERRAIN_SELECT=some;FRIENDLY_SELECT=few;GAME_TIME_LIMIT=20;seed_value=4242")

    def test_encode_includes_all_options(self):
        code = game_code_encode(self.map)
        self.assertIn("TERRAIN_SELECT=some", code)
        self.assertIn("seed_value=4242", code)

    def test_encode_none_map(self):
        self.assertEqual(game_code_encode(None), "")

    def test_decode_roundtrip_restores_values_and_types(self):
        code = game_code_encode(self.map)
        set_shared_variable("DIFFICULTY", 11)
        set_shared_variable("seed_value", 1)
        set_shared_variable("GAME_TIME_LIMIT", "99")
        m = game_code_decode(code)
        self.assertIs(m, self.map)
        self.assertEqual(get_shared_variable("DIFFICULTY"), 5)
        self.assertIsInstance(get_shared_variable("DIFFICULTY"), int)
        self.assertEqual(get_shared_variable("seed_value"), 4242)
        # GAME_TIME_LIMIT stays a string to match its live type
        self.assertEqual(get_shared_variable("GAME_TIME_LIMIT"), "20")
        self.assertIsInstance(get_shared_variable("GAME_TIME_LIMIT"), str)

    def test_decode_foreign_map_is_noop(self):
        set_shared_variable("DIFFICULTY", 7)
        m = game_code_decode("other_mission;DIFFICULTY=1")
        self.assertIsNone(m)
        self.assertEqual(get_shared_variable("DIFFICULTY"), 7)  # untouched

    def test_decode_empty_and_none(self):
        self.assertIsNone(game_code_decode(""))
        self.assertIsNone(game_code_decode(None))

    def test_coerce_like(self):
        self.assertEqual(_coerce_like("5", 0), 5)            # int -> int
        self.assertEqual(_coerce_like("few", "some"), "few")  # str -> str
        self.assertEqual(_coerce_like("20", "x"), "20")       # str stays str
        self.assertEqual(_coerce_like("3.5", 1.0), 3.5)       # float -> float
        self.assertEqual(_coerce_like("7", None), 7)          # unknown -> guess int


class TestGameCodePresets(unittest.TestCase):
    def setUp(self):
        self.tmp = os.path.join(tempfile.gettempdir(), "test_game_code_presets.yaml")
        if os.path.exists(self.tmp):
            os.remove(self.tmp)

    def tearDown(self):
        if os.path.exists(self.tmp):
            os.remove(self.tmp)

    def test_label(self):
        self.assertEqual(
            game_code_label("siege;PLAYER_COUNT=2;DIFFICULTY=5;seed_value=4242"),
            "P2 D5 seed4242")
        self.assertEqual(game_code_label(""), "")

    def test_save_separates_by_map(self):
        game_code_presets_save_code("siege;DIFFICULTY=5;seed_value=1", filename=self.tmp)
        game_code_presets_save_code("siege;DIFFICULTY=7;seed_value=2", filename=self.tmp)
        game_code_presets_save_code("border_war;DIFFICULTY=3;seed_value=9", filename=self.tmp)
        data = game_code_presets_load(self.tmp)
        self.assertEqual(set(data.keys()), {"siege", "border_war"})
        self.assertEqual(
            game_code_presets_for_map("siege", self.tmp),
            [{"name": "Preset 1", "code": "siege;DIFFICULTY=5;seed_value=1"},
             {"name": "Preset 2", "code": "siege;DIFFICULTY=7;seed_value=2"}])
        self.assertEqual(len(game_code_presets_for_map("border_war", self.tmp)), 1)

    def test_save_default_and_explicit_name(self):
        game_code_presets_save_code("siege;DIFFICULTY=5", filename=self.tmp)
        game_code_presets_save_code("siege;DIFFICULTY=7", name="Brutal", filename=self.tmp)
        presets = game_code_presets_for_map("siege", self.tmp)
        self.assertEqual([p["name"] for p in presets], ["Preset 1", "Brutal"])

    def test_legacy_string_entries_get_default_names(self):
        # A file written by the old format (bare code strings) still loads.
        from sbs_utils.fs import save_yaml_data
        save_yaml_data(self.tmp, {"siege": ["siege;DIFFICULTY=5", "siege;DIFFICULTY=7"]})
        presets = game_code_presets_for_map("siege", self.tmp)
        self.assertEqual([p["name"] for p in presets], ["Preset 1", "Preset 2"])
        self.assertEqual(presets[0]["code"], "siege;DIFFICULTY=5")

    def test_save_dedups(self):
        game_code_presets_save_code("siege;DIFFICULTY=5", filename=self.tmp)
        game_code_presets_save_code("siege;DIFFICULTY=5", filename=self.tmp)
        self.assertEqual(len(game_code_presets_for_map("siege", self.tmp)), 1)

    def test_for_map_missing_returns_empty(self):
        self.assertEqual(game_code_presets_for_map("nope", self.tmp), [])

    def test_load_missing_file_returns_empty_dict(self):
        self.assertEqual(game_code_presets_load(self.tmp), {})

    def test_save_empty_code_is_noop(self):
        self.assertIsNone(game_code_presets_save_code("", filename=self.tmp))
        self.assertFalse(os.path.exists(self.tmp))


class TestPlayerLoadout(unittest.TestCase):
    def test_round_trip(self):
        slots = [{"name": "Artemis", "hull": "tsn_light_cruiser"},
                 {"name": "Intrepid", "hull": "tsn_battle_cruiser"}]
        token = player_loadout_encode(slots)
        self.assertEqual(player_loadout_decode(token), slots)

    def test_token_is_game_code_safe(self):
        # No ';' (pair sep) or '=' (key sep) may appear, or it corrupts the code.
        token = player_loadout_encode([{"name": "A;B=C|D~E", "hull": "hull;X"}])
        self.assertNotIn(";", token)
        self.assertNotIn("=", token)
        # The separators we sanitize don't survive inside a field.
        slot = player_loadout_decode(token)[0]
        self.assertNotIn("|", slot["name"])
        self.assertNotIn("~", slot["name"])

    def test_empty_and_none(self):
        self.assertEqual(player_loadout_encode([]), "")
        self.assertEqual(player_loadout_decode(""), [])
        self.assertEqual(player_loadout_decode(None), [])

    def test_from_ships_sorts_by_id(self):
        class Ship:
            def __init__(self, id, name, art_id):
                self.id, self.name, self.art_id = id, name, art_id
        ships = [Ship(20, "Second", "hull_b"), Ship(10, "First", "hull_a")]
        self.assertEqual(
            player_loadout_decode(player_loadout_from_ships(ships)),
            [{"name": "First", "hull": "hull_a"},
             {"name": "Second", "hull": "hull_b"}])

    def test_folds_through_a_game_code(self):
        # The whole point: SHIP_LOADOUT survives a game-code encode/decode.
        token = player_loadout_encode([{"name": "Artemis", "hull": "tsn_light_cruiser"}])
        code = f"siege;SHIP_LOADOUT={token}"
        pairs = dict(p.partition("=")[::2] for p in code.split(";")[1:])
        self.assertEqual(player_loadout_decode(pairs["SHIP_LOADOUT"]),
                         [{"name": "Artemis", "hull": "tsn_light_cruiser"}])


class TestGameCodeLabelLoadout(unittest.TestCase):
    """SHIP_LOADOUT must not be spelled out in a preset label."""

    def test_loadout_is_summarized_as_a_count(self):
        token = player_loadout_encode([{"name": "Artemis", "hull": "tsn_light_cruiser"},
                                       {"name": "Intrepid", "hull": "tsn_battle_cruiser"}])
        label = game_code_label(f"siege;PLAYER_COUNT=2;SHIP_LOADOUT={token}")
        self.assertEqual(label, "P2 ships2")
        # The raw names would be longer than the whole rest of the label.
        self.assertNotIn("Artemis", label)

    def test_empty_loadout_contributes_nothing(self):
        self.assertEqual(game_code_label("siege;PLAYER_COUNT=2;SHIP_LOADOUT="), "P2")


class TestGameCodeLastUsed(unittest.TestCase):
    """The opt-in "start it the way it started last time" slot.

    Shares the per-mission preset file, under a reserved key that is not a map path -
    so it can never appear in the presets dropdown.
    """

    def setUp(self):
        self.tmp = os.path.join(tempfile.gettempdir(), "test_game_code_last.yaml")
        if os.path.exists(self.tmp):
            os.remove(self.tmp)
        self.map = FakeMap("siege", SIEGE_PROPS)
        set_shared_variable("PLAYER_COUNT", 2)
        set_shared_variable("DIFFICULTY", 5)
        set_shared_variable("TERRAIN_SELECT", "some")
        set_shared_variable("FRIENDLY_SELECT", "few")
        set_shared_variable("GAME_TIME_LIMIT", "20")
        set_shared_variable("seed_value", 4242)
        set_shared_variable("SHIP_LOADOUT", None)
        self._orig_list = maps.maps_get_list
        maps.maps_get_list = lambda **kw: [self.map]

    def tearDown(self):
        maps.maps_get_list = self._orig_list
        if os.path.exists(self.tmp):
            os.remove(self.tmp)

    def test_round_trip_restores_the_setup(self):
        game_code_last_save(game_code_encode(self.map), filename=self.tmp)
        set_shared_variable("DIFFICULTY", 11)
        set_shared_variable("PLAYER_COUNT", 8)
        self.assertTrue(game_code_last_apply(self.map, filename=self.tmp))
        self.assertEqual(get_shared_variable("DIFFICULTY"), 5)
        self.assertEqual(get_shared_variable("PLAYER_COUNT"), 2)

    def test_it_carries_the_ships_onto_the_ships(self):
        """Restoring writes the ships and CLEARS the var, so a later pick wins."""
        class Ship:
            def __init__(self, id, name, art_id):
                self.id, self.name, self.art_id = id, name, art_id
        token = player_loadout_encode([{"name": "Vengeance", "hull": "tsn_battle_cruiser"}])
        set_shared_variable("SHIP_LOADOUT", token)
        game_code_last_save(game_code_encode(self.map, with_loadout=True), filename=self.tmp)
        set_shared_variable("SHIP_LOADOUT", "")

        ship = Ship(10, "Artemis", "tsn_light_cruiser")
        game_code_decode(game_code_last_code("siege", self.tmp))
        self.assertEqual(player_loadout_apply_to_ships([ship]), 1)
        self.assertEqual(ship.name, "Vengeance")
        self.assertEqual(ship.art_id, "tsn_battle_cruiser")
        # Cleared: the roster reconcile has nothing left to override a later pick with.
        self.assertEqual(get_shared_variable("SHIP_LOADOUT"), "")

    def test_apply_to_ships_leaves_the_var_alone_when_there_are_no_ships(self):
        # Too early to land on anything - and nobody has had the chance to choose
        # anything either, so the reconcile applying it at start is the right outcome.
        token = player_loadout_encode([{"name": "Vengeance", "hull": "tsn_battle_cruiser"}])
        set_shared_variable("SHIP_LOADOUT", token)
        self.assertEqual(player_loadout_apply_to_ships([]), 0)
        self.assertEqual(get_shared_variable("SHIP_LOADOUT"), token)

    def test_remembers_per_map(self):
        game_code_last_save("siege;DIFFICULTY=5", filename=self.tmp)
        game_code_last_save("border_war;DIFFICULTY=9", filename=self.tmp)
        self.assertEqual(game_code_last_code("siege", self.tmp), "siege;DIFFICULTY=5")
        self.assertEqual(game_code_last_code("border_war", self.tmp), "border_war;DIFFICULTY=9")

    def test_resave_replaces_rather_than_appends(self):
        game_code_last_save("siege;DIFFICULTY=5", filename=self.tmp)
        game_code_last_save("siege;DIFFICULTY=7", filename=self.tmp)
        self.assertEqual(game_code_last_code("siege", self.tmp), "siege;DIFFICULTY=7")

    def test_never_appears_as_a_preset(self):
        # The reserved key must not leak into the dropdown, whatever map is asked for.
        game_code_last_save("siege;DIFFICULTY=5", filename=self.tmp)
        self.assertEqual(game_code_presets_for_map("siege", self.tmp), [])
        self.assertEqual(game_code_presets_for_map("__last_used__", self.tmp), [])

    def test_coexists_with_named_presets(self):
        game_code_presets_save_code("siege;DIFFICULTY=3", name="Easy", filename=self.tmp)
        game_code_last_save("siege;DIFFICULTY=9", filename=self.tmp)
        self.assertEqual([p["name"] for p in game_code_presets_for_map("siege", self.tmp)],
                         ["Easy"])
        self.assertEqual(game_code_last_code("siege", self.tmp), "siege;DIFFICULTY=9")

    def test_apply_is_a_noop_with_nothing_saved(self):
        self.assertFalse(game_code_last_apply(self.map, filename=self.tmp))

    def test_apply_is_a_noop_for_a_map_this_story_lacks(self):
        # The cross-mission guard: a setup remembered elsewhere names a map path this
        # story does not have, so decode changes nothing.
        game_code_last_save("some_other_mission_map;DIFFICULTY=1", filename=self.tmp)
        set_shared_variable("DIFFICULTY", 5)
        self.assertFalse(game_code_last_apply("some_other_mission_map", filename=self.tmp))
        self.assertEqual(get_shared_variable("DIFFICULTY"), 5)

    def test_save_empty_is_a_noop(self):
        self.assertIsNone(game_code_last_save("", filename=self.tmp))
        self.assertFalse(os.path.exists(self.tmp))

    def test_apply_accepts_a_path_or_a_label(self):
        game_code_last_save("siege;DIFFICULTY=5", filename=self.tmp)
        set_shared_variable("DIFFICULTY", 11)
        self.assertTrue(game_code_last_apply("siege", filename=self.tmp))
        self.assertEqual(get_shared_variable("DIFFICULTY"), 5)


if __name__ == "__main__":
    unittest.main()
