"""Tile world lint: the quiet mistakes made loud.

Each one here fails SILENTLY at runtime - an area that does not load, a prop never placed,
an exit into nowhere, a hostile frozen in rock - which is why the linter exists. Each test
plants one mistake in a small clean world and checks the finding names the right line.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import os
import shutil
import tempfile
import unittest

from sbs_utils.procedural import tilemap_lint as TL
from sbs_utils.procedural.tilemap import tilemap_tileset_parse

TILESET = """tileset: test
kinds:
  dirt:  walk see
  rock:
  water: see
"""

RIDGE = """area: ridge
tileset: test
entry: landing
legend:
  .: dirt
  #: rock
  ~: water
  L: dirt @landing
  c: dirt @to_colony
exits:
  to_colony: colony @to_ridge
---
######
#.L.c#
#..~.#
######
"""

COLONY = """area: colony
tileset: test
legend:
  .: dirt
  #: rock
  r: dirt @to_ridge
---
#####
#r..#
#####
"""

WORLD = """## [Props](props)

### [Drone](drone)
---
Area: ridge
Mark: landing
Sprite: prop:drone
---

## [Hostiles](hostiles)

### [Glassback](gb)
---
Area: ridge
At: 1, 1
Patrol: 1 1; 2 2
---
"""


def codes(findings):
    return sorted(f.code for f in findings)


class TileLintBase(unittest.TestCase):
    def world(self, ridge=RIDGE, colony=COLONY, tileset=TILESET):
        areas = {}
        for text in (ridge, colony):
            rec = TL.tilemap_area_lenient(text)
            if rec:
                areas[rec["key"]] = rec
        ts = {"test": tilemap_tileset_parse(tileset)} if tileset else None
        return {"tilesets": ts, "areas": areas}

    def area(self, text, **kw):
        return TL.tilemap_lint_area(text, self.world(ridge=text, **kw))

    def placements(self, text, **kw):
        return TL.tilemap_lint_placements(text, self.world(**kw))


class TestACleanWorldIsClean(TileLintBase):
    def test_nothing_to_say(self):
        w = self.world()
        self.assertEqual(TL.tilemap_lint_area(RIDGE, w), [])
        self.assertEqual(TL.tilemap_lint_area(COLONY, w), [])
        self.assertEqual(TL.tilemap_lint_placements(WORLD, w), [])
        self.assertEqual(TL.tilemap_lint_tileset(TILESET), [])


class TestAreaFiles(TileLintBase):
    def test_EVERY_UNKNOWN_CHARACTER_IS_NAMED_WITH_ITS_COLUMN(self):
        """The parser stops at the first; the author wants all of them."""
        text = RIDGE.replace("#..~.#", "#.?~?#")
        found = [f for f in self.area(text) if f.code == "tiles-unknown-char"]
        self.assertEqual([(f.line, f.col) for f in found], [(15, 2), (15, 4)])

    def test_one_typo_does_not_hide_the_rest(self):
        text = RIDGE.replace("#..~.#", "#.?~.#").replace("entry: landing", "entry: nowhere")
        self.assertEqual(codes(self.area(text)), ["tiles-entry", "tiles-unknown-char"])

    def test_a_kind_the_tileset_lacks(self):
        text = RIDGE.replace("~: water", "~: lava")
        found = [f for f in self.area(text) if f.code == "tiles-unknown-kind"]
        self.assertEqual(len(found), 1)
        self.assertEqual((found[0].line, found[0].col, found[0].end_col), (7, 5, 9))

    def test_no_tileset_file_means_no_claim_about_kinds(self):
        text = RIDGE.replace("~: water", "~: lava")
        self.assertEqual(self.area(text, tileset=None), [])

    def test_a_tileset_nobody_wrote(self):
        text = RIDGE.replace("tileset: test", "tileset: tset")
        self.assertIn("tiles-unknown-tileset", codes(self.area(text)))

    def test_a_mark_never_drawn(self):
        text = RIDGE.replace("  c: dirt @to_colony", "  c: dirt @to_colony\n  o: dirt @obelisk")
        self.assertEqual(codes(self.area(text)), ["tiles-mark-unplaced"])

    def test_an_entry_in_rock(self):
        text = RIDGE.replace("entry: landing", "entry: 0, 0")
        found = self.area(text)
        self.assertEqual(codes(found), ["tiles-entry"])
        self.assertIn("rock", found[0].message)

    def test_an_exit_into_nowhere(self):
        text = RIDGE.replace("to_colony: colony @to_ridge", "to_colony: colonny @to_ridge")
        self.assertEqual(codes(self.area(text)), ["tiles-exit"])

    def test_an_exit_arriving_at_a_mark_that_is_not_there(self):
        text = RIDGE.replace("colony @to_ridge", "colony @dock")
        self.assertEqual(codes(self.area(text)), ["tiles-exit"])

    def test_a_to_mark_with_no_area(self):
        text = RIDGE.replace("L: dirt @landing", "L: dirt @to_moon")
        text = text.replace("entry: landing", "entry: 2, 1")
        self.assertEqual(codes(self.area(text)), ["tiles-exit"])

    def test_the_file_alone_skips_the_cross_area_checks(self):
        text = RIDGE.replace("to_colony: colony @to_ridge", "to_colony: colonny @to_ridge")
        self.assertEqual(TL.tilemap_lint_area(text), [])

    def test_a_duplicate_legend_key(self):
        text = RIDGE.replace("  #: rock", "  #: rock\n  #: water")
        self.assertIn("tiles-legend-duplicate", codes(self.area(text)))

    def test_a_file_with_no_map(self):
        found = TL.tilemap_lint_area("area: x\nlegend:\n  .: dirt\n")
        self.assertEqual(codes(found), ["tiles-syntax"])


class TestTilesetFiles(TileLintBase):
    def test_a_typo_is_on_its_line(self):
        found = TL.tilemap_lint_tileset(TILESET.replace("rock:", "rock: sold"))
        self.assertEqual([(f.code, f.line) for f in found], [("tileset-syntax", 4)])


class TestPlacements(TileLintBase):
    def test_an_area_that_is_not_there(self):
        found = self.placements(WORLD.replace("Area: ridge\nMark", "Area: ridg\nMark"))
        self.assertEqual(codes(found), ["tiles-unknown-area"])
        self.assertEqual((found[0].line, found[0].col), (5, 6))

    def test_a_mark_that_is_not_there(self):
        self.assertEqual(codes(self.placements(WORLD.replace("Mark: landing", "Mark: lnding"))),
                         ["tiles-unknown-mark"])

    def test_A_MARK_NAME_IN_AT_IS_NEVER_PLACED(self):
        text = WORLD.replace("Mark: landing", "At: landing")
        self.assertEqual(codes(self.placements(text)), ["tiles-at-not-a-cell"])

    def test_off_the_map(self):
        found = self.placements(WORLD.replace("At: 1, 1", "At: 9, 1"))
        self.assertEqual(codes(found), ["tiles-off-map"])
        self.assertIn("6 x 4", found[0].message)

    def test_a_hostile_in_rock(self):
        self.assertEqual(codes(self.placements(WORLD.replace("At: 1, 1", "At: 0, 1"))),
                         ["tiles-unwalkable"])

    def test_A_PATROL_THROUGH_WATER_NAMES_THE_POINT(self):
        found = self.placements(WORLD.replace("Patrol: 1 1; 2 2", "Patrol: 1 1; 3 2"))
        self.assertEqual(codes(found), ["tiles-unwalkable"])
        self.assertEqual(found[0].col, len("Patrol: 1 1; "))

    def test_a_prop_may_stand_in_rock(self):
        self.assertEqual(self.placements(WORLD.replace("Mark: landing", "At: 0, 0")), [])

    def test_a_mission_with_no_tiles_says_nothing(self):
        self.assertEqual(TL.tilemap_lint_placements(WORLD, {"areas": {}}), [])


class TestAMission(unittest.TestCase):
    def test_files_on_disk(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root)
        os.makedirs(os.path.join(root, "surface"))
        for name, text in (("surface/test.tileset", TILESET),
                           ("surface/ridge.tiles", RIDGE),
                           ("surface/colony.tiles", COLONY),
                           ("world.amd", WORLD.replace("At: 1, 1", "At: 9, 1"))):
            with open(os.path.join(root, name), "w", encoding="utf-8") as fh:
                fh.write(text)
        found = TL.tilemap_lint_mission(root)
        self.assertEqual([(rel, f.code) for rel, f in found], [("world.amd", "tiles-off-map")])


if __name__ == "__main__":
    unittest.main()


class TestLanguageServer(unittest.TestCase):
    """The squiggles and the tile editor's data, through the real server loop."""

    def setUp(self):
        import json
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        self.root = os.path.join(tmp, "m")
        os.makedirs(os.path.join(self.root, "surface"))
        os.makedirs(os.path.join(self.root, "media", "tileart", "builtin"))
        files = {"story.json": "{}", "surface/test.tileset": TILESET,
                 "surface/ridge.tiles": RIDGE, "surface/colony.tiles": COLONY,
                 "world.amd": WORLD,
                 "media/tileart/builtin/manifest.json": json.dumps({
                     "sheets": {"s": "s.png"},
                     "sprites": {"g:dirt": {"sheet": "s", "rect": [0, 0, 64, 64]},
                                 "g:rock": {"sheet": "s", "rect": [64, 0, 128, 64]}},
                     "ground": {"dirt": {"cell": "g:dirt"}, "rock": {"cell": "g:rock"}}})}
        for name, text in files.items():
            with open(os.path.join(self.root, name), "w", encoding="utf-8") as fh:
                fh.write(text)

    def drive(self, msgs):
        import io
        import json
        from sbs_utils.procedural import amd_lsp

        def frame(m):
            data = json.dumps(m).encode("utf-8")
            return b"Content-Length: " + str(len(data)).encode() + b"\r\n\r\n" + data
        amd_lsp._tiles_cache.clear()
        out = io.BytesIO()
        amd_lsp.serve(stdin=io.BytesIO(b"".join(frame(m) for m in msgs)), stdout=out)
        raw, got, i = out.getvalue(), [], 0
        while i < len(raw):
            j = raw.find(b"\r\n\r\n", i)
            n = int(raw[i:j].decode().split(":")[1])
            got.append(json.loads(raw[j + 4:j + 4 + n]))
            i = j + 4 + n
        return got

    def uri(self, rel):
        from pathlib import Path
        return Path(os.path.join(self.root, rel)).as_uri()

    def test_an_area_gets_squiggles(self):
        text = RIDGE.replace("#..~.#", "#.?~.#")
        got = self.drive([
            {"jsonrpc": "2.0", "method": "textDocument/didOpen", "params": {"textDocument": {
                "uri": self.uri("surface/ridge.tiles"), "text": text}}},
            {"jsonrpc": "2.0", "method": "exit"}])
        diags = got[0]["params"]["diagnostics"]
        self.assertEqual([(d["code"], d["range"]["start"]) for d in diags],
                         [("tiles-unknown-char", {"line": 14, "character": 2})])

    def test_the_amd_gets_its_placements_checked(self):
        text = WORLD.replace("At: 1, 1", "At: 9, 1")
        got = self.drive([
            {"jsonrpc": "2.0", "method": "textDocument/didOpen", "params": {"textDocument": {
                "uri": self.uri("world.amd"), "text": text}}},
            {"jsonrpc": "2.0", "method": "exit"}])
        codes_ = [d["code"] for d in got[0]["params"]["diagnostics"]]
        self.assertIn("tiles-off-map", codes_)

    def test_an_unsaved_edit_in_one_area_reaches_the_other(self):
        """Renaming the arrival mark in colony breaks ridge's exits: line - live."""
        colony = COLONY.replace("r: dirt @to_ridge", "r: dirt @to_ridge\n  d: dirt @dock")
        got = self.drive([
            {"jsonrpc": "2.0", "method": "textDocument/didOpen", "params": {"textDocument": {
                "uri": self.uri("surface/ridge.tiles"), "text": RIDGE}}},
            {"jsonrpc": "2.0", "method": "textDocument/didOpen", "params": {"textDocument": {
                "uri": self.uri("surface/colony.tiles"),
                "text": colony.replace("@to_ridge", "@from_ridge")}}},
            {"jsonrpc": "2.0", "method": "exit"}])
        ridge = [m for m in got if m["params"]["uri"].endswith("ridge.tiles")][-1]
        self.assertIn("tiles-exit", [d["code"] for d in ridge["params"]["diagnostics"]])

    def test_the_editor_gets_the_looks(self):
        got = self.drive([
            {"jsonrpc": "2.0", "id": 7, "method": "tiles/preview", "params": {
                "textDocument": {"uri": self.uri("surface/ridge.tiles")}, "text": RIDGE}},
            {"jsonrpc": "2.0", "id": 8, "method": "textDocument/hover", "params": {
                "textDocument": {"uri": self.uri("surface/ridge.tiles")},
                "position": {"line": 0, "character": 0}}},
            {"jsonrpc": "2.0", "method": "exit"}])
        res = next(m for m in got if m.get("id") == 7)["result"]
        self.assertTrue(res["ok"])
        self.assertEqual(res["looks"][0][0], "g:rock")
        self.assertEqual(res["looks"][1][1], "g:dirt")
        self.assertIsNone(res["looks"][2][3])            # water: no art in this set
        self.assertEqual(sorted(res["sprites"]), ["g:dirt", "g:rock"])
        self.assertFalse(res["kinds"]["water"]["walk"])
        self.assertEqual(res["problems"], [])
        # Who stands here, read from the mission's .amd through the server's own index.
        self.assertEqual(sorted(p["key"] for p in res["placements"]), ["drone", "gb"])
        self.assertTrue(next(p for p in res["placements"] if p["key"] == "gb")["at"])
        # Anything that reads the AMD model answers a tile file with nothing.
        self.assertIsNone(next(m for m in got if m.get("id") == 8)["result"])


class TestPreviewMatchesTheGame(unittest.TestCase):
    def test_the_same_looks_as_the_runtime_and_nothing_left_behind(self):
        from sbs_utils.procedural import tilemap as T
        from sbs_utils.procedural.tilemap_art import tilemap_art_ground
        from sbs_utils.procedural.tilemap_preview import tilemap_preview
        ground = {"dirt": {"cell": "g:dirt", "variants": ["g:dirt2", "g:dirt3"], "over": 1},
                  "rock": {"cell": "g:rock", "tall": True,
                           "edges": {"10": ["g:rock_ew", "g:rock_ew2"]}},
                  "water": {"cell": "g:water", "fringe": {"n": "g:wf_n", "s": "g:wf_s",
                                                          "e": "g:wf_e", "w": "g:wf_w"},
                            "over": 2}}
        world = {"tilesets": {"test": tilemap_tileset_parse(TILESET)},
                 "areas": {"ridge": TL.tilemap_area_lenient(RIDGE)}}
        T.tilemap_clear()
        T.tilemap_clear_tilesets()
        self.addCleanup(T.tilemap_clear)
        self.addCleanup(T.tilemap_clear_tilesets)
        T.tilemap_tileset_load(TILESET)
        tilemap_art_ground("test", ground)
        T.tilemap_load(RIDGE)
        want = [[T.tilemap_cell_look(T.tilemap_kind_spec("ridge", T.tilemap_kind("ridge", x, y)),
                                     x, y, "ridge") for x in range(6)] for y in range(4)]
        before = (dict(T._TILESETS), dict(T._AREAS))

        import json
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root)
        os.makedirs(os.path.join(root, "media", "tileart", "builtin"))
        with open(os.path.join(root, "media", "tileart", "builtin", "manifest.json"), "w") as fh:
            json.dump({"sheets": {}, "sprites": {}, "ground": ground}, fh)
        got = tilemap_preview(RIDGE, root, world=world)
        self.assertEqual(got["looks"], want)
        self.assertEqual(got["fringes"],
                         [[x, y, T.tilemap_cell_fringes("ridge", x, y)]
                          for y in range(4) for x in range(6)
                          if T.tilemap_cell_fringes("ridge", x, y)])
        self.assertTrue(got["fringes"])              # the seam really was exercised
        self.assertEqual((dict(T._TILESETS), dict(T._AREAS)), before)


class TestPlacementsForTheEditor(TileLintBase):
    """What the tile editor draws and drags: every thing on an area, and WHERE in the .amd
    its position is written, to the column."""

    def placed(self, text=WORLD):
        from sbs_utils.procedural.amd_core import parse
        from sbs_utils.procedural.tilemap_preview import tilemap_placements
        return {p["key"]: p for p in tilemap_placements(
            "ridge", [("file:///w.amd", parse(text), text)], self.world())}

    def test_a_mark_placed_prop_stands_on_its_mark(self):
        p = self.placed()["drone"]
        self.assertEqual((p["kind"], p["how"], p["mark"], p["cell"]), ("prop", "mark", "landing", [2, 1]))
        self.assertIsNone(p["at"])

    def test_AT_AND_EACH_PATROL_POINT_CARRY_THEIR_SOURCE_COLUMNS(self):
        p = self.placed()["gb"]
        lines = WORLD.split("\n")
        at = p["at"]
        self.assertEqual(lines[at["line"]][at["start"]:at["end"]], "1, 1")
        self.assertEqual([lines[q["line"]][q["start"]:q["end"]] for q in p["patrol"]], ["1 1", "2 2"])
        self.assertEqual([(q["x"], q["y"]) for q in p["patrol"]], [(1, 1), (2, 2)])

    def test_problems_ride_along(self):
        p = self.placed(WORLD.replace("At: 1, 1", "At: 9, 1"))["gb"]
        self.assertEqual(p["cell"], [9, 1])
        self.assertTrue(any("off the map" in m for m in p["problems"]))

    def test_only_this_area(self):
        self.assertEqual(self.placed(WORLD.replace("Area: ridge\nMark", "Area: colony\nMark")).keys(),
                         {"gb"})

    def test_hidden_and_calm(self):
        text = WORLD.replace("Patrol: 1 1; 2 2", "Patrol: 1 1; 2 2\nCalm: yes\nHidden until: lp_power")
        p = self.placed(text)["gb"]
        self.assertTrue(p["calm"] and p["hidden"])

    def test_the_preview_picks_a_standing_frame(self):
        from sbs_utils.procedural.tilemap_preview import _sprite_look
        sprites = {"fig:a": 1, "fig:a_s_idle": 1, "fig:b_s": 1, "prop:c": 1}
        self.assertEqual([_sprite_look(sprites, k) for k in ("fig:a", "fig:b", "prop:c", "x")],
                         ["fig:a_s_idle", "fig:b_s", "prop:c", None])


class TestTilesetPreviewForTheEditor(unittest.TestCase):
    """What the tileset editor shows: the looks the art sets offer, the art each kind
    ends up wearing, and how many cells of the areas use each kind."""

    def setUp(self):
        import json
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)
        os.makedirs(os.path.join(self.root, "surface"))
        os.makedirs(os.path.join(self.root, "media", "tileart", "builtin"))
        for name, text in (("story.json", "{}"), ("surface/test.tileset", TILESET),
                           ("surface/ridge.tiles", RIDGE), ("surface/colony.tiles", COLONY)):
            with open(os.path.join(self.root, name), "w", encoding="utf-8") as fh:
                fh.write(text)
        with open(os.path.join(self.root, "media", "tileart", "builtin", "manifest.json"), "w") as fh:
            json.dump({"sheets": {"s": "s.png"},
                       "sprites": {"g:dirt": {"sheet": "s", "rect": [0, 0, 64, 64]},
                                   "g:sand0": {"sheet": "s", "rect": [64, 0, 128, 64]},
                                   "fig:a_s_idle": {"sheet": "s", "rect": [0, 64, 64, 128]},
                                   "fig:a_e_idle": {"sheet": "s", "rect": [64, 64, 128, 128]}},
                       "ground": {"dirt": {"cell": "g:dirt"},
                                  "sand": {"grid": ["g:sand0", "g:sand1"], "tall": True}}}, fh)

    def preview(self, text=TILESET):
        from sbs_utils.procedural.tilemap_preview import tilemap_tileset_preview
        return tilemap_tileset_preview(text, self.root)

    def test_the_looks_on_offer_each_with_a_picture(self):
        looks = self.preview()["looks"]
        self.assertEqual(sorted(looks), ["dirt", "sand"])
        self.assertEqual((looks["dirt"]["key"], looks["sand"]["key"]), ("g:dirt", "g:sand0"))
        self.assertTrue(looks["sand"]["tall"])

    def test_a_kind_with_no_art_says_so(self):
        art = self.preview(TILESET.replace("look=dust", "look=dirt"))["art"]
        self.assertEqual(art["dirt"], "g:dirt")
        self.assertIsNone(art["rock"])               # no set has a `rock` look

    def test_usage_counts_cells_in_the_areas_that_use_it(self):
        r = self.preview(TILESET.replace("tileset: Filed", "tileset: test"))
        self.assertEqual(r["areas"], ["colony", "ridge"])
        self.assertTrue(r["areaPaths"]["ridge"].endswith(os.path.join("surface", "ridge.tiles")))
        self.assertEqual(r["usage"]["rock"], 16 + 12)   # ridge 6x4 ring, colony 5x3 ring
        self.assertEqual(r["usage"]["water"], 1)

    def test_a_broken_file_still_lists_the_looks(self):
        r = self.preview("tileset: t\nkinds:\n  dirt: wlak\n")
        self.assertFalse(r["ok"])
        self.assertIn("wlak", r["error"])
        self.assertIn("dirt", r["looks"])

    def test_placements_carry_every_facing(self):
        from sbs_utils.procedural.amd_core import parse
        from sbs_utils.procedural.tilemap_preview import tilemap_preview
        world_text = WORLD.replace("Sprite: prop:drone", "Sprite: fig:a")
        r = tilemap_preview(RIDGE, self.root,
                            amd_docs=[("file:///w.amd", parse(world_text), world_text)])
        drone = next(p for p in r["placements"] if p["key"] == "drone")
        self.assertEqual(drone["looks"], {"n": None, "e": "fig:a_e_idle", "s": "fig:a_s_idle", "w": None})
        self.assertEqual(drone["look"], "fig:a_s_idle")
        self.assertIn("fig:a_e_idle", r["sprites"])


class TestTilesetOverTheServer(unittest.TestCase):
    """`tiles/tilesetPreview` through the real server loop, on the same small mission."""

    setUp = TestLanguageServer.setUp
    drive = TestLanguageServer.drive
    uri = TestLanguageServer.uri

    def test_the_tileset_editor_gets_its_table(self):
        got = self.drive([
            {"jsonrpc": "2.0", "id": 9, "method": "tiles/tilesetPreview", "params": {
                "textDocument": {"uri": self.uri("surface/test.tileset")},
                "text": TILESET.replace("tileset: Filed", "tileset: test")}},
            {"jsonrpc": "2.0", "method": "exit"}])
        res = next(m for m in got if m.get("id") == 9)["result"]
        self.assertTrue(res["ok"])
        self.assertEqual(res["art"]["dirt"], "g:dirt")
        self.assertEqual(res["usage"]["dirt"], 7 + 3)       # ridge, and colony's r
        self.assertEqual(res["problems"], [])
