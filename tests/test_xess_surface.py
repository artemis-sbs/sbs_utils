"""A SURFACE is a place the xESS shell lives.

The device was written for one console - the handheld a boarding party carries - and its
shell reached straight into the boarding and EVA modules for its identity bar, its
revision and the app that opens itself. A second console (OpenUniverse's Admiral panel)
wants the same shell and has none of those things.

THREE THINGS HERE ARE LOAD-BEARING:

* **Boarding is untouched.** Same app table object, same inventory keys, same click tags.
  Every parameter defaults to the handheld, so no existing caller changed - and the eight
  boarding/EVA/xess test files pass unedited.
* **A non-boarding surface never reaches a boarding module.** Not as a condition inside a
  shared function, but structurally: everything boarding-specific is named by the boarding
  DESCRIPTOR, so nothing else can reach it. A panel on a console with no boarding party
  must not import one to draw a tile.
* **The bar and the app area repaint separately.** A panel whose bar carries a countdown
  would otherwise rebuild its app region every second, which on a screen holding a
  selectable queue replaces the row under the cursor.
"""
import unittest
from unittest import mock

from sbs_utils.fs import test_set_exe_dir

test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  (import first to break a circular import)
from cosmos_dev.mock import sbs
from sbs_utils.gui import GuiClient
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.procedural.gui import xess as X
from sbs_utils.procedural.inventory import get_inventory_value
from sbs_utils.spaceobject import SpaceObject

CID = 0x8000000000000001
MINE = "admiral"


def _draw(client_id):
    """An app that draws nothing - this file is about the shell, not the content."""
    return None


class _SurfaceBase(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        self.addCleanup(setattr, FrameContext, "page", FrameContext.page)
        self.addCleanup(setattr, FrameContext, "task", FrameContext.task)
        FrameContext.page = None
        FrameContext.task = None
        SpaceObject.clear()
        X.xess_clear()
        self.addCleanup(X.xess_clear)
        GuiClient(CID)
        X.xess_surface(MINE, title="Admiralty")
        X.xess_register("build", title="Build", draw=_draw, surface=MINE)


class ASurfaceKeepsItsOwnApps(_SurfaceBase):
    def test_a_mission_app_is_not_on_the_handheld(self):
        self.assertEqual(X.xess_registered(MINE), ["build"])
        self.assertNotIn("build", X.xess_registered())

    def test_the_handheld_still_has_its_builtins(self):
        self.assertIn("crew", X.xess_registered())
        self.assertIn("fire", X.xess_registered())

    def test_open_state_does_not_leak_between_surfaces(self):
        X.xess_open(CID, "build", MINE)
        self.assertEqual(X.xess_opened(CID, MINE), "build")
        self.assertIsNone(X.xess_opened(CID))

    def test_an_app_from_another_surface_cannot_be_opened(self):
        self.assertFalse(X.xess_open(CID, "build"))          # "build" is not on boarding
        self.assertFalse(X.xess_open(CID, "crew", MINE))     # "crew" is not on admiral

    def test_the_boarding_inventory_keys_are_the_ones_it_always_wrote(self):
        """A live client's open app must not move because the library was upgraded."""
        X.xess_open(CID, "crew")
        self.assertEqual(get_inventory_value(CID, "XESS_APP", None), "crew")
        X.xess_open(CID, "build", MINE)
        self.assertEqual(get_inventory_value(CID, "XESS_APP:admiral", None), "build")

    def test_a_mission_surface_is_forgotten_on_reset_and_boarding_is_restored(self):
        X.xess_clear()
        self.assertEqual(X.xess_registered(MINE), [])
        self.assertNotIn(MINE, X.xess_surfaces())
        self.assertIn("crew", X.xess_registered())
        self.assertIn(X.SURFACE_BOARDING, X.xess_surfaces())


class ItNeverReachesIntoBoarding(_SurfaceBase):
    """The structural promise. A panel on some other console must not drag the boarding
    party in behind it - not because a condition says so, but because nothing on that path
    names those modules."""

    def test_the_revision_asks_nothing_about_boarding(self):
        with mock.patch("sbs_utils.procedural.boarding.boarding_seq") as seq, \
             mock.patch("sbs_utils.procedural.boarding_site.boarding_armed") as armed:
            X.xess_revision(CID, MINE)
            self.assertEqual(seq.call_count, 0)
            self.assertEqual(armed.call_count, 0)
            X.xess_revision(CID)
            self.assertGreater(seq.call_count, 0)
            self.assertGreater(armed.call_count, 0)

    def test_leaving_an_app_does_not_disarm_anything(self):
        """Leaving FIRE disarms - that is the HANDHELD's rule, and a console with no
        weapon must not run it."""
        with mock.patch("sbs_utils.procedural.boarding_site.boarding_disarm") as disarm:
            X.xess_open(CID, "build", MINE)
            X.xess_open(CID, None, MINE)
            self.assertEqual(disarm.call_count, 0)

    def test_a_surface_with_no_descriptor_still_draws(self):
        X.xess_register("orphan", draw=_draw, surface="nowhere")
        self.assertEqual(X.xess_revision(CID, "nowhere")[:2], (None, None))


class TheBarAndTheAppRepaintSeparately(_SurfaceBase):
    """The reason the tick is split. The Admiral's bar carries a build countdown; its app
    region carries a queue you click. One must not rebuild the other."""

    def setUp(self):
        super().setUp()
        self.line = ["Sector (0,1)", "Federation", "idle"]
        X.xess_surface(MINE, title="Admiralty",
                       identity=lambda cid: tuple(self.line),
                       revision=lambda cid: self.app_rev,
                       identity_area="area: 72, 2, 100, 12;",
                       app_area="area: 72, 12, 100, 100;")
        self.app_rev = 0

    def _view(self):
        widgets = {k: mock.Mock() for k in ("name", "job", "at")}
        view = dict(widgets)
        # MagicMock, not Mock: the region is entered with `with` when it rebuilds.
        view.update({"cid": CID, "surface": MINE, "app": mock.MagicMock(),
                     "bar": X._bar_styles(CID, MINE),
                     "rev": X.xess_revision(CID, MINE)})

        class _Page:
            client_id = CID
        page = _Page()
        setattr(page, X._view_key(MINE), view)
        FrameContext.page = page
        return view, widgets

    def test_a_bar_change_alone_does_not_rebuild_the_app(self):
        view, widgets = self._view()
        self.line[2] = "Building Extractor 0:42"
        with mock.patch("sbs_utils.procedural.gui.update.gui_rebuild") as rebuild:
            self.assertTrue(X.gui_xess_tick(MINE))
            self.assertEqual(rebuild.call_count, 0)
        for w in widgets.values():
            self.assertEqual(w.update.call_count, 1)

    def test_an_app_change_rebuilds_the_region(self):
        view, _ = self._view()
        self.app_rev = 1
        # `_draw_app` is stubbed because drawing needs a real page and a task; what is
        # under test is WHETHER the region is rebuilt, not what lands in it.
        with mock.patch("sbs_utils.procedural.gui.update.gui_rebuild") as rebuild, \
             mock.patch.object(X, "_draw_app"):
            self.assertTrue(X.gui_xess_tick(MINE))
            self.assertEqual(rebuild.call_count, 1)

    def test_nothing_moving_is_free(self):
        self._view()
        with mock.patch("sbs_utils.procedural.gui.update.gui_rebuild") as rebuild:
            self.assertTrue(X.gui_xess_tick(MINE))
            self.assertEqual(rebuild.call_count, 0)

    def test_every_part_of_the_bar_updates_together(self):
        """A bar right about the room and stale about the name describes the previous
        person."""
        view, widgets = self._view()
        self.line[0] = "Kestrel Reach"
        X.gui_xess_tick(MINE)
        for w in widgets.values():
            self.assertEqual(w.update.call_count, 1)

    def test_a_tick_with_no_screen_is_a_quiet_no(self):
        FrameContext.page = None
        self.assertFalse(X.gui_xess_tick(MINE))


if __name__ == "__main__":
    unittest.main()
