"""`boarding_deck_visit`: a party sent aboard a ship, on a deck drawn from its own plan.

The deck generator could draw any hull's interior as a tile map, and no mission called
it: there was no way to say where a writer's things go on a ship nobody has drawn, no way
to open a party onto it, nothing that held the ship still, and nothing that took the deck
down again. This is that - one call - and what is asserted is the WORLD it leaves: a
party standing on the prize's own deck, the strongbox in her brig, her crew calm about
it, and nothing left behind when they go home.

A writer's side of it is two lines of AMD - `Area: deck` and `Mark: brig` - read here by
the game's own reader and loaded with the call a story makes (`boarding_ground_load`).

    python -m unittest tests.test_boarding_deck_visit
"""
import contextlib
import io
import json
import logging
import os
import shutil
import tempfile
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  (import first: circular import)
from cosmos_dev.mock import sbs as sbs
from tests.reset_helper import reset_mock

from sbs_utils.gui import GuiClient
from sbs_utils.handlerhooks import reset_mission_state, reset_mission_audit
from sbs_utils.mast.mast_globals import MastGlobals
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.procedural import boarding as A
from sbs_utils.procedural import boarding_combat as K
from sbs_utils.procedural import boarding_deckplan as D
from sbs_utils.procedural import boarding_ground as BG
from sbs_utils.procedural import boarding_props as P
from sbs_utils.procedural import crew
from sbs_utils.procedural import tilemap as T
from sbs_utils.procedural import tilemap_art as TA
from sbs_utils.procedural.amd_mission import amd_mission_data
from sbs_utils.procedural.grid import grid_merge_ascii
from sbs_utils.procedural.gui import boarding_gui as G
from sbs_utils.procedural.gui.image import ImageAtlas
from sbs_utils.procedural.internal_damage import grid_interior_reset
from sbs_utils.procedural.inventory import set_inventory_value
from sbs_utils.procedural.links import link
from sbs_utils.procedural.query import to_id, to_object
from sbs_utils.procedural.quest import document_get_amd_file
from sbs_utils.procedural.roles import has_role
from sbs_utils.procedural.settings import settings_get_defaults
from sbs_utils.procedural.sides import side_ensure, side_surrender
from sbs_utils.procedural.signal import signal_emit, signal_observe, signal_unobserve
from sbs_utils.procedural.space_objects import delete_object
from sbs_utils.procedural.spawn import npc_spawn, player_spawn

HELM = 0x8000000000000001
SCI = 0x8000000000000002

# LegendaryMissions' `races/pirate_brigantine.grid`, as shipped.
BRIGANTINE = """ship: pirate_brigantine
layout: default
size: 12x12
legend:
  g: gun-deck / system,weapon,beam
  t: tube-deck / system,weapon,torpedo
  f: fwd-shield
  a: aft-shield
  s: sensors
  b: crew-berths / room,cabin,quarters
  c: captains-cabin / room,cabin,vip
  y: surgery / room,med,sickbay
  r: brig
  m: maneuver
  p: plunder-hold / room,bay,cargo
  i: impulse
  w: warp
  o: boat-bay / room,bay,shuttle
---



     gg
     tt
    fssf
    bccb
   by..yb
   mr..rm
  pp....pp
  app..ppa
 wwiigoiiww
"""

# A hull with a lab and no brig.
SURVEYOR = """ship: science_ship
layout: default
size: 6x3
legend:
  l: science-lab / room,lab
  q: crew-quarters
---
ll..qq
ll..qq
......
"""

# A mission with ground of its own AND things aboard whatever is boarded.
TILESET = """tileset: dv_yard
kinds:
  dirt:   walk see   look=dirt   color=#653
  rock:              look=rock   color=#444
"""

LANDING = """area: landing
title: The Landing
tileset: dv_yard
entry: pad
legend:
  .: dirt
  #: rock
  P: dirt @pad
  L: dirt @lamp
---
#######
#.P.L.#
#######
"""

WORLD = """# [Mission](mission)

## [Props](props)

### [Strongbox](strongbox)
---
Area: deck
Mark: brig
Sprite: prop:crate
Scene: strongbox
Blocks: yes
---
Bolted to the deck of the brig.

### [Ledger](ledger)
---
Area: deck
Mark: quarters
Item: ledger
---
The purser's ledger.

### [Sample case](sample_case)
---
Area: deck
Mark: lab
Item: samples
---
A case of sample jars.

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
Talk scene: cook
---
Sitting on a cask in the hold.

## [Hostiles](hostiles)

### [Hold-out](holdout)
---
Area: deck
Mark: quarters
HP: 2
---
Will not strike his colors.

## [Scenes](scenes)

### [The strongbox](strongbox)
% Bolted down, and locked twice.

- [Take her as a prize]() ; signal boarding_deck_take
- [Leave it]()

### [The cook](cook)
% "I only do the stew."

- [Leave him]()
"""

DECK_ONLY = WORLD.replace("""### [Lamp](lamp)
---
Area: landing
Mark: lamp
---
A lamp ashore.

""", "")

STATION_ART = {
    "sheets": {"all": "all.png"},
    "sprites": {
        "g:floor_corridor": {"sheet": "all", "rect": [0, 0, 64, 64]},
        "prop:crate": {"sheet": "all", "rect": [64, 0, 128, 64]},
        "prop:door_station": {"sheet": "all", "rect": [128, 0, 192, 64]},
    },
    "ground": {"floor_corridor": {"cell": "g:floor_corridor"}},
}
# A later set that draws the crate its own way: loading `station` AGAIN would undo it.
FRONTIER_ART = {
    "sheets": {"all": "all.png"},
    "sprites": {"prop:crate": {"sheet": "all", "rect": [0, 64, 64, 128]}},
}


class _Handler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.lines = []

    def emit(self, record):
        self.lines.append(record.getMessage())


class _Base(unittest.TestCase):
    world = WORLD
    hull_map = False            # the mock has one; most tests plan from the text

    def setUp(self):
        reset_mock(sbs)
        TickDispatcher.clear()
        crew.crew_clear()
        grid_interior_reset()
        self.addCleanup(reset_mission_state)
        self.addCleanup(TickDispatcher.clear)
        self.addCleanup(crew.crew_clear)
        self.addCleanup(grid_interior_reset)
        T.tilemap_clear_tilesets()
        self.addCleanup(T.tilemap_clear_tilesets)
        T.tilemap_set_clock(0.0)
        self.addCleanup(T.tilemap_set_clock, None)
        self.now = 0.0

        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.write("ground/yard.tileset", TILESET)
        self.write("ground/landing.tiles", LANDING)
        self.write("mission.amd", self.world)

        self.art = {}
        real_find = TA.tilemap_art_find
        TA.tilemap_art_find = lambda name: self.art.get(name)
        self.addCleanup(setattr, TA, "tilemap_art_find", real_find)
        self.addCleanup(self._forget_keys)
        settings = settings_get_defaults()
        had = settings.get("TILE_ART", self)
        settings.pop("TILE_ART", None)
        self.addCleanup(lambda: settings.pop("TILE_ART", None) if had is self
                        else settings.__setitem__("TILE_ART", had))
        self.addCleanup(settings.__setitem__, "BOARDING_AUTO_BEAM",
                        settings.get("BOARDING_AUTO_BEAM", False))

        grid_merge_ascii(BRIGANTINE, "test")
        grid_merge_ascii(SURVEYOR, "test")
        if not self.hull_map:
            real_map = sbs.get_hull_map
            sbs.get_hull_map = lambda *a, **k: None
            self.addCleanup(setattr, sbs, "get_hull_map", real_map)

        side_ensure("tsn")
        side_ensure("pirate")
        self.ship = to_id(player_spawn(0, 0, 0, "Artemis", "tsn", "tsn_light_cruiser"))
        self.prize = to_id(npc_spawn(900, 0, 0, "Black Gull", "pirate",
                                     "pirate_brigantine", "behav_npcship"))
        side_surrender(self.prize)
        self.sit(HELM, "helm")
        self.sit(SCI, "science")

        self.seen = []
        signal_observe(self._obs)
        self.addCleanup(signal_unobserve, self._obs)
        self.runtime = _Handler()
        logging.getLogger("mast.runtime").addHandler(self.runtime)
        self.addCleanup(logging.getLogger("mast.runtime").removeHandler, self.runtime)
        self.debug = _Handler()                     # what DEBUG() writes to debug.log
        self.debug.setLevel(logging.DEBUG)
        logging.getLogger("debug").addHandler(self.debug)
        self.addCleanup(logging.getLogger("debug").removeHandler, self.debug)

    # --- helpers ---------------------------------------------------------------------
    def _forget_keys(self):
        for manifest in (STATION_ART, FRONTIER_ART):
            for k in manifest["sprites"]:
                ImageAtlas.all.pop(k, None)

    def _obs(self, name, data):
        self.seen.append((name, dict(data) if isinstance(data, dict) else data))

    def named(self, name):
        return [d for n, d in self.seen if n == name]

    def write(self, rel, text):
        path = os.path.join(self.tmp, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        return path

    def add_art(self, name, manifest):
        folder = os.path.join(self.tmp, "media", "tileart", name)
        os.makedirs(folder)
        with open(os.path.join(folder, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f)
        self.art[name] = folder.replace("\\", "/")

    def sit(self, client_id, console):
        GuiClient(client_id)
        set_inventory_value(client_id, "CONSOLE_TYPE", console)
        link(self.ship, "consoles", client_id)
        crew.crew_assign(client_id, self.ship, console)

    def load(self):
        """What a story does: read the file, load the ground with one line."""
        doc = document_get_amd_file(os.path.join(self.tmp, "mission.amd"),
                                    data_parser=amd_mission_data)
        with contextlib.redirect_stdout(io.StringIO()):
            return BG.boarding_ground_load(doc, folder=self.tmp)

    def board(self, target=None, **kw):
        self.out = io.StringIO()
        with contextlib.redirect_stdout(self.out):
            return D.boarding_deck_visit(self.ship, target or self.prize,
                                         BG.boarding_ground_scenes(), **kw)

    def loud(self):
        """What `mast.runtime` heard - less the one line about this harness, which has
        no LegendaryMissions `boarding` addon to draw a boarded console with."""
        return [line for line in self.runtime.lines if "no boarding console" not in line]

    def said(self, text):
        return [line for line in self.out.getvalue().splitlines() if text in line]

    def advance(self, seconds):
        from cosmos_dev.mock.sbs import TICKS_PER_SECOND
        for _ in range(int(seconds * TICKS_PER_SECOND) + 1):
            self.now += 1.0 / TICKS_PER_SECOND
            T.tilemap_set_clock(self.now)
            TickDispatcher.dispatch_tick()
            sbs.sim._time_tick_counter += 1

    def down(self, client_id=HELM):
        self.assertIsNotNone(A.boarding_beam_down(client_id))
        self.assertTrue(G.boarding_go_down(client_id))
        return A.boarding_me(client_id)

    def at(self, key):
        rec = P.boarding_prop(key) or K.boarding_hostile(key)
        where = T.tilemap_where(rec["id"]) if rec and rec["id"] is not None else None
        return (where[1], where[2]) if where else None

    def snapshot(self):
        return json.dumps({"props": P._props_snapshot(), "hostiles": K._hostiles_snapshot()},
                          sort_keys=True)


class TheGroundWaitsForADeckTests(_Base):
    """`boarding_ground_load` with `Area: deck` records, before anybody is boarded."""

    def test_deck_records_are_waiting_not_unplaced(self):
        got = self.load()
        self.assertEqual(got["unplaced"], [])
        self.assertEqual(self.runtime.lines, [])
        self.assertEqual((got["props"], got["people"]), (4, 2))
        self.assertIsNone(self.at("strongbox"))
        self.assertIsNotNone(self.at("lamp"))                    # the mission's own ground

    def test_a_typo_in_another_area_is_still_loud(self):
        self.write("mission.amd", self.world.replace("Mark: lamp", "Mark: lmap"))
        got = self.load()
        self.assertEqual(got["unplaced"], ["lamp"])
        self.assertTrue(any("lamp" in line for line in self.runtime.lines))

    def test_once_a_deck_is_up_a_record_it_cannot_stand_is_reported(self):
        """Only the WAIT is quiet. With a deck built, unplaced means unplaced again."""
        self.load()
        self.board()
        P.boarding_prop_remove("strongbox")
        self.assertIn("strongbox", BG.boarding_ground_unplaced())

    def test_a_mission_with_no_deck_records_reports_as_it_did(self):
        world = self.world
        for key in ("strongbox", "ledger", "sample_case"):
            world = world.replace("(%s)\n---\nArea: deck" % key, "(%s)\n---\nArea: landing" % key)
        self.write("mission.amd", world.replace("Area: deck", "Area: landing"))
        got = self.load()
        # Every one of them is now a mark that area does not have: all said, as before.
        self.assertEqual(got["unplaced"],
                         ["cook", "holdout", "ledger", "sample_case", "strongbox"])
        self.assertEqual(len(self.runtime.lines), 5)


class ABoardingMissionWithNoGroundTests(_Base):
    world = DECK_ONLY

    def setUp(self):
        super().setUp()
        shutil.rmtree(os.path.join(self.tmp, "ground"))

    def test_it_is_not_told_off_for_having_no_tiles_file(self):
        got = self.load()
        self.assertEqual(got["areas"], 0)
        self.assertEqual(self.runtime.lines, [])
        self.assertEqual(got["unplaced"], [])

    def test_and_it_boards(self):
        self.load()
        self.assertIsNotNone(self.board())
        self.assertIsNotNone(self.at("strongbox"))


class NoTilesAndGroundOfItsOwnTests(_Base):
    def setUp(self):
        super().setUp()
        shutil.rmtree(os.path.join(self.tmp, "ground"))

    def test_a_mission_that_names_its_own_area_is_still_told(self):
        """`Area: landing` and no .tiles file is the mistake it always was."""
        self.load()
        self.assertTrue(any("no .tiles file" in line for line in self.runtime.lines))


class TheVisitOpensTests(_Base):
    def setUp(self):
        super().setUp()
        self.load()

    def test_it_is_callable_from_mast(self):
        import sbs_utils.mast_sbs.mast_sbs_procedural  # noqa: F401
        for name in ("boarding_deck_visit", "boarding_deck_ready", "boarding_deck_target",
                     "boarding_deck_boarders", "boarding_deck_settle",
                     "boarding_deck_release", "boarding_deck_has_plan",
                     "boarding_deck_art_ready", "boarding_hostile_forget",
                     "grid_get_open_cells"):
            self.assertTrue(callable(MastGlobals.globals.get(name)), name)

    def test_a_party_is_opened_onto_the_prizes_own_deck(self):
        invite = self.board()
        self.assertIsNotNone(invite)
        self.assertTrue(invite.get("crew"))
        visit = A.boarding_visiting()
        self.assertTrue(visit.get("tile"))
        self.assertEqual(visit.get("area"), "deck")
        self.assertEqual(visit.get("ship"), self.ship)
        self.assertEqual(A.boarding_invite_title(), "Black Gull")
        self.assertEqual(A.boarding_place(), "Black Gull")
        self.assertEqual(T.tilemap_title("deck"), "Black Gull")
        self.assertEqual(D.boarding_deck_target(), self.prize)
        self.assertEqual(D.boarding_deck_boarders(), self.ship)
        self.assertEqual(self.loud(), [])

    def test_the_prize_wears_the_role_while_they_are_aboard(self):
        self.assertFalse(has_role(self.prize, "boarding_target"))
        self.board()
        self.assertTrue(has_role(self.prize, "boarding_target"))

    def test_it_is_her_deck(self):
        self.board()
        for mark in ("room:brig", "room:captains-cabin", "room:plunder-hold", "brig",
                     "quarters", "cargo", "sickbay", "bay", "hallway", "entry"):
            self.assertTrue(T.tilemap_mark_cells("deck", mark), mark)

    def test_a_writers_things_are_in_rooms_of_their_kind(self):
        self.board()
        self.assertIn(self.at("strongbox"), T.tilemap_mark_cells("deck", "room:brig"))
        self.assertIn(self.at("ledger"), T.tilemap_mark_cells("deck", "quarters"))
        self.assertIn(self.at("cook"), T.tilemap_mark_cells("deck", "room:plunder-hold"))
        self.assertIn(self.at("holdout"), T.tilemap_mark_cells("deck", "quarters"))
        self.assertEqual(BG.boarding_ground_unplaced(), [])

    def test_no_lab_aboard_a_brigantine_is_the_hallway_and_one_line(self):
        self.board()
        self.assertIn(self.at("sample_case"), T.tilemap_mark_cells("deck", "room:hallway"))
        self.assertEqual(len(self.said("no free 'lab'")), 1)

    def test_HER_CREW_IS_THE_CROWD_AND_CALM_ABOARD_A_SURRENDERED_SHIP(self):
        self.board()
        crowd = [k for k in K.boarding_hostiles("deck") if K.boarding_hostile(k).get("generated")]
        self.assertGreaterEqual(len(crowd), 2)
        for key in crowd:
            rec = K.boarding_hostile(key)
            self.assertEqual(rec["state"], "calm", key)
            self.assertIn(rec["sprite"], D.RACE_CREWS["pirate"])
            self.assertIsNotNone(self.at(key))
        # The writer's hold-out is not one of them, and is not calm.
        self.assertFalse(K.boarding_hostile("holdout").get("generated"))
        self.assertEqual(K.boarding_hostile("holdout")["state"], "idle")
        self.assertEqual(K.boarding_hostile("cook")["state"], "calm")

    def test_aboard_a_ship_still_at_war_three_in_five_fight(self):
        from sbs_utils.procedural.sides import side_set_relations, side_unsurrender
        side_unsurrender(self.prize)
        side_set_relations("tsn", "pirate", sbs.DIPLOMACY.HOSTILE)
        self.board()
        crowd = [K.boarding_hostile(k) for k in K.boarding_hostiles("deck")
                 if K.boarding_hostile(k).get("generated")]
        self.assertTrue(any(not r["calm"] for r in crowd))

    def test_going_down_stands_you_at_her_entry(self):
        self.board()
        me = self.down()
        at = T.tilemap_where(me)
        self.assertEqual(at[0], "deck")
        self.assertEqual((at[1], at[2]), T.tilemap_entry("deck"))
        self.assertEqual(T.tilemap_mark_at("deck", at[1], at[2]), "entry")

    def test_the_strongbox_opens_its_scene_and_the_cook_talks(self):
        self.board()
        me = self.down()
        x, y = self.at("strongbox")
        spot = next(c for c in ((x, y - 1), (x - 1, y), (x + 1, y), (x, y + 1))
                    if T.tilemap_is_open("deck", *c))
        T.tilemap_place(me, "deck", *spot)
        self.assertEqual(P.boarding_interact(HELM, "strongbox")[0], "scene")
        self.assertEqual(A.boarding_scene(A.boarding_channel_of(HELM)), "strongbox")

    def test_a_ship_with_no_plan_opens_nothing(self):
        other = to_id(npc_spawn(0, 0, 500, "Skiff", "pirate", "pirate_fighter",
                                "behav_npcship"))
        from sbs_utils.procedural.grid import grid_get_grid_data
        grid_get_grid_data()["pirate_fighter"] = {"grid_objects": []}
        self.assertFalse(D.boarding_deck_has_plan(other))
        self.assertIsNone(self.board(other))
        self.assertIsNone(A.boarding_visiting())
        self.assertIsNone(T.tilemap_area("deck"))
        self.assertFalse(has_role(other, "boarding_target"))
        self.assertEqual(len(self.said("no interior plan")), 1)

    def test_one_party_at_a_time_and_nothing_is_built_for_the_second(self):
        self.board()
        other = to_id(npc_spawn(0, 0, 500, "Surveyor", "pirate", "science_ship",
                                "behav_npcship"))
        before = T.tilemap_size("deck")
        self.assertIsNone(self.board(other))
        self.assertEqual(T.tilemap_size("deck"), before)         # still the Gull's deck
        self.assertEqual(D.boarding_deck_target(), self.prize)
        self.assertFalse(has_role(other, "boarding_target"))

    def test_a_mission_with_an_area_called_deck_is_told_and_nothing_opens(self):
        T.tilemap_load(LANDING.replace("area: landing", "area: deck"))
        self.assertIsNone(self.board())
        self.assertEqual(len(self.said("a tile area of its own called 'deck'")), 1)
        self.assertFalse(has_role(self.prize, "boarding_target"))


class WhichPlanTests(_Base):
    """The line that says where the hallways came from - what an engine check reads."""

    def setUp(self):
        super().setUp()
        self.load()

    def test_no_hull_map_says_grid_text_on_the_console_and_in_debug_log(self):
        self.board()
        lines = self.said("was planned from: grid text")
        self.assertEqual(len(lines), 1, self.out.getvalue())
        self.assertIn("Black Gull", lines[0])
        self.assertIn("pirate_brigantine", lines[0])
        self.assertTrue(any("[boarding_deck]" in line and "planned from: grid text" in line
                            for line in self.debug.lines))


class WithAHullMapTests(_Base):
    hull_map = True

    def test_the_engines_own_open_cells_are_used_and_it_says_so(self):
        self.load()
        self.assertIsNotNone(self.board())
        self.assertEqual(len(self.said("was planned from: hull map")), 1)
        self.assertIsNotNone(self.at("strongbox"))


class LeavingTests(_Base):
    def setUp(self):
        super().setUp()
        self.load()
        self.board()

    def gone(self):
        self.assertIsNone(A.boarding_visiting())
        self.assertIsNone(A.boarding_invitation())
        self.assertIsNone(T.tilemap_area("deck"))
        self.assertFalse(D.boarding_deck_built())
        self.assertIsNone(D.boarding_deck_target())
        self.assertEqual([k for k, r in P._PROPS.items() if r.get("generated")], [])
        self.assertEqual([k for k, r in K._HOSTILES.items() if r.get("generated")], [])
        self.assertEqual(len(self.named("boarding_visit_ended")), 1)

    def test_ending_the_visit_takes_the_deck_down_and_the_role_off(self):
        me = self.down()
        self.assertTrue(A.boarding_visit_end())
        self.gone()
        self.assertFalse(has_role(self.prize, "boarding_target"))
        self.assertIsNone(T.tilemap_where(me))
        self.assertIsNotNone(to_object(self.prize))              # she is still there

    def test_a_writers_records_wait_for_the_next_ship(self):
        A.boarding_visit_end()
        self.assertEqual(P.boarding_prop("strongbox")["at"], "brig")
        self.assertIsNone(P.boarding_prop("strongbox")["id"])
        self.assertEqual(BG.boarding_ground_unplaced(), [])      # waiting again, not lost

    def test_THE_SHIP_GONE_ENDS_THE_VISIT(self):
        self.down()
        delete_object(self.prize)
        from sbs_utils.delete_queue import DeleteQueue
        DeleteQueue.clear()
        sbs.delete_object(self.prize)
        self.advance(2)
        self.gone()

    def test_the_game_ending_takes_it_down_with_no_tick(self):
        """The results screen pauses the sim, and a paused sim ticks nothing."""
        self.down()
        signal_emit("game_over", {"WIN": True, "TEXT": "done"})
        self.gone()
        self.assertFalse(has_role(self.prize, "boarding_target"))

    def test_the_next_ship_boarded_is_her_own_deck(self):
        A.boarding_visit_end()
        other = to_id(npc_spawn(0, 0, 500, "Surveyor", "pirate", "science_ship",
                                "behav_npcship"))
        self.seen.clear()
        self.assertIsNotNone(self.board(other))
        self.assertEqual(T.tilemap_title("deck"), "Surveyor")
        self.assertEqual(D.boarding_deck_target(), other)
        self.assertTrue(T.tilemap_mark_cells("deck", "room:science-lab"))
        self.assertEqual(T.tilemap_mark_cells("deck", "room:brig"), [])
        # The lab she has; the brig she has not.
        self.assertIn(self.at("sample_case"), T.tilemap_mark_cells("deck", "room:science-lab"))
        self.assertIn(self.at("strongbox"), T.tilemap_mark_cells("deck", "room:hallway"))
        self.assertEqual(len(self.said("no free 'brig'")), 1)
        self.assertTrue(has_role(other, "boarding_target"))
        self.assertFalse(has_role(self.prize, "boarding_target"))

    def test_nothing_is_left_on_the_reset_ledger(self):
        self.down()
        reset_mission_state()
        leaks = [line for line in reset_mission_audit() if "board" in line or "tile" in line]
        self.assertEqual(leaks, [])
        self.assertEqual(D.boarding_deck_count(), 0)


class HeldStillTests(_Base):
    def test_whatever_flies_her_she_is_held_where_she_is(self):
        self.load()
        self.board()
        obj = to_object(self.prize)
        self.assertEqual(obj.data_set.get("throttle", 0), 0)
        obj.data_set.set("throttle", 1.5, 0)                     # somebody orders her home
        obj.data_set.set("target_pos_x", 99999.0, 0)
        self.advance(2)
        self.assertEqual(obj.data_set.get("throttle", 0), 0)
        self.assertAlmostEqual(obj.data_set.get("target_pos_x", 0), obj.pos.x, places=3)

    def test_and_let_go_when_the_party_leaves(self):
        self.load()
        self.board()
        A.boarding_visit_end()
        obj = to_object(self.prize)
        obj.data_set.set("throttle", 1.5, 0)
        self.advance(3)
        self.assertEqual(obj.data_set.get("throttle", 0), 1.5)


class SavesTests(_Base):
    """A boarded ship's furniture, doors and crew never reach a saved game."""

    def test_a_visit_adds_nothing_to_either_provider(self):
        self.load()
        before = self.snapshot()
        self.assertEqual(before, '{"hostiles": {}, "props": {}}')
        self.board()
        self.down()
        self.advance(2)                                          # doors slide, crew stand
        for key in list(K._HOSTILES):
            if K._HOSTILES[key].get("generated"):
                K._hostile_hit(K._HOSTILES[key], "full")
        self.assertEqual(self.snapshot(), before)
        A.boarding_visit_end()
        self.assertEqual(self.snapshot(), before)

    def test_what_a_writer_put_aboard_is_kept_as_it_always_was(self):
        self.load()
        self.board()
        K._hostile_hit(K.boarding_hostile("holdout"), "full")
        me = self.down()
        x, y = self.at("ledger")
        T.tilemap_place(me, "deck", x, y)
        self.assertEqual(P.boarding_interact(HELM, "ledger")[0], "picked")
        want = '{"hostiles": {"down": ["holdout"]}, "props": {"taken": ["ledger"]}}'
        self.assertEqual(self.snapshot(), want)
        A.boarding_visit_end()
        self.assertEqual(self.snapshot(), want)                  # and after the deck is gone


class ArtTests(_Base):
    def setUp(self):
        super().setUp()
        self.load()

    def test_with_no_art_it_boards_and_says_so_once(self):
        self.assertFalse(D.boarding_deck_art_ready())
        self.assertFalse(D.boarding_deck_ready(self.prize))      # so the button is not shown
        self.assertIsNotNone(self.board())
        self.assertEqual(len(self.said("'station' is not installed")), 1)
        self.assertEqual(self.loud(), [])                        # not a failed run
        A.boarding_visit_end()
        self.board()
        self.assertEqual(self.said("'station' is not installed"), [])

    def test_with_the_art_it_is_ready_and_the_deck_is_dressed(self):
        self.add_art("station", STATION_ART)
        self.assertTrue(D.boarding_deck_art_ready())
        self.assertTrue(D.boarding_deck_ready(self.prize))
        self.board()
        self.assertEqual(TA.tilemap_art_loaded(), ["station"])
        spec = T.tilemap_kind_spec("deck", D.HALL)
        self.assertEqual(spec.get("cell"), "g:floor_corridor")

    def test_A_SET_ALREADY_LOADED_IS_NOT_LOADED_AGAIN(self):
        """`TILE_ART: station, frontier` - frontier's crate wins. Loading station again
        for the deck would put station's crate back on top."""
        self.add_art("station", STATION_ART)
        self.add_art("frontier", FRONTIER_ART)
        TA.tilemap_art_use("station", "frontier")
        self.assertEqual(TA.tilemap_art_origin("prop:crate"), "frontier")
        self.board()
        self.assertEqual(TA.tilemap_art_origin("prop:crate"), "frontier")
        self.assertEqual(TA.tilemap_art_loaded(), ["station", "frontier"])
        # ...and the deck is dressed all the same.
        self.assertEqual(T.tilemap_kind_spec("deck", D.HALL).get("cell"), "g:floor_corridor")

    def test_a_second_ship_is_dressed_too(self):
        self.add_art("station", STATION_ART)
        self.board()
        A.boarding_visit_end()
        self.board()
        self.assertEqual(T.tilemap_kind_spec("deck", D.HALL).get("cell"), "g:floor_corridor")
        self.assertEqual(TA.tilemap_art_loaded(), ["station"])


if __name__ == "__main__":
    unittest.main()
