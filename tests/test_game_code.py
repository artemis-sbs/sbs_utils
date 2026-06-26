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
        maps.maps_get_list = lambda: [self.map]

    def tearDown(self):
        maps.maps_get_list = self._orig_list

    def test_property_vars_in_declaration_order(self):
        self.assertEqual(
            _map_property_vars(self.map),
            ["PLAYER_COUNT", "DIFFICULTY", "TERRAIN_SELECT",
             "FRIENDLY_SELECT", "GAME_TIME_LIMIT", "seed_value"])

    def test_default_includes_all_properties(self):
        self.assertEqual(
            game_code_vars(self.map),
            ["PLAYER_COUNT", "DIFFICULTY", "TERRAIN_SELECT",
             "FRIENDLY_SELECT", "GAME_TIME_LIMIT", "seed_value"])

    def test_metadata_gamecode_overrides_default(self):
        m = FakeMap("siege", SIEGE_PROPS, game_code=["DIFFICULTY", "seed_value"])
        self.assertEqual(game_code_vars(m), ["DIFFICULTY", "seed_value"])

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
        game_code_presets_save_code("siege;DIFFICULTY=5;seed_value=1", self.tmp)
        game_code_presets_save_code("siege;DIFFICULTY=7;seed_value=2", self.tmp)
        game_code_presets_save_code("border_war;DIFFICULTY=3;seed_value=9", self.tmp)
        data = game_code_presets_load(self.tmp)
        self.assertEqual(set(data.keys()), {"siege", "border_war"})
        self.assertEqual(
            game_code_presets_for_map("siege", self.tmp),
            ["siege;DIFFICULTY=5;seed_value=1", "siege;DIFFICULTY=7;seed_value=2"])
        self.assertEqual(len(game_code_presets_for_map("border_war", self.tmp)), 1)

    def test_save_dedups(self):
        game_code_presets_save_code("siege;DIFFICULTY=5", self.tmp)
        game_code_presets_save_code("siege;DIFFICULTY=5", self.tmp)
        self.assertEqual(len(game_code_presets_for_map("siege", self.tmp)), 1)

    def test_for_map_missing_returns_empty(self):
        self.assertEqual(game_code_presets_for_map("nope", self.tmp), [])

    def test_load_missing_file_returns_empty_dict(self):
        self.assertEqual(game_code_presets_load(self.tmp), {})

    def test_save_empty_code_is_noop(self):
        self.assertIsNone(game_code_presets_save_code("", self.tmp))
        self.assertFalse(os.path.exists(self.tmp))


if __name__ == "__main__":
    unittest.main()
