"""The tile world: areas as ASCII, actors that walk them, fog, and exits between areas.

The properties under test are the ones a player notices:

* **Nobody walks through rock, water or a shut door** - and a door opening mid-walk or
  closing in front of somebody is handled, not a teleport.
* **Stepping onto a marked place says so, once**, so a scene can belong to a place.
* **An exit takes a crew member to the next area, beside the way back** - never onto it.
* **The map shows only what the crew has seen**, and never an actor out of sight.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from sbs_utils.agent import clear_shared
from sbs_utils.procedural import tilemap as T
from sbs_utils.procedural.signal import signal_observe, signal_unobserve

TILES = {
    ".": "dirt", "#": "rock", "~": "water", "+": "door",
}

KINDS = {"dirt": {"cell": "tile:dirt"}, "rock": {"cell": "tile:rock", "walk": False},
         "water": {"cell": "tile:water", "walk": False, "see": True},
         "door": {"cell": "tile:door", "walk": True, "see": False}}

RIDGE = """area: ridge
title: Landing Ridge
tileset: test
entry: landing
legend:
  .: dirt
  #: rock
  ~: water
  L: dirt @landing
  c: dirt @to_colony
  o: dirt @overlook
---
##########
#...c....#
#.######.#
#.#~~~~#.#
#........#
#..L..oo.#
##########
"""

COLONY = """area: colony
title: Stillwater
tileset: test
legend:
  .: dirt
  #: rock
  r: dirt @to_ridge
---
#######
#.....#
#..r..#
#.....#
#######
"""

A, B = 101, 102


class TileBase(unittest.TestCase):
    def setUp(self):
        clear_shared()
        T.tilemap_clear()
        T.tilemap_clear_tilesets()
        self.addCleanup(T.tilemap_clear)
        self.addCleanup(T.tilemap_clear_tilesets)
        T.tilemap_tileset("test", KINDS)
        T.tilemap_load(RIDGE)
        T.tilemap_load(COLONY)
        self.now = 0.0
        T.tilemap_set_clock(self.now)
        self.seen = []
        signal_observe(self._obs)
        self.addCleanup(signal_unobserve, self._obs)
        # The tick task needs no dispatcher here: tests drive tilemap_tick by hand.
        T._WATCH["task"] = object()

    def _obs(self, name, data):
        if name.startswith("tilemap_"):
            self.seen.append((name, dict(data)))

    def run_until_still(self, agent, limit=400):
        for _ in range(limit):
            self.now += 0.05
            T.tilemap_set_clock(self.now)
            T.tilemap_tick()
            if not T.tilemap_walking(agent):
                return
        self.fail("still walking")


class TestParsing(TileBase):
    def test_size_and_marks(self):
        self.assertEqual(T.tilemap_size("ridge"), (10, 7))
        self.assertEqual(T.tilemap_mark_cells("ridge", "overlook"), [(6, 5), (7, 5)])
        self.assertEqual(T.tilemap_mark_at("ridge", 4, 1), "to_colony")

    def test_hash_is_a_legend_key_not_a_comment(self):
        self.assertEqual(T.tilemap_kind("ridge", 0, 0), "rock")

    def test_entry_is_the_named_mark(self):
        self.assertEqual(T.tilemap_entry("ridge"), (3, 5))

    def test_an_unknown_character_is_an_error(self):
        with self.assertRaises(T.TilemapError):
            T.tilemap_parse("area: x\nlegend:\n  .: dirt\n---\n.?.\n")

    def test_a_bad_file_is_skipped_not_raised(self):
        self.assertIsNone(T.tilemap_load("no separator here"))


class TestWalking(TileBase):
    def setUp(self):
        super().setUp()
        T.tilemap_place(A, "ridge", party=True)

    def test_a_path_goes_round_rock_and_water(self):
        path = T.tilemap_path("ridge", (3, 5), (1, 1))
        for x, y in path:
            self.assertIn(T.tilemap_kind("ridge", x, y), ("dirt",))
        self.assertEqual(path[-1], (1, 1))

    def test_walking_arrives(self):
        T.tilemap_walk(A, 8, 1)
        self.run_until_still(A)
        self.assertEqual(T.tilemap_where(A), ("ridge", 8, 1))
        self.assertIn("tilemap_arrived", [n for n, _ in self.seen])

    def test_speed_is_cells_per_second(self):
        T.tilemap_walk(A, 7, 5)                     # 4 cells away
        self.now += 0.5
        T.tilemap_set_clock(self.now)
        T.tilemap_tick()
        # The first step is taken at once, then one every 0.25 s: three by 0.5 s.
        self.assertEqual(T.tilemap_where(A)[1:], (6, 5))

    def test_a_goal_in_rock_walks_as_close_as_it_can_and_says_so(self):
        T.tilemap_walk(A, 5, 3)                     # water
        self.run_until_still(A)
        self.assertIn("tilemap_blocked", [n for n, _ in self.seen])
        self.assertEqual(T.tilemap_where(A)[1:], (5, 4))

    def test_A_DOOR_SHUT_IN_FRONT_OF_YOU_REROUTES(self):
        T.tilemap_walk(A, 1, 1)
        self.now += 0.3
        T.tilemap_set_clock(self.now)
        T.tilemap_tick()
        T.tilemap_block("ridge", [(1, 3)])          # the west corridor closes
        self.run_until_still(A)
        self.assertEqual(T.tilemap_where(A)[1:], (1, 1))

    def test_a_blocking_actor_is_walked_round(self):
        T.tilemap_place(B, "ridge", 2, 4, blocks=True)
        path = T.tilemap_path("ridge", (3, 5), (1, 4), ignore=A)
        self.assertNotIn((2, 4), path)

    def test_an_arrival_intent_runs_only_at_the_goal(self):
        got = []
        T.tilemap_walk(A, 5, 3, intent=got.append)   # water: never reached
        self.run_until_still(A)
        self.assertEqual(got, [])
        T.tilemap_walk(A, 1, 1, intent=got.append)
        self.run_until_still(A)
        self.assertEqual(got, [A])


class TestMarks(TileBase):
    def test_entering_a_mark_says_so_once(self):
        T.tilemap_place(A, "ridge", party=True)
        T.tilemap_walk(A, 8, 5)                     # across both overlook cells
        self.run_until_still(A)
        entered = [d["TILEMAP_MARK"] for n, d in self.seen if n == "tilemap_entered"]
        self.assertEqual(entered, ["overlook"])


class TestExits(TileBase):
    def test_stopping_on_an_exit_takes_you_through(self):
        T.tilemap_place(A, "ridge", party=True)
        T.tilemap_walk(A, 4, 1)
        self.run_until_still(A)
        area, x, y = T.tilemap_where(A)
        self.assertEqual(area, "colony")
        self.assertNotEqual((x, y), (3, 2))         # not ON the way back
        self.assertEqual(abs(x - 3) + abs(y - 2), 1)
        moved = [d for n, d in self.seen if n == "tilemap_moved"]
        self.assertEqual((moved[-1]["TILEMAP_FROM"], moved[-1]["TILEMAP_AREA"]),
                         ("ridge", "colony"))

    def test_a_non_party_actor_does_not_wander_off(self):
        T.tilemap_place(B, "ridge", party=False)
        T.tilemap_walk(B, 4, 1)
        self.run_until_still(B)
        self.assertEqual(T.tilemap_where(B)[0], "ridge")

    def test_an_explicit_exit_table_wins(self):
        rec = T.tilemap_area("ridge")
        rec["exits"]["to_colony"] = "colony 1,1"
        self.assertEqual(T.tilemap_exit_target("ridge", "to_colony"), ("colony", (1, 1)))


class TestFog(TileBase):
    def test_a_party_actor_reveals_what_it_can_see(self):
        T.tilemap_place(A, "ridge", party=True)
        self.assertTrue(T.tilemap_explored("ridge", 3, 5))
        self.assertFalse(T.tilemap_explored("colony", 1, 1))

    def test_rock_hides_what_is_behind_it(self):
        T.tilemap_place(A, "ridge", 1, 1, party=True)
        self.assertFalse(T.tilemap_explored("ridge", 8, 5))   # behind the rock wall

    def test_water_does_not_block_sight(self):
        self.assertTrue(T.tilemap_sees("ridge", 3, 4, 3, 2))  # across the water row

    def test_a_non_party_actor_reveals_nothing(self):
        T.tilemap_place(B, "ridge", party=False)
        self.assertEqual(T.tilemap_area("ridge")["explored"], set())

    def test_visible_is_only_what_is_in_sight_now(self):
        T.tilemap_place(A, "ridge", 1, 1, party=True)
        self.assertIn((2, 1), T.tilemap_visible("ridge"))
        self.assertNotIn((8, 5), T.tilemap_visible("ridge"))


class TestRevisionAndReset(TileBase):
    def test_a_step_moves_the_revision(self):
        T.tilemap_place(A, "ridge", party=True)
        before = T.tilemap_revision("ridge")
        T.tilemap_walk(A, 5, 5)
        self.run_until_still(A)
        self.assertGreater(T.tilemap_revision("ridge"), before)

    def test_the_reset_empties_the_world(self):
        T.tilemap_place(A, "ridge")
        T._WATCH["task"] = None
        T.tilemap_clear()
        self.assertEqual(T.tilemap_count(), 0)


class TestFacingAndStride(TileBase):
    """A figure turns to face where it walks and swings a foot per step."""

    def setUp(self):
        super().setUp()
        T.tilemap_place(A, "ridge", 1, 4, party=True)

    def step_once(self):
        rec = T.tilemap_actor(A)
        self.now = max(self.now, rec["next"])
        T.tilemap_set_clock(self.now)
        T.tilemap_tick()

    def test_walking_east_faces_east_and_strides(self):
        T.tilemap_walk(A, 5, 4)
        self.step_once()
        rec = T.tilemap_actor(A)
        self.assertEqual((rec["facing"], rec["stride"]), ("e", 1))
        self.now += 0.3
        self.step_once()
        self.assertEqual(T.tilemap_actor(A)["stride"], 2)

    def test_arriving_stands_idle(self):
        T.tilemap_walk(A, 3, 4)
        self.run_until_still(A)
        self.assertEqual(T.tilemap_actor(A)["stride"], 0)

    def test_face_turns_toward_a_cell(self):
        T.tilemap_face(A, 1, 1)
        self.assertEqual(T.tilemap_actor(A)["facing"], "n")
        T.tilemap_face(A, 6, 4)
        self.assertEqual(T.tilemap_actor(A)["facing"], "e")

    def test_turning_repaints(self):
        before = T.tilemap_revision("ridge")
        T.tilemap_face(A, 1, 1)             # north: away from the default south
        self.assertGreater(T.tilemap_revision("ridge"), before)


class TestSpriteLook(TileBase):
    """The look falls back key by key: a set may have some facings and not others."""

    def setUp(self):
        super().setUp()
        from sbs_utils.procedural.gui.image import ImageAtlas
        self.have = ImageAtlas.all
        self.added = []
        T.tilemap_place(A, "ridge", 1, 4, sprite="tt:who", party=True)

    def add(self, *keys):
        from sbs_utils.procedural.gui.image import ImageAtlas
        for k in keys:
            ImageAtlas(k, "media/none", 0, 0, 1, 1)
            self.added.append(k)
        self.addCleanup(lambda: [self.have.pop(k, None) for k in self.added])

    def look(self):
        return T.tilemap_sprite_look(T.tilemap_actor(A))

    def test_a_plain_sprite_is_itself(self):
        self.assertEqual(self.look(), "tt:who")

    def test_a_facing_and_frame_win_when_they_exist(self):
        self.add("tt:who_s", "tt:who_e_a")
        self.assertEqual(self.look(), "tt:who_s")
        rec = T.tilemap_actor(A)
        rec["facing"], rec["stride"] = "e", 1
        self.assertEqual(self.look(), "tt:who_e_a")
        rec["stride"] = 2                       # no _e_b: falls back to the plain sprite
        self.assertEqual(self.look(), "tt:who")

    def test_down_wins_when_there_is_one(self):
        T.tilemap_set_pose(A, "down")
        self.assertEqual(self.look(), "tt:who")  # no _down look: stays itself
        self.add("tt:who_down")
        self.assertEqual(self.look(), "tt:who_down")
        T.tilemap_set_pose(A, None)
        self.assertEqual(self.look(), "tt:who")


EDGY = """area: edgy
tileset: test
legend:
  .: dirt
  #: rock
---
.....
.###.
.....
"""


class TestNeighborLooks(TileBase):
    def setUp(self):
        super().setUp()
        T.tilemap_tileset("test", dict(KINDS, rock={
            "cell": "tile:rock", "walk": False, "tall": True,
            "edges": {"10": "tile:rock_we", "8": "tile:rock_w_end", "2": "tile:rock_e_end"}},
            dirt={"cell": "tile:dirt", "shade": "tile:dirt_shade"}))
        T.tilemap_load(EDGY)

    def look(self, x, y):
        kind = T.tilemap_kind("edgy", x, y)
        return T.tilemap_cell_look(T.tilemap_kind_spec("edgy", kind), x, y, "edgy")

    def test_a_run_of_rock_picks_its_edges(self):
        self.assertEqual(self.look(1, 1), "tile:rock_e_end")   # rock only to its east
        self.assertEqual(self.look(2, 1), "tile:rock_we")
        self.assertEqual(self.look(3, 1), "tile:rock_w_end")

    def test_ground_south_of_something_tall_is_in_shade(self):
        self.assertEqual(self.look(2, 2), "tile:dirt_shade")
        self.assertEqual(self.look(0, 2), "tile:dirt")
        self.assertEqual(self.look(2, 0), "tile:dirt")

    def test_A_GRID_TEXTURE_IS_PICKED_BY_POSITION(self):
        """Four pieces of one bigger texture: neighbours always get neighbouring pieces,
        so the texture runs on across cells with no seam."""
        T.tilemap_tileset("test", dict(KINDS, dirt={
            "cell": "g:0", "grid": ["g:0", "g:1", "g:2", "g:3"]}))
        looks = {(x, y): self.look(x, y) for x in range(0, 4) for y in (0, 2)}
        self.assertEqual(looks[(0, 0)], "g:0")
        self.assertEqual(looks[(1, 0)], "g:1")
        self.assertEqual(looks[(2, 0)], "g:0")
        self.assertEqual(looks[(1, 2)], "g:1")      # y 2 is an even row again
        spec = T.tilemap_kind_spec("edgy", "dirt")
        self.assertEqual(T.tilemap_cell_look(spec, 1, 1), "g:3")

    def test_GROUND_THAT_GOES_OVER_FRAYS_ONTO_ITS_NEIGHBOUR(self):
        """Salt crust over dirt: the dirt cell beside salt gets salt's strip on that
        edge; the salt cell gets nothing from the dirt below it in priority."""
        T.tilemap_tileset("test", {
            "dirt": {"cell": "g:dirt", "over": 1},
            "rock": {"cell": "g:salt", "over": 3,
                     "fringe": {"n": "f:n", "e": "f:e", "s": "f:s", "w": "f:w"}}})
        # EDGY: row 1 is dirt, rock, rock, rock, dirt.
        self.assertEqual(T.tilemap_cell_fringes("edgy", 0, 1), ["f:e"])   # rock to its east
        self.assertEqual(T.tilemap_cell_fringes("edgy", 2, 0), ["f:s"])   # rock below it
        self.assertEqual(T.tilemap_cell_fringes("edgy", 2, 1), [])        # rock itself
        self.assertEqual(T.tilemap_cell_fringes("edgy", 0, 0), [])        # all dirt around

    def test_A_CONVEX_CORNER_GETS_A_CORNER_PIECE(self):
        T.tilemap_tileset("test", {
            "dirt": {"cell": "g:dirt", "over": 1},
            "rock": {"cell": "g:salt", "over": 3,
                     "fringe": {"n": "f:n", "e": "f:e", "s": "f:s", "w": "f:w",
                                "ne": "f:ne", "se": "f:se", "sw": "f:sw", "nw": "f:nw"}}})
        # (0, 0): rock is only diagonally across, at (1, 1).
        self.assertEqual(T.tilemap_cell_fringes("edgy", 0, 0), ["f:se"])
        # (0, 1): rock to the east - the edge strip, and no corner piece on top of it.
        self.assertEqual(T.tilemap_cell_fringes("edgy", 0, 1), ["f:e"])

    def test_a_kind_with_no_priority_keeps_hard_edges(self):
        T.tilemap_tileset("test", {
            "dirt": {"cell": "g:dirt"},
            "rock": {"cell": "g:salt", "over": 3, "fringe": {"e": "f:e"}}})
        self.assertEqual(T.tilemap_cell_fringes("edgy", 0, 1), [])

    def test_without_the_area_nothing_changes(self):
        spec = T.tilemap_kind_spec("edgy", "dirt")
        self.assertEqual(T.tilemap_cell_look(spec, 2, 2), "tile:dirt")


if __name__ == "__main__":
    unittest.main()
