"""`tag:` names a widget for the SCRIPT; it is not the tag the engine uses (LM #349).

`gui_update("inner-text-A", ...)` used to do nothing when the widget was built inside
a listbox `item_template`, for two independent reasons:

  * the listbox builds rows against a `SubPage` shim and threw its `tag_map` away, so
    the page never learned the row widgets -- the two other `SubPage` users (overlay,
    tabbed panel) have always merged theirs;
  * an author's `tag:` OVERWROTE the widget's engine tag. Inside a listbox that is
    actively harmful: the listbox routes events with
    `event.sub_tag.startswith(self.tag_prefix)`, so a renamed row widget stopped being
    recognized as its own.

Now the name is registered as an extra key in the same `tag_map` -- the idiom
`click_tag` has always used -- and the engine keeps the library-managed tag.

These tests pin both halves, and equally that a TOP-LEVEL `tag:` still resolves, that
the measure pass registers nothing, and that a row scrolled out of view does not leave
a live entry pointing at a widget nobody draws.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import logging
import unittest

from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.vec import Vec3
from sbs_utils.gui import GuiClient
from sbs_utils.mast_sbs.maststorypage import StoryPage

import sbs_utils.procedural.gui  # noqa: F401  (circular-import order)
from sbs_utils.procedural.gui import gui_text, gui_row, gui_update
from sbs_utils.pages.widgets.layout_listbox import LayoutListbox
from sbs_utils.pages.layout.bounds import Bounds


class _FakeMain:
    def __init__(self, page):
        self.page = page


class _FakeGuiTask:
    """Enough for style parsing (`task.main.page.client_id`) and props formatting."""
    def __init__(self, page):
        self.main = _FakeMain(page)

    def set_variable(self, *a, **k):
        pass

    def get_variable(self, *a, **k):
        return None

    def compile_and_format_string(self, s):
        return s

    def format_string(self, s):
        return s


PANEL = Bounds(2.0, 10.0, 30.0, 90.0)


class TagAliasBase(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.aspect_ratios[0] = Vec3(1024, 768, 0)
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        self.page = StoryPage()
        self.page.pending_gui = False
        self.page.client_id = 0
        self.page.gui_task = _FakeGuiTask(self.page)
        self.task = self.page.gui_task
        # so gui_page_for_client(0) finds this page and the listbox merges into it
        self.client = GuiClient(0)
        self.client.page_stack.append(self.page)
        FrameContext.page = self.page
        FrameContext.task = self.task

    def tearDown(self):
        from sbs_utils.gui import Gui
        Gui.clients.pop(0, None)
        FrameContext.page = None
        FrameContext.task = None
        FrameContext.context = None

    def _lb(self, items, template, **kw):
        b = Bounds(PANEL)
        lb = LayoutListbox(b.left, b.top, "lb", items, item_template=template, **kw)
        lb.tag = "lb"
        lb.bounds = b
        lb.client_id = 0
        return lb

    @staticmethod
    def _named_template(item, **kwargs):
        gui_row("row-height: 1.2em;")
        gui_text(f"$text:`{item}`;font:gui-2;", style=f"tag:row-{item};")
        return None


class TestTopLevelUnchanged(TagAliasBase):
    """The half that must NOT move: a named widget outside any container."""

    def test_the_name_resolves(self):
        gui_text("$text:`hello`;", style="tag:status;")
        self.assertIn("status", self.page.pending_tag_map)

    def test_the_engine_tag_is_the_library_ordinal(self):
        item = gui_text("$text:`hello`;", style="tag:status;")
        self.assertEqual("status", item.alias)
        self.assertNotEqual("status", item.tag,
                            "the author's name must not become the engine's tag")
        self.assertTrue(item.tag.isdigit(), f"expected an ordinal, got {item.tag!r}")

    def test_gui_update_changes_the_value(self):
        item = gui_text("$text:`before`;", style="tag:status;")
        self.assertTrue(gui_update("status", "$text:`after`;"))
        self.assertIn("after", item.message)

    def test_an_unknown_name_is_a_miss_not_a_raise(self):
        self.assertFalse(gui_update("no-such-widget", "$text:`x`;"))

    def test_click_tag_still_reaches_the_engine(self):
        # Deliberately NOT aliased: ClickableTrigger matches click_tag against
        # event.sub_tag by the author's own string.
        item = gui_text("$text:`hi`;", style="tag:status;click_tag:menu;")
        self.assertEqual("menu", item.click_tag)


class TestListboxRowsAreReachable(TagAliasBase):
    """The reported bug."""

    def test_a_row_widget_is_registered_on_the_page(self):
        lb = self._lb(["A", "B", "C"], self._named_template)
        lb._present(FakeEvent(0))
        self.assertIn("row-A", self.page.tag_map,
                      "the listbox must publish its row widgets to the page")

    def test_gui_update_changes_a_row(self):
        lb = self._lb(["A", "B", "C"], self._named_template)
        lb._present(FakeEvent(0))
        self.assertTrue(gui_update("row-B", "$text:`CHANGED`;"))
        item = self.page.tag_map["row-B"][0]
        self.assertIn("CHANGED", item.message)

    def test_the_row_keeps_the_listbox_tag_prefix(self):
        """The regression that would otherwise be invisible.

        LayoutListbox._on_message drops any event whose sub_tag does not start with
        its prefix. When `tag:` overwrote the engine tag, naming a row widget took it
        out of the listbox's own namespace and its clicks stopped arriving.
        """
        lb = self._lb(["A"], self._named_template)
        lb._present(FakeEvent(0))
        item = self.page.tag_map["row-A"][0]
        self.assertTrue(item.tag.startswith(lb.tag_prefix),
                        f"{item.tag!r} left the listbox namespace {lb.tag_prefix!r}")

    def test_the_measure_pass_registers_nothing(self):
        """calc_max runs the template for EVERY item just to size it and throws the
        widgets away. Registering those would fill the page with dead entries for
        rows that were never drawn."""
        lb = self._lb(["A", "B", "C"], self._named_template)
        lb.calc_max(0)
        self.assertNotIn("row-A", self.page.tag_map)


class TestScrolledAwayRows(TagAliasBase):
    @staticmethod
    def _template(item, **kwargs):
        gui_row("row-height: 1.2em;")
        gui_text(f"$text:`{item}`;font:gui-2;", style=f"tag:row-{item};")
        return None

    def test_an_offscreen_row_is_a_miss(self):
        lb = self._lb([f"i{n}" for n in range(60)], self._template)
        lb._present(FakeEvent(0))
        shown = [s.item_index for s in lb.sections if getattr(s, "item_index", None) is not None]
        self.assertLess(len(shown), 60, "a 60-item list must not all fit")
        # Nothing built it, so nothing can update it -- and that must not raise.
        self.assertFalse(gui_update("row-i59", "$text:`x`;"))

    def test_scrolling_retracts_the_rows_that_left(self):
        """A stale entry points at a widget nobody draws any more; updating it would
        paint at coordinates that belong to nothing."""
        lb = self._lb([f"i{n}" for n in range(60)], self._template)
        lb._present(FakeEvent(0))
        self.assertIn("row-i0", self.page.tag_map)
        lb.cur = 40
        lb.sections = []
        lb._present(FakeEvent(0))
        self.assertNotIn("row-i0", self.page.tag_map,
                         "a row that scrolled away must not stay resolvable")
        self.assertIn("row-i40", self.page.tag_map)

    def test_a_same_named_widget_elsewhere_survives_the_retraction(self):
        """The retraction takes back only what THIS listbox put there."""
        lb = self._lb(["A", "B"], self._template)
        lb._present(FakeEvent(0))
        mine = gui_text("$text:`page level`;", style="tag:row-A;")
        self.page.tag_map["row-A"] = (mine, None)
        lb.items = ["C", "D"]
        lb.sections = []
        lb._present(FakeEvent(0))
        self.assertIs(mine, self.page.tag_map["row-A"][0])


class TestDuplicateNames(TagAliasBase):
    @staticmethod
    def _constant_template(item, **kwargs):
        gui_row("row-height: 1.2em;")
        gui_text(f"$text:`{item}`;", style="tag:row-label;")
        return None

    def test_last_row_wins_and_it_says_so(self):
        lb = self._lb(["A", "B", "C"], self._constant_template)
        with self.assertLogs("gui", level="WARNING") as captured:
            lb._present(FakeEvent(0))
        text = "\n".join(captured.output)
        self.assertIn("row-label", text)
        self.assertIn("item-unique", text)
        # Whichever row was drawn last is the one that answers.
        item = self.page.tag_map["row-label"][0]
        self.assertIn("C", item.message)

    def test_a_unique_name_per_row_is_silent(self):
        logger = logging.getLogger("gui")
        records = []

        class Collect(logging.Handler):
            def emit(self, record):
                records.append(record)

        handler = Collect(level=logging.WARNING)
        logger.addHandler(handler)
        try:
            lb = self._lb(["A", "B", "C"], self._named_template)
            lb._present(FakeEvent(0))
        finally:
            logger.removeHandler(handler)
        self.assertEqual([], [r.getMessage() for r in records])


class TestTheUpdateSticks(TagAliasBase):
    @staticmethod
    def _template(item, **kwargs):
        gui_row("row-height: 1.2em;")
        gui_text(f"$text:`{item}`;", style=f"tag:row-{item};")
        return None

    def test_a_repaint_does_not_undo_the_update(self):
        """The template rebuilds each row from the item data, so without the override
        memo an update lasts only until the list next draws -- which happens on every
        scroll and every selection."""
        lb = self._lb(["A", "B"], self._template)
        lb._present(FakeEvent(0))
        gui_update("row-A", "$text:`PINNED`;")
        lb.sections = []
        lb._present(FakeEvent(0))
        item = self.page.tag_map["row-A"][0]
        self.assertIn("PINNED", item.message)

    def test_new_items_drop_the_override(self):
        lb = self._lb(["A", "B"], self._template)
        lb._present(FakeEvent(0))
        gui_update("row-A", "$text:`PINNED`;")
        lb.items = ["A", "B"]          # new data, even if it looks the same
        lb.sections = []
        lb._present(FakeEvent(0))
        item = self.page.tag_map["row-A"][0]
        self.assertNotIn("PINNED", item.message)


class TestNamingTheContainerItself(TagAliasBase):
    """LM consoles/common_console_select.mast:259 names the LISTBOX `sh_ship_list`
    and later calls gui_update("sh_ship_list", None) to force a repaint."""

    def test_a_named_listbox_still_resolves(self):
        from sbs_utils.procedural.gui import gui_list_box

        def tmpl(item, **kwargs):
            gui_row("row-height: 1.2em;")
            gui_text(f"$text:`{item}`;")

        lb = gui_list_box(["a", "b"], "background:#1572;tag:sh_ship_list;",
                          item_template=tmpl)
        self.assertEqual("sh_ship_list", lb.alias)
        self.assertIn("sh_ship_list", self.page.pending_tag_map)
        # props=None is the shipped call: the value is the re-present, not the props.
        self.assertTrue(gui_update("sh_ship_list", None))

    def test_the_listbox_tag_and_its_prefix_agree_again(self):
        """LayoutListbox freezes tag_prefix and local_region_tag in __init__, so
        renaming .tag used to leave the box's own children in a different namespace
        from the box. Naming it no longer touches .tag, so they match."""
        from sbs_utils.procedural.gui import gui_list_box

        def tmpl(item, **kwargs):
            gui_row("row-height: 1.2em;")
            gui_text(f"$text:`{item}`;")

        lb = gui_list_box(["a"], "tag:sh_ship_list;", item_template=tmpl)
        self.assertEqual(lb.tag_prefix, lb.tag)
        self.assertEqual(lb.tag + "$$", lb.local_region_tag)


class TestNamedRowsAndSections(TagAliasBase):
    """A row never goes through add_content, so it was unreachable before."""

    def test_a_named_row_resolves(self):
        row = gui_row("tag:toggle;row-height: 1.5em;")
        self.assertEqual("toggle", row.alias)
        self.assertIn("toggle", self.page.pending_tag_map)


if __name__ == '__main__':
    unittest.main()
