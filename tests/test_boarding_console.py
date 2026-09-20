"""The crew console builds, and then UPDATES rather than repainting.

The single most-repeated GUI mistake in this codebase is answering "the number moved"
with "rebuild the screen". A repaint is not a local redraw: it re-sends every widget on
the page across the network to that console, and a watcher does it forever. It is also
how a screen gets caught mid-build - reported from play as "it repaints empty" and "there
are two list boxes".

TWO BANDS NOW, NOT THREE. The column is an identity bar and one app area, because every
one of the device's functions is an app - answering the scene and leaving the surface
included. The three-band version needed a reserve row whose height had to equal two
pinned regions added together, and most of the geometry tests in this file used to guard
that arithmetic. They are gone with the arithmetic: what is left is the one property that
still matters, which is that the two bands are ADJACENT and share an edge by
construction.

WHAT IS NOT COVERED HERE, and should be said rather than implied: nothing in this file
builds the screen for real, so "the tick updates instead of repainting" is asserted by
construction (the `on change` calls a function; `gui_rebuild` touches only the app
region) rather than measured. Counting `page.pending_layouts` either side of a tick would
measure it, and needs a driven page - `reference_drive_a_mast_panel_headless` is the
recipe. Until then the browser pass is what proves the layout.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir

test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.gui import GuiClient
from sbs_utils.procedural import boarding as A
from sbs_utils.procedural import boarding_site as B
from sbs_utils.procedural.gui import boarding_console as C
from sbs_utils.procedural.gui import xess as X
from sbs_utils.procedural.lifeform import lifeform_spawn
from sbs_utils.procedural.query import to_id, to_object
from sbs_utils.procedural.spawn import npc_spawn, player_spawn

CID = 0x8000000000000001
OTHER = 0x8000000000000002


class _ConsoleBase(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        SpaceObject.clear()
        A.boarding_clear()
        B.boarding_site_clear()
        GuiClient(CID)
        self.ship = to_object(player_spawn(0, 0, 0, "Artemis", "tsn", "tsn_light_cruiser"))
        self.site = to_object(npc_spawn(3000, 0, 3000, "Kepler", "tsn",
                                        "tsn_destroyer", "behav_station"))
        B.boarding_site_build(self.site)
        self.who = lifeform_spawn("Lt Marek", "terran_male", "boarding,science")
        A.boarding_invite(self.ship, [self.who], title="Kepler")
        A.boarding_beam_down(CID, self.who)
        self.fig = B.boarding_figure_spawn(self.site, self.who, 3, 1)
        B.boarding_take(CID, self.fig, self.site)

    def tearDown(self):
        B.boarding_site_clear()
        X.xess_clear()


class ItBuilds(_ConsoleBase):
    def test_the_revision_is_per_console_not_global(self):
        """One crew member answering must not repaint the other five screens."""
        GuiClient(OTHER)
        self.assertNotEqual(C.boarding_console_revision(CID),
                            C.boarding_console_revision(OTHER))

    def test_the_revision_moves_when_the_character_moves(self):
        before = C.boarding_console_revision(CID)
        blob = to_object(self.fig).data_set
        blob.set("curx", 5, 0)
        blob.set("cury", 1, 0)
        self.assertNotEqual(before, C.boarding_console_revision(CID))

    def test_it_says_where_you_are_standing(self):
        where = C.where_text(CID)
        self.assertTrue(where)
        self.assertNotEqual("aboard", where, "a figure on the interior has a place")

    def test_a_console_with_no_body_still_answers(self):
        """The column must draw for an observer, not raise. A console watching without a
        character is an ordinary state - it is what the main screen is."""
        self.assertEqual("aboard", C.where_text(0x8000000000000009))

    def test_the_identity_falls_back_rather_than_raising(self):
        name, job, at = X._identity(0x8000000000000009)
        self.assertEqual("Observer", name)
        self.assertEqual("aboard", at)


class ItUpdatesInPlace(_ConsoleBase):
    """The tick has to be reachable without a real page, so these drive the parts."""

    def setUp(self):
        super().setUp()
        # PUT THE PAGE BACK. These tests move `FrameContext.page`, which is global - the
        # first version left it pointing at a fake object and 103 tests in unrelated
        # files errored, none of them mine. A fixture that borrows shared state has to
        # give it back in the same breath.
        self.addCleanup(setattr, FrameContext, "page", FrameContext.page)

    def test_a_tick_with_no_screen_is_a_quiet_no(self):
        """A handler can outlive the page that registered it. That must not raise."""
        FrameContext.page = None
        self.assertFalse(C.gui_boarding_console_tick())
        self.assertFalse(X.gui_xess_tick())

    def test_the_tick_is_idempotent_when_nothing_changed(self):
        """Called every frame by an `on change`, so an unchanged revision must be free
        rather than doing the work again."""
        class _Page:
            client_id = CID
        page = _Page()
        setattr(page, C.VIEW, {"cid": CID, "rev": C.boarding_console_revision(CID)})
        setattr(page, X.VIEW, {"cid": CID, "rev": X.xess_revision(CID)})
        FrameContext.page = page
        self.assertTrue(C.gui_boarding_console_tick())


class TheMapIsNeverInARowWithControls(unittest.TestCase):
    """`gui_layout_widget` must have its own section.

    The engine draws its widget at its own size over whatever MAST put beside it, so
    controls sharing the row do not overlap - they vanish. Pinned as source, because it
    is invisible at build time and only shows on a real console.
    """

    def test_the_builder_gives_the_interior_its_own_section(self):
        import inspect
        src = inspect.getsource(C.gui_boarding_console)
        map_at = src.index('gui_layout_widget("ship_internal_view")')
        before = src[:map_at]
        self.assertIn("gui_section", before,
                      "the interior must be opened in its own section")
        # Nothing may be drawn between opening that section and the widget.
        last_section = before.rindex("gui_section")
        between = before[last_section:]
        for drawn in ("gui_text(", "gui_button(", "gui_face(", "gui_text_area("):
            self.assertNotIn(drawn, between,
                             "%s shares the interior's section - the engine will draw "
                             "over it" % drawn)


class TheTwoBandsShareAnEdge(unittest.TestCase):
    """The bug Doug reported as "text overlaps", pinned as geometry.

    The first version ran the flow to the bottom of the screen and then pinned regions ON
    TOP of it. A region is positioned on an ABSOLUTE screen area, the engine does not
    clip, and a TextArea clears only its own sub-region, so two things were painted into
    the same pixels.

    With one region the whole class of bug reduces to one property: the bar ENDS exactly
    where the app area BEGINS. These assert it holds by construction - both edges are
    `APP_TOP_PX`, so they cannot drift - rather than by two numbers happening to match.
    """

    def _edges(self, area):
        """The four coordinates of an area string, as written."""
        return [e.strip().rstrip(";")
                for e in area.split(":", 1)[1].split(",")]

    def test_the_bar_ends_where_the_app_area_begins(self):
        bar = self._edges(C.boarding_identity_area())
        app = self._edges(C.boarding_app_area())
        self.assertEqual(bar[3], app[1], "the bands do not share an edge")

    def test_and_that_edge_is_the_ONE_constant(self):
        """Two numbers that merely happen to be equal drift the first time one is
        changed. They have to be the same symbol."""
        self.assertIn("%dpx" % C.APP_TOP_PX, C.boarding_identity_area())
        self.assertIn("%dpx" % C.APP_TOP_PX, C.boarding_app_area())
        self.assertEqual(C.PANEL_TOP_PX + C.IDENTITY_PX, C.APP_TOP_PX)

    def test_the_bands_are_measured_in_PX_not_percent(self):
        """A percentage bar would be a different number of lines tall at every screen
        height, and the text in it does not scale with the screen."""
        bar = self._edges(C.boarding_identity_area())
        self.assertTrue(bar[1].endswith("px"))
        self.assertTrue(bar[3].endswith("px"))

    def test_the_app_area_runs_to_the_BOTTOM(self):
        self.assertTrue(C.boarding_app_area().rstrip(";").endswith("100"))

    def test_both_bands_start_where_the_map_ends(self):
        for width in (50, 66, 80):
            C.gui_boarding_console.__globals__["_map_width"] = width
            for area in (C.boarding_identity_area(), C.boarding_app_area()):
                self.assertIn("area: %d," % (width + 1), area)
        C.gui_boarding_console.__globals__["_map_width"] = C.MAP_WIDTH_DEFAULT

    def test_there_is_exactly_ONE_region_in_the_column(self):
        """The whole simplification. A second region would need something to keep the
        first one's content out of it, which is the reserve-row arithmetic this replaced.
        """
        import inspect
        # The builder, not `gui_xess` - that is now a one-line wrapper naming the
        # boarding SURFACE, and every panel is built by this one function.
        src = inspect.getsource(X.gui_xess_panel)
        self.assertEqual(1, src.count("gui_region("))


class ThePartsOfTheBarAllUpdate(_ConsoleBase):
    """A bar that is right about the room and stale about the name describes the previous
    person, which is worse than a blank one. The TNG face builder found this by poking
    only its face widget and leaving the description under it describing the last pick."""

    def test_the_tick_updates_every_part(self):
        import inspect
        src = inspect.getsource(X.gui_xess_tick)
        for part in ("name", "job", "at"):
            self.assertIn('view["%s"].update(' % part, src)

    def test_the_bar_shows_ARMED_instead_of_the_room(self):
        """The bar is the only band on screen in EVERY state, the tile sheet included, so
        it is the only place an armed weapon can be seen from everywhere."""
        plain = X._at_style(CID, "Sample Lab")
        B.boarding_arm(CID, B.SETTING_CUT)
        armed = X._at_style(CID, "Sample Lab")
        self.assertNotEqual(plain, armed)
        self.assertIn("ARMED", armed)
        self.assertIn(X.ARMED, armed)

    def test_the_revision_moves_the_instant_the_weapon_is_live(self):
        """Armed has to be visible the instant it is true - that is a safety feature, so
        the screen has to hear about it."""
        before = C.boarding_console_revision(CID)
        B.boarding_arm(CID)
        self.assertNotEqual(before, C.boarding_console_revision(CID))


class TheSelectionFollowingWidgetsAreNotDrawn(unittest.TestCase):
    """`grid_object_list`, `grid_face` and `grid_control` all follow the engine's grid
    SELECTION, which is one value per SHIP. Drawing any of them would make each person's
    portrait and verb list follow whoever clicked most recently, which is the whole
    problem the crew console exists to avoid."""

    def test_none_of_them_appear_in_the_builder(self):
        import inspect
        for module in (C, X):
            src = inspect.getsource(module)
            for widget in ("grid_object_list", "grid_face", "grid_control"):
                self.assertNotIn('gui_layout_widget("%s")' % widget, src)


if __name__ == "__main__":
    unittest.main()
