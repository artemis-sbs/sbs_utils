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


# ==========================================================================================
# `Area: deck` and `Mark: <a kind of room>`: a writer's things aboard a ship nobody drew.
# ==========================================================================================

# A brig, two cabins, a hold and a hallway - and no lab.
DECK_PLAN = """ship: pirate_test
size: 8x6
legend:
  r: brig
  b: crew-berths / room,cabin,quarters
  c: captains-cabin / room,cabin,vip
  p: plunder-hold / room,bay,cargo
  i: impulse
---
 rr..bb
 rr..bb
 ....cc
 pp..cc
 pp..ii
 pp..ii
"""

DECK_WORLD = """# [Mission](mission)

## [Props](props)

### [Strongbox](strongbox)
---
Area: deck
Mark: brig
Sprite: prop:crate
Scene: box
Blocks: yes
---
Bolted to the deck.

### [Ledger](ledger)
---
Area: deck
Mark: brig
Sprite: prop:keycard
Item: ledger
---
A ledger.

### [Sample case](sample_case)
---
Area: deck
Mark: lab
Item: samples
---
A case.

### [Retort](retort)
---
Area: deck
Mark: lab
Item: retort
---
Glass.

### [Sea chest](chest)
---
Area: deck
Mark: room:captains-cabin
Blocks: yes
Scene: box
---
A chest.

### [Boarding ladder](ladder)
---
Area: deck
Mark: entry
---
A ladder.

### [Lamp](lamp)
---
Area: landing
Mark: lamp
---
A lamp ashore.

## [People](people)

### [The cook](cook)
---
Area: deck
Mark: cargo
Calm: yes
Talk scene: box
---
Sitting on a cask.

## [Hostiles](hostiles)

### [Hold-out](holdout)
---
Area: deck
Mark: quarters
HP: 2
Drops: cutlass
---
Will not strike his colors.

### [Second hold-out](holdout_2)
---
Area: deck
Mark: quarters
HP: 1
---
Nor will he.

## [Scenes](scenes)

### [The box](box)
% It is a box.

- [Leave it]()
"""


def _deck_doc():
    from sbs_utils.procedural.amd_doc import amd_document
    from sbs_utils.procedural.amd_mission import amd_mission_data
    return amd_document(DECK_WORLD, data_parser=amd_mission_data)


def _lib_grid_files():
    """LegendaryMissions' floor plans, beside this repo. Empty when it is not there."""
    import glob
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    return sorted(glob.glob(os.path.join(here, "..", "..", "LegendaryMissions", "races",
                                         "*.grid")))


class _DeckBase(unittest.TestCase):
    def setUp(self):
        from sbs_utils.procedural import boarding_combat as K
        from sbs_utils.procedural.amd_doc import amd_section
        mock_sbs.create_new_sim()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())
        self.addCleanup(setattr, FrameContext, "context", None)
        for clear in (T.tilemap_clear, T.tilemap_clear_tilesets, P.boarding_props_clear,
                      D.boarding_deck_clear, K.boarding_combat_clear):
            clear()
            self.addCleanup(clear)
        self.K = K
        self.doc = _deck_doc()
        P.boarding_props_declare(amd_section(self.doc, "props"))
        K.boarding_hostiles_declare(amd_section(self.doc, "people"))
        K.boarding_hostiles_declare(amd_section(self.doc, "hostiles"))
        P.boarding_props_place()
        K.boarding_hostiles_place()

    def build(self, plan=DECK_PLAN):
        import contextlib
        import io
        self.out = io.StringIO()
        with contextlib.redirect_stdout(self.out):
            area = D.boarding_deck_build(D.boarding_deck_plan_ascii(plan), D.DECK_AREA,
                                         title="Prize")
        return area

    def said(self, text):
        return [line for line in self.out.getvalue().splitlines() if text in line]

    def at(self, key):
        rec = P.boarding_prop(key) or self.K.boarding_hostile(key)
        where = T.tilemap_where(rec["id"]) if rec and rec["id"] is not None else None
        return (where[1], where[2]) if where else None


class TestKindMarks(_DeckBase):
    """A built deck has a mark per KIND of room, holding floor nothing stands on."""

    def test_every_kind_aboard_is_a_mark_of_free_floor(self):
        area = self.build()
        for kind in ("brig", "quarters", "cargo", "impulse", "hallway"):
            cells = T.tilemap_mark_cells(area, kind)
            self.assertTrue(cells, kind)
        kit = {(T.tilemap_where(P.boarding_prop(k)["id"])[1:])
               for k in P.boarding_props(area) if "_kit_" in k}
        for kind in ("brig", "quarters", "cargo", "impulse"):
            self.assertFalse(set(T.tilemap_mark_cells(area, kind)) & kit, kind)

    def test_two_rooms_of_one_kind_are_one_mark(self):
        area = self.build()
        berths = set(T.tilemap_mark_cells(area, "room:crew-berths"))
        cabin = set(T.tilemap_mark_cells(area, "room:captains-cabin"))
        quarters = set(T.tilemap_mark_cells(area, "quarters"))
        self.assertTrue(quarters & berths)
        self.assertTrue(quarters & cabin)
        self.assertLessEqual(quarters, berths | cabin)

    def test_the_room_marks_are_as_they_were(self):
        """Additive: a cell still answers with its room, and the entry with `entry`."""
        area = self.build()
        cell = T.tilemap_mark_cells(area, "brig")[0]
        self.assertEqual(T.tilemap_mark_at(area, *cell), "room:brig")
        self.assertEqual(T.tilemap_mark_at(area, *T.tilemap_entry(area)), "entry")

    def test_a_kind_the_hull_lacks_is_no_mark(self):
        area = self.build()
        self.assertEqual(T.tilemap_mark_cells(area, "lab"), [])

    def test_the_words_a_mark_takes(self):
        words = D.boarding_deck_mark_words()
        for word in ("brig", "cargo", "quarters", "bridge", "warp", "entry", "hallway"):
            self.assertIn(word, words)
        self.assertNotIn("brgi", words)


class TestSettle(_DeckBase):
    """`Area: deck` records get a room of their kind when a deck is built."""

    def test_nothing_is_anywhere_until_a_ship_is_boarded(self):
        for key in ("strongbox", "ledger", "cook", "holdout"):
            self.assertIsNone(self.at(key), key)

    def test_each_stands_in_a_room_of_its_kind(self):
        area = self.build()
        self.assertIn(self.at("strongbox"), T.tilemap_mark_cells(area, "room:brig"))
        self.assertIn(self.at("ledger"), T.tilemap_mark_cells(area, "room:brig"))
        self.assertIn(self.at("cook"), T.tilemap_mark_cells(area, "room:plunder-hold"))
        for key in ("holdout", "holdout_2"):
            self.assertIn(self.at(key), T.tilemap_mark_cells(area, "quarters"), key)

    def test_two_of_one_kind_get_two_cells(self):
        self.build()
        self.assertNotEqual(self.at("strongbox"), self.at("ledger"))
        self.assertNotEqual(self.at("holdout"), self.at("holdout_2"))

    def test_NOTHING_IS_STOOD_ON_THE_FURNITURE(self):
        area = self.build()
        kit = {T.tilemap_where(P.boarding_prop(k)["id"])[1:]
               for k in P.boarding_props(area) if P.boarding_prop(k).get("generated")
               and P.boarding_prop(k)["blocks"]}
        for key in ("strongbox", "ledger", "chest", "cook", "holdout", "holdout_2"):
            self.assertNotIn(self.at(key), kit, key)

    def test_a_room_named_outright_is_honored_on_the_hull_that_has_it(self):
        area = self.build()
        self.assertIn(self.at("chest"), T.tilemap_mark_cells(area, "room:captains-cabin"))
        self.assertEqual(self.said("chest"), [])

    def test_entry_is_beside_where_the_party_arrives_and_never_on_it(self):
        area = self.build()
        self.assertIn(self.at("ladder"), T.tilemap_mark_cells(area, "entry"))
        self.assertNotEqual(self.at("ladder"), T.tilemap_entry(area))

    def test_A_MISSING_KIND_IS_THE_HALLWAY_AND_ONE_LINE(self):
        """No lab aboard: both lab things stand in the hallway, and it is said ONCE."""
        area = self.build()
        halls = T.tilemap_mark_cells(area, "room:hallway")
        self.assertIn(self.at("sample_case"), halls)
        self.assertIn(self.at("retort"), halls)
        self.assertNotEqual(self.at("sample_case"), self.at("retort"))
        lines = self.said("no free 'lab'")
        self.assertEqual(len(lines), 1, self.out.getvalue())
        self.assertIn("Sample case", lines[0])
        self.assertIn("Retort", lines[0])
        self.assertIn("brig", lines[0])                      # what this hull does have

    def test_the_fallback_does_not_fail_a_headless_run(self):
        """It is not a mistake in anybody's files, so `mast.runtime` hears nothing."""
        import logging
        heard = []

        class Catch(logging.Handler):
            def emit(self, record):
                heard.append(record.getMessage())
        handler = Catch()
        logger = logging.getLogger("mast.runtime")
        logger.addHandler(handler)
        self.addCleanup(logger.removeHandler, handler)
        self.build()
        self.assertEqual(heard, [])

    def test_the_deck_is_still_one_walk(self):
        """Nothing that blocks was stood where it cuts a room off."""
        area = self.build()
        rec = D._DECKS[area]
        blocked = {c for c in rec["floor"] if not T.tilemap_is_open(area, *c)}
        start = T.tilemap_entry(area)
        self.assertEqual(D._reach(rec["floor"], blocked, start), rec["floor"] - blocked)

    def test_an_area_of_the_missions_own_is_untouched(self):
        self.build()
        self.assertEqual(P.boarding_prop("lamp")["at"], "lamp")
        self.assertNotIn("deck_mark", P.boarding_prop("lamp"))

    def test_settling_again_moves_nobody(self):
        area = self.build()
        before = {k: self.at(k) for k in ("strongbox", "ledger", "cook", "holdout")}
        self.assertEqual(D.boarding_deck_settle(area), {})
        self.assertEqual({k: self.at(k) for k in before}, before)

    def test_what_is_declared_after_the_deck_is_up_is_settled_too(self):
        area = self.build()
        P.boarding_props_declare({"children": [{
            "key": "late", "display_text": "Late", "description": "x",
            "data": {"area": "deck", "mark": "brig", "blocks": "yes"}}]})
        got = D.boarding_deck_settle(area)
        self.assertEqual(list(got), ["late"])
        self.assertIn(self.at("late"), T.tilemap_mark_cells(area, "room:brig"))
        self.assertNotIn(self.at("late"), (self.at("strongbox"), self.at("ledger")))

    def test_any_other_generated_deck_settles_nothing(self):
        """`deck_<ship id>` (boarding_deck_for) is not `Area: deck`."""
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            D.boarding_deck_build(D.boarding_deck_plan_ascii(DECK_PLAN), "deck_77")
        self.assertIsNone(self.at("strongbox"))
        self.assertEqual(D._DECKS["deck_77"]["settled"], {})

    def test_the_ships_own_crew_stands_on_nothing_a_writer_put_down(self):
        area = self.build()
        mine = {self.at(k) for k in ("strongbox", "ledger", "sample_case", "retort",
                                     "chest", "ladder", "cook", "holdout", "holdout_2")}
        keys = D.boarding_deck_crew(area, hostile=False, count=12)
        self.assertTrue(keys)
        for k in keys:
            self.assertNotIn(self.at(k), mine, k)


class TestRelease(_DeckBase):
    """The party leaves: the deck goes, a writer's records wait for the next ship."""

    def test_the_deck_and_everything_generated_is_gone(self):
        area = self.build()
        crew = D.boarding_deck_crew(area, hostile=False, count=3)
        self.assertTrue(D.boarding_deck_release(area))
        self.assertIsNone(T.tilemap_area(area))
        self.assertFalse(D.boarding_deck_built(area))
        self.assertEqual([k for k in P._PROPS if P._PROPS[k].get("generated")], [])
        for key in crew:
            self.assertIsNone(self.K.boarding_hostile(key))
        self.assertFalse(D.boarding_deck_release(area))          # nothing left to take down

    def test_a_writers_records_are_kept_and_wait_again(self):
        area = self.build()
        D.boarding_deck_release(area)
        for key, word in (("strongbox", "brig"), ("ledger", "brig"), ("sample_case", "lab")):
            rec = P.boarding_prop(key)
            self.assertIsNotNone(rec, key)
            self.assertIsNone(rec["id"])
            self.assertEqual(rec["at"], word)
        self.assertEqual(self.K.boarding_hostile("holdout")["at"], "quarters")
        self.assertIsNone(self.K.boarding_hostile("holdout")["id"])

    def test_the_next_ship_is_settled_afresh(self):
        self.build()
        D.boarding_deck_release(D.DECK_AREA)
        # A hull with a lab and no brig.
        area = self.build("ship: other\nsize: 6x3\nlegend:\n  l: lab / room,lab\n"
                          "  q: crew-quarters\n"
                          "---\nll..qq\nll..qq\n......\n")
        self.assertIn(self.at("sample_case"), T.tilemap_mark_cells(area, "room:lab"))
        self.assertIn(self.at("strongbox"), T.tilemap_mark_cells(area, "room:hallway"))
        self.assertEqual(len(self.said("no free 'brig'")), 1)

    def test_what_was_taken_or_put_down_stays_so(self):
        area = self.build()
        P.boarding_prop("ledger")["taken"] = True
        P.boarding_prop_remove("ledger")
        self.K._hostile_hit(self.K.boarding_hostile("holdout"), "full")
        D.boarding_deck_release(area)
        self.build()
        self.assertIsNone(self.at("ledger"))
        self.assertIsNone(self.at("holdout"))
        self.assertIsNotNone(self.at("holdout_2"))

    def test_what_a_holdout_dropped_does_not_follow_to_the_next_ship(self):
        area = self.build()
        self.K._hostile_hit(self.K.boarding_hostile("holdout"), "full")
        self.assertIsNotNone(P.boarding_prop("drop_holdout_0"))
        D.boarding_deck_release(area)
        self.assertIsNone(P.boarding_prop("drop_holdout_0"))


class TestGeneratedStaysOutOfSaves(_DeckBase):
    """A boarded ship's furniture, doors and crew are nobody's to save."""

    def snapshot(self):
        import json
        return json.dumps({"props": P._props_snapshot(),
                           "hostiles": self.K._hostiles_snapshot()}, sort_keys=True)

    def test_a_deck_and_its_crowd_add_nothing(self):
        before = self.snapshot()
        area = self.build()
        crew = D.boarding_deck_crew(area, hostile=True, count=6)
        self.assertEqual(self.snapshot(), before)
        for key in crew:                                         # every one of them shot
            self.K._hostile_hit(self.K.boarding_hostile(key), "full")
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.snapshot(), '{"hostiles": {}, "props": {}}')

    def test_a_writers_holdout_and_strongbox_are_still_kept(self):
        area = self.build()
        D.boarding_deck_crew(area, hostile=False, count=3)
        self.K._hostile_hit(self.K.boarding_hostile("holdout"), "full")
        P.boarding_prop("ledger")["taken"] = True
        self.assertEqual(self.K._hostiles_snapshot(), {"down": ["holdout"]})
        self.assertEqual(P._props_snapshot(), {"taken": ["ledger"]})

    def test_a_save_that_names_a_generated_key_does_not_fell_the_next_crowd(self):
        """An older save, or a hand-edited one: `deck_crew_0` down means nothing here."""
        self.K._hostiles_restore({"down": ["deck_crew_0", "holdout"]})
        area = self.build()
        keys = D.boarding_deck_crew(area, hostile=False, count=3)
        self.assertIn("deck_crew_0", keys)
        self.assertIsNotNone(self.at("deck_crew_0"))
        self.assertIsNone(self.at("holdout"))                    # a writer's: honored


class TestPlanSource(unittest.TestCase):
    """Where a live ship's hallways come from - and saying which."""

    GRID = ("ship: tsn_light_cruiser\nsize: 5x3\nlegend:\n  i: impulse\n  c: cargo\n"
            "---\ni...c\n.....\nc...i\n")

    def setUp(self):
        from tests.reset_helper import reset_mock
        from sbs_utils.procedural.internal_damage import grid_interior_reset
        from sbs_utils.procedural.grid import grid_merge_ascii
        from sbs_utils.procedural.query import to_id
        from sbs_utils.procedural.spawn import npc_spawn
        reset_mock(mock_sbs)
        grid_interior_reset()
        for clear in (T.tilemap_clear, T.tilemap_clear_tilesets, P.boarding_props_clear,
                      D.boarding_deck_clear):
            clear()
            self.addCleanup(clear)
        grid_merge_ascii(self.GRID, "test")
        self.ship = to_id(npc_spawn(0, 0, 0, "Prize", "raider", "tsn_light_cruiser",
                                    "behav_npcship"))

    def no_hull_map(self, value=None):
        real = mock_sbs.get_hull_map
        mock_sbs.get_hull_map = lambda *a, **k: value
        self.addCleanup(setattr, mock_sbs, "get_hull_map", real)

    def test_the_text_keeps_its_hallways(self):
        from sbs_utils.procedural.grid import grid_get_open_cells
        got = grid_get_open_cells("tsn_light_cruiser")
        self.assertEqual((got["w"], got["h"]), (5, 3))
        self.assertIn([1, 0], got["hallways"])
        self.assertEqual(len(got["hallways"]), 11)
        self.assertIsNone(grid_get_open_cells("no_such_hull"))

    def test_a_hull_map_is_used_when_the_engine_has_one(self):
        plan = D.boarding_deck_plan(self.ship)
        self.assertEqual(plan["source"], "hull map")

    def test_NO_HULL_MAP_IS_PLANNED_FROM_THE_GRID_TEXT(self):
        self.no_hull_map(None)
        plan = D.boarding_deck_plan(self.ship)
        self.assertEqual(plan["source"], "grid text")
        self.assertEqual(plan["cells"][(1, 0)], "")
        self.assertEqual(plan["cells"][(0, 0)], "impulse")
        self.assertEqual(len(plan["cells"]), 15)
        self.assertEqual((plan["w"], plan["h"]), (5, 3))

    def test_a_hull_map_with_nothing_open_is_no_hull_map(self):
        class Shut:
            w, h = 5, 3

            def is_grid_point_open(self, x, y):
                return False
        self.no_hull_map(Shut())
        self.assertEqual(D.boarding_deck_plan(self.ship)["source"], "grid text")

    def test_neither_is_the_rooms_alone(self):
        """The engine's own grid data: rooms, and no text to say where the halls ran."""
        from sbs_utils.procedural.grid import grid_get_grid_data, GRID_DATA_OPEN_KEY
        grid_get_grid_data()["tsn_light_cruiser"].pop(GRID_DATA_OPEN_KEY)
        self.no_hull_map(None)
        plan = D.boarding_deck_plan(self.ship)
        self.assertEqual(plan["source"], "rooms only")
        self.assertEqual(len(plan["cells"]), 4)
        # ...and it still builds one walk, by gangway.
        layout = D.boarding_deck_layout(plan)
        tiles = walkable(layout)
        self.assertEqual(reach(tiles, layout["entry"][0]), tiles)

    def test_a_hull_key_has_no_hull_map_and_reads_the_text(self):
        self.assertEqual(D.boarding_deck_plan("tsn_light_cruiser")["source"], "grid text")


@unittest.skipUnless(_lib_grid_files(), "LegendaryMissions is not beside this repo")
class TestEveryShippedPlan(unittest.TestCase):
    """Every floor plan LegendaryMissions ships, built as `Area: deck` and settled."""

    def setUp(self):
        from sbs_utils.procedural import boarding_combat as K
        mock_sbs.create_new_sim()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())
        self.addCleanup(setattr, FrameContext, "context", None)
        self.K = K
        self.clears = (T.tilemap_clear, T.tilemap_clear_tilesets, P.boarding_props_clear,
                       D.boarding_deck_clear, K.boarding_combat_clear)
        for clear in self.clears:
            clear()
            self.addCleanup(clear)

    def build(self, path):
        for clear in self.clears:
            clear()
        with open(path, encoding="utf-8") as f:
            plan = D.boarding_deck_plan_ascii(f.read())
        area = D.boarding_deck_build(plan, D.DECK_AREA)
        present = {D.boarding_deck_room_kind(name) for name in plan["cells"].values()}
        return plan, area, sorted(present)

    def stand(self, area, records, place=False):
        """Declare props, settle them, and hand back ``({key: cell}, what was said)``."""
        import contextlib
        import io
        P.boarding_props_declare({"children": [
            {"key": key, "display_text": key, "description": "x",
             "data": {"area": "deck", "mark": mark, "blocks": "yes" if blocks else "no"}}
            for key, mark, blocks in records]})
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            got = D.boarding_deck_settle(area, place=place)
        return got, out.getvalue()

    def lift(self, area, keys):
        for key in keys:
            P.boarding_prop_forget(key)
            D._DECKS[area]["settled"].pop(key, None)
        D._DECKS[area]["fallbacks"].clear()

    def test_every_kind_aboard_has_a_free_cell_and_two_of_a_kind_get_two(self):
        files = _lib_grid_files()
        self.assertGreater(len(files), 60)
        for path in files:
            name = path.replace("\\", "/").rsplit("/", 1)[-1]
            with self.subTest(plan=name):
                plan, area, present = self.build(path)
                self.assertIsNotNone(area)
                rec = D._DECKS[area]
                start = T.tilemap_entry(area)
                for kind in present:
                    free = set(T.tilemap_mark_cells(area, kind)) - {start}
                    self.assertTrue(free, (kind, "a kind aboard with nowhere to stand"))
                    clear = D._reach(rec["floor"], set(), start)
                    # Two things that do not block: two cells of that kind of room.
                    got, said = self.stand(area, [("a", kind, False), ("b", kind, False)])
                    self.assertEqual(sorted(got), ["a", "b"], (kind, said))
                    self.assertNotEqual(got["a"], got["b"], kind)
                    self.assertIn(got["a"], free, kind)
                    if len(free) > 1:
                        self.assertIn(got["b"], free, kind)
                        self.assertEqual(said, "", kind)
                    else:
                        self.assertIn("no free '%s'" % kind, said, kind)
                    self.lift(area, ["a", "b"])
                    # Two that BLOCK. A room with a way through it and one tile to spare
                    # cannot take one: that one is in the hallway, it is said, and the
                    # deck is never cut either way.
                    got, said = self.stand(area, [("a", kind, True), ("b", kind, True)])
                    self.assertEqual(sorted(got), ["a", "b"], (kind, said))
                    self.assertNotEqual(got["a"], got["b"], kind)
                    for key in ("a", "b"):
                        if got[key] not in free:
                            self.assertIn("no free '%s'" % kind, said, (kind, key))
                    self.assertEqual(D._reach(rec["floor"], set(got.values()), start),
                                     clear - set(got.values()), kind)
                    self.lift(area, ["a", "b"])

    def test_a_kind_no_hull_has_is_the_hallway_and_one_line(self):
        for path in _lib_grid_files():
            name = path.replace("\\", "/").rsplit("/", 1)[-1]
            with self.subTest(plan=name):
                plan, area, present = self.build(path)
                got, said = self.stand(area, [("a", "orangery", True),
                                              ("b", "orangery", False)])
                self.assertEqual(sorted(got), ["a", "b"])
                self.assertNotEqual(got["a"], got["b"])
                halls = set(T.tilemap_mark_cells(area, "hallway"))
                if halls:
                    self.assertIn(got["a"], halls)
                    self.assertIn(got["b"], halls)
                else:
                    # A fighter is one cabin with no hallway at all: any floor will do.
                    self.assertIn(got["a"], D._DECKS[area]["floor"])
                self.assertEqual(said.count("'orangery' is not a kind of room"), 1, said)
                self.assertEqual(len(said.strip().splitlines()), 1, said)

    def test_one_thing_in_every_room_at_once_and_the_deck_is_still_one_walk(self):
        for path in _lib_grid_files():
            name = path.replace("\\", "/").rsplit("/", 1)[-1]
            with self.subTest(plan=name):
                plan, area, present = self.build(path)
                got, said = self.stand(area, [(f"p_{k}", k, True) for k in present],
                                       place=True)
                self.assertEqual(len(got), len(present), said)
                self.assertEqual(len(set(got.values())), len(got))
                rec = D._DECKS[area]
                kit = {T.tilemap_where(r["id"])[1:] for r in P._PROPS.values()
                       if r.get("generated") and r["blocks"] and r["id"] is not None}
                for key, cell in got.items():
                    self.assertIsNotNone(P.boarding_prop(key)["id"], key)
                    self.assertNotIn(cell, kit, key)
                blocked = {c for c in rec["floor"] if not T.tilemap_is_open(area, *c)}
                start = T.tilemap_entry(area)
                self.assertEqual(D._reach(rec["floor"], blocked, start),
                                 rec["floor"] - blocked)

    def test_the_brigantine_has_the_rooms_the_lecture_boards(self):
        path = next(p for p in _lib_grid_files() if p.endswith("pirate_brigantine.grid"))
        plan, area, present = self.build(path)
        for kind in ("brig", "quarters", "cargo", "sickbay", "bay", "hallway"):
            self.assertIn(kind, present)
        self.assertTrue(T.tilemap_mark_cells(area, "room:captains-cabin"))


if __name__ == "__main__":
    unittest.main()
