"""The badge that is on screen without opening anything.

Playtest asked for two things the PADD could not give: see the crew character you are
playing, and know something is waiting before you go looking. Both are one small readout
that is always visible.

The rect is not a guess. `data/guiboxdata.txt` puts `ship_data` at `3, 5, 27, 47` on
helm, weapons, engineering, science and comms alike, so the band above it is the one
place identical on every console - and on science it has to stop at x=27, where
`radar_zoom_ctrl` (`27,0,68,6`) starts.

Driven through the real `gui_queue_console_tabs`, not by calling the model. The bug that
cost three reports was invisible to a model test because the model was right; only
building the screen showed it.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import cosmos_dev.mock.sbs as sbs
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.agent import clear_shared
from sbs_utils.gui import GuiClient
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.pages.layout.text import Text
from sbs_utils.procedural.inventory import set_inventory_value
from sbs_utils.procedural.gui import epadd as E

CID = 7

#: The engine's own numbers, from guiboxdata.txt. If these change the badge moves.
SHIP_DATA_LEFT, SHIP_DATA_TOP, SHIP_DATA_RIGHT = 3, 5, 27
#: Where science's radar zoom starts. The badge must not reach it.
SCIENCE_RADAR_LEFT = 27


class _Sim:
    time_tick_counter = 0


class _Main:
    def __init__(self, page):
        self.page = page


class _Task:
    def __init__(self):
        self.main = None

    def jump(self, label):
        pass

    def tick_in_context(self):
        pass

    def set_variable(self, *a, **k):
        pass

    def get_variable(self, *a, **k):
        return None

    def compile_and_format_string(self, s):
        return s

    def format_string(self, s):
        return s

    def eval_code_checked(self, code):
        return True

    def get_id(self):
        return 1


class _Label:
    """Stands in for the `//gui/tab/epadd` route, whose presence is what turns the
    strip into the PADD button."""

    def test(self, task):
        return True


class BadgeBase(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        clear_shared()
        FrameContext.context = Context(_Sim(), sbs, FakeEvent(CID, "test"))
        GuiClient(0)
        GuiClient(CID)
        page = StoryPage()
        page.pending_gui = False
        page.client_id = CID
        page.console = "normal_helm"
        page.gui_task = _Task()
        page.gui_task.main = _Main(page)
        page.pending_layouts = []
        page.pending_row = None
        self.page = page
        FrameContext.page = page
        FrameContext.task = page.gui_task
        set_inventory_value(CID, "CONSOLE_TYPE", "helm")

        from sbs_utils.mast_sbs.story_nodes.gui_tab_decorator_label import (
            GuiTabDecoratorLabel)
        self._saved_tabs = dict(GuiTabDecoratorLabel.all)
        GuiTabDecoratorLabel.all["epadd"] = _Label()
        self.addCleanup(self._restore, GuiTabDecoratorLabel)
        E.gui_app_mode(True)

    def _restore(self, cls):
        cls.all.clear()
        cls.all.update(self._saved_tabs)

    def tearDown(self):
        FrameContext.page = None
        FrameContext.task = None
        FrameContext.context = None

    def crew(self, name, rank=""):
        set_inventory_value(CID, "CREW_NAME", name)
        set_inventory_value(CID, "CREW_RANK", rank)

    def build(self):
        self.page.pending_layouts = []
        self.page.gui_queue_console_tabs()
        return self.page.pending_layouts

    def badge_layout(self):
        """The badge, as the page hands it over. A tab button subclasses Text, so
        walking the layouts for text finds the topbar instead."""
        self.build()
        return getattr(self.page, "identity_badge", None)

    def badge_text(self):
        """The badge's words, or None when no badge was drawn."""
        layout = self.badge_layout()
        if layout is None:
            return None
        for row in getattr(layout, "rows", None) or ():
            for col in getattr(row, "columns", None) or ():
                if isinstance(col, Text):
                    return col.message
        return None


class TestItSaysWhoYouAre(BadgeBase):
    def test_the_crew_member_is_on_screen(self):
        """The first thing the playtest asked for."""
        self.crew("Marek", "Lt")
        self.assertIn("Lt Marek", self.badge_text() or "")

    def test_a_crew_member_with_no_rank_is_just_their_name(self):
        self.crew("Marek")
        self.assertIn("Marek", self.badge_text() or "")

    def test_NOTHING_TO_SAY_DRAWS_NO_BOX(self):
        """A mission using none of this must not get an empty panel welded to every
        console."""
        self.assertIsNone(self.badge_text())

    def test_it_is_gone_when_epadd_is_off(self):
        """Opt-in, like everything else here - the classic strip is unchanged."""
        self.crew("Marek", "Lt")
        E.gui_app_mode(False)
        self.assertIsNone(self.badge_text())


class TestItSaysWhatIsWaiting(BadgeBase):
    def setUp(self):
        super().setUp()
        self.crew("Marek", "Lt")

    def register(self, tab, status):
        from sbs_utils.mast_sbs.story_nodes.gui_tab_decorator_label import (
            GuiTabDecoratorLabel)
        GuiTabDecoratorLabel.all[tab] = _Label()
        set_inventory_value(CID, "console_tabs",
                            dict(get_tabs(CID), **{tab: True}))
        E.gui_app_register(tab, title=tab.title(), status=status)

    def test_an_app_with_something_to_report_is_counted(self):
        self.register("messages", lambda: "3")
        self.assertIn("(1)", self.badge_text() or "")

    def test_two_of_them_count_as_two(self):
        self.register("messages", lambda: "3")
        self.register("quest", lambda: "!")
        self.assertIn("(2)", self.badge_text() or "")

    def test_an_app_with_nothing_to_report_is_not_counted(self):
        self.register("messages", lambda: "")
        self.assertNotIn("(", self.badge_text() or "")

    def test_A_PROVIDER_THAT_RAISES_COSTS_ONLY_ITS_OWN_BADGE(self):
        """The strip is drawn on every build of every console. A throwing status
        provider must not be able to take the badge - or the topbar - with it."""
        def boom():
            raise RuntimeError("no")
        self.register("messages", boom)
        self.assertIn("Lt Marek", self.badge_text() or "")


class TestWhereItSits(BadgeBase):
    """The rect, against the engine's own numbers.

    Percent across, PIXELS down. The band between the strip and ship data is a fixed
    height on every screen, and sizing it as a percentage grew it with the screen: on a
    real bridge the badge landed inside the info panel at 1024x768 and again, lower, on
    a bigger one.
    """

    def setUp(self):
        super().setUp()
        self.crew("Marek", "Lt")

    def style(self):
        """The area string the badge is placed with. Asserted at the source: once
        `apply_control_styles` has parsed it, `layout.bounds_style` is a style node
        and the numbers are no longer readable as text."""
        self.assertIsNotNone(self.badge_layout(), "no badge was drawn to place")
        return E.gui_app_identity_bounds()

    def parts(self):
        return [p.strip() for p in self.style().split(",")]

    def test_the_badge_is_actually_placed_with_it(self):
        """Guards the seam the rest of this class asserts across: the geometry is read
        from the function, so something has to check the layout uses it."""
        layout = self.badge_layout()
        self.assertIsNotNone(layout.bounds_style,
                             "the badge layout was never given an area")

    def px(self, i):
        return int(self.parts()[i].removesuffix("px"))

    def test_it_starts_where_ship_data_starts(self):
        """Left of that is the icon column, and that icon collapses the info panel."""
        self.assertEqual(self.px(0),
                         round(SHIP_DATA_LEFT / 100.0 * E.IDENTITY_BASELINE_W))

    def test_EVERY_EDGE_IS_PIXELS(self):
        """The correction. The engine DRAWS the info panel at a fixed size inside its
        percentage rect, so a percentage width grew out of the panel on a bigger screen
        and landed on the widgets beside it - measured on a real bridge."""
        for part in self.parts():
            self.assertTrue(part.endswith("px"), part)

    def test_IT_IS_NO_WIDER_THAN_THE_PANEL(self):
        """The reported fault, stated as the property that prevents it."""
        panel = round((SHIP_DATA_RIGHT - SHIP_DATA_LEFT) / 100.0
                      * E.IDENTITY_BASELINE_W)
        self.assertLessEqual(self.px(2) - self.px(0), panel)

    def test_and_that_width_does_not_move_with_the_screen(self):
        """A percentage width is the same number here but a different box on every
        console, which is exactly how it grew off the panel."""
        self.assertEqual(self.px(2) - self.px(0),
                         E.IDENTITY_RIGHT_PX - E.IDENTITY_LEFT_PX)

    def test_IT_STOPS_BEFORE_SCIENCES_RADAR_ZOOM(self):
        """The one console where the band is not free all the way across. Reaching
        past ship_data's right edge draws over the magnifiers on science."""
        self.assertLessEqual(self.px(2),
                             round(SCIENCE_RADAR_LEFT / 100.0
                                   * E.IDENTITY_BASELINE_W))

    def test_it_sits_below_the_strip(self):
        top = self.px(1)
        self.assertGreaterEqual(top, E.STRIP_PX)

    def test_IT_CLEARS_THE_INFO_PANEL_AT_1024x768(self):
        """The tightest case, and the one that was reported. Ship data starts at
        35 + 5% of (768 - 35) = 71.7px; anything at or past that is inside the panel.
        """
        self.assertLess(self.px(3), E.ship_data_top_px(768))

    def test_and_clears_it_on_a_bigger_screen_too(self):
        """A fixed band can only get safer as the screen grows - the percentage one
        got worse, which is why it failed on both."""
        for height in (1080, 1440, 2160):
            self.assertLess(self.px(3), E.ship_data_top_px(height), height)

    def test_the_band_is_the_same_height_on_every_screen(self):
        """The property a percentage cannot have, stated directly."""
        self.assertEqual(self.px(3) - self.px(1), E.IDENTITY_HEIGHT_PX)

    def test_it_has_its_own_background(self):
        """It draws over ship data's overhanging art, and that art goes away when the
        panel is collapsed - so borrowing it would leave text on the radar."""
        layout = self.badge_layout()
        row = (getattr(layout, "rows", None) or [None])[0]
        self.assertIsNotNone(row.background_color, "the badge row lost its background")


class TestItStaysCurrentWithoutARebuild(BadgeBase):
    """The case the badge exists for.

    A signal does not wake `await gui()`. A console parked on Helm all game never
    rebuilds its screen, so a badge that only updates on a build would be frozen at
    whatever it said when they sat down - which is exactly the crew member who never
    learns they have mail.
    """

    def setUp(self):
        super().setUp()
        self.crew("Marek", "Lt")
        self.waiting = ""
        from sbs_utils.mast_sbs.story_nodes.gui_tab_decorator_label import (
            GuiTabDecoratorLabel)
        GuiTabDecoratorLabel.all["messages"] = _Label()
        set_inventory_value(CID, "console_tabs", {"messages": True})
        E.gui_app_register("messages", title="Messages",
                           status=lambda: self.waiting)
        self.build()

    def tick(self, by=None):
        """Advance the sim past the throttle and run one present."""
        sim = FrameContext.context.sim
        sim.time_tick_counter += (by if by is not None
                                  else self.page.IDENTITY_REFRESH_TICKS)
        self.page._tick_identity_badge()

    def text(self):
        return self.page.identity_label.message

    def test_mail_arriving_moves_it_with_no_rebuild(self):
        self.assertNotIn("(1)", self.text())
        self.waiting = "3"
        self.tick()
        self.assertIn("(1)", self.text())

    def test_and_it_goes_away_again(self):
        self.waiting = "3"
        self.tick()
        self.waiting = ""
        self.tick()
        self.assertNotIn("(1)", self.text())

    def test_THE_THROTTLE_HOLDS_IT_BACK(self):
        """Reading it calls every status provider, so it must not run every frame."""
        self.waiting = "3"
        self.tick(by=0)
        self.assertNotIn("(1)", self.text())

    def test_A_RAISE_INSIDE_THE_REFRESH_DOES_NOT_TAKE_THE_CONSOLE_DOWN(self):
        """This runs inside `present`, on every console, every frame - so anything
        that throws here takes the whole screen with it.

        Patched at `gui_app_identity_text` rather than at a status provider: a
        provider that raises is already swallowed by `gui_app_badge`, so going in
        that way tests the wrong guard and passes with this one deleted.
        """
        def boom(*a, **k):
            raise RuntimeError("no")
        real, E.gui_app_identity_text = E.gui_app_identity_text, boom
        try:
            self.tick()
        finally:
            E.gui_app_identity_text = real
        self.assertIn("Lt Marek", self.text())

    def test_PRESENT_IS_WHAT_DRIVES_IT(self):
        """The wiring, not the method. Calling `_tick_identity_badge` by hand passes
        just as happily with the call removed from `present` - which would ship a
        badge that never moves on a real bridge.
        """
        self.waiting = "3"
        FrameContext.context.sim.time_tick_counter += (
            self.page.IDENTITY_REFRESH_TICKS)
        try:
            self.page.present(FakeEvent(CID, "test"))
        except Exception:
            pass                 # present goes on to do far more than we need here
        self.assertIn("(1)", self.text())

    def test_nothing_to_update_is_not_an_error(self):
        """A console with no badge at all still ticks."""
        self.page.identity_label = None
        self.tick()


class TestAwkwardNames(BadgeBase):
    """A crew name is authored content, and it lands inside a style string.

    `gui_text_escape` wraps the value in backticks so a `:` or `;` inside it is read
    as text, and STRIPS any backtick already in it - because that character is the
    quoting delimiter, so hand-writing the quotes leaves it unbalanced and the style
    parser loses the rest of the string. `tests/test_gui_text_quoting` enforces the
    escaping library-wide; this is the behaviour behind the rule.
    """

    def test_A_BACKTICK_IN_A_NAME_LEAVES_THE_QUOTES_BALANCED(self):
        """The case hand-quoting gets wrong: "O`Neil" written by hand produces
        `O`Neil`, three delimiters, and the style parser loses the rest of the string.

        Through the AWAY name deliberately. A crew post is run through `crew._plain`,
        which already turns a backtick into an apostrophe, so that path cannot carry
        one and proves nothing. A lifeform's name is not, so this is the source that
        can actually reach the widget with a delimiter in it.
        """
        from sbs_utils.procedural.lifeform import lifeform_spawn
        from sbs_utils.procedural.away import away_assign
        away_assign(CID, lifeform_spawn("Ensign O`Neil", "", "away"))
        self.addCleanup(away_assign, CID, None)
        message = self.badge_text() or ""
        text = message.split("$text:", 1)[1].split(";", 1)[0]
        self.assertEqual(text.count("`"), 2, message)

    def test_a_semicolon_is_quoted_rather_than_read_as_style(self):
        self.crew("Marek; color:red")
        message = self.badge_text() or ""
        self.assertIn("`Marek; color:red`", message)

    def test_an_ordinary_name_is_untouched(self):
        self.crew("Marek", "Lt")
        self.assertIn("Lt Marek", self.badge_text() or "")


class TestTheMainScreenGetsNoBadge(BadgeBase):
    """The badge names the person at the console. The main screen is the whole room's
    view, so a name on it is either wrong or somebody else's - the same reason the
    away team gives it no character."""

    def test_not_by_console_name(self):
        self.page.console = "mainscreen"
        self.crew("Marek", "Lt")
        self.assertIsNone(self.badge_text())

    def test_not_by_role_either(self):
        """A morphed main screen reports its type through the role, and `page.console`
        is empty on a console that came through `gui_console_enter`."""
        from sbs_utils.procedural.roles import add_role, remove_role
        add_role(CID, "mainscreen")
        # A role on a CLIENT outlives clear_shared(), so without this the next test
        # class runs against a console that is still the main screen.
        self.addCleanup(remove_role, CID, "mainscreen")
        self.crew("Marek", "Lt")
        self.assertIsNone(self.badge_text())

    def test_AND_AN_ORDINARY_CONSOLE_STILL_GETS_ONE(self):
        """The guard must not be so broad it takes the badge off the bridge."""
        self.crew("Marek", "Lt")
        self.assertIn("Lt Marek", self.badge_text() or "")

    def test_the_live_refresh_skips_it_too(self):
        """`present` runs on the main screen as well, and a badge built nowhere would
        otherwise be refreshed into existence."""
        self.page.console = "mainscreen"
        self.crew("Marek", "Lt")
        self.build()
        FrameContext.context.sim.time_tick_counter += 100
        self.page._tick_identity_badge()
        self.assertIsNone(getattr(self.page, "identity_label", None))


class TestItSurvivesBeingDrawn(BadgeBase):
    """Reported from the engine as a new runtime error, and it was the badge.

        row.py:258  "__bg:" + self.tag
        TypeError: can only concatenate str (not "NoneType") to str

    `Row()` starts with `tag = None`, and `_pre_present` builds the backdrop's own tag
    from it - so a row with a BACKGROUND and no tag raises. The badge is the first row
    here to want a background of its own, which is why nothing else had hit it: the
    strip's row, built four lines away, declares none.

    Every test above this one BUILDS the badge and never presents it, and every one of
    them passed with the bug in place. Presenting is the whole test.
    """

    def setUp(self):
        super().setUp()
        self.crew("Marek", "Lt")

    def test_THE_BADGE_PRESENTS(self):
        layout = self.badge_layout()
        self.assertIsNotNone(layout, "no badge to present")
        layout.calc(CID)
        layout.present(FakeEvent(CID, "test"))

    def test_the_row_itself_carries_a_tag(self):
        """The rule, stated where it is cheap to check: a background needs a tag."""
        layout = self.badge_layout()
        row = (getattr(layout, "rows", None) or [None])[0]
        self.assertIsNotNone(row.background_color, "the badge lost its background")
        self.assertIsNotNone(row.tag, "a row with a background needs a tag")

    def test_and_the_bare_rule_holds_for_any_row(self):
        """Not specific to the badge - this is why the library raised at all."""
        from sbs_utils.pages.layout.row import Row
        bare = Row()
        bare.background_color = "#1572"
        with self.assertRaises(TypeError):
            bare._pre_present(FakeEvent(CID, "test"))


def get_tabs(cid):
    from sbs_utils.procedural.inventory import get_inventory_value
    return get_inventory_value(cid, "console_tabs", {}) or {}


if __name__ == "__main__":
    unittest.main()
