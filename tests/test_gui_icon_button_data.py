"""gui_icon_button carries `data` the way gui_button does (LM #708).

An icon button had no way to say WHICH row it belonged to: a loop that built
one per item could only close over the loop variable, which every handler then
read at its final value -- the for-loop handler trap. `data` is the answer the
rest of the widgets already had; these pin that it reaches a handler by both
routes (unpacked as variables, and as `__ITEM__.data`) and that `on_press`
behaves the way gui_button's does.

The one deliberate difference from gui_button: with no `on_press` NO runtime
node is registered. Every icon button ever written passed None there, and a
MessageHandler with nothing to run starts a sub-task on the label None for
every click.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import cosmos_dev.mock.sbs as sbs
from sbs_utils.agent import clear_shared
from sbs_utils.gui import Gui
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.mast.mast_globals import MastGlobals
from sbs_utils.mast.maststory import MastStory
from sbs_utils.mast.mastscheduler import MastScheduler
from sbs_utils.mast_sbs import story_nodes  # noqa: F401  (registers gui nodes)
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.pages.layout.icon import Icon
from sbs_utils.pages.layout.icon_button import IconButton

CID = 1

# A module-level sink keeps these assertions independent of `shared` scoping.
HITS = []


def icb_hit(what):
    HITS.append(what)


def icb_press():
    """on_press=<python callable> -- MessageHandler calls this with no args."""
    HITS.append("callable")


# MAST globals live in ONE flat namespace shared by the whole discovered suite,
# so these carry a file-specific prefix.
MastGlobals.import_python_function(icb_hit)
MastGlobals.import_python_function(icb_press)


class IconButtonPage(StoryPage):
    story = None


class _Base(unittest.TestCase):
    """Build a real StoryPage from a MAST snippet, present it, click a widget."""

    def tearDown(self):
        if getattr(self, "_orig_rte", None) is not None:
            MastScheduler.runtime_error = self._orig_rte
        Gui.clients = {}
        Gui.widget_list_sent = {}
        IconButtonPage.story = None
        FrameContext.task = None
        FrameContext.page = None
        FrameContext.mast = None
        FrameContext.context = None
        HITS.clear()

    def start(self, code):
        HITS.clear()
        clear_shared()
        Gui.clients = {}
        Gui.widget_list_sent = {}
        sbs.create_new_sim()
        sbs.resume_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(0, "test"))

        story = MastStory()
        errors = story.compile(code, "iconbuttondata", story)
        self.assertEqual(errors, [], f"compile errors: {errors}")
        story.compiler_errors = []
        IconButtonPage.story = story
        FrameContext.mast = story

        self.errors = []
        self._orig_rte = MastScheduler.runtime_error
        MastScheduler.runtime_error = lambda s, message: self.errors.append(message)

        self.page = IconButtonPage()
        Gui.push(CID, self.page)
        self.present(3)
        return self.page

    def present(self, n=1):
        for _ in range(n):
            sbs.sim._time_tick_counter += 30      # ~1 sim-second per present
            self.page.present(FakeEvent(CID, "gui_present"))

    def entries(self, kind):
        """(tag, widget, runtime_node) for every widget of `kind` on the page."""
        out = []
        for tag, entry in list(self.page.tag_map.items()):
            item = entry[0] if isinstance(entry, tuple) and entry else entry
            node = entry[1] if isinstance(entry, tuple) and len(entry) > 1 else None
            if not isinstance(item, kind):
                continue
            # A click-tagged widget is in the map twice, under its engine tag
            # and under its click_tag. It is still one widget.
            if any(found is item for _, found, _ in out):
                continue
            out.append((tag, item, node))
        return out

    def only(self, kind=IconButton):
        found = self.entries(kind)
        self.assertEqual(len(found), 1, f"expected one {kind.__name__}, got {found}")
        return found[0]

    def click(self, tag):
        """A click the way the engine delivers one: dispatch, then a tick."""
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(CID, "gui_message"))
        Gui.on_message(FakeEvent(client_id=CID, tag="gui_message", sub_tag=tag))
        self.present(1)

    def assertNoRuntimeErrors(self):
        self.assertEqual(self.errors, [], f"runtime errors: {self.errors}")


HEAD = 'gui_section("area: 5,5,95,95;")\ngui_row()\n'


class TestIconButtonData(_Base):

    def test_data_is_attached_to_the_widget(self):
        self.start(HEAD + 'd = ~~{"slot": 7}~~\n'
                          'b = gui_icon_button("icon_index:1;", data=d)\n'
                          'await gui()\n')
        _, widget, _ = self.only()
        self.assertEqual(widget.data, {"slot": 7})

    def test_no_data_leaves_it_none(self):
        self.start(HEAD + 'b = gui_icon_button("icon_index:1;")\n'
                          'await gui()\n')
        _, widget, node = self.only()
        self.assertIsNone(widget.data)
        # No on_press means nothing to run -- see the module docstring.
        self.assertIsNone(node)

    def test_a_dict_unpacks_into_an_on_gui_message_block(self):
        """The issue's own example: read the value back in the handler."""
        self.start(HEAD + 'd = ~~{"some": "data"}~~\n'
                          'b = gui_icon_button("icon_index:1;", data=d)\n'
                          'on gui_message(b):\n'
                          '    icb_hit(some)\n'
                          '    icb_hit(__ITEM__.data.get("some"))\n'
                          'await gui()\n')
        tag, _, _ = self.only()
        self.click(tag)
        self.assertNoRuntimeErrors()
        self.assertEqual(HITS, ["data", "data"])

    def test_a_gui_message_label_handler_gets_the_data(self):
        self.start(HEAD + 'd = ~~{"slot": 3}~~\n'
                          'b = gui_icon_button("icon_index:1;", data=d)\n'
                          'gui_message(b, icb_label)\n'
                          'await gui()\n'
                          '\n'
                          '== icb_label ==\n'
                          '    icb_hit(slot)\n'
                          '    icb_hit(__ITEM__.data.get("slot"))\n')
        tag, _, _ = self.only()
        self.click(tag)
        self.assertNoRuntimeErrors()
        self.assertEqual(HITS, [3, 3])

    def test_each_button_in_a_loop_carries_its_own_row(self):
        """The trap this exists to close: without data every handler reads the
        loop variable at its FINAL value."""
        self.start(HEAD + 'for i in range(3):\n'
                          '    d = ~~{"slot": i}~~\n'
                          '    b = gui_icon_button("icon_index:1;", data=d)\n'
                          '    on gui_message(b):\n'
                          '        icb_hit(slot)\n'
                          'await gui()\n')
        found = self.entries(IconButton)
        self.assertEqual(len(found), 3)
        for tag, _, _ in found:
            self.click(tag)
        self.assertNoRuntimeErrors()
        self.assertEqual(HITS, [0, 1, 2])


class TestIconButtonOnPress(_Base):

    def test_on_press_calls_a_python_callable(self):
        self.start(HEAD + 'b = gui_icon_button("icon_index:1;", on_press=icb_press)\n'
                          'await gui()\n')
        tag, _, node = self.only()
        self.assertIsNotNone(node)
        self.click(tag)
        self.assertNoRuntimeErrors()
        self.assertEqual(HITS, ["callable"])

    def test_on_press_jumps_to_a_label_with_the_data_in_scope(self):
        self.start(HEAD + 'd = ~~{"slot": 5}~~\n'
                          'b = gui_icon_button("icon_index:1;", data=d, on_press=icb_jumped)\n'
                          'await gui()\n'
                          '\n'
                          '== icb_jumped ==\n'
                          '    icb_hit(slot)\n'
                          '    icb_hit(__ITEM__.data.get("slot"))\n'
                          # on_press jumps the GUI TASK, so the label it lands
                          # on has to leave a screen behind it.
                          '    gui_section("area: 5,5,95,95;")\n'
                          '    gui_row()\n'
                          '    gui_text("done")\n'
                          '    await gui()\n')
        tag, _, _ = self.only()
        self.click(tag)
        self.assertNoRuntimeErrors()
        self.assertEqual(HITS, [5, 5])


class TestIconData(_Base):
    """A plain icon becomes clickable with a `click_tag:`, so it carries data too."""

    def test_icon_data_reaches_a_handler(self):
        self.start(HEAD + 'd = ~~{"slot": 9}~~\n'
                          'ic = gui_icon("icon_index:1;", style="click_tag: icb_icon;", data=d)\n'
                          'on gui_message(ic):\n'
                          '    icb_hit(slot)\n'
                          'await gui()\n')
        _, widget, _ = self.only(Icon)
        self.assertEqual(widget.data, {"slot": 9})
        self.click("icb_icon")
        self.assertNoRuntimeErrors()
        self.assertEqual(HITS, [9])


if __name__ == "__main__":
    unittest.main()
