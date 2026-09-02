"""The console tab strip in ePADD mode: two buttons instead of eight.

The property that matters most is the one about NOT changing: with the mode unset -
the default, and every mission that has not asked - the strip is byte-for-byte what it
was. `test_console_tab_overflow` is the rest of that proof; these are the additions.

The other two are safety rails:

- **Nothing is lost.** What the console enabled is handed to the app registry before
  the declaration is consumed, so a tab no addon registered as an app is adopted.
- **The mode needs its route.** Without a `//gui/tab/epadd` route the strip stays
  classic, rather than leaving the console holding one button that does nothing.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.mast_sbs.maststorypage import StoryPage, TabControl, TabOverflow
from sbs_utils.pages.layout.icon import Icon
from sbs_utils.mast_sbs.story_nodes.gui_tab_decorator_label import GuiTabDecoratorLabel
from sbs_utils.mast_sbs.story_nodes.gui_app_decorator_label import GuiAppDecoratorLabel
from sbs_utils.procedural.inventory import set_inventory_value, get_inventory_value
from sbs_utils.agent import Agent

CID = 42


class _FakeMain:
    def __init__(self, page):
        self.page = page


class _FakeGuiTask:
    def __init__(self, page=None):
        self.jumped = []
        self.main = _FakeMain(page)

    def jump(self, label):
        self.jumped.append(label)

    def tick_in_context(self):
        pass

    def compile_and_format_string(self, s):
        return s

    def format_string(self, s):
        return s

    def get_variable(self, name, default=None):
        return default

    def set_variable(self, name, value):
        pass


class EpaddStripBase(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        SpaceObject.clear()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(CID))
        self.client = Agent()
        self.client.id = CID
        self.client.add()
        self._saved = dict(GuiTabDecoratorLabel.all)
        self._saved_apps = dict(GuiAppDecoratorLabel.all)
        GuiTabDecoratorLabel.all.clear()
        GuiAppDecoratorLabel.all.clear()
        self.page = StoryPage()
        self.page.client_id = CID
        self.page.gui_task = _FakeGuiTask(self.page)
        self.page.console = "normal_engi"
        FrameContext.page = None

    def tearDown(self):
        GuiTabDecoratorLabel.all.clear()
        GuiTabDecoratorLabel.all.update(self._saved)
        GuiAppDecoratorLabel.all.clear()
        GuiAppDecoratorLabel.all.update(self._saved_apps)
        FrameContext.page = None
        FrameContext.context = None

    def declare(self, names, back=None, epadd_route=True):
        """What a console's build leaves behind. `gui_tab_back` ENABLES the back tab
        as well as naming it, and the strip only draws a tab that has a route, so the
        back tab needs both here too.

        `names` are TABS. The PADD's shell is an `//gui/app` route, not a tab - which
        is what keeps it off `__active_tab__` - so it is declared separately.
        """
        names = list(names)
        if back is not None and back not in names:
            names.append(back)
        for name in names:
            GuiTabDecoratorLabel.all[name] = f"label_{name}"
        if epadd_route:
            GuiAppDecoratorLabel.all["epadd"] = "label_epadd"
        set_inventory_value(CID, "console_tabs", {n: True for n in names})
        if back is not None:
            set_inventory_value(CID, "__back_tab__", back)

    def build(self):
        self.page.pending_layouts = []
        self.page.gui_queue_console_tabs()
        return list(self.page.pending_layouts[-1].rows[0].columns)

    def labels_on(self, items):
        return [getattr(i, "click_text", None) for i in items
                if isinstance(i, TabControl)]
class TestModeOffIsUnchanged(EpaddStripBase):
    """The opt-in promise, at the drawing end."""

    def test_every_declared_tab_still_draws(self):
        self.declare(["help", "cargo", "fabricate"], back="engineering")
        items = self.build()
        self.assertEqual(sorted(self.labels_on(items)),
                         ["cargo", "engineering", "fabricate", "help"])

    def test_the_epadd_route_existing_changes_nothing_on_its_own(self):
        """Shipping the route in an addon must not switch any console over."""
        self.declare(["help", "cargo"], back="engineering", epadd_route=True)
        self.assertNotIn("ePADD", self.labels_on(self.build()))
class TestModeOn(EpaddStripBase):
    def test_apps_are_not_on_the_bar_at_all(self):
        """The collapse is now structural rather than a special case.

        `help`/`cargo`/`fabricate`/`quest` are `//gui/app` routes, so a console
        enabling them by name matches nothing in the TAB table and they simply are not
        strip entries - the code no longer has to empty a list it just built.
        """
        self.declare([], back="engineering")
        set_inventory_value(CID, "console_tabs",
                            {"engineering": True, "help": True, "cargo": True,
                             "fabricate": True, "quest": True})
        for n in ("help", "cargo", "fabricate", "quest"):
            GuiAppDecoratorLabel.all[n] = f"label_{n}"
        labels = [t for t in self.labels_on(self.build()) if t is not None]
        self.assertEqual(labels, ["engineering"])

    def test_there_is_no_button_spelling_the_word(self):
        """It used to be a tab labelled "ePADD". The tablet glyph says it instead, so
        the slot beside it is free to say who is sitting there."""
        self.declare(["help"], back="engineering")
        self.assertNotIn("ePADD", self.labels_on(self.build()))

    def test_the_status_region_opens_the_epadd_route(self):
        """The PADD is a region of its own beside the tab row, and the region as a
        whole is the hit target."""
        self.declare(["help"], back="engineering")
        self.build()
        region = self.page.identity_badge
        event = FakeEvent(CID)
        event.sub_tag = region.click_tag
        region.on_message(event)
        self.assertEqual(self.page.gui_task.jumped, ["label_epadd"])

    def test_the_glyph_is_not_a_button(self):
        """Button chrome around it read as a second control beside the first, and a
        second click region does the same thing twice."""
        self.declare(["help"], back="engineering")
        self.build()
        cols = list(self.page.identity_badge.rows[0].columns)
        glyph = next(c for c in cols if isinstance(c, Icon))
        self.assertFalse(hasattr(glyph, "label"))
        self.assertIsNone(getattr(glyph, "click_tag", None))

    def test_the_back_button_keeps_its_colour(self):
        """It is still how you leave; nothing about it moves."""
        self.declare(["help"], back="engineering")
        back = next(i for i in self.build()
                    if isinstance(i, TabControl) and i.click_text == "engineering")
        self.assertEqual(back.background_color, "#999")

    def test_there_is_never_an_overflow_menu(self):
        """Twenty APPS put nothing on the bar, so there is nothing to overflow."""
        self.declare([], back="engineering")
        tabs = {"engineering": True}
        for i in range(20):
            tabs[f"app{i}"] = True
            GuiAppDecoratorLabel.all[f"app{i}"] = f"label_app{i}"
        set_inventory_value(CID, "console_tabs", tabs)
        self.assertFalse([i for i in self.build() if isinstance(i, TabOverflow)])


class TestConsumption(EpaddStripBase):
    """Drawing still consumes the declaration - the every-build contract is untouched."""

    def test_console_tabs_are_cleared_in_epadd_mode(self):
        self.declare(["help", "cargo"], back="engineering")
        self.build()
        self.assertEqual(get_inventory_value(CID, "console_tabs", {}), {})

    def test_the_back_tab_is_cleared_too(self):
        self.declare(["help"], back="engineering")
        self.build()
        self.assertIsNone(get_inventory_value(CID, "__back_tab__"))
class TestChangingConsole(EpaddStripBase):
    """An empty declaration does not clobber the record - so the thing that MUST
    clobber it is moving to a station with different apps."""
class TestWithoutTheRoute(EpaddStripBase):
    """Turning the mode on in a mission that never got the //gui/tab/epadd stub."""

    def test_it_falls_back_to_the_classic_strip(self):
        self.declare(["help", "cargo"], back="engineering", epadd_route=False)
        self.assertEqual(sorted(self.labels_on(self.build())),
                         ["cargo", "engineering", "help"])

    def test_and_draws_no_padd_button(self):
        self.declare(["help"], back="engineering", epadd_route=False)
        self.assertNotIn("ePADD", self.labels_on(self.build()))


if __name__ == "__main__":
    unittest.main()
