"""The ePADD shell: the home screen it draws, and opening an app from it.

Layout and render are only real in a browser - what is checked here is the structure
the builder produces: one clickable tile per app, uniquely tagged, grouped, and the
open path landing on the tab's own label.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import cosmos_dev.mock.sbs as sbs          # registers the bare `sbs` shim
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.gui import GuiClient
from sbs_utils.agent import clear_shared
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.mast_sbs.story_nodes.gui_tab_decorator_label import GuiTabDecoratorLabel
from sbs_utils.procedural.gui.epadd import (
    gui_app_register, gui_app_adopt_record, gui_app_home, gui_app_open,
    gui_app_chrome)

ENGI = 7
SERVER = 0


class _FakeSim:
    time_tick_counter = 0


class _Main:
    def __init__(self, page):
        self.page = page


class _RecordingTask:
    """The `_FakeGuiTask` shape test_gui_message_multi_handler settled on - enough for
    style parsing (`task.main.page.client_id`) and props formatting - plus a record of
    where the task was sent instead of going there.
    """

    def __init__(self):
        self.jumped = []
        self.ticked = 0
        self.main = None

    def jump(self, label):
        self.jumped.append(label)

    def tick_in_context(self):
        self.ticked += 1

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


def _page(console="normal_engi"):
    page = StoryPage()
    page.pending_gui = False          # skip on_new_gui() wiring in add_tag
    page.client_id = ENGI
    page.console = console
    page.gui_task = _RecordingTask()
    page.gui_task.main = _Main(page)
    return page


def _walk(item, out):
    out.append(item)
    for attr in ("rows", "columns"):
        for child in getattr(item, attr, None) or ():
            _walk(child, out)


def _all_items(page):
    """Everything built so far - INCLUDING the row still pending.

    A row only lands in pending_layouts when the next row starts (or at present
    time), so the last thing a builder added is still in `pending_row`. The grid path
    flushes as it goes and looked complete; the list path does not, and its listbox
    was invisible here until this walked it too."""
    out = []
    for layout in page.pending_layouts:
        _walk(layout, out)
    if page.pending_row is not None:
        _walk(page.pending_row, out)
    return out


def _tile_tags(page):
    """Every tile's click_tag, in the order the page laid them out."""
    tags = []
    for item in _all_items(page):
        tag = getattr(item, "_click_tag", None)
        if tag and str(tag).startswith("epadd-app-"):
            tags.append(str(tag))
    return tags


class EpaddShellBase(unittest.TestCase):
    def setUp(self):
        FrameContext.context = Context(_FakeSim(), sbs, FakeEvent(ENGI, "test"))
        FrameContext.page = None
        FrameContext.task = None
        clear_shared()
        GuiTabDecoratorLabel.clear()
        for cid in (SERVER, ENGI):
            GuiClient(cid)

    def tearDown(self):
        FrameContext.page = None
        FrameContext.task = None
        FrameContext.context = None
        GuiTabDecoratorLabel.clear()

    def build(self, page=None, **kwargs):
        page = page or _page()
        FrameContext.page = page
        FrameContext.task = page.gui_task
        gui_app_home(**kwargs)
        return page


class TestHomeScreen(EpaddShellBase):
    def setUp(self):
        super().setUp()
        for p in ("cargo", "fabricate", "quests", "help"):
            GuiTabDecoratorLabel(p)
        gui_app_register("cargo", title="Cargo", group="Ship", sort=10,
                         consoles="engineering", description="Hold manifest")
        gui_app_register("fabricate", title="Fabricate", group="Ship", sort=20,
                         consoles="engineering")
        gui_app_register("quests", title="Quests", group="Mission", sort=10)
        gui_app_register("help", title="Help", group="Mission", sort=20)

    def test_one_clickable_tile_per_app(self):
        page = self.build()
        self.assertEqual(len(_tile_tags(page)), 4)

    def test_every_tile_tag_is_unique(self):
        """click_tag is a real engine tag matched against event.sub_tag - two tiles
        sharing one means the wrong app opens."""
        tags = _tile_tags(self.build())
        self.assertEqual(len(tags), len(set(tags)))

    def test_tiles_are_named_for_their_tab(self):
        self.assertIn("epadd-app-cargo", _tile_tags(self.build()))

    def test_a_console_that_scopes_nothing_out_still_gets_its_apps(self):
        page = self.build(_page(console="normal_helm"))
        tags = _tile_tags(page)
        self.assertIn("epadd-app-quests", tags)
        self.assertNotIn("epadd-app-cargo", tags)      # Engineering's

    def test_a_console_with_no_apps_at_all_says_so_rather_than_drawing_nothing(self):
        GuiTabDecoratorLabel.clear()                   # every route gone
        page = self.build()
        self.assertEqual(_tile_tags(page), [])
        self.assertTrue(page.pending_layouts)           # the bar and the line still drew

    def test_it_draws_into_the_body_below_the_strip(self):
        page = self.build()
        self.assertTrue(page.pending_layouts)


def _tile_item(page, tab):
    """The layout item behind one tile, so a click can be delivered to it."""
    for item in _all_items(page):
        if str(getattr(item, "_click_tag", "")) == f"epadd-app-{tab}":
            return item
    return None


class TestClickingATileOpensIt(EpaddShellBase):
    """The mechanism the design rests on and a browser cannot be asked about here:
    the WHOLE tile is the hit target. A sub-section carrying `click_text` emits a
    click region over its own bounds, and the event comes back on its click_tag."""

    def setUp(self):
        super().setUp()
        self.label = GuiTabDecoratorLabel("cargo")
        gui_app_register("cargo", title="Cargo", group="Ship")
        self.page = self.build()

    def test_the_tile_carries_a_click_region(self):
        """No click_text means Layout._post_present emits nothing and the tile is
        decoration - the failure would be a home screen where nothing is clickable."""
        item = _tile_item(self.page, "cargo")
        self.assertIsNotNone(item)
        self.assertTrue(getattr(item, "click_text", None))

    def test_a_click_on_it_sends_the_gui_task_to_the_app(self):
        item = _tile_item(self.page, "cargo")
        item.on_message(FakeEvent(ENGI, "gui_message", sub_tag=item.click_tag))
        self.assertEqual(self.page.gui_task.jumped, [self.label])

    def test_a_click_meant_for_something_else_opens_nothing(self):
        item = _tile_item(self.page, "cargo")
        item.on_message(FakeEvent(ENGI, "gui_message", sub_tag="someone-elses-tag"))
        self.assertEqual(self.page.gui_task.jumped, [])


class TestDenseMode(EpaddShellBase):
    def setUp(self):
        super().setUp()
        for i in range(15):
            name = f"app{i:02d}"
            GuiTabDecoratorLabel(name)
            gui_app_register(name, title=f"App {i}", group="Ship")

    def test_more_than_twelve_apps_still_draws_them_all(self):
        """The old strip hid the overflow behind a More (n) dropdown. Nothing hides."""
        self.assertEqual(len(_tile_tags(self.build())), 15)

    def test_columns_can_be_forced(self):
        page = self.build(columns=2)
        self.assertEqual(len(_tile_tags(page)), 15)


class TestOpen(EpaddShellBase):
    def setUp(self):
        super().setUp()
        self.label = GuiTabDecoratorLabel("cargo")
        self.page = _page()
        FrameContext.page = self.page
        FrameContext.task = self.page.gui_task

    def test_opening_an_app_sends_the_gui_task_to_its_label(self):
        self.assertTrue(gui_app_open("cargo"))
        self.assertEqual(self.page.gui_task.jumped, [self.label])

    def test_and_ticks_it_in_context(self):
        """The second of the two lines TabControl runs - without it the jump does not
        take effect until something else happens to tick the task."""
        gui_app_open("cargo")
        self.assertEqual(self.page.gui_task.ticked, 1)

    def test_an_unknown_tab_opens_nothing_rather_than_raising(self):
        self.assertFalse(gui_app_open("nosuch"))
        self.assertEqual(self.page.gui_task.jumped, [])

    def test_the_name_is_matched_case_insensitively(self):
        self.assertTrue(gui_app_open("CARGO"))

    def test_with_no_gui_task_it_declines(self):
        self.page.gui_task = None
        self.assertFalse(gui_app_open("cargo"))


class TestChrome(EpaddShellBase):
    def test_the_app_bar_draws(self):
        page = _page()
        FrameContext.page = page
        FrameContext.task = page.gui_task
        gui_app_chrome("Cargo", subtitle="42 of 60 units held")
        self.assertTrue(page.pending_row.columns or page.pending_layouts)

    def test_a_title_carrying_a_colon_does_not_truncate_the_bar(self):
        """Free prose in a style string: an unescaped `:` reads as a style property
        and silently eats the rest - the trap gui_map_picker documents on its cards."""
        page = _page()
        FrameContext.page = page
        FrameContext.task = page.gui_task
        gui_app_chrome("Cargo: deck 3", subtitle="a; b")
        texts = [getattr(i, "message", "") or "" for i in _all_items(page)]
        joined = " ".join(str(t) for t in texts)
        self.assertNotIn("deck 3;", joined)


class TestAdoptedTilesDraw(EpaddShellBase):
    def test_an_adopted_tab_gets_a_tile_like_any_other(self):
        """The safety property, at the drawing end: a tab nobody registered still
        reaches the screen."""
        GuiTabDecoratorLabel("mystery")
        page = _page()
        FrameContext.page = page
        FrameContext.task = page.gui_task
        gui_app_adopt_record({"mystery"}, back_tab="engineering")
        gui_app_home()
        self.assertIn("epadd-app-mystery", _tile_tags(page))


if __name__ == "__main__":
    unittest.main()


class TestColumnsFollowTheScreen(unittest.TestCase):
    """Four columns is four columns whether the console is 1920 or 1024 wide - and at
    1024 that is a ~230px tile with ~174px for the title, where a two-word name wraps
    and that one tile stops matching its neighbours. Reported from a real 1024x768
    bridge as "the brain scan behaves different than the others"; "Brain scan" is the
    only two-word title LM registers.
    """

    def setUp(self):
        from sbs_utils.helpers import FrameContext as FC
        self.saved = dict(FC.aspect_ratios)
        self.addCleanup(lambda: (FC.aspect_ratios.clear(),
                                 FC.aspect_ratios.update(self.saved)))

    def cols(self, width, dense=False):
        from sbs_utils.helpers import FrameContext as FC
        from sbs_utils.vec import Vec3
        from sbs_utils.procedural.gui.epadd import _columns_for
        FC.aspect_ratios[ENGI] = Vec3(width, 768, 0)
        return _columns_for(ENGI, dense)

    def test_a_wide_console_gets_the_full_four(self):
        self.assertEqual(self.cols(1920), 4)

    def test_1024_drops_to_three(self):
        self.assertEqual(self.cols(1024), 3)

    def test_a_narrow_console_never_goes_below_one(self):
        self.assertEqual(self.cols(200), 1)

    def test_dense_still_capped_by_the_screen(self):
        self.assertEqual(self.cols(1920, dense=True), 6)
        self.assertEqual(self.cols(1024, dense=True), 3)

    def test_an_unknown_client_falls_back_to_the_default(self):
        """A build with no client to ask must not collapse to one column."""
        from sbs_utils.procedural.gui.epadd import _columns_for
        self.assertEqual(_columns_for(None, False), 4)


class TestItFallsBackToAList(EpaddShellBase):
    """A grid does not scroll and the engine does not clip, so a sheet that overflows
    draws over itself. Past what fits, the same apps become a scrolling list with
    collapsible group headers - which is the only reason "nothing is hidden" is true
    rather than aspirational.
    """

    def setUp(self):
        super().setUp()
        from sbs_utils.helpers import FrameContext as FC
        self.saved = dict(FC.aspect_ratios)
        self.addCleanup(lambda: (FC.aspect_ratios.clear(),
                                 FC.aspect_ratios.update(self.saved)))

    def screen(self, w, h):
        from sbs_utils.helpers import FrameContext as FC
        from sbs_utils.vec import Vec3
        FC.aspect_ratios[ENGI] = Vec3(w, h, 0)

    def register(self, n):
        for i in range(n):
            name = f"app{i:02d}"
            GuiTabDecoratorLabel(name)
            gui_app_register(name, title=f"App {i}", group="Ship",
                             description="something")

    def listboxes(self, page):
        from sbs_utils.pages.widgets.layout_listbox import LayoutListbox
        return [i for i in _all_items(page) if isinstance(i, LayoutListbox)]

    def test_a_few_apps_stay_a_grid(self):
        self.screen(1920, 1080)
        self.register(6)
        page = self.build()
        self.assertEqual(self.listboxes(page), [])
        self.assertEqual(len(_tile_tags(page)), 6)

    def test_too_many_for_the_screen_becomes_a_list(self):
        self.screen(1024, 768)
        self.register(40)
        page = self.build()
        self.assertTrue(self.listboxes(page), "should have fallen back to a list")
        self.assertEqual(_tile_tags(page), [], "and drawn no tiles")

    def test_the_same_count_still_fits_on_a_bigger_screen(self):
        """The switch is about the SCREEN, not about a magic number of apps."""
        self.screen(1024, 768)
        self.register(30)
        small = self.build()
        self.setUp()
        self.screen(1920, 1080)
        self.register(30)
        big = self.build()
        self.assertTrue(self.listboxes(small))
        self.assertEqual(self.listboxes(big), [])

    def test_a_client_that_has_not_reported_its_size_is_assumed_SMALL(self):
        """It answers 1024x768 with z=99. Assuming the smallest common console is the
        safe direction: a list that scrolls is never broken, a grid that overflows
        draws over itself. The page rebuilds when the real size arrives."""
        self.register(40)
        page = self.build()
        self.assertTrue(self.listboxes(page))

    def test_the_list_carries_a_header_per_group(self):
        from sbs_utils.procedural.gui.listbox import gui_list_box_is_header
        self.screen(1024, 768)
        self.register(40)
        GuiTabDecoratorLabel("quest")
        gui_app_register("quest", title="Quests", group="Mission")
        page = self.build()
        lb = self.listboxes(page)[0]
        heads = [i for i in lb.items if gui_list_box_is_header(i)]
        self.assertEqual([h.label for h in heads], ["SHIP", "MISSION"])
