"""Boarding decks drawn from a ship's interior plan (procedural/boarding_deckplan.py)."""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sys
import unittest
from collections import deque

import cosmos_dev.mock.sbs as mock_sbs
sys.modules.setdefault("sbs", mock_sbs)

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  (import first: circular import)
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.procedural import boarding_deckplan as D
from sbs_utils.procedural import boarding_props as P
from sbs_utils.procedural import tilemap as T

# Quarters and a two-node impulse room on a hallway; cargo below; a pod off on its own.
PLAN = """ship: test_ship
size: 8x5
legend:
  q: crew-quarters
  i: impulse
  c: cargo
  s: sensors
---
qq..ii
qq..ii
..cc..
..cc..
       s
"""


def walkable(layout):
    blocked = {(x, y) for _, x, y, _ in layout["furniture"]}
    return {(x, y) for y, row in enumerate(layout["tiles"]) for x, k in enumerate(row)
            if k is not None and k not in (D.HULL, D.WALL) and (x, y) not in blocked}


def reach(tiles, start):
    seen = {start}
    q = deque([start])
    while q:
        x, y = q.popleft()
        for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if n in tiles and n not in seen:
                seen.add(n)
                q.append(n)
    return seen


class TestPlans(unittest.TestCase):
    def test_an_ascii_plan_gives_rooms_and_hallway(self):
        plan = D.boarding_deck_plan_ascii(PLAN)
        self.assertEqual(plan["cells"][(0, 0)], "crew-quarters")
        self.assertEqual(plan["cells"][(2, 0)], "")                 # hallway
        self.assertNotIn((6, 0), plan["cells"])                     # off the hull

    def test_rooms_find_their_kit_by_role_then_name(self):
        self.assertEqual(D.boarding_deck_room_kind("impulse"), "impulse")
        self.assertEqual(D.boarding_deck_room_kind("vip-quarters"), "quarters")
        self.assertEqual(D.boarding_deck_room_kind("shuttle-bay"), "bay")
        self.assertEqual(D.boarding_deck_room_kind("workshop"), "workshop")
        self.assertEqual(D.boarding_deck_room_kind("grog-locker"), "cargo")
        self.assertEqual(D.boarding_deck_room_kind(""), "hallway")
        self.assertEqual(D.boarding_deck_room_kind("mystery-room"), "room")


class TestLayout(unittest.TestCase):
    def setUp(self):
        self.addCleanup(D.boarding_deck_clear)
        self.plan = D.boarding_deck_plan_ascii(PLAN)
        self.layout = D.boarding_deck_layout(self.plan)

    def test_every_plan_cell_becomes_a_block_of_tiles(self):
        self.assertEqual((self.layout["w"], self.layout["h"]), (8 * 3 + 1, 5 * 3 + 1))
        self.assertTrue(self.layout["cell_tiles"][(4, 0)])

    def test_the_whole_deck_is_one_walk_from_the_entry(self):
        tiles = walkable(self.layout)
        self.assertEqual(reach(tiles, self.layout["entry"][0]), tiles)

    def test_a_pod_off_on_its_own_is_joined_by_a_gangway(self):
        sensors = self.layout["rooms"]["room:sensors"]
        self.assertTrue(sensors & reach(walkable(self.layout), self.layout["entry"][0]))

    def test_rooms_are_walled_off_and_have_a_door(self):
        L = self.layout
        # The top wall of the cargo hold, where it meets the hallway, is bulkhead...
        row = [L["tiles"][2 * 3][x] for x in range(2 * 3 + 1, 4 * 3)]
        self.assertTrue(all(k in (D.WALL, D.DOOR) for k in row), row)
        # ...and every room has a doorway.
        for mark in ("room:crew-quarters", "room:impulse", "room:cargo"):
            tiles = L["rooms"][mark]
            self.assertTrue(any(n in L["doors"] for t in tiles
                                for n in ((t[0] + 1, t[1]), (t[0] - 1, t[1]),
                                          (t[0], t[1] + 1), (t[0], t[1] - 1))), mark)

    def test_a_system_gets_one_piece_of_kit_per_node(self):
        kit = [f for f in self.layout["furniture"] if f[3] is not None]
        impulse = sorted(f[3] for f in kit if f[0] == "prop:power_cell")
        self.assertEqual(impulse, [(4, 0), (4, 1), (5, 0), (5, 1)])

    def test_rooms_are_furnished_by_kind(self):
        sprites = {f[0] for f in self.layout["furniture"]}
        self.assertTrue(sprites & {"prop:bunk", "prop:desk", "prop:plant"})
        self.assertTrue(sprites & {"prop:crate", "prop:crate_wide", "prop:barrel"})

    def test_nothing_stands_in_or_beside_a_doorway(self):
        L = self.layout
        spots = {(x, y) for _, x, y, _ in L["furniture"]}
        for d in L["doors"]:
            self.assertFalse(spots & {d, (d[0] + 1, d[1]), (d[0] - 1, d[1]),
                                      (d[0], d[1] + 1), (d[0], d[1] - 1)}, d)

    def test_outside_the_ship_is_empty_but_for_a_rim_of_hull(self):
        L = self.layout
        self.assertIsNone(L["tiles"][L["h"] - 1][0])
        self.assertEqual(L["tiles"][0][0], D.HULL)

    def test_the_same_plan_always_gives_the_same_deck(self):
        again = D.boarding_deck_layout(D.boarding_deck_plan_ascii(PLAN))
        self.assertEqual(again["tiles"], self.layout["tiles"])
        self.assertEqual(again["furniture"], self.layout["furniture"])

    def test_a_mission_can_refurnish_a_kind_of_room(self):
        D.boarding_deck_kit("cargo", furniture=["prop:barrel"])
        L = D.boarding_deck_layout(self.plan)
        cargo = L["rooms"]["room:cargo"]
        self.assertEqual({f[0] for f in L["furniture"] if (f[1], f[2]) in cargo},
                         {"prop:barrel"})

    def test_the_text_is_an_area_file(self):
        rec = T.tilemap_parse(D.boarding_deck_text(self.layout, "deck_test"))
        self.assertEqual((rec["w"], rec["h"]), (self.layout["w"], self.layout["h"]))
        self.assertEqual(sorted(rec["marks"]["entry"]), sorted(self.layout["entry"]))


class TestBuild(unittest.TestCase):
    def setUp(self):
        mock_sbs.create_new_sim()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())
        self.addCleanup(setattr, FrameContext, "context", None)
        for clear in (T.tilemap_clear, T.tilemap_clear_tilesets, P.boarding_props_clear,
                      D.boarding_deck_clear):
            clear()
            self.addCleanup(clear)
        self.area = D.boarding_deck_build(D.boarding_deck_plan_ascii(PLAN), "deck_test",
                                          title="Test ship")

    def test_it_loads_an_area_with_rooms_marked(self):
        self.assertEqual(self.area, "deck_test")
        self.assertTrue(T.tilemap_mark_cells(self.area, "room:impulse"))
        self.assertTrue(T.tilemap_mark_cells(self.area, "room:hallway"))
        at = T.tilemap_entry(self.area)
        self.assertEqual(T.tilemap_mark_at(self.area, *at), "entry")

    def test_the_furniture_is_scenery_that_blocks(self):
        keys = P.boarding_props(self.area)
        self.assertTrue(keys)
        self.assertTrue(all(P.boarding_prop_is_scenery(k) for k in keys))
        where = T.tilemap_where(P.boarding_prop(keys[0])["id"])
        self.assertFalse(T.tilemap_is_open(self.area, where[1], where[2]))

    def test_a_system_node_knows_its_kit(self):
        key = D.boarding_deck_system_prop(self.area, (4, 0))
        self.assertEqual(P.boarding_prop(key)["sprite"], "prop:power_cell")
        self.assertTrue(D.boarding_deck_tiles_of(self.area, (4, 0)))


if __name__ == "__main__":
    unittest.main()
