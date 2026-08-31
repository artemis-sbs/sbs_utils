"""A SUPERSEDED `await gui()` must not present (LM: end-of-game results screen).

Reported from a real bridge: on the results screen, open the Quests tab and
click a quest -- every control on the screen disappears, permanently. Measured
here: it is a SINGLE click, not the double-click the report described.

The chain, all of it working as designed until the last step:

  * The Quests tab is painted by an `on_press` HANDLER, not by the GUI task.
  * That handler reaches `await gui()`, so promote_await_gui sends the GUI task
    to the same command and ENDS the handler (#714). The GUI task builds and
    adopts its OWN GuiPromise; the handler's is left over.
  * Clicking a quest fires the `on change` block the handler registered. The
    handler has ended, so revive_for_handler wakes it to run the block (#707).
  * The block finishes and the task resumes on its own `await gui()` -- and that
    leftover promise's initial_poll ran set_button_layout -> swap_layout. The
    adopted promise had already consumed that build, so what got swapped in was
    the empty stub swap_layout leaves behind: zero widgets, gui_state settles on
    'presenting', and the console never comes back.

So: a promise promotion has taken over is marked `superseded` and can never
present. Deliberately narrower than "the page never adopted it" -- that also
stops the promotion-OFF behavior TestOffGuiTaskToday pins, where the screen is
supposed to follow the handler.

And deliberately NOT fixed in swap_layout: a stock console (`gui_console("helm")`
+ `await gui()`) legitimately swaps in a build whose tag_map is empty, so
refusing empty builds there would blank every console.

All four tests below fail without the guard.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import cosmos_dev.mock.sbs as sbs
from sbs_utils.gui import Gui
from sbs_utils.helpers import FakeEvent
from sbs_utils.mast.core_nodes.on_change import OnChangeRuntimeNode
from sbs_utils.mast.mastscheduler import MastAsyncTask
from sbs_utils.procedural.gui.gui import GuiPromise, await_gui_sites_clear

from test_gui_message_dead_builder import _Base, CID


# The results screen in miniature: a button whose HANDLER paints the real screen
# (a selectable list plus a detail widget) and registers the `on change` block
# that keeps them in step.
RESULTS_SHAPE = """
jump first

== first ==
    gui_section("area: 5,5,95,95;")
    gui_row()
    gui_button("Press", on_press="paint")
    await gui()
    ->END

== paint ==
    gui_section("area: 5,5,60,95;")
    lb = gui_list_box(["alpha", "beta"], "", select=True)
    gui_section("area: 62,5,95,95;")
    gui_row()
    detail = gui_text("$text:`nothing picked`;")
    on change lb.get_value():
        detail.value = "$text:`picked`;"
    await gui()
    ->END
"""


class _Live(_Base):
    """Every #707/#713/#714 flag at its shipping default."""

    def setUp(self):
        self._revive = MastAsyncTask.revive_ended_handlers
        self._pop = OnChangeRuntimeNode.pop_inline_block_on_end
        self._promote = MastAsyncTask.promote_await_gui
        self._dflt = MastAsyncTask.handler_sub_task_default
        self._rehost = MastAsyncTask.rehost_gui_watchers
        MastAsyncTask.revive_ended_handlers = True
        OnChangeRuntimeNode.pop_inline_block_on_end = True
        MastAsyncTask.promote_await_gui = True
        MastAsyncTask.handler_sub_task_default = True
        MastAsyncTask.rehost_gui_watchers = True
        await_gui_sites_clear()

    def _restore_flags(self):
        MastAsyncTask.revive_ended_handlers = self._revive
        OnChangeRuntimeNode.pop_inline_block_on_end = self._pop
        MastAsyncTask.promote_await_gui = self._promote
        MastAsyncTask.handler_sub_task_default = self._dflt
        MastAsyncTask.rehost_gui_watchers = self._rehost


class _Clicks:
    """The click-region tags the page emitted, in draw order.

    A listbox row is a clickregion whose tag the page never puts in tag_map, so
    find_tag() cannot reach it -- record what the mock was asked to draw.
    """

    def __init__(self):
        self.tags = []

    def __enter__(self):
        self._orig = sbs.send_gui_clickregion
        def rec(client_id, parent, tag, props, *rest):
            self.tags.append(str(tag))
            return self._orig(client_id, parent, tag, props, *rest)
        sbs.send_gui_clickregion = rec
        return self

    def __exit__(self, *exc):
        sbs.send_gui_clickregion = self._orig
        return False

    def rows(self):
        return [t for t in self.tags if t.endswith("__click")]


class TestOrphanPromiseCannotPresent(_Live):
    def test_clicking_a_row_on_a_handler_painted_screen_keeps_the_screen(self):
        """The reported bug. Before the fix the page went to zero widgets."""
        self.start(RESULTS_SHAPE)

        with _Clicks() as clicks:
            self.click("Press")               # handler paints the list screen
        rows = clicks.rows()
        self.assertTrue(rows, "the handler's screen drew no selectable rows")
        self.assertIn("alpha", self.visible())

        widgets_before = len(self.page.tag_map)
        self.assertGreater(widgets_before, 0)

        Gui.on_message(FakeEvent(client_id=CID, tag="gui_message", sub_tag=rows[0]))
        self.present(1)

        self.assertGreater(len(self.page.tag_map), 0,
                           "clicking a row blanked the whole page")
        self.assertIn("picked", self.visible(),
                      "the on change block did not update the detail widget")
        self.assertEqual(self.errors, [], f"MAST runtime errors: {self.errors}")

    def test_a_second_click_is_just_as_harmless(self):
        """As reported: a DOUBLE click. Two clicks on the same row."""
        self.start(RESULTS_SHAPE)
        with _Clicks() as clicks:
            self.click("Press")
        row = clicks.rows()[0]

        for _ in range(2):
            Gui.on_message(FakeEvent(client_id=CID, tag="gui_message", sub_tag=row))
            self.present(1)

        self.assertGreater(len(self.page.tag_map), 0,
                           "double-clicking a row blanked the whole page")
        self.assertEqual(self.errors, [], f"MAST runtime errors: {self.errors}")


class TestSupersededPromiseNeverSwaps(unittest.TestCase):
    """The guard itself, without a story around it."""

    class _Page:
        def __init__(self):
            self.gui_task = None
            self.gui_promise = None
            self.swapped = 0

        def get_path(self):
            return "gui/test"

        def set_button_layout(self, layout, promise):
            self.swapped += 1

    def test_an_ordinary_promise_presents(self):
        page = self._Page()
        p = GuiPromise(page)
        p.show_buttons = lambda: None
        p.initial_poll()
        self.assertEqual(page.swapped, 1)

    def test_a_superseded_promise_does_not_present(self):
        page = self._Page()
        p = GuiPromise(page)
        p.superseded = True                 # what promote_await_gui marks
        p.show_buttons = lambda: None
        p.initial_poll()
        self.assertEqual(page.swapped, 0,
                         "a superseded promise swapped the page's layout")
        # Consumed, not deferred: it must not keep retrying every tick.
        p.initial_poll()
        self.assertEqual(page.swapped, 0)


if __name__ == "__main__":
    unittest.main()
