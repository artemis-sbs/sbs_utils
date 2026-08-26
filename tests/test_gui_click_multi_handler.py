"""Every matching `on gui_click` handler runs, not just the first (LM #614).

`gui_message` had this defect in its registration; `gui_click` had it in its
DISPATCH -- `StoryPage.on_message` walked `self.on_click` and returned on the
first handler whose click() returned True. Two consequences:

  * two `on gui_click(w):` blocks for the same widget, only the first ran;
  * a catch-all `gui_click()` -- no name, so it matches every click -- silently
    shadowed every handler registered after it, which is the harder one to see
    because the catch-all itself looks like it is working.

Registration order is source order, and a handler whose name does not match is
skipped exactly as before.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import cosmos_dev.mock.sbs as sbs
from sbs_utils.mast.maststory import MastStory
from sbs_utils.mast_sbs import story_nodes  # noqa: F401  (registers route/gui nodes)
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.mast.mastscheduler import MastScheduler, MastAsyncTask
from sbs_utils.mast.mast_globals import MastGlobals
from sbs_utils.mast.core_nodes.on_change import OnChangeRuntimeNode
from sbs_utils.agent import clear_shared
from sbs_utils.gui import Gui
from sbs_utils.helpers import FrameContext, Context, FakeEvent

CID = 1

HITS = []


def gc_hit(what):
    HITS.append(what)


MastGlobals.import_python_function(gc_hit)


class ClickPage(StoryPage):
    story = None


class _Base(unittest.TestCase):
    def setUp(self):
        self._revive = MastAsyncTask.revive_ended_handlers
        self._pop = OnChangeRuntimeNode.pop_inline_block_on_end
        MastAsyncTask.revive_ended_handlers = True
        OnChangeRuntimeNode.pop_inline_block_on_end = True

    def tearDown(self):
        # hasattr, NOT "is not None": `on_runtime_error` DEFAULTS to None, so a
        # truthiness guard skips the restore and leaks this test's hook - and the
        # list it appends to - into every test that runs afterwards.
        if hasattr(self, "_orig_rte"):
            MastScheduler.on_runtime_error = self._orig_rte
        Gui.clients = {}
        Gui.widget_list_sent = {}
        ClickPage.story = None
        FrameContext.task = None
        FrameContext.page = None
        FrameContext.mast = None
        FrameContext.context = None
        HITS.clear()
        MastAsyncTask.revive_ended_handlers = self._revive
        OnChangeRuntimeNode.pop_inline_block_on_end = self._pop

    def start(self, code):
        HITS.clear()
        clear_shared()
        Gui.clients = {}
        Gui.widget_list_sent = {}
        sbs.create_new_sim()
        sbs.resume_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(0, "test"))

        story = MastStory()
        errors = story.compile(code, "guiclick", story)
        self.assertEqual(errors, [], f"compile errors: {errors}")
        story.compiler_errors = []
        ClickPage.story = story
        FrameContext.mast = story

        self.errors = []
        self._orig_rte = MastScheduler.on_runtime_error
        # StoryScheduler OVERRIDES `runtime_error`, so patching it on MastScheduler
        # binds a method nothing calls and the assertion below is vacuous. The
        # class-level `on_runtime_error` seam is what the story scheduler actually
        # fires (and is what cosmos_dev's verdict uses).
        MastScheduler.on_runtime_error = self.errors.append

        self.page = ClickPage()
        Gui.push(CID, self.page)
        self.present(3)
        return self.page

    def present(self, n=1):
        for _ in range(n):
            sbs.sim._time_tick_counter += 30
            self.page.present(FakeEvent(CID, "gui_present"))

    def click(self, click_tag):
        """A click on a click_tag, then the tick the engine always follows with."""
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(CID, "gui_message"))
        Gui.on_message(FakeEvent(client_id=CID, tag="gui_message",
                                 sub_tag=click_tag))
        self.present(1)


HEAD = 'gui_section("area: 5,5,95,95;")\ngui_row()\n'

TWO_BLOCKS = HEAD + """gui_text("$text:hi;", style="click_tag: spot;")
on gui_click("spot"):
    gc_hit("one")
on gui_click("spot"):
    gc_hit("two")
await gui()
"""

CATCH_ALL_FIRST = HEAD + """gui_text("$text:hi;", style="click_tag: spot;")
on gui_click():
    gc_hit("catch-all")
on gui_click("spot"):
    gc_hit("specific")
await gui()
"""

TWO_TARGETS = HEAD + """gui_text("$text:a;", style="click_tag: alpha;")
gui_text("$text:b;", style="click_tag: beta;")
on gui_click("alpha"):
    gc_hit("alpha")
on gui_click("beta"):
    gc_hit("beta")
await gui()
"""


class TestGuiClickMultiplicity(_Base):
    def test_two_blocks_on_one_tag_both_run(self):
        self.start(TWO_BLOCKS)
        self.click("spot")
        self.assertEqual(HITS, ["one", "two"])
        self.assertEqual(self.errors, [])

    def test_a_catch_all_no_longer_shadows_a_specific_handler(self):
        """The one that was hardest to see: the catch-all looked like it worked."""
        self.start(CATCH_ALL_FIRST)
        self.click("spot")
        self.assertEqual(HITS, ["catch-all", "specific"])

    def test_a_handler_for_another_tag_is_still_skipped(self):
        self.start(TWO_TARGETS)
        self.click("beta")
        self.assertEqual(HITS, ["beta"])


if __name__ == "__main__":
    unittest.main()
