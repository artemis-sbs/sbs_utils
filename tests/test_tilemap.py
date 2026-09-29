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


if __name__ == "__main__":
    unittest.main()
