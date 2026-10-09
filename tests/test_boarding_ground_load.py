"""`boarding_ground_load(doc)`: a mission's ground, loaded with one call.

The files are real files in a real folder - a `.tileset`, two `.tiles` areas in a
subfolder, an `.amd` read by the game's own reader - and the call under test is the one
a `story.mast` makes. What is asserted is the WORLD afterwards: areas that can be walked,
things standing on their marks, a click that opens a scene.

    python -m unittest tests.test_boarding_ground_load
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import json
import logging
import os
import shutil
import tempfile
import unittest

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  (import first: circular import)
import cosmos_dev.mock.sbs as sbs
from tests.reset_helper import reset_mock

from sbs_utils.gui import GuiClient
from sbs_utils.handlerhooks import reset_mission_state, reset_mission_audit
from sbs_utils.mast.mast_globals import MastGlobals
from sbs_utils.procedural import boarding as A
from sbs_utils.procedural import boarding_combat as K
from sbs_utils.procedural import boarding_ground as BG
from sbs_utils.procedural import boarding_hints as H
from sbs_utils.procedural import boarding_props as P
from sbs_utils.procedural import boarding_tiles as BT
from sbs_utils.procedural import tilemap as T
from sbs_utils.procedural import tilemap_art as TA
from sbs_utils.procedural.amd_mission import amd_mission_data
from sbs_utils.procedural.gui import boarding_gui as G
from sbs_utils.procedural.gui.image import ImageAtlas
from sbs_utils.procedural.inventory import set_inventory_value
from sbs_utils.procedural.lifeform import lifeform_spawn
from sbs_utils.procedural.quest import document_get_amd_file
from sbs_utils.procedural.settings import settings_get_defaults
from sbs_utils.procedural.signal import signal_emit

CID = 0x8000000000000041

TILESET = """tileset: gl_yard
title: Yard ground
kinds:
  dirt:   walk see   look=dirt   color=#653
  rock:              look=rock   color=#444
  gate:   walk see   look=exit   color=#fc4
"""

LANDING = """area: landing
title: The Landing
tileset: gl_yard
entry: pad
legend:
  .: dirt
  #: rock
  P: dirt @pad
  T: dirt @terminal
  D: dirt @door
  N: dirt @nest
  V: gate @to_vault
exits:
  to_vault: vault @to_landing
---
############
#..........#
#.P....T...#
#........N.#
#######D####
#..........#
#####V######
"""

VAULT = """area: vault
title: The Vault
tileset: gl_yard
known: no
legend:
  .: dirt
  #: rock
  L: gate @to_landing
  C: dirt @core
exits:
  to_landing: landing @to_vault
---
###L###
#.....#
#..C..#
#######
"""

WORLD = """# [Mission](mission)

## [Crew](crew)
---
crew
Ship: Artemis
---

### [Chief Okoro](okoro)
---
Console: engineering
Roles: engineering
Skills: engineering 4, science 1
---

## [Props](props)

### [Terminal](terminal)
---
Area: landing
Mark: terminal
Sprite: prop:terminal
Scene: terminal_read
Blocks: yes
Scan: Still drawing power from somewhere.
---
A terminal, lit.

### [Vault door](door)
---
Area: landing
Mark: door
Opens with: signal vault_power
Blocks: yes
---
A door with no handle.

### [Core](core)
---
Area: vault
Mark: core
Item: core
---

## [People](people)

### [Warden](warden)
---
Area: landing
At: 3, 3
Calm: yes
Talk scene: warden_talk
---
He was here before you.

## [Hostiles](hostiles)

### [Glassback](glassback)
---
Area: landing
Mark: nest
Hidden until: nest_woken
---

## [Scenes](scenes)

### [The terminal](terminal_read)
% One line, repeating.

- [Read it](terminal_read) ; learn manifest
- [Step back]()

### [The warden](warden_talk)
% He nods.

- [Leave him]()
"""

ART = {
    "sheets": {"all": "all.png"},
    "sprites": {
        "fig:crew_eva": {"sheet": "all", "rect": [0, 0, 64, 64]},
        "prop:bag": {"sheet": "all", "rect": [64, 0, 128, 64]},
        "prop:terminal": {"sheet": "all", "rect": [128, 0, 192, 64]},
        "ui:hint_new": {"sheet": "all", "rect": [192, 0, 256, 64]},
        "gl:dirt": {"sheet": "all", "rect": [0, 64, 64, 128]},
    },
    "ground": {"dirt": {"cell": "gl:dirt"}},
}


class _Handler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.lines = []

    def emit(self, record):
        self.lines.append(record.getMessage())


class _Base(unittest.TestCase):
    world = WORLD
    tile_art = None

    def setUp(self):
        reset_mock(sbs)
        self.addCleanup(reset_mission_state)
        T.tilemap_clear_tilesets()
        self.addCleanup(T.tilemap_clear_tilesets)
        self.addCleanup(self._forget_keys)
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.write("ground/yard.tileset", TILESET)
        self.write("ground/landing.tiles", LANDING)
        self.write("ground/vault.tiles", VAULT)
        self.write("mission.amd", self.world)
        # A built site and a checkout hold COPIES of the areas; they are not the mission.
        self.write("__site__/tilemaps/landing.tiles", LANDING.replace("The Landing", "A COPY"))
        self.write(".git/x/vault.tiles", VAULT.replace("The Vault", "A COPY"))
        self.art = {}
        real_find = TA.tilemap_art_find
        TA.tilemap_art_find = lambda name: self.art.get(name)
        self.addCleanup(setattr, TA, "tilemap_art_find", real_find)
        settings = settings_get_defaults()
        had = settings.get("TILE_ART", self)
        if self.tile_art is None:
            settings.pop("TILE_ART", None)
        else:
            settings["TILE_ART"] = self.tile_art
        self.addCleanup(lambda: settings.pop("TILE_ART", None) if had is self
                        else settings.__setitem__("TILE_ART", had))
        self.runtime = _Handler()
        logging.getLogger("mast.runtime").addHandler(self.runtime)
        self.addCleanup(logging.getLogger("mast.runtime").removeHandler, self.runtime)
        self.debug = _Handler()                     # what DEBUG() writes to debug.log
        self.debug.setLevel(logging.DEBUG)
        logging.getLogger("debug").addHandler(self.debug)
        self.addCleanup(logging.getLogger("debug").removeHandler, self.debug)
        T._WATCH["task"] = object()         # no tick tasks in a unit test
        K._WATCH["task"] = object()

    def _forget_keys(self):
        for k in list(ART["sprites"]):
            ImageAtlas.all.pop(k, None)

    def write(self, rel, text):
        path = os.path.join(self.tmp, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        return path

    def add_art(self, name, manifest=ART):
        folder = os.path.join(self.tmp, "media", "tileart", name)
        os.makedirs(folder)
        with open(os.path.join(folder, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f)
        self.art[name] = folder.replace("\\", "/")

    def doc(self):
        return document_get_amd_file(os.path.join(self.tmp, "mission.amd"),
                                     data_parser=amd_mission_data)

    def load(self):
        return BG.boarding_ground_load(self.doc(), folder=self.tmp)

    def go_down(self):
        ship = lifeform_spawn("Ship", "", "x")
        A.boarding_invite(ship, [], title="Yard", area="landing")
        GuiClient(CID)
        body = lifeform_spawn("Okoro", "", "boarding,engineering")
        set_inventory_value(body.id, A.JOBS_KEY, ["engineering"])
        A.boarding_assign(CID, body.id)
        G.boarding_go_down(CID)
        return body.id


class OneCallTests(_Base):
    def test_it_is_callable_from_mast(self):
        import sbs_utils.mast_sbs.mast_sbs_procedural  # noqa: F401
        self.assertIs(MastGlobals.globals.get("boarding_ground_load"), BG.boarding_ground_load)

    def test_the_tileset_and_every_area_are_loaded(self):
        got = self.load()
        self.assertEqual((got["tilesets"], got["areas"]), (1, 2))
        self.assertTrue(T.tilemap_tileset_known("gl_yard"))
        self.assertEqual(sorted(T.tilemap_areas()), ["landing", "vault"])
        self.assertTrue(T.tilemap_is_open("landing", 2, 2))
        self.assertFalse(T.tilemap_is_open("landing", 0, 0))

    def test_copies_under_a_built_site_are_not_the_mission(self):
        self.load()
        self.assertEqual(T.tilemap_title("landing"), "The Landing")
        self.assertEqual(T.tilemap_title("vault"), "The Vault")

    def test_props_and_people_stand_where_the_file_says(self):
        got = self.load()
        self.assertEqual((got["props"], got["people"]), (3, 2))
        self.assertEqual(P.boarding_prop_at("landing", 7, 2), "terminal")
        self.assertEqual(P.boarding_prop_at("vault", 3, 2), "core")
        warden = K.boarding_hostile("warden")
        self.assertEqual(T.tilemap_where(warden["id"]), ("landing", 3, 3))
        self.assertEqual(K.boarding_hostile_state("warden"), "calm")
        self.assertEqual(got["unplaced"], [])
        self.assertEqual(self.runtime.lines, [])

    def test_somebody_hidden_is_not_reported_as_unplaced(self):
        got = self.load()
        self.assertIsNone(K.boarding_hostile("glassback")["id"])
        self.assertNotIn("glassback", got["unplaced"])
        signal_emit("nest_woken")
        self.assertIsNotNone(K.boarding_hostile("glassback")["id"])

    def test_the_scenes_are_wired_so_a_click_opens_one(self):
        got = self.load()
        self.assertEqual(got["scenes"], 2)
        self.assertEqual(sorted(BG.boarding_ground_scenes()), ["terminal_read", "warden_talk"])
        self.go_down()
        T.tilemap_place(A.boarding_me(CID), "landing", 6, 2)
        self.assertTrue(BT.boarding_tile_click(CID, "landing", 7, 2))
        self.assertEqual(A.boarding_scene(A.boarding_channel_of(CID)), "terminal_read")

    def test_a_click_reaches_a_person_too(self):
        self.load()
        self.go_down()
        T.tilemap_place(A.boarding_me(CID), "landing", 3, 2)
        self.assertTrue(BT.boarding_tile_click(CID, "landing", 3, 3))
        self.assertEqual(A.boarding_scene(A.boarding_channel_of(CID)), "warden_talk")

    def test_guards_and_skills_are_ready(self):
        got = self.load()
        self.assertEqual(got["skills"], 1)
        body = self.go_down()
        from sbs_utils.procedural.amd_dialogue import dialogue_guard_ok
        self.assertTrue(dialogue_guard_ok("engineering", body, None))
        from sbs_utils.procedural.boarding_checks import boarding_skills_declare, _TABLE
        self.assertEqual(_TABLE.get("chief okoro"), {"engineering": 4, "science": 1})

    def test_the_walk_tick_is_started(self):
        T._WATCH["task"] = None
        self.load()
        self.assertIsNotNone(T._WATCH["task"])

    def test_two_files_are_one_world(self):
        """Dawnline keeps the world and its scenes in two files."""
        world, _, scenes = self.world.partition("## [Scenes](scenes)")
        self.write("mission.amd", world)
        self.write("scenes.amd", "# [Scenes file](sf)\n\n## [Scenes](scenes)" + scenes)
        second = document_get_amd_file(os.path.join(self.tmp, "scenes.amd"),
                                       data_parser=amd_mission_data)
        got = BG.boarding_ground_load([self.doc(), second], folder=self.tmp)
        self.assertEqual((got["props"], got["people"], got["scenes"]), (3, 2, 2))


class CalledAgainTests(_Base):
    def test_a_second_call_rebuilds_nothing(self):
        self.load()
        signal_emit("vault_power")
        self.assertTrue(P.boarding_prop_is_open("door"))
        door_id = P.boarding_prop("door")["id"]
        actors = len(T.tilemap_actors())
        got = self.load()
        self.assertTrue(P.boarding_prop_is_open("door"), "the door was shut again")
        self.assertEqual(P.boarding_prop("door")["id"], door_id)
        self.assertEqual(len(T.tilemap_actors()), actors)
        self.assertEqual((got["tilesets"], got["areas"], got["props"], got["people"]),
                         (1, 2, 3, 2))

    def test_a_tileset_left_by_the_mission_before_is_not_kept(self):
        """Tilesets outlive the per-mission reset. Same name, different rules: the one
        in THIS mission's folder is the one that counts."""
        T.tilemap_tileset("gl_yard", {"dirt": {"walk": False}, "rock": {"walk": True},
                                      "gate": {"walk": False}})
        self.load()
        self.assertTrue(T.tilemap_is_open("landing", 2, 2))
        self.assertFalse(T.tilemap_is_open("landing", 0, 0))

    def test_the_reset_leaves_nothing(self):
        self.load()
        self.assertGreater(BG.boarding_ground_count(), 0)
        reset_mission_state()
        self.assertEqual(BG.boarding_ground_count(), 0)
        self.assertIsNone(BG.boarding_ground_loaded())
        held = [row for row in reset_mission_audit() if "boarding ground" in str(row)]
        self.assertEqual(held, [])


class WhatCannotBePlacedTests(_Base):
    world = (WORLD.replace("Mark: terminal", "Mark: termnal")
             .replace("Area: vault\nMark: core", "Area: valt\nMark: core")
             .replace("At: 3, 3", ""))

    def test_each_is_named_and_said_where_a_test_run_fails_on_it(self):
        got = self.load()
        self.assertEqual(got["unplaced"], ["core", "terminal", "warden"])
        said = "\n".join(self.runtime.lines)
        self.assertIn("'Terminal' (terminal) is at 'termnal' in 'landing'", said)
        self.assertIn("door, nest, pad, terminal", said)       # the marks there are
        self.assertIn("the area 'valt', and no .tiles file", said)
        self.assertIn("'Warden' (warden) has no place in 'landing'", said)

    def test_it_is_said_once(self):
        self.load()
        n = len(self.runtime.lines)
        self.load()
        self.assertEqual(len(self.runtime.lines), n)

    def test_a_mark_name_in_at_is_explained(self):
        self.write("mission.amd", WORLD.replace("Mark: terminal", "At: terminal"))
        got = self.load()
        self.assertEqual(got["unplaced"], ["terminal"])
        self.assertIn("`Mark:`", "\n".join(self.runtime.lines))


class NoGroundTests(_Base):
    def test_a_mission_with_no_area_file_is_told(self):
        for name in ("landing", "vault"):
            os.remove(os.path.join(self.tmp, "ground", name + ".tiles"))
        got = self.load()
        self.assertEqual(got["areas"], 0)
        self.assertIn("no .tiles file", "\n".join(self.runtime.lines))

    def test_an_area_drawn_with_a_tileset_nobody_wrote_is_told(self):
        os.remove(os.path.join(self.tmp, "ground", "yard.tileset"))
        self.load()
        self.assertIn("tileset 'gl_yard'", "\n".join(self.runtime.lines))


class ArtTests(_Base):
    tile_art = "frontier, station"

    def test_the_named_sets_are_loaded_and_dress_the_ground(self):
        self.add_art("frontier")
        self.add_art("station", {"sheets": {}, "sprites": {}, "ground": {}})
        got = self.load()
        self.assertEqual(got["art"], ["frontier", "station"])
        self.assertEqual(got["art_missing"], [])
        self.assertEqual(T.tilemap_kind_spec("landing", "dirt").get("cell"), "gl:dirt")
        self.assertTrue(T.tilemap_kind_spec("landing", "dirt").get("walk", True))

    def test_the_default_looks_come_from_the_art(self):
        self.add_art("frontier")
        self.add_art("station", {"sheets": {}, "sprites": {}, "ground": {}})
        self.load()
        self.assertEqual(BT._STYLE["sprite"], "fig:crew_eva")
        self.assertEqual(K._DROP["sprite"], "prop:bag")
        self.assertEqual(H._STYLE, {"new": "ui:hint_new", "lead": None, "way": None})

    def test_a_look_the_mission_chose_is_kept(self):
        self.add_art("frontier")
        self.add_art("station", {"sheets": {}, "sprites": {}, "ground": {}})
        BT.boarding_tile_style(sprite="fig:captain_f")
        K.boarding_drop_sprite("prop:crate")
        self.addCleanup(K._DROP.__setitem__, "sprite", None)
        self.load()
        self.assertEqual(BT._STYLE["sprite"], "fig:captain_f")
        self.assertEqual(K._DROP["sprite"], "prop:crate")

    def test_the_reset_hands_the_default_looks_back(self):
        self.add_art("frontier")
        self.add_art("station", {"sheets": {}, "sprites": {}, "ground": {}})
        self.load()
        reset_mission_state()
        self.assertIsNone(BT._STYLE["sprite"])
        self.assertIsNone(K._DROP["sprite"])
        self.assertEqual(H._STYLE, {"new": None, "lead": None, "way": None})

    def test_missing_packs_are_said_once_and_plainly_and_the_ground_still_loads(self):
        import contextlib
        import io
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            got = self.load()
            self.load()
        said = out.getvalue()
        self.assertEqual(got["art"], [])
        self.assertEqual(got["art_missing"], ["frontier", "station"])
        self.assertEqual(said.count("is not installed"), 1, said)
        self.assertIn("'frontier', 'station'", said)
        self.assertIn("story.json", said)
        self.assertNotIn("'builtin'", said)          # a mission may have no art of its own
        # Not installed is not a mistake in the mission: a test run does not fail on it.
        self.assertEqual(self.runtime.lines, [])
        # But it IS written where an author can find it in the engine, which shows
        # neither stdout nor a named log category: debug.log.
        self.assertEqual(sum("is not installed" in line for line in self.debug.lines), 1)
        # And the world is there, drawn without it.
        self.assertEqual(sorted(T.tilemap_areas()), ["landing", "vault"])
        self.assertEqual(P.boarding_prop_at("landing", 7, 2), "terminal")
        self.assertIsNone(BT._STYLE["sprite"])

    def test_the_missions_own_builtin_set_is_used_when_it_has_one(self):
        self.add_art("builtin")
        got = self.load()
        self.assertEqual(got["art"], ["builtin"])
        self.assertEqual(got["art_missing"], ["frontier", "station"])


STORY = '''shared MISSION_DOC = None
crew_load_amd("mission.amd")

@map/away "Away"
    shared MISSION_DOC = document_get_amd_file(get_mission_dir_filename("mission.amd"), data_parser=amd_mission_data)
    quest_grant_amd(SHARED, amd_section(MISSION_DOC, "quests"))
    boarding_ground_load(MISSION_DOC)
    ->END
'''

QUESTS = """
## [Quests](quests)

### [Go](go)
---
Scope: shared
---
Go.
"""

LOOT = """
## [Loot](loot)

### [Coin](coin)
---
Price: 2
---
A coin.
"""


class LintKnowsWhatItReadsTests(unittest.TestCase):
    """`boarding_ground_load(doc)` reads Props, People, Hostiles and Scenes by itself, so
    the story has no `amd_section(..., "props")` line - and lint, which looks for those
    lines, reported every one of them as a section nothing reads."""

    def unread(self, world, story=STORY):
        from sbs_utils.procedural.amd_lint import amd_lint
        return sorted({f.message.split("`")[1] for f in amd_lint(
            file_path="mission.amd", content=world, mast_sources=[story], cross_file=False)
            if f.code == "section-not-loaded"})

    def test_the_sections_it_reads_are_not_reported(self):
        self.assertEqual(self.unread(WORLD + QUESTS), [])

    def test_without_the_call_they_are(self):
        story = STORY.replace("    boarding_ground_load(MISSION_DOC)\n", "")
        self.assertEqual(self.unread(WORLD + QUESTS, story),
                         ["hostiles", "people", "props", "scenes"])

    def test_a_section_it_does_not_read_is_still_reported(self):
        self.assertEqual(self.unread(WORLD + QUESTS + LOOT), ["loot"])


if __name__ == "__main__":
    unittest.main()
