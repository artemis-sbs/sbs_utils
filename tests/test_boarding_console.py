"""The crew console builds, and then UPDATES rather than repainting.

The single most-repeated GUI mistake in this codebase is answering "the number moved"
with "rebuild the screen". A repaint is not a local redraw: it re-sends every widget on
the page across the network to that console, and a watcher does it forever. It is also
how a screen gets caught mid-build - reported from play as "it repaints empty" and "there
are two list boxes".

These tests cover the parts that can be driven without a live page: the per-console
revision, the fallbacks for a console with no character, and - as SOURCE assertions - the
two structural rules that are invisible until a real console draws. `gui_layout_widget`
in a row with MAST controls does not overlap them, it makes them vanish; and drawing any
of the three selection-following grid widgets would make each person's portrait follow
whoever clicked last.

WHAT IS NOT COVERED HERE, and should be said rather than implied: nothing in this file
builds the screen for real, so "the tick updates instead of repainting" is asserted by
construction (the `on change` calls a function, `gui_rebuild` touches only the actions
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
from sbs_utils.procedural.lifeform import lifeform_spawn
from sbs_utils.procedural.query import to_id, to_object
from sbs_utils.procedural.spawn import npc_spawn, player_spawn

CID = 0x8000000000000001


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


class ItBuilds(_ConsoleBase):
    def test_the_revision_is_per_console_not_global(self):
        """One crew member answering must not repaint the other five screens."""
        other = 0x8000000000000002
        GuiClient(other)
        self.assertNotEqual(C.boarding_console_revision(CID),
                            C.boarding_console_revision(other))

    def test_the_revision_moves_when_the_character_moves(self):
        before = C.boarding_console_revision(CID)
        blob = to_object(self.fig).data_set
        blob.set("curx", 5, 0)
        blob.set("cury", 1, 0)
        self.assertNotEqual(before, C.boarding_console_revision(CID))

    def test_it_says_where_you_are_standing(self):
        where = C._where_text(CID)
        self.assertTrue(where)
        self.assertNotEqual("aboard", where, "a figure on the interior has a place")

    def test_a_console_with_no_body_still_answers(self):
        """The panel must draw for an observer, not raise. A console watching without a
        character is an ordinary state - it is what the main screen is."""
        self.assertEqual("aboard", C._where_text(0x8000000000000009))

    def test_who_falls_back_rather_than_raising(self):
        who, name, job = C._who(0x8000000000000009)
        self.assertIsNone(who)
        self.assertEqual("Observer", name)


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

    def test_the_tick_is_idempotent_when_nothing_changed(self):
        """Called every frame by an `on change`, so an unchanged revision must be free
        rather than doing the work again."""
        class _Page:
            pass
        page = _Page()
        setattr(page, C.VIEW, {"cid": CID, "rev": C.boarding_console_revision(CID)})
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


class TheSelectionFollowingWidgetsAreNotDrawn(unittest.TestCase):
    """`grid_object_list`, `grid_face` and `grid_control` all follow the engine's grid
    SELECTION, which is one value per SHIP. Drawing any of them would make each person's
    portrait and verb list follow whoever clicked most recently, which is the whole
    problem the crew console exists to avoid."""

    def test_none_of_them_appear_in_the_builder(self):
        import inspect
        src = inspect.getsource(C)
        for widget in ("grid_object_list", "grid_face", "grid_control"):
            self.assertNotIn('gui_layout_widget("%s")' % widget, src)


if __name__ == "__main__":
    unittest.main()
