"""The xESS home sheet never squashes its tiles to make room for the scene's line.

Engine-seen, author course 3 lessons 12 and 16: Back to the home while a scene's line
was showing (Pim's `"You are from the ship." ...`, the lift's `The lamp comes up amber,
then green. ...`) drew every tile at ~0.07 of the screen, its title printed over its blurb
(`defect_home_squash.png`, `defect_home_squash2.png`). The line sat in a FIXED 170px band
and the eight tiles of a ground visit are content rows - so when the two did not fit, the
layout scaled the tiles down, never the band.

THE RULE: the tiles keep their own height; the line gets what is left (up to its cap),
and when what is left is not even two lines it is not drawn on the home at all - it is in
Act, whose tile says so.

This presents the real console, on a ground, at the engine shoot's 1280x960, and checks the
emitted rects.

    python -m unittest tests.test_xess_home_room
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sys
import unittest

import cosmos_dev.mock.sbs as mock_sbs
sys.modules.setdefault("sbs", mock_sbs)

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  (import first: circular import)
from sbs_utils.agent import clear_shared
from sbs_utils.gui import Gui, GuiClient
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.mast.maststory import MastStory
from sbs_utils.mast.mastscheduler import MastScheduler
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.vec import Vec3
from sbs_utils.procedural import boarding as A
from sbs_utils.procedural import tilemap as T
from sbs_utils.procedural import boarding_tiles as BT
from sbs_utils.procedural import boarding_props as P
from sbs_utils.procedural import boarding_checks as C
from sbs_utils.procedural import boarding_combat as K
from sbs_utils.procedural.gui import boarding_gui as G
from sbs_utils.procedural.gui import xess as X
from sbs_utils.procedural.gui import xess_ground  # noqa: F401  (registers Look/Pack/...)
from sbs_utils.procedural.inventory import set_inventory_value
from sbs_utils.procedural.lifeform import lifeform_spawn
from sbs_utils.pages.layout import measure as M

CID = 0x80000000000000A1
SCALE = 960 / 768.0
STORY = """
gui_boarding_console()
await gui()
"""

AREA = """area: gully
title: The Dry Gully
tileset: g
entry: arrive
legend:
  .: dirt
  #: rock
  A: dirt @arrive
---
##########
#.A......#
#........#
##########
"""
KINDS = {"dirt": {"cell": "g:dirt"}, "rock": {"cell": "g:rock", "walk": False}}

PIM = ('"You are from the ship." She does not get up. "I came out here to start the '
       'pump, nine days ago. I got as far as the door."')
LIFT = ("The lamp comes up amber, then green. Behind you the winding drum takes up its "
        "slack with a groan, and the cage gate unlocks.")


def _scene(line):
    return {"talk": {"key": "talk", "display_text": "talk", "data": {},
                     "description": "%% %s\n- [Promise to bring it back](done)\n"
                                    "- [Leave her be]()\n" % line},
            "done": {"key": "done", "display_text": "done", "data": {},
                     "description": "% She nods.\n"}}


class ConsolePage(StoryPage):
    story = None


class TheHomeKeepsItsTiles(unittest.TestCase):
    def setUp(self):
        clear_shared()
        SpaceObject.clear()
        Gui.clients = {}
        Gui.widget_list_sent = {}
        mock_sbs.create_new_sim()
        mock_sbs.resume_sim()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent(0, "test"))
        FrameContext.page = None
        FrameContext.task = None
        FrameContext.aspect_ratios[CID] = Vec3(1280, 960, 0)
        self.addCleanup(FrameContext.aspect_ratios.pop, CID, None)
        # THE ENGINE'S FONTS AT 960 TALL. The engine draws (and measures) text bigger at
        # a bigger window - its tiles stood ~96px apart in the shoot where the mock's
        # stand 80 - and that is what took a ground's eight tiles to the foot of the
        # column. The mock's metrics are its 768-tall ones, so they are scaled here.
        for name in ("get_text_line_width", "get_text_block_height"):
            orig_fn = getattr(mock_sbs, name)
            self.addCleanup(setattr, mock_sbs, name, orig_fn)
        lw, bh = mock_sbs.get_text_line_width, mock_sbs.get_text_block_height
        mock_sbs.get_text_line_width = lambda f, t: int(lw(f, t) * SCALE)
        mock_sbs.get_text_block_height = (
            lambda f, t, w: int(bh(f, t, max(1, int(w / SCALE))) * SCALE))
        M.measure_cache_clear()
        self.addCleanup(M.measure_cache_clear)
        for clear in (A.boarding_clear, T.tilemap_clear, BT.boarding_tile_clear,
                      P.boarding_props_clear, C.boarding_checks_clear,
                      K.boarding_combat_clear, X.xess_clear):
            clear()
            self.addCleanup(clear)
        Gui.clients[CID] = GuiClient(CID)
        T.tilemap_tileset("g", KINDS)
        T.tilemap_load(AREA)
        T._WATCH["task"] = object()
        K._WATCH["task"] = object()
        T.tilemap_set_clock(0.0)
        ship = lifeform_spawn("Ship", "", "x")
        A.boarding_invite(ship, [], title="Gully", area="gully")
        body = lifeform_spawn("Chief Okoro", "", "boarding,engineering")
        set_inventory_value(body.id, A.JOBS_KEY, ["engineering"])
        A.boarding_assign(CID, body.id)
        G.boarding_go_down(CID)

        self.texts = []
        orig = mock_sbs.send_gui_text

        def rec(client_id, parent, tag, props, left, top, right, bottom):
            self.texts.append((props or "", left, top, right, bottom))
            return orig(client_id, parent, tag, props, left, top, right, bottom)

        mock_sbs.send_gui_text = rec
        self.addCleanup(setattr, mock_sbs, "send_gui_text", orig)

        story = MastStory()
        errors = story.compile(STORY, "xesshome", story)
        self.assertEqual([], errors)
        story.compiler_errors = []
        ConsolePage.story = story
        FrameContext.mast = story
        self.errors = []
        self._orig_rte = MastScheduler.on_runtime_error
        MastScheduler.on_runtime_error = self.errors.append

    def tearDown(self):
        MastScheduler.on_runtime_error = self._orig_rte
        Gui.clients = {}
        Gui.widget_list_sent = {}
        ConsolePage.story = None
        FrameContext.task = None
        FrameContext.page = None
        FrameContext.mast = None
        FrameContext.context = None
        SpaceObject.clear()

    def build(self):
        Gui.widget_list_sent = {}
        page = ConsolePage()
        Gui.push(CID, page)
        self.texts.clear()
        mock_sbs.sim._time_tick_counter += 30
        page.gui_state = "repaint"
        page.present(FakeEvent(CID, "gui_present"))
        self.assertEqual([], self.errors)

    def tile_rows(self):
        """[(title rect, blurb rect)] for each tile on the home, in screen order."""
        apps = X.xess_apps(CID)
        self.assertGreaterEqual(len(apps), 8, "fixture: the ground's eight apps")
        out = []
        for app in apps:
            title = [t for t in self.texts if "$text:`%s`;font:gui-3" % app["title"] in t[0]]
            blurb = [t for t in self.texts if app.get("blurb") and app["blurb"] in t[0]]
            self.assertTrue(title and blurb, "tile %s did not draw" % app["title"])
            out.append((app["title"], title[0], blurb[0]))
        return out

    def assert_tiles_whole(self, why):
        px = 960 / 100.0
        for name, title, blurb in self.tile_rows():
            self.assertLessEqual(title[4], blurb[2] + 0.01,
                                 "%s: the tile's title is printed over its blurb - %s"
                                 % (name, why))
            self.assertGreaterEqual((title[4] - title[2]) * px + 0.5,
                                    M.measure_line_height("gui-3", name),
                                    "%s: the title row is squashed - %s" % (name, why))

    def test_the_home_with_nothing_said(self):
        X.xess_open(CID, None)
        self.build()
        self.assert_tiles_whole("no line at all")

    def test_back_home_with_pims_line_showing(self):
        A.boarding_scene_begin(_scene(PIM), "talk")
        X.xess_open(CID, None)
        self.build()
        self.assert_tiles_whole("Pim's line was showing (c3-12)")

    def test_back_home_after_the_lift_runs(self):
        A.boarding_scene_begin(_scene(LIFT), "talk")
        X.xess_open(CID, None)
        self.build()
        self.assert_tiles_whole("the lift's line was showing (c3-16)")

    def test_with_room_to_spare_the_line_keeps_its_full_band(self):
        """Four tiles leave plenty: the line is drawn, at its cap as before."""
        for key in ("look", "pack", "tasks", "beam"):
            X.xess_unregister(key)
        A.boarding_scene_begin(_scene(PIM), "talk")
        X.xess_open(CID, None)
        self.build()
        said = [t for t in self.texts if "You are from" in t[0]]
        self.assertTrue(said, "the line is not on the home")
        top = min(t[2] for t in said)
        crew = [t for t in self.texts if "$text:`Crew`;font:gui-3" in t[0]][0]
        # The first tile's title sits under the band plus the tile's own 10px top padding.
        self.assertAlmostEqual(X.BEAT_PX + 10, (crew[2] - top) * 9.6, delta=2)

    def test_the_line_never_overlaps_the_first_tile(self):
        A.boarding_scene_begin(_scene(PIM), "talk")
        X.xess_open(CID, None)
        self.build()
        first = self.tile_rows()[0][1]
        said = [t for t in self.texts if "nine days ago" in t[0] or "You are from" in t[0]]
        for t in said:
            self.assertLessEqual(t[4], first[2] + 0.01,
                                 "the scene's line runs into the first tile: %r" % (t,))


if __name__ == "__main__":
    unittest.main()
