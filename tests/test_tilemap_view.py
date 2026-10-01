"""The tile view: what a console is actually sent.

* **A first paint sends every tile; a step sends only what moved.** That is the cost the
  engine spike measured and the reason a tile map is affordable at all.
* **Actors are re-sent after tiles**, because the engine draws in send order.
* **Nothing out of sight is sent** - an unexplored tile is hidden and a hostile out of
  line of sight is not drawn.
* **A click names the world cell**, wherever the camera is.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import cosmos_dev.mock.sbs as sbs
from sbs_utils.agent import clear_shared
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.pages.layout.bounds import Bounds
from sbs_utils.pages.layout.tilemap_view import TileView
from sbs_utils.procedural import tilemap as T
from sbs_utils.procedural.gui.image import gui_image_add_atlas_grid

CID = 7
KINDS = {"dirt": {"cell": "tv:dirt"}, "rock": {"cell": "tv:rock", "walk": False}}

AREA = "area: field\ntileset: tv\nlegend:\n  .: dirt\n  #: rock\n---\n" + \
    "\n".join(["#" * 40] + ["#" + "." * 38 + "#"] * 28 + ["#" * 40]) + "\n"


class ViewBase(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(CID, "gui_present"))
        self.addCleanup(setattr, FrameContext, "context", None)
        clear_shared()
        T.tilemap_clear()
        self.addCleanup(T.tilemap_clear)
        gui_image_add_atlas_grid("media/tiles", 16, 16, ["tv:dirt", "tv:rock"], cell=64)
        T.tilemap_tileset("tv", KINDS)
        T.tilemap_load(AREA)
        T._WATCH["task"] = object()
        self.now = 0.0
        T.tilemap_set_clock(0.0)
        T.tilemap_place(1, "field", 5, 5, sprite="tv:dirt", party=True)
        self.sent = []
        orig_img, orig_click = sbs.send_gui_image, sbs.send_gui_clickregion
        sbs.send_gui_image = lambda c, p, tag, props, *r: self.sent.append(("img", tag, props, r))
        sbs.send_gui_clickregion = lambda c, p, tag, props, *r: self.sent.append(("clk", tag, props, r))
        self.addCleanup(setattr, sbs, "send_gui_image", orig_img)
        self.addCleanup(setattr, sbs, "send_gui_clickregion", orig_click)
        self.clicks = []
        self.view = TileView("tv", follow=1, cols=16,
                             on_click=lambda *a: self.clicks.append(a))
        self.view.set_bounds(Bounds(0, 0, 66, 100))

    def paint(self):
        self.sent.clear()
        self.view.present(FakeEvent(CID, "gui_present"))
        return list(self.sent)

    def walk(self, x, y):
        T.tilemap_walk(1, x, y)
        for _ in range(400):
            self.now += 0.05
            T.tilemap_set_clock(self.now)
            T.tilemap_tick()
            if not T.tilemap_walking(1):
                return


def _shown_slots(sent):
    """Figure slot sends that put something ON the map (not parked, not void)."""
    return [x for x in sent if ":a" in x[1] and "color:#000" not in x[2]]


class TestWhatIsSent(ViewBase):
    def test_the_first_paint_sends_the_whole_viewport(self):
        from sbs_utils.pages.layout.tilemap_view import ACTOR_SLOTS
        sent = self.paint()
        tiles = [s for s in sent if s[0] == "img" and ":t" in s[1]]
        clicks = [s for s in sent if s[0] == "clk"]
        slots = [s for s in sent if s[0] == "img" and ":a" in s[1]]
        rows = self.view._geometry[0]
        self.assertEqual(len(tiles), 16 * rows)
        self.assertEqual(len(clicks), 16 * rows)
        self.assertEqual(len(slots), ACTOR_SLOTS)

    def test_a_view_is_never_wider_than_max_cols(self):
        """A whole big map at once is thousands of widgets in one section; the engine
        crashed drawing ones that size. Wider asks are drawn MAX_COLS wide."""
        from sbs_utils.pages.layout.tilemap_view import MAX_COLS
        wide = TileView("tvw", follow=1, cols=91)
        self.assertEqual(wide.cols, MAX_COLS)
        self.assertEqual(TileView("tvn", follow=1, cols=17).cols, 17)

    def test_a_full_pool_drops_furniture_never_a_person(self):
        """A crowded view (a furnished deck, a city street) can hold more things than the
        figure pool: whatever is left out must be furniture, not someone standing there."""
        from sbs_utils.pages.layout.tilemap_view import ACTOR_SLOTS
        self.view.fog = False                     # every one of them in view
        n = 0
        for y in range(1, 12):
            for x in range(1, 15):
                if n < ACTOR_SLOTS + 10 and (x, y) != (5, 5):
                    n += 1
                    T.tilemap_place(1000 + n, "field", x, y, sprite="tv:rock", fixed=True)
        # A high id, so it comes after all the furniture in the world's own order.
        T.tilemap_place(99999, "field", 6, 6, sprite="tv:dirt", party=False)
        self.paint()
        people = {aid for aid in self.view._slots if aid in (1, 99999)}
        self.assertEqual(people, {1, 99999})
        self.assertEqual(len(self.view._slots), ACTOR_SLOTS)

    def test_NOTHING_IS_EVER_SENT_EMPTY(self):
        """An empty image never becomes a widget, so it can never be updated later."""
        for kind, tag, props, _ in self.paint():
            if kind == "img":
                self.assertTrue(props, f"{tag} sent with no image")

    def test_NO_TAG_FIRST_APPEARS_AFTER_THE_BUILD(self):
        """Engine rule: an out-of-band update only changes a tag the BUILD made. Fog
        lifting, the camera paging and a new actor appearing must all reuse build tags."""
        built = {s[1] for s in self.paint()}
        self.walk(30, 20)                              # the camera pages, fog lifts
        T.tilemap_place(2, "field", 31, 20, sprite="tv:rock", party=False)
        later = {s[1] for s in self.paint()}
        self.assertTrue(later)
        self.assertEqual(later - built, set())

    def test_EVERY_CLICK_REGION_HAS_A_STYLE(self):
        """An empty style draws a magenta hover square in the engine."""
        for kind, tag, props, _ in self.paint():
            if kind == "clk":
                self.assertIn("background_color", props)

    def test_a_repaint_with_nothing_changed_sends_nothing(self):
        self.paint()
        self.assertEqual(self.paint(), [])

    def test_a_step_sends_little(self):
        self.paint()
        self.walk(6, 5)
        sent = self.paint()
        self.assertLess(len(sent), 90)
        self.assertEqual(len(_shown_slots(sent)), 1)

    def test_ACTORS_GO_AFTER_TILES(self):
        """The engine draws in send order."""
        sent = self.paint()
        last_tile = max(i for i, s in enumerate(sent) if ":t" in s[1])
        first_slot = min(i for i, s in enumerate(sent) if ":a" in s[1])
        self.assertGreater(first_slot, last_tile)


class TestFog(ViewBase):
    def test_an_unexplored_tile_is_the_void_look(self):
        sent = self.paint()
        void = [s for s in sent if ":t" in s[1] and "color:#000" in s[2]]
        self.assertTrue(void)                      # far corners are unexplored

    def test_a_hostile_out_of_sight_is_not_shown(self):
        T.tilemap_place(2, "field", 14, 14, sprite="tv:rock", party=False)
        self.assertEqual(len(_shown_slots(self.paint())), 1)   # only the crew member

    def test_a_hostile_in_sight_is_shown(self):
        T.tilemap_place(2, "field", 7, 5, sprite="tv:rock", party=False)
        self.assertEqual(len(_shown_slots(self.paint())), 2)

    def test_fog_lifting_repaints_tiles(self):
        self.paint()
        self.walk(20, 5)
        sent = self.paint()
        lit = [s for s in sent if ":t" in s[1] and "color:#000" not in s[2]]
        self.assertTrue(lit)


class TestCamera(ViewBase):
    def test_the_camera_holds_still_then_pages(self):
        self.paint()
        cam = self.view._camera
        self.walk(7, 5)
        self.paint()
        self.assertEqual(self.view._camera, cam)   # still well inside
        self.walk(30, 20)
        self.paint()
        self.assertNotEqual(self.view._camera, cam)
        self.assertIsNotNone(self.view.view_cell(30, 20))

    def test_a_click_names_the_world_cell(self):
        self.walk(30, 20)
        self.paint()
        vx, vy = self.view.view_cell(31, 21)
        self.view.on_message(FakeEvent(CID, "gui_message", sub_tag=f"tv:c{vx}_{vy}"))
        self.assertEqual(self.clicks, [(CID, "field", 31, 21)])

    def test_someone_elses_click_tag_is_ignored(self):
        self.paint()
        self.view.on_message(FakeEvent(CID, "gui_message", sub_tag="other:c1_1"))
        self.assertEqual(self.clicks, [])


class TestTallSprites(ViewBase):
    """3/4 art: a figure taller than its cell, a ship several cells wide."""

    def setUp(self):
        super().setUp()
        from sbs_utils.procedural.gui.image import ImageAtlas
        from sbs_utils.procedural import tilemap_art as TA
        ImageAtlas("tv:tall", "media/tiles", 0, 0, 64, 96)
        ImageAtlas("tv:ship", "media/tiles", 0, 0, 256, 192)
        TA.tilemap_sprite_size("tv:tall", 1, 1.5)
        TA.tilemap_sprite_size("tv:ship", 4, 3, anchor=(0.5, 1.0))
        self.addCleanup(TA.tilemap_art_clear)
        T.tilemap_set_sprite(1, sprite="tv:tall")

    def figure(self, sent, aid=1):
        slot = self.view._slots[aid]
        return [s for s in sent if s[1] == f"tv:a{slot}"][-1]

    def cell(self, sent, x, y):
        return next(s for s in sent if s[1] == "tv:t%d_%d" % self.view.view_cell(x, y))[3]

    def test_a_tall_figure_stands_on_its_cell_and_rises_above_it(self):
        sent = self.paint()
        l, t, r, b = self.cell(sent, 5, 5)
        fl, ft, fr, fb = self.figure(sent)[3]
        self.assertAlmostEqual(fb, b)
        self.assertAlmostEqual(fl, l)
        self.assertAlmostEqual(ft, b - 1.5 * (b - t))

    def test_a_wide_set_piece_is_centered_on_its_anchor(self):
        T.tilemap_place(9, "field", 8, 8, sprite="tv:ship", fixed=True)
        T.tilemap_reveal_all("field")
        sent = self.paint()
        l, t, r, b = self.cell(sent, 8, 8)
        sl, st, sr, sb = self.figure(sent, 9)[3]
        self.assertAlmostEqual((sl + sr) / 2, (l + r) / 2)
        self.assertAlmostEqual(sr - sl, 4 * (r - l))

    def test_the_southern_figure_is_sent_last(self):
        T.tilemap_place(2, "field", 5, 6, sprite="tv:tall", party=True)
        sent = self.paint()
        figs = [s[1] for s in sent if ":a" in s[1] and "color:#000" not in s[2]]
        self.assertEqual(figs[-1], f"tv:a{self.view._slots[2]}")

    def test_OVERTAKING_RE_SENDS_IN_ROW_ORDER(self):
        """Walk the northern figure past the southern one: it must now be drawn over it."""
        T.tilemap_place(2, "field", 6, 6, sprite="tv:tall", party=True)
        self.paint()
        T.tilemap_place(1, "field", 5, 7)
        sent = self.paint()
        figs = [s[1] for s in sent if ":a" in s[1] and "color:#000" not in s[2]]
        self.assertEqual(figs, [f"tv:a{self.view._slots[2]}", f"tv:a{self.view._slots[1]}"])

    def test_A_TALL_FIGURE_IN_THE_TOP_ROW_IS_CROPPED_TO_THE_VIEW(self):
        self.paint()
        left, top = self.view._camera[1], self.view._camera[2]
        T.tilemap_place(1, "field", left + 2, top)
        sent = self.paint()
        _, _, props, (fl, ft, fr, fb) = self.figure(sent)
        y0 = self.view._geometry[4]
        self.assertAlmostEqual(ft, y0)
        # A third of the picture is above the view: the crop starts a third down.
        self.assertIn("sub_rect:0,32,64,96", props)

    def test_NO_TAG_FIRST_APPEARS_AFTER_THE_BUILD_WITH_TALL_ART(self):
        built = {s[1] for s in self.paint()}
        T.tilemap_place(9, "field", 8, 8, sprite="tv:ship", fixed=True)
        self.walk(12, 12)
        later = {s[1] for s in self.paint()}
        self.assertEqual(later - built, set())

    def test_a_plain_sprite_still_fills_exactly_its_cell(self):
        T.tilemap_set_sprite(1, sprite="tv:dirt")
        sent = self.paint()
        self.assertEqual(self.figure(sent)[3], self.cell(sent, 5, 5))


class TestFringes(ViewBase):
    """Where the dirt field meets its rock border, rock frays onto the dirt."""

    def setUp(self):
        super().setUp()
        from sbs_utils.procedural.gui.image import ImageAtlas
        for side in "nesw":
            ImageAtlas("tv:rock_f" + side, "media/tiles", 0, 0, 64, 64)
        T.tilemap_tileset("tv", {
            "dirt": {"cell": "tv:dirt", "over": 1},
            "rock": {"cell": "tv:rock", "walk": False, "over": 2,
                     "fringe": {s: "tv:rock_f" + s for s in "nesw"}}})
        T.tilemap_reveal_all("field")
        T.tilemap_place(1, "field", 2, 2)            # the camera sits on the corner

    def test_FRINGES_GO_BETWEEN_GROUND_AND_FIGURES(self):
        sent = self.paint()
        idx = {s[1]: i for i, s in enumerate(sent)}
        fr = [i for t, i in idx.items() if ":f" in t and "color:#000" not in sent[i][2]]
        self.assertTrue(fr, "no fringe drawn at the rock border")
        last_tile = max(i for t, i in idx.items() if ":t" in t)
        figures = [i for t, i in idx.items() if ":a" in t and "color:#000" not in sent[i][2]]
        self.assertGreater(min(fr), last_tile)
        self.assertLess(max(fr), min(figures))

    def test_NO_FRINGE_TAG_FIRST_APPEARS_AFTER_THE_BUILD(self):
        built = {s[1] for s in self.paint()}
        self.walk(20, 14)
        later = {s[1] for s in self.paint()}
        self.assertEqual(later - built, set())

    def test_nothing_unseen_is_frayed(self):
        T.tilemap_area("field")["explored"] = {(2, 2)}
        sent = self.paint()
        self.assertFalse([s for s in sent if ":f" in s[1] and "color:#000" not in s[2]])


class TestHintBadges(ViewBase):
    """Badges over what is still worth a look (``boarding_hints``)."""

    def setUp(self):
        super().setUp()
        self.badges = {(6, 5): "tv:rock"}
        self.view.hints = lambda cid, area: dict(self.badges)

    def test_a_badge_sits_in_the_corner_of_its_tile(self):
        sent = self.paint()
        tile = next(s for s in sent if s[1] == "tv:t%d_%d" % self.view.view_cell(6, 5))
        badge = [s for s in sent if ":h" in s[1] and "color:#000" not in s[2]]
        self.assertEqual(len(badge), 1)
        (tl, tt, tr, tb), (bl, bt, br, bb) = tile[3], badge[0][3]
        self.assertAlmostEqual(br, tr)
        self.assertAlmostEqual(bt, tt)
        self.assertLess(br - bl, tr - tl)

    def test_BADGES_GO_AFTER_FIGURES(self):
        """Send order is draw order: a figure re-sent must not cover a badge."""
        self.paint()
        self.walk(6, 6)
        sent = self.paint()
        last_figure = max(i for i, s in enumerate(sent) if ":a" in s[1])
        first_badge = min(i for i, s in enumerate(sent) if ":h" in s[1])
        self.assertGreater(first_badge, last_figure)

    def test_a_dealt_with_thing_loses_its_badge(self):
        self.paint()
        self.badges.clear()
        sent = self.paint()
        self.assertTrue(any(":h0" in s[1] and "color:#000" in s[2] for s in sent))

    def test_a_badge_rides_above_a_tall_figure(self):
        from sbs_utils.procedural.gui.image import ImageAtlas
        from sbs_utils.procedural import tilemap_art as TA
        ImageAtlas("tv:tall", "media/tiles", 0, 0, 64, 96)
        TA.tilemap_sprite_size("tv:tall", 1, 1.5)
        self.addCleanup(TA.tilemap_art_clear)
        T.tilemap_place(3, "field", 6, 5, sprite="tv:tall", fixed=True)
        sent = self.paint()
        tile = next(s for s in sent if s[1] == "tv:t%d_%d" % self.view.view_cell(6, 5))
        badge = next(s for s in sent if ":h" in s[1] and "color:#000" not in s[2])
        th = tile[3][3] - tile[3][1]
        self.assertAlmostEqual(badge[3][1], tile[3][1] - 0.5 * th)

    def test_NO_BADGE_TAG_FIRST_APPEARS_AFTER_THE_BUILD(self):
        self.badges = {}
        built = {s[1] for s in self.paint()}
        self.badges = {(6, 5): "tv:rock", (7, 5): "tv:dirt"}
        later = {s[1] for s in self.paint()}
        self.assertEqual(later - built, set())

    def test_a_badge_can_carry_a_tint(self):
        self.badges = {(6, 5): ("tv:rock", "#fa0")}
        badge = [s for s in self.paint() if ":h" in s[1] and "color:#000" not in s[2]]
        self.assertEqual(len(badge), 1)
        self.assertIn("color:#fa0", badge[0][2])


class TestTintsAndGeneratedWindows(ViewBase):
    """A generated window (a galaxy around what the console looks at) with per-cell
    tints: panning regenerates the window, so it must reuse the build's tags."""

    def setUp(self):
        super().setUp()
        self.origin = 0
        self.view = TileView("gw", area="win", cols=12, fog=False,
                             on_click=lambda *a: self.clicks.append(a))
        self.view.set_bounds(Bounds(0, 0, 66, 100))
        self.regen()

    def regen(self):
        o = self.origin
        T.tilemap_generate("win", 12, 30,
                           lambda x, y: ("rock", "#0a6") if (x + o) % 5 == 0 else "dirt",
                           "tv")

    def tile(self, sent, x, y):
        vx, vy = self.view.view_cell(x, y)
        return next(s for s in sent if s[1] == f"gw:t{vx}_{vy}")

    def test_a_tinted_tile_is_sent_in_its_tint(self):
        sent = self.paint()
        self.assertIn("color:#0a6", self.tile(sent, 0, 15)[2])
        self.assertIn("color:white", self.tile(sent, 1, 15)[2])

    def test_fog_grey_wins_over_a_tint(self):
        """Seen-but-not-in-sight is information; a tint must not hide it."""
        self.view.fog = True
        T.tilemap_reveal_all("win")
        sent = self.paint()
        self.assertIn("color:#777", self.tile(sent, 0, 15)[2])

    def test_A_PAN_SENDS_NO_NEW_TAG(self):
        built = {s[1] for s in self.paint()}
        self.origin = 2
        self.regen()
        later = self.paint()
        self.assertTrue(later)
        self.assertEqual({s[1] for s in later} - built, set())

    def test_an_identical_regeneration_sends_nothing(self):
        self.paint()
        self.regen()
        self.assertEqual(self.paint(), [])

    def test_a_click_names_the_window_cell(self):
        self.paint()
        vx, vy = self.view.view_cell(4, 15)
        self.view.on_message(FakeEvent(CID, "gui_message", sub_tag=f"gw:c{vx}_{vy}"))
        self.assertEqual(self.clicks[-1][1:], ("win", 4, 15))

    def test_a_view_built_before_its_area_says_so(self):
        from unittest import mock
        late = TileView("late", area="not_yet", cols=6)
        late.set_bounds(Bounds(0, 0, 50, 50))
        with mock.patch("sbs_utils.procedural.execution.log") as log:
            late.present(FakeEvent(CID, "gui_present"))
            late.present(FakeEvent(CID, "gui_present"))
        self.assertEqual(log.call_count, 1)
        self.assertIn("before its area", log.call_args[0][0])


if __name__ == "__main__":
    unittest.main()


# --- the whole page path: a real MAST page, clicked the way the engine delivers it ----

import os as _os
import tempfile as _tempfile

_CLICKS = []


def tv_page_click(client_id, area, x, y):
    _CLICKS.append((client_id, area, x, y))


class TestAClickThroughTheRealPage(unittest.TestCase):
    """The engine delivers a click as `gui_message` to `Gui.on_message`; the page walks
    its layouts; the view must hear it. A unit call to `view.on_message` skips all that."""

    def setUp(self):
        from sbs_utils.handlerhooks import reset_mission_state
        from sbs_utils.gui import Gui
        from sbs_utils.mast.maststory import MastStory
        from sbs_utils.mast.mast_globals import MastGlobals
        from sbs_utils.mast_sbs.maststorypage import StoryPage
        from sbs_utils.mast.mastscheduler import MastScheduler
        import sbs_utils.mast_sbs.story_nodes  # noqa: F401
        reset_mission_state()
        sbs.create_new_sim()
        sbs.resume_sim()
        clear_shared()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(0, "test"))
        T.tilemap_clear()
        self.addCleanup(T.tilemap_clear)
        gui_image_add_atlas_grid("media/tiles", 16, 16, ["tv:dirt", "tv:rock"], cell=64)
        T.tilemap_tileset("tv", KINDS)
        T.tilemap_load(AREA)
        T._WATCH["task"] = object()
        _CLICKS.clear()
        MastGlobals.import_python_function(tv_page_click)
        self.rte = []
        self._orig = MastScheduler.on_runtime_error
        MastScheduler.on_runtime_error = self.rte.append
        self.addCleanup(setattr, MastScheduler, "on_runtime_error", self._orig)
        tmp = _tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        story = MastStory()
        story.basedir = tmp.name
        errors = story.compile("\n".join([
            'gui_section("area: 0, 0, 66, 100;")',
            'gui_tilemap(77, "field", on_click=tv_page_click)',
            "await gui()", ""]), "tvpage", story)
        self.assertEqual(errors, [])
        T.tilemap_place(77, "field", 5, 5, sprite="tv:dirt", party=True)

        class TvPage(StoryPage):
            pass
        TvPage.story = story
        FrameContext.mast = story
        self.page = TvPage()
        self.Gui = Gui
        Gui.clients = {}
        from sbs_utils.gui import GuiClient
        GuiClient(CID)
        self.sent = []
        orig = sbs.send_gui_clickregion
        sbs.send_gui_clickregion = lambda c, p, tag, props, *r: (self.sent.append(tag), orig(c, p, tag, props, *r))
        self.addCleanup(setattr, sbs, "send_gui_clickregion", orig)
        Gui.push(CID, self.page)     # presents at once: record BEFORE it
        self.present()

    def tearDown(self):
        self.Gui.clients = {}
        FrameContext.task = None
        FrameContext.page = None
        FrameContext.mast = None

    def present(self):
        for _ in range(2):
            sbs.sim._time_tick_counter += 30
            FrameContext.context = Context(sbs.sim, sbs, FakeEvent(CID, "gui_present"))
            self.page.gui_state = "repaint"
            self.page.present(FakeEvent(CID, "gui_present"))
        self.assertEqual(self.rte, [])

    def test_a_tile_click_reaches_the_handler(self):
        tags = [t for t in self.sent if ":c" in str(t)]
        self.assertTrue(tags, "the page sent no tile click regions")
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(CID, "gui_message"))
        self.Gui.on_message(FakeEvent(client_id=CID, tag="gui_message", sub_tag=tags[20]))
        self.assertEqual(len(_CLICKS), 1)
        self.assertEqual(_CLICKS[0][:2], (CID, "field"))

    def test_THE_REPAINT_AFTER_A_STEP_DOES_NOT_RAISE(self):
        """Engine-found: the view kept its camera edge in `self.margin`, which the layout
        overwrites with a Bounds - the first repaint after a step raised a TypeError."""
        from sbs_utils.pages.layout.dirty import Dirty
        T.tilemap_set_clock(0.0)
        T.tilemap_walk(77, 30, 20)
        for i in range(200):
            T.tilemap_set_clock(i * 0.1)
            T.tilemap_tick()
            Dirty.represent_dirty()
        self.assertEqual(T.tilemap_where(77), ("field", 30, 20))
