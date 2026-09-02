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
    """The rect, against the engine's own numbers."""

    def setUp(self):
        super().setUp()
        self.crew("Marek", "Lt")

    def bounds(self):
        layout = self.badge_layout()
        self.assertIsNotNone(layout, "no badge was drawn to place")
        b = layout.bounds
        return b.left, b.top, b.right, b.bottom

    def test_it_starts_where_ship_data_starts(self):
        """Left of that is the icon column, and that icon collapses the info panel."""
        self.assertEqual(self.bounds()[0], SHIP_DATA_LEFT)

    def test_IT_STOPS_BEFORE_SCIENCES_RADAR_ZOOM(self):
        """The one console where the band is not free all the way across. Reaching
        past x=27 would draw over the magnifiers on science and nowhere else, which
        is the worst kind of bug to find."""
        self.assertLessEqual(self.bounds()[2], SCIENCE_RADAR_LEFT)

    def test_it_sits_above_the_info_panel(self):
        """Computed here from the engine numbers rather than read back off the badge,
        so this checks the CONVERSION - engine percentages are of the console area,
        which starts under the topbar, and using 5 raw would put the badge inside the
        info panel on every console."""
        bottom = self.bounds()[3]
        self.assertLessEqual(bottom, self.ship_data_top() + 0.001)

    def ship_data_top(self):
        from sbs_utils.gui import get_client_aspect_ratio
        height = getattr(get_client_aspect_ratio(CID), "y", 0) or 1080
        console_top = E.BODY_TOP_PX / float(height) * 100.0
        return console_top + (SHIP_DATA_TOP / 100.0) * (100.0 - console_top)

    def test_it_sits_below_the_topbar(self):
        """Engine y=0 is the BOTTOM of the topbar, not the top of the screen, so the
        badge has to start under the strip rather than at zero."""
        self.assertGreater(self.bounds()[1], 0)

    def test_it_has_its_own_background(self):
        """It draws over ship data's overhanging art, and that art goes away when the
        panel is collapsed - so borrowing it would leave text on the radar."""
        layout = self.badge_layout()
        row = (getattr(layout, "rows", None) or [None])[0]
        style = str(getattr(row, "background_color", "")) + str(getattr(row, "message", ""))
        self.assertTrue(style.strip(), "the badge row declared no background")


def get_tabs(cid):
    from sbs_utils.procedural.inventory import get_inventory_value
    return get_inventory_value(cid, "console_tabs", {}) or {}


if __name__ == "__main__":
    unittest.main()


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
