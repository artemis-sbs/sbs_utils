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
import sbs_utils.mast_sbs.maststorypage as MSP
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.pages.layout.icon import Icon
from sbs_utils.mast_sbs.story_nodes.gui_app_decorator_label import GuiAppDecoratorLabel
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
        self.jumped = []

    def jump(self, label):
        self.jumped.append(label)

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

        self._saved_tabs = dict(GuiAppDecoratorLabel.all)
        GuiAppDecoratorLabel.all["epadd"] = _Label()
        self.addCleanup(self._restore, GuiAppDecoratorLabel)

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
        """The PADD's glyph, as the page hands it over.

        It is a slot of the tab strip now, not a band of its own under it - the old
        absolutely-positioned box sat over the ship-data panel and collided with its
        readouts on a real console (playtest, 2026-09-01).
        """
        self.build()
        return getattr(self.page, "identity_badge", None)

    def badge_text(self):
        """The name beside the glyph, or None when nothing was drawn."""
        self.build()
        label = getattr(self.page, "identity_label", None)
        return None if label is None else label.message

    def regions(self):
        """Every click region the badge emits, as {tag: (props, rect)}.

        Driven through `_post_present`, because "how many regions" and "what is painted
        in them" are things only the SEND shows - the model was right in both of the
        bugs this pins.
        """
        badge = self.padd_region()
        sent = {}
        real = sbs.send_gui_clickregion
        sbs.send_gui_clickregion = (
            lambda cid, parent, tag, props, l, t, r, b:
                sent.__setitem__(tag, (props, (l, t, r, b))))
        try:
            badge.calc(CID)
            badge._post_present(FakeEvent(CID))
            for row in badge.rows:
                row._post_present(FakeEvent(CID))
                for col in row.columns:
                    col._post_present(FakeEvent(CID))
        finally:
            sbs.send_gui_clickregion = real
        return sent

    def padd_region(self):
        """The PADD's own layout - one region over the strip's left two slots."""
        self.build()
        return getattr(self.page, "identity_badge", None)

    def tab_row_columns(self):
        """The tab row - a SEPARATE layout from the PADD's region, found by not
        being it rather than by position."""
        self.build()
        padd = getattr(self.page, "identity_badge", None)
        for layout in self.page.pending_layouts:
            if layout is not padd and getattr(layout, "rows", None):
                return list(layout.rows[0].columns)
        return []

    def padd_columns(self):
        """What is drawn inside that region, left to right."""
        region = self.padd_region()
        if region is None:
            return []
        return list(region.rows[0].columns)

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
        console.

        The SLOT still exists - it is the only way in to the PADD now that no button
        spells the word - but with nothing to say it carries no panel, so what is on
        screen is the glyph alone."""
        cols = self.padd_columns()           # builds
        self.assertIsNone(self.page.identity_text)
        self.assertIsNone(cols[1].background_color,
                          "an empty status must not draw a box")
class TestItSaysWhatIsWaiting(BadgeBase):
    def setUp(self):
        super().setUp()
        self.crew("Marek", "Lt")

    def register(self, tab, status):
        GuiAppDecoratorLabel.all[tab] = _Label()
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
    """In the strip, as its left two slots.

    It used to be a band of its own with an absolute pixel rect UNDER the strip, sized
    from ship_data's own edges. That put it on top of the info panel, which is where it
    collided with the panel's readouts on a real console - reported from the playtest
    with a screenshot, 2026-09-01. The strip is where every other control on that bar
    already lives, so the whole rect calculation is gone rather than corrected.
    """

    def setUp(self):
        super().setUp()
        self.crew("Marek", "Lt")

    def test_the_glyph_is_the_leftmost_thing_in_the_strip(self):
        cols = self.padd_columns()
        self.assertIsInstance(cols[0], Icon)

    def test_and_the_name_sits_next_to_it(self):
        cols = self.padd_columns()
        self.assertIs(cols[1], self.page.identity_label)
        self.assertIn("Lt Marek", cols[1].message)

    def test_the_glyph_is_drawn_rather_than_pressed(self):
        """Part of the status, not a control of its own: a plain `Icon` and a plain
        `Text` inside the region, neither of them a button. The REGION is what is
        clickable - see the next test."""
        cols = self.padd_columns()
        self.assertIsInstance(cols[0], Icon)
        self.assertFalse(hasattr(cols[0], "label"))
        self.assertFalse(hasattr(cols[1], "label"))

    def test_THE_WHOLE_STATUS_IS_THE_CLICK_REGION(self):
        """ONE region over both slots, not two that do the same thing.

        A Row gives every column its own click region, so a glyph and a name side by
        side were two hit targets and pressing either highlighted only its own half.
        The PADD is its own Layout, which emits one region over its whole bounds."""
        region = self.padd_region()
        self.assertIsNotNone(region.click_tag)
        for col in self.padd_columns():
            self.assertIsNone(getattr(col, "click_tag", None),
                              "a child must not open a second hit target")

    def test_pressing_the_region_opens_the_padd(self):
        region = self.padd_region()
        event = FakeEvent(CID, "test")
        event.sub_tag = region.click_tag
        region.on_message(event)
        self.assertEqual(len(self.page.gui_task.jumped), 1,
                         "pressing the region jumps to the epadd route")

    def test_A_CLICK_MEANT_FOR_SOMETHING_ELSE_DOES_NOTHING(self):
        """The test whose absence let the PADD bounce reach an engine.

        `Layout.on_message` calls `on_message_cb` for EVERY event handed to it, not
        only ones aimed at it - unlike `Column.on_message`, which returns early on a
        tag miss. `StoryPage.on_message` walks every layout for every event, so an
        unfiltered callback on the identity region fires on somebody else's click.

        Reported from a real engine run as "on the ePADD home, clicking an app just
        seems to run home again": the tile's own filtered handler opened the app, and
        then this region's unfiltered one re-entered the PADD shell in the same walk.
        Two builds per click, and the last one always won.
        """
        region = self.padd_region()
        region.on_message(FakeEvent(CID, "test", sub_tag="epadd-app-cargo"))
        self.assertEqual(self.page.gui_task.jumped, [],
                         "the status region must ignore a click aimed elsewhere")

    def test_THE_CLICK_TAG_DOES_NOT_MOVE_BETWEEN_BUILDS(self):
        """The region is re-created every build, and a Layout's default click tag is
        `__click:{tag}` where tag is a build-order ordinal that jumps ~2100 each time.
        So every visit to the PADD asked the engine for a NEW click region and left the
        old one live.

        Measured in a real session: presses arriving as `__click:68684` while the
        current region was `81284`. The press is answered by a region that belongs to
        nothing, this handler correctly ignores it, and the click is consumed rather
        than reaching the bar's Back - one dead press per stale region, which is the
        reported "N visits, N presses to get out".
        """
        first = self.padd_region().click_tag
        self.page.identity_badge = None
        second = self.padd_region().click_tag
        self.assertEqual(first, second)
        self.assertEqual(first, MSP.IDENTITY_CLICK_TAG)
        self.assertNotIn("__click:", str(first),
                         "a derived tag is a new engine region every build")

    def test_A_PRESS_PAINTS_NO_WORDS(self):
        """The engine draws click text at its own size over the region's WHOLE rect, so
        the crew name came back oversized and centred, spilling up over the topbar and
        reading as a second copy of the label (playtest image, 2026-09-02).

        The region is asked for by TAG. Nothing on this control carries click text.
        """
        region = self.padd_region()
        self.assertIsNone(region.click_text)
        props = self.regions()[MSP.IDENTITY_CLICK_TAG][0]
        self.assertNotIn("$text:", props)
        self.assertIn("background_color", props)     # it still tints on press

    def test_THE_BADGE_EMITS_EXACTLY_ONE_REGION(self):
        """The bounds looked wrong because there were TWO.

        The refresh ticker used to set `click_text` on the NAME LABEL, which gave the
        label its own click region on top of the badge's - a second hit target, with the
        label's content-sized bounds rather than the badge's, painting the name over the
        strip. One control, one region.
        """
        self.crew("Ione Marek", "Commander")
        self.build()
        self.page._identity_tick = -999               # let the ticker actually run
        self.page.sim = _Sim()
        self.page._tick_identity_badge()
        label = self.page.identity_label
        self.assertIsNone(getattr(label, "click_text", None))

        regions = self.regions()
        self.assertEqual(list(regions), [MSP.IDENTITY_CLICK_TAG], regions)

    def test_the_region_covers_the_badge_and_not_more(self):
        """And its rect is the badge's own - the strip's left slots."""
        rect = self.regions()[MSP.IDENTITY_CLICK_TAG][1]
        self.assertEqual(rect, (MSP._strip_left(CID), 0, MSP._identity_right(CID),
                                MSP._strip_bottom(CID)))

    def test_IT_SITS_AGAINST_THE_OPTIONS_BUTTON_AT_ANY_SIZE(self):
        """The Options button is a fixed-PIXEL control, so a percentage only touches it
        at one resolution. 20% is 205px on a 1024 screen - right where it ended - and
        768px on a 4K one, leaving 563px of empty bar between the button and the badge
        (playtest images, 2026-09-02).

        Both edges are pixels now, so the badge is the same box on every display.
        """
        from sbs_utils.vec import Vec3
        saved = FrameContext.aspect_ratios
        try:
            for w, h in ((1024, 768), (1920, 1080), (2560, 1440), (3840, 2160)):
                FrameContext.aspect_ratios = {CID: Vec3(w, h, 0)}
                left = MSP._strip_left(CID) / 100 * w
                width = (MSP._identity_right(CID) - MSP._strip_left(CID)) / 100 * w
                self.assertAlmostEqual(left, MSP.STRIP_LEFT_PX, places=2,
                                       msg=f"{w}x{h} left {left:.0f}px")
                self.assertAlmostEqual(width, MSP.IDENTITY_WIDTH_PX, places=2,
                                       msg=f"{w}x{h} width {width:.0f}px")
        finally:
            FrameContext.aspect_ratios = saved

    def test_the_tab_row_starts_where_the_badge_ends(self):
        """One bar, no overlap and no hole - the tabs take whatever is left of it."""
        import inspect
        src = inspect.getsource(MSP.StoryPage.gui_queue_console_tabs)
        self.assertIn("_identity_right(self.client_id) if show_epadd", src)
        self.assertIn("else _strip_left(self.client_id)", src)

    def test_IT_IS_AS_TALL_AS_THE_BAR(self):
        """A Layout's rect is a PERCENT; the row inside it is declared in PIXELS. The
        two only agree at one resolution, and the playtest's was not it: 3% of a 768
        screen is 23px against a 35px row, so the press highlight stopped a third of the
        way up from the bottom of the bar and the badge read as floating in it.

        Checked in pixels at four resolutions, because a percentage that is right at one
        of them is exactly the bug.
        """
        from sbs_utils.vec import Vec3
        # RESTORED. `aspect_ratios` is a class attribute on FrameContext, so leaving a
        # resolution behind here decides the answer for every later test in the run -
        # it took out test_epadd_shell's unreported-size case on the first attempt.
        saved = FrameContext.aspect_ratios
        try:
            for w, h in ((1024, 768), (1920, 1080), (2560, 1440), (3840, 2160)):
                FrameContext.aspect_ratios = {CID: Vec3(w, h, 0)}
                px = MSP._strip_bottom(CID) / 100 * h
                self.assertAlmostEqual(px, MSP.STRIP_ROW_PX, places=3,
                                       msg=f"{w}x{h} gave {px:.1f}px")
        finally:
            FrameContext.aspect_ratios = saved

    def test_and_the_tab_strip_takes_the_same_bottom(self):
        """One bar. The tabs and the badge sit on it, so a press on either has to reach
        the same depth - they were 3% and 3% while the row was 35px."""
        import inspect
        src = inspect.getsource(MSP.StoryPage.gui_queue_console_tabs)
        self.assertIn("_strip_bottom(self.client_id)", src)

    def test_IT_FOLLOWS_A_WINDOW_RESIZE(self):
        """Without a rebuild - which is all a resize gets.

        `screen_size` sets `gui_state = "refresh"`, and refresh re-presents the EXISTING
        layouts; it does not build new ones. So bounds passed to the Layout constructor
        are frozen at whatever the build computed, and converting px to percent by hand
        at build time is only right until the window changes size. Measured before the
        fix: a band starting at 555px on a 1024 screen started at 2081px on a 4K one.

        `Layout.calc` re-resolves `bounds_style` against the CURRENT aspect ratio every
        pass, so the rect is declared as a px `area:` and follows the window on its own.
        The PADD's own screens hid this by rebuilding; the console screen does not.
        """
        from sbs_utils.vec import Vec3
        saved = FrameContext.aspect_ratios
        try:
            badge = self.padd_region()
            for w, h in ((1024, 768), (1920, 1080), (2560, 1440), (3840, 2160)):
                FrameContext.aspect_ratios = {CID: Vec3(w, h, 0)}
                badge.calc(CID)                      # a resize calcs; it does NOT build
                b = badge.bounds
                self.assertAlmostEqual(b.left / 100 * w, MSP.STRIP_LEFT_PX, places=2,
                                       msg=f"{w}x{h} left")
                self.assertAlmostEqual(b.right / 100 * w,
                                       MSP.STRIP_LEFT_PX + MSP.IDENTITY_WIDTH_PX,
                                       places=2, msg=f"{w}x{h} right")
                self.assertAlmostEqual(b.bottom / 100 * h, MSP.STRIP_ROW_PX, places=2,
                                       msg=f"{w}x{h} bottom")
        finally:
            FrameContext.aspect_ratios = saved

    def test_and_so_does_the_tab_strip_beside_it(self):
        """One bar: if only half of it follows the window, they part company."""
        from sbs_utils.vec import Vec3
        saved = FrameContext.aspect_ratios
        try:
            self.build()
            badge = self.page.identity_badge
            strip = next(l for l in self.page.pending_layouts if l is not badge)
            for w, h in ((1024, 768), (3840, 2160)):
                FrameContext.aspect_ratios = {CID: Vec3(w, h, 0)}
                strip.calc(CID)
                self.assertAlmostEqual(strip.bounds.left / 100 * w,
                                       MSP.STRIP_LEFT_PX + MSP.IDENTITY_WIDTH_PX,
                                       places=2, msg=f"{w}x{h}")
        finally:
            FrameContext.aspect_ratios = saved

    def test_the_press_flash_is_not_opaque_white(self):
        """The engine default blanks whatever is under it while a finger is down."""
        region = self.padd_region()
        self.assertIsNotNone(region.click_background)
        self.assertNotEqual(str(region.click_background).lower(), "white")

    def test_the_status_says_nothing_extra_when_pressed(self):
        """click_text unset, so `_pre_present` emits no `$text:` for the highlight -
        flashing the crew member's own name back at them says nothing."""
        self.assertIsNone(self.padd_columns()[1].click_text)

    def test_the_glyph_is_the_engines_own_phone(self):
        """Resolved through the NAME table, so a mission that re-skins `phone`
        re-skins this. `134` is the cell in grid-icon-sheet the engineering grid
        draws from."""
        from sbs_utils.procedural.gui.icon_sheet import icon_resolve
        index, _ = icon_resolve(MSP.IDENTITY_ICON)
        self.assertEqual(index, 134)
        self.assertIn(f"icon_index:{index}", self.padd_columns()[0].props)

    def test_there_is_no_word_for_it(self):
        """The glyph carries the meaning, which is what frees the label to say who you
        are instead of naming the button."""
        texts = [getattr(c, "message", "") or "" for c in self.padd_columns()]
        self.assertFalse(any("ePADD" in t for t in texts), texts)

    def test_the_tab_row_keeps_the_slots_the_padd_does_not(self):
        """Seven across the strip, and the PADD's region holds three of them - a PADD
        screen puts ONE tab on the bar, so the middle was empty while the name was
        squeezed against the Options button. The row beside it pads to the rest.

        Asserted against the constants rather than a literal, so moving the split moves
        the test with it."""
        self.assertEqual(len(self.tab_row_columns()),
                         MSP.STRIP_SLOTS - MSP.IDENTITY_SLOTS)
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

    def test_the_glyph_carries_a_tag(self):
        """A background needs a tag - `_pre_present` builds the backdrop's own tag from
        it. The badge used to own a ROW with a background, which is how the library
        raised; now it is a column in the strip's row, and the strip's row declares no
        background. The tag still matters: it is the click target."""
        icon = self.badge_layout()
        self.assertIsNotNone(icon.tag, "a drawn widget still needs its own tag")

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
