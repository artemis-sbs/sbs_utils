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

    def test_NO_BADGE_TAG_FIRST_APPEARS_AFTER_THE_BUILD(self):
        self.badges = {}
        built = {s[1] for s in self.paint()}
        self.badges = {(6, 5): "tv:rock", (7, 5): "tv:dirt"}
        later = {s[1] for s in self.paint()}
        self.assertEqual(later - built, set())


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
