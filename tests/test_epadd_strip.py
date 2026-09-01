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
from sbs_utils.mast_sbs.story_nodes.gui_tab_decorator_label import GuiTabDecoratorLabel
from sbs_utils.procedural.inventory import set_inventory_value, get_inventory_value
from sbs_utils.procedural.gui.epadd import gui_app_adopted
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
        GuiTabDecoratorLabel.all.clear()
        self.page = StoryPage()
        self.page.client_id = CID
        self.page.gui_task = _FakeGuiTask(self.page)
        self.page.console = "normal_engi"
        FrameContext.page = None

    def tearDown(self):
        GuiTabDecoratorLabel.all.clear()
        GuiTabDecoratorLabel.all.update(self._saved)
        FrameContext.page = None
        FrameContext.context = None

    def declare(self, names, back=None, epadd_route=True):
        """What a console's build leaves behind. `gui_tab_back` ENABLES the back tab
        as well as naming it, and the strip only draws a tab that has a route, so the
        back tab needs both here too."""
        names = list(names)
        if back is not None and back not in names:
            names.append(back)
        for name in names:
            GuiTabDecoratorLabel.all[name] = f"label_{name}"
        if epadd_route:
            GuiTabDecoratorLabel.all["epadd"] = "label_epadd"
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

    def mode_on(self):
        set_inventory_value(CID, "epadd_mode", True)


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

    def test_nothing_is_adopted_while_the_mode_is_off(self):
        self.declare(["help", "cargo"], back="engineering")
        self.build()
        self.assertEqual(gui_app_adopted(CID), set())


class TestModeOn(EpaddStripBase):
    def test_the_strip_is_the_padd_and_the_back_button(self):
        self.declare(["help", "cargo", "fabricate", "quest"], back="engineering")
        self.mode_on()
        self.assertEqual(sorted(self.labels_on(self.build())),
                         ["ePADD", "engineering"])

    def test_the_padd_button_is_spelled_properly(self):
        """The classic strip labels a tab with its raw lowercase route path, which
        would draw this one as "epadd". This button is drawn here, so it carries a
        literal."""
        self.declare(["help"], back="engineering")
        self.mode_on()
        self.assertIn("ePADD", self.labels_on(self.build()))

    def test_the_padd_button_opens_the_epadd_route(self):
        self.declare(["help"], back="engineering")
        self.mode_on()
        padd = next(i for i in self.build()
                    if isinstance(i, TabControl) and i.click_text == "ePADD")
        event = FakeEvent(CID)
        event.sub_tag = padd.click_tag
        padd.on_message(event)
        self.assertEqual(self.page.gui_task.jumped, ["label_epadd"])

    def test_the_back_button_keeps_its_colour(self):
        """It is still how you leave; nothing about it moves."""
        self.declare(["help"], back="engineering")
        self.mode_on()
        back = next(i for i in self.build()
                    if isinstance(i, TabControl) and i.click_text == "engineering")
        self.assertEqual(back.background_color, "#999")

    def test_there_is_never_an_overflow_menu(self):
        self.declare([f"tab{i}" for i in range(20)], back="engineering")
        self.mode_on()
        self.assertFalse([i for i in self.build() if isinstance(i, TabOverflow)])


class TestAdoption(EpaddStripBase):
    def test_what_the_console_enabled_is_handed_to_the_registry(self):
        self.declare(["help", "cargo", "fabricate"], back="engineering")
        self.mode_on()
        self.build()
        self.assertEqual(gui_app_adopted(CID), {"help", "cargo", "fabricate"})

    def test_the_back_tab_is_not_adopted(self):
        self.declare(["help", "engineering"], back="engineering")
        self.mode_on()
        self.build()
        self.assertEqual(gui_app_adopted(CID), {"help"})

    def test_the_padd_itself_is_not_adopted(self):
        self.declare(["help", "epadd"], back="engineering")
        self.mode_on()
        self.build()
        self.assertEqual(gui_app_adopted(CID), {"help"})

    def test_it_is_recorded_against_the_pages_client(self):
        """The strip is read off the page's client_id, so the record has to match -
        the same identity bug console_tab._tab_client_id exists to fix."""
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(0, "test"))  # server
        self.declare(["help"], back="engineering")
        self.mode_on()
        self.build()
        self.assertEqual(gui_app_adopted(CID), {"help"})
        self.assertEqual(get_inventory_value(0, "epadd_adopted", set()) or set(), set())


class TestConsumption(EpaddStripBase):
    """Drawing still consumes the declaration - the every-build contract is untouched."""

    def test_console_tabs_are_cleared_in_epadd_mode(self):
        self.declare(["help", "cargo"], back="engineering")
        self.mode_on()
        self.build()
        self.assertEqual(get_inventory_value(CID, "console_tabs", {}), {})

    def test_the_back_tab_is_cleared_too(self):
        self.declare(["help"], back="engineering")
        self.mode_on()
        self.build()
        self.assertIsNone(get_inventory_value(CID, "__back_tab__"))

    def test_the_adopted_record_SURVIVES_the_build(self):
        """Unlike console_tabs. The home screen is a different build from the
        console's, so a consumed record would be empty by the time it is read."""
        self.declare(["help"], back="engineering")
        self.mode_on()
        self.build()
        self.build()
        self.assertEqual(gui_app_adopted(CID), {"help"})


class TestChangingConsole(EpaddStripBase):
    """An empty declaration does not clobber the record - so the thing that MUST
    clobber it is moving to a station with different apps."""

    def test_a_different_console_replaces_the_record(self):
        self.declare(["cargo", "fabricate"], back="engineering")
        self.mode_on()
        self.build()
        self.assertEqual(gui_app_adopted(CID), {"cargo", "fabricate"})

        self.page.console = "normal_helm"
        set_inventory_value(CID, "console_tabs", {"quest": True})
        set_inventory_value(CID, "__back_tab__", "helm")
        GuiTabDecoratorLabel.all["quest"] = "label_quest"
        GuiTabDecoratorLabel.all["helm"] = "label_helm"
        self.build()
        self.assertEqual(gui_app_adopted(CID), {"quest"},
                         "helm must not inherit engineering's apps")

    def test_a_console_that_enables_nothing_ends_up_with_nothing(self):
        self.declare(["cargo"], back="engineering")
        self.mode_on()
        self.build()
        self.page.console = "normal_helm"
        set_inventory_value(CID, "console_tabs", {})
        self.build()
        self.assertEqual(gui_app_adopted(CID), set())


class TestWithoutTheRoute(EpaddStripBase):
    """Turning the mode on in a mission that never got the //gui/tab/epadd stub."""

    def test_it_falls_back_to_the_classic_strip(self):
        self.declare(["help", "cargo"], back="engineering", epadd_route=False)
        self.mode_on()
        self.assertEqual(sorted(self.labels_on(self.build())),
                         ["cargo", "engineering", "help"])

    def test_and_draws_no_padd_button(self):
        self.declare(["help"], back="engineering", epadd_route=False)
        self.mode_on()
        self.assertNotIn("ePADD", self.labels_on(self.build()))


if __name__ == "__main__":
    unittest.main()
