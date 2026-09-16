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


class TheFlowAndTheActionsNeverShareAPixel(unittest.TestCase):
    """The bug Doug reported as "text overlaps", pinned as geometry.

    The first version ran the flow section to y=97 with the prose row declared `1fr` - so
    it expanded to the bottom - and then pinned the choices region at y=60..97 ON TOP of
    it. A region is positioned on an ABSOLUTE screen area, the engine does not clip, and a
    TextArea clears only its own sub-region, so prose and buttons were painted into the
    same pixels.

    The fix is the idiom `messages_gui` already proves: the flow's last row RESERVES the
    band and the region is pinned to the SAME band, both stated once as one constant.
    These tests assert they agree by construction rather than by coincidence.
    """

    def test_the_reserved_row_and_the_region_are_the_same_band(self):
        self.assertIn("%dpx" % C.ACTIONS_BAND_PX, C.boarding_actions_reserve())
        self.assertIn("100-%dpx" % C.ACTIONS_BAND_PX, C.boarding_actions_area(66))

    def test_the_region_is_pinned_to_the_BOTTOM_not_a_guessed_percent(self):
        """A percentage would only line up with the flow at one screen height."""
        area = C.boarding_actions_area(66)
        self.assertIn("100;", area, "the band must end at the bottom of the screen")
        self.assertNotIn(",60,", area.replace(" ", ""))

    def test_the_region_starts_where_the_map_ends(self):
        for width in (50, 66, 80):
            self.assertIn("area: %d," % (width + 1), C.boarding_actions_area(width))

    def test_the_builder_reserves_the_band_BEFORE_opening_the_region(self):
        """Order matters: the row has to be in the flow, and the flow is done once the
        region is opened."""
        import inspect
        src = inspect.getsource(C.gui_boarding_console)
        reserve = src.index("boarding_actions_reserve()")
        region = src.index("boarding_actions_area(")
        self.assertLess(reserve, region)

    def test_the_flow_section_runs_to_the_bottom(self):
        """It must NOT stop short at a percentage - the reserved row is what keeps the
        prose out, and a section that stops early just leaves a gap the region covers."""
        import inspect
        src = inspect.getsource(C.gui_boarding_console)
        self.assertIn("PANEL_TOP, PANEL_RIGHT", src)
        self.assertNotIn("99,97", src.replace(" ", ""))


class TheFaceRowIsNotFlex(unittest.TestCase):
    """`gui_face` builds a SQUARE with no `measure()`, and `_measure_row_height` excludes
    squares by construction - "a row of nothing but squares therefore has no natural
    height at all and returns None, falling back to flex". So `row-height: content` on the
    face was a SECOND flex row competing with the prose row for the same space, which is
    invisible until something else is also flexing."""

    def test_it_declares_a_fixed_height(self):
        import inspect
        src = inspect.getsource(C.gui_boarding_console)
        face_at = src.index("gui_face(face)")
        row = src.rindex("gui_row(", 0, face_at)
        decl = src[row:face_at]
        self.assertNotIn("content", decl,
                         "a square cannot be measured, so `content` here means flex")
        self.assertIn("em", decl)


class TheChoicesAreAList(unittest.TestCase):
    """A stack of fixed rows in a fixed-height region spills: fixed rows are never scaled
    down, so past what fits the buttons draw over the map. A listbox scrolls, and it is
    the house pattern for anything repeating."""

    def test_the_choices_go_through_a_listbox(self):
        import inspect
        src = inspect.getsource(C._draw_actions)
        self.assertIn("gui_list_box(", src)

    def test_no_button_is_built_in_a_loop(self):
        """The for-loop handler trap: a handler registered in a loop captures the loop
        variable at its LAST value, so every button would answer with the last choice."""
        import inspect
        src = inspect.getsource(C._draw_actions)
        self.assertNotIn("for ", src.split("gui_list_box(")[0].split("choices = []")[-1])

    def test_the_item_template_returns_None(self):
        """The listbox only calls `resize_to_content()` when a template returns None; a
        returned size leaves the item section degenerate, which kills selection.

        Parsed rather than grepped - the first version of this test matched the word
        "returns" in the function's own docstring and failed on prose.
        """
        import ast
        import inspect
        import textwrap
        tree = ast.parse(textwrap.dedent(inspect.getsource(C._choice_row)))
        returns = [n for n in ast.walk(tree)
                   if isinstance(n, ast.Return) and n.value is not None]
        self.assertEqual([], returns, "an item template must return None")

    def test_a_covering_choice_says_so(self):
        class _Ch:
            label = "Read the panel"
            covering = "Dr Sorel"
        self.assertIn("covering for Dr Sorel", C._choice_text(_Ch()))

    def test_an_ordinary_choice_is_just_its_label(self):
        class _Ch:
            label = "Read the panel"
            covering = None
        self.assertEqual("Read the panel", C._choice_text(_Ch()))

    def test_the_way_home_is_always_drawn(self):
        """Even with no scene open and no choices - otherwise there is no way off the
        ship, and a region that draws nothing keeps its previous content on screen."""
        import inspect
        src = inspect.getsource(C._draw_actions)
        beam = src.index('gui_button("Beam up"')
        self.assertNotIn("if choices", src[src.index("gui_row(\"row-height: %dpx"):beam])


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
