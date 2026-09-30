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

    def test_A_BIG_PIECE_FITS_ITS_ROOM_AND_NEVER_CUTS_THE_DECK(self):
        """A crate three tiles wide covers three tiles: all of them in its room, none by
        a door, and the deck still one walk with every one of them taken out."""
        from sbs_utils.procedural import tilemap_art as TA
        TA.tilemap_sprite_base("prop:crate_wide", (-1.3, -0.3, 1.3, 0.3))
        self.addCleanup(TA.tilemap_art_clear)
        D.boarding_deck_kit("cargo", furniture=["prop:crate_wide"])
        L = D.boarding_deck_layout(self.plan)
        cargo = L["rooms"]["room:cargo"]
        wide = [f for f in L["furniture"] if f[0] == "prop:crate_wide"]
        self.assertTrue(wide)
        near_door = {n for d in L["doors"] for n in ((d[0] + 1, d[1]), (d[0] - 1, d[1]),
                                                    (d[0], d[1] + 1), (d[0], d[1] - 1))}
        taken = set()
        for sprite, x, y, _ in L["furniture"]:
            foot = {(x + dx, y + dy) for dx, dy in TA.tilemap_sprite_cells(sprite)}
            if sprite == "prop:crate_wide":
                self.assertEqual(len(foot), 3)
                self.assertLessEqual(foot, cargo)
            self.assertFalse(foot & (L["doors"] | near_door), (sprite, x, y))
            taken |= foot
        tiles = walkable(L) - taken
        self.assertEqual(reach(tiles, L["entry"][0]), tiles)

    def test_the_text_is_an_area_file(self):
        rec = T.tilemap_parse(D.boarding_deck_text(self.layout, "deck_test"))
        self.assertEqual((rec["w"], rec["h"]), (self.layout["w"], self.layout["h"]))
        self.assertEqual(sorted(rec["marks"]["entry"]), sorted(self.layout["entry"]))


class TestDeckPreview(unittest.TestCase):
    """What `sbs site` draws a ship deck from: the deck the game builds, as preview data -
    its tiles, its rooms as marks, its furniture and doors as props."""

    def setUp(self):
        self.addCleanup(D.boarding_deck_clear)
        from sbs_utils.procedural.tilemap_preview import tilemap_preview_deck
        self.got = tilemap_preview_deck(PLAN)
        self.layout = D.boarding_deck_layout(D.boarding_deck_plan_ascii(PLAN))

    def test_it_is_the_deck_the_game_lays_out(self):
        self.assertTrue(self.got["ok"], self.got.get("error"))
        self.assertEqual(self.got["ship"], "test_ship")
        self.assertEqual((self.got["area"]["w"], self.got["area"]["h"]),
                         (self.layout["w"], self.layout["h"]))
        self.assertEqual(self.got["tiles"], self.layout["tiles"])

    def test_its_furniture_and_doors_stand_where_the_game_puts_them(self):
        props = sorted((p["sprite"], p["cell"][0], p["cell"][1])
                       for p in self.got["placements"] if p["display"] != "door")
        self.assertEqual(props, sorted((s, x, y) for s, x, y, _ in self.layout["furniture"]))
        doors = sorted(tuple(p["cell"]) for p in self.got["placements"]
                       if p["display"] == "door")
        self.assertEqual(doors, sorted(self.layout["doors"]))
        self.assertTrue(all(p["kind"] == "prop" for p in self.got["placements"]))

    def test_its_rooms_are_marks_and_the_hallway_is_not(self):
        marks = self.got["marks"]
        self.assertIn("room:crew-quarters", marks)
        self.assertIn("entry", marks)
        self.assertNotIn("room:hallway", marks)
        self.assertNotIn("door", marks)

    def test_a_plan_with_nothing_open_says_so(self):
        from sbs_utils.procedural.tilemap_preview import tilemap_preview_deck
        got = tilemap_preview_deck("ship: empty\nsize: 2x2\nlegend:\n  q: crew-quarters\n---\n")
        self.assertFalse(got["ok"])


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
        kit = next(k for k in keys if "_kit_" in k)
        where = T.tilemap_where(P.boarding_prop(kit)["id"])
        self.assertFalse(T.tilemap_is_open(self.area, where[1], where[2]))

    def test_every_doorway_has_a_door_drawn_the_way_its_wall_runs(self):
        doors = D._DECKS[self.area]["doors"]
        self.assertEqual(set(doors), set(T.tilemap_mark_cells(self.area, "door")))
        sides = {side for _, side in doors.values()}
        self.assertEqual(sides, {"front", "side"})
        for tile, (key, side) in doors.items():
            self.assertEqual(P.boarding_prop(key)["sprite"], D.DOOR_SPRITES[side][0])
            self.assertTrue(T.tilemap_is_open(self.area, *tile))    # a door never blocks

    def test_a_door_slides_open_for_someone_beside_it_and_shuts_behind_them(self):
        tile, (key, side) = sorted(D._DECKS[self.area]["doors"].items())[0]
        T.tilemap_place(9001, self.area, tile[0], tile[1] + 1, sprite="fig:crew_m")
        D.boarding_deck_animate_step(self.area)
        actor = T.tilemap_actor(P.boarding_prop(key)["id"])
        self.assertEqual(actor["sprite"], D.DOOR_SPRITES[side][1])
        T.tilemap_remove(9001)
        D.boarding_deck_animate_step(self.area)
        self.assertEqual(actor["sprite"], D.DOOR_SPRITES[side][0])

    def test_a_system_node_knows_its_kit(self):
        key = D.boarding_deck_system_prop(self.area, (4, 0))
        self.assertEqual(P.boarding_prop(key)["sprite"], "prop:power_cell")
        self.assertTrue(D.boarding_deck_tiles_of(self.area, (4, 0)))


class TestTheShipsCrew(unittest.TestCase):
    """A boarded ship's own crew: guards who fight, hands who keep out of it."""

    def setUp(self):
        from sbs_utils.procedural import boarding_combat as K
        mock_sbs.create_new_sim()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())
        self.addCleanup(setattr, FrameContext, "context", None)
        for clear in (T.tilemap_clear, T.tilemap_clear_tilesets, P.boarding_props_clear,
                      D.boarding_deck_clear, K.boarding_combat_clear):
            clear()
            self.addCleanup(clear)
        self.K = K
        self.area = D.boarding_deck_build(D.boarding_deck_plan_ascii(PLAN), "deck_crew")

    def test_aboard_an_enemy_three_in_five_are_guards_in_the_hallways(self):
        keys = D.boarding_deck_crew(self.area, hostile=True, count=5)
        self.assertEqual(len(keys), 5)
        recs = [self.K.boarding_hostile(k) for k in keys]
        guards = [r for r in recs if not r["calm"]]
        hands = [r for r in recs if r["calm"]]
        self.assertEqual((len(guards), len(hands)), (3, 2))
        halls = set(T.tilemap_mark_cells(self.area, "room:hallway"))
        for g in guards:
            at = T.tilemap_where(g["id"])
            self.assertIn((at[1], at[2]), halls)
            self.assertEqual(len(g["patrol"]), 2)
        for h in hands:
            at = T.tilemap_where(h["id"])
            self.assertNotIn((at[1], at[2]), halls)
            self.assertEqual(h["state"], "calm")

    def test_aboard_any_other_ship_nobody_fights(self):
        keys = D.boarding_deck_crew(self.area, hostile=False, count=4)
        self.assertTrue(all(self.K.boarding_hostile(k)["calm"] for k in keys))

    def test_the_crew_is_drawn_as_the_ships_race_and_stays_off_doors_and_the_entry(self):
        D._DECKS[self.area]["ship"] = "kralien_cruiser"
        keys = D.boarding_deck_crew(self.area, hostile=True, count=6)
        sprites = {self.K.boarding_hostile(k)["sprite"] for k in keys}
        self.assertTrue(sprites <= set(D.RACE_CREWS["kralien"]))
        avoid = set(T.tilemap_mark_cells(self.area, "entry")) | \
            set(T.tilemap_mark_cells(self.area, "door"))
        for k in keys:
            at = T.tilemap_where(self.K.boarding_hostile(k)["id"])
            self.assertNotIn((at[1], at[2]), avoid)

    def test_hands_can_be_talked_to_with_the_missions_scene(self):
        keys = D.boarding_deck_crew(self.area, hostile=False, count=2, talk_scene="crew_talk")
        self.assertEqual({self.K.boarding_hostile(k)["talk"] for k in keys}, {"crew_talk"})

    def test_the_same_deck_gets_the_same_crew(self):
        keys = D.boarding_deck_crew(self.area, hostile=True, count=4)
        first = [T.tilemap_where(self.K.boarding_hostile(k)["id"]) for k in keys]
        for k in keys:
            T.tilemap_remove(self.K.boarding_hostile(k)["id"])
        self.K.boarding_combat_clear()
        again = [T.tilemap_where(self.K.boarding_hostile(k)["id"])
                 for k in D.boarding_deck_crew(self.area, hostile=True, count=4)]
        self.assertEqual(first, again)


class TestTheLiveShip(unittest.TestCase):
    """The deck follows its ship: damage shows, repair teams walk."""

    SHIP = 555

    def setUp(self):
        mock_sbs.create_new_sim()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())
        self.addCleanup(setattr, FrameContext, "context", None)
        for clear in (T.tilemap_clear, T.tilemap_clear_tilesets, P.boarding_props_clear,
                      D.boarding_deck_clear):
            clear()
            self.addCleanup(clear)
        self.area = D.boarding_deck_build(D.boarding_deck_plan_ascii(PLAN), "deck_live")
        self.state = []
        real = D._grid_state
        D._grid_state = lambda ship: list(self.state)
        self.addCleanup(setattr, D, "_grid_state", real)
        T.tilemap_set_clock(0.0)
        self.addCleanup(T.tilemap_set_clock, None)

    def kit(self, cell):
        return P.boarding_prop(D.boarding_deck_system_prop(self.area, cell))

    def test_a_damaged_node_goes_dark_with_rubble_and_comes_back_repaired(self):
        self.state = [(901, 4, 0, True, False, None)]
        self.assertTrue(D.boarding_deck_sync(self.area, self.SHIP))
        self.assertEqual(self.kit((4, 0))["color"], D.DAMAGED_TINT)
        rubble = [k for k in P.boarding_props(self.area) if "_rubble_" in k]
        self.assertEqual(len(rubble), 1)
        self.assertEqual(P.boarding_prop(rubble[0])["sprite"], "prop:debris_pile")
        self.assertTrue(P.boarding_prop_is_scenery(rubble[0]))
        self.state = [(901, 4, 0, False, False, None)]
        D.boarding_deck_sync(self.area, self.SHIP)
        self.assertIsNone(self.kit((4, 0))["color"])
        self.assertFalse([k for k in P.boarding_props(self.area) if "_rubble_" in k])

    def test_a_damaged_system_throws_sparks_that_flicker_until_repaired(self):
        self.state = [(901, 4, 0, True, False, None)]
        D.boarding_deck_sync(self.area, self.SHIP)
        key = D._DECKS[self.area]["sparks"][(4, 0)]
        actor = T.tilemap_actor(P.boarding_prop(key)["id"])
        seen = set()
        for _ in range(4):
            D.boarding_deck_animate_step(self.area)
            seen.add(actor["sprite"])
        self.assertEqual(seen, set(D.SPARKS))
        self.state = [(901, 4, 0, False, False, None)]
        D.boarding_deck_sync(self.area, self.SHIP)
        self.assertIsNone(P.boarding_prop(key))
        self.assertNotIn(key, D._DECKS[self.area]["flicker"])

    def test_a_damaged_room_that_is_not_a_system_burns(self):
        self.state = [(902, 0, 0, True, False, None)]            # crew quarters
        D.boarding_deck_sync(self.area, self.SHIP)
        key = D._DECKS[self.area]["sparks"][(0, 0)]
        self.assertEqual(P.boarding_prop(key)["sprite"], D.FIRE[0])
        self.assertEqual(D._DECKS[self.area]["flicker"][key], D.FIRE)

    def test_nothing_changes_when_nothing_did(self):
        self.state = [(901, 4, 0, True, False, None)]
        D.boarding_deck_sync(self.area, self.SHIP)
        self.assertEqual(D.boarding_deck_sync(self.area, self.SHIP), 0)

    def test_a_repair_team_stands_where_engineering_has_it_and_walks_when_it_moves(self):
        self.state = [(950, 0, 0, False, True, 6)]
        D.boarding_deck_sync(self.area, self.SHIP)
        at = T.tilemap_where(950)
        self.assertIn((at[1], at[2]), D.boarding_deck_tiles_of(self.area, (0, 0)))
        self.state = [(950, 3, 2, False, True, 6)]
        D.boarding_deck_sync(self.area, self.SHIP)
        self.assertTrue(T.tilemap_walking(950))

    def test_a_ships_teams_are_drawn_as_its_race(self):
        self.assertEqual(D.boarding_deck_race("kralien_cruiser"), "kralien")
        self.assertEqual(D.boarding_deck_race("xim_scout"), "ximni")
        self.assertEqual(D.boarding_deck_race("tsn_light_cruiser"), "human")
        self.assertEqual(D.boarding_deck_race("mystery_hull"), "human")
        self.assertEqual(D.boarding_deck_race("starbase_torgoth"), "torgoth")
        self.assertEqual(D.boarding_deck_race("starbase_civil"), "human")
        D._DECKS[self.area]["ship"] = "torgoth_goliath"
        self.state = [(950, 0, 0, False, True, 6)]
        D.boarding_deck_sync(self.area, self.SHIP)
        self.assertEqual(T.tilemap_actor(950)["sprite"], "fig:torgoth")

    def test_a_team_at_zero_hp_is_down_and_a_team_that_is_gone_leaves(self):
        self.state = [(950, 0, 0, False, True, 0)]
        D.boarding_deck_sync(self.area, self.SHIP)
        self.assertEqual(T.tilemap_actor(950)["pose"], "down")
        self.state = []
        D.boarding_deck_sync(self.area, self.SHIP)
        self.assertIsNone(T.tilemap_where(950))


class TestAMockShip(unittest.TestCase):
    """End to end on the mock: a real ship's interior, read and built into a deck."""

    def setUp(self):
        from tests.reset_helper import reset_mock
        from sbs_utils.procedural.internal_damage import grid_interior_reset
        from sbs_utils.procedural.grid import grid_merge_ascii
        reset_mock(mock_sbs)
        grid_interior_reset()
        for clear in (T.tilemap_clear, T.tilemap_clear_tilesets, P.boarding_props_clear,
                      D.boarding_deck_clear):
            clear()
            self.addCleanup(clear)
        grid_merge_ascii("ship: tsn_light_cruiser\nsize: 3x2\nlegend:\n  i: impulse\n"
                         "  c: cargo\n---\nici\nccc", "test")

    def test_the_ship_is_read_built_and_its_damage_shown(self):
        from sbs_utils.procedural.internal_damage import grid_rebuild_grid_objects
        from sbs_utils.procedural.grid import grid_objects
        from sbs_utils.procedural.query import to_id
        from sbs_utils.procedural.roles import add_role
        from sbs_utils.procedural.spawn import player_spawn
        ship = to_id(player_spawn(0, 0, 0, "Probe", "tsn", "tsn_light_cruiser"))
        grid_rebuild_grid_objects(ship)
        plan = D.boarding_deck_plan(ship)
        self.assertEqual(plan["cells"][(0, 0)], "impulse")
        area = D.boarding_deck_build(plan, "probe_deck")
        self.assertIsNotNone(D.boarding_deck_system_prop(area, (0, 0)))
        state = D._grid_state(ship)
        node = next(g for g, x, y, _, damcon, _ in state if (x, y) == (0, 0) and not damcon)
        add_role(node, "__damaged__")
        D.boarding_deck_sync(area, ship)
        kit = P.boarding_prop(D.boarding_deck_system_prop(area, (0, 0)))
        self.assertEqual(kit["color"], D.DAMAGED_TINT)
        self.assertTrue(grid_objects(ship))

    def test_an_interior_builds_when_the_damcon_prefab_is_missing(self):
        """Under a running story a missing prefab label RAISES (the mock returns None);
        it used to take the whole interior build - and the deck - down with it."""
        from sbs_utils.procedural import internal_damage as ID
        from sbs_utils.procedural.grid import grid_objects
        from sbs_utils.procedural.query import to_id
        from sbs_utils.procedural.spawn import player_spawn

        def missing(*a, **k):
            raise Exception("Calling undefined label prefab_lifeform_damcons")
        real = ID.prefab_spawn
        ID.prefab_spawn = missing
        self.addCleanup(setattr, ID, "prefab_spawn", real)
        ship = to_id(player_spawn(0, 0, 0, "Probe", "tsn", "tsn_light_cruiser"))
        ID.grid_rebuild_grid_objects(ship)
        self.assertTrue(grid_objects(ship))
        self.assertIsNotNone(D.boarding_deck_for(ship))

    def test_a_ships_deck_is_built_once_and_watched(self):
        from sbs_utils.procedural.internal_damage import grid_rebuild_grid_objects
        from sbs_utils.procedural.query import to_id
        from sbs_utils.procedural.spawn import player_spawn
        ship = to_id(player_spawn(0, 0, 0, "Probe", "tsn", "tsn_light_cruiser"))
        grid_rebuild_grid_objects(ship)
        deck = D.boarding_deck_for(ship, title="Probe")
        self.assertEqual(deck, f"deck_{ship}")
        self.assertEqual(T.tilemap_title(deck), "Probe")
        self.assertIsNotNone(D._DECKS[deck]["watch"])
        props = len(P.boarding_props(deck))
        self.assertEqual(D.boarding_deck_for(ship), deck)        # not built again
        self.assertEqual(len(P.boarding_props(deck)), props)


if __name__ == "__main__":
    unittest.main()
