"""GUI handlers registered by a task that has ENDED (LM issue #707).

CHARACTERIZATION -- pins behavior as it is TODAY so any later change is
measured, not guessed. Several of these assertions are expected to FLIP when
the fix lands; each one says so.

`on gui_message(w):` compiles to an inline block inside the label that ran the
`on` statement, and MessageTrigger keeps a hard reference to the task that was
executing it. On click it does push_inline_block() + tick_in_context() on THAT
task. If the task has since ended (->END / yield success), MastTicker.tick()
returns at its leading `if self.done:` before ever looking at pending_jump, so
the block is discarded silently -- and the tag_map entry survives, because it is
only cleared when a new GUI is presented.

The handler kinds fail differently, which is why the matrix is worth the length:
  on gui_message(w):      inline block on the builder task   -> dropped
  on_press=<label>        task.jump() with no tick           -> dropped
  on_press=<callable>     called directly, no task involved  -> works
  gui_message(w, label)   sub-task parented to the corpse    -> one tick, then stalls
  gui_message_callback    on_message_cb, no task at all      -> works
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import cosmos_dev.mock.sbs as sbs
from sbs_utils.mast.maststory import MastStory
from sbs_utils.mast_sbs import story_nodes  # noqa: F401  (registers route/gui nodes)
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.mast.mastscheduler import MastScheduler
from sbs_utils.mast.mast_globals import MastGlobals
from sbs_utils.agent import clear_shared
from sbs_utils.gui import Gui
from sbs_utils.helpers import FrameContext, Context, FakeEvent, props_display_text

CID = 1

# Collector shared with MAST. A module-level list keeps these assertions
# independent of `shared` variable scoping, which is not what they are about.
HITS = []


def probe_hit(what):
    HITS.append(what)


def probe_press():
    """on_press=<python callable> -- MessageHandler calls this with no args."""
    HITS.append("callable")


def probe_cb(event, item):
    """gui_message_callback -- Column.on_message calls cb(event, layout_item)."""
    HITS.append("cb")


MastGlobals.import_python_function(probe_hit)
MastGlobals.import_python_function(probe_press)
MastGlobals.import_python_function(probe_cb)


class HandlerPage(StoryPage):
    story = None


class _Base(unittest.TestCase):
    """Build a real StoryPage from a MAST snippet, present it, click by text."""

    def start(self, code):
        HITS.clear()
        clear_shared()
        Gui.clients = {}
        Gui.widget_list_sent = {}
        sbs.create_new_sim()
        sbs.resume_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(0, "test"))

        story = MastStory()
        errors = story.compile(code, "deadbuilder", story)
        self.assertEqual(errors, [], f"compile errors: {errors}")
        story.compiler_errors = []
        HandlerPage.story = story
        FrameContext.mast = story

        self.errors = []
        self._orig_rte = MastScheduler.runtime_error
        MastScheduler.runtime_error = lambda s, message: self.errors.append(message)

        self.page = HandlerPage()
        Gui.push(CID, self.page)
        self.present(3)
        return self.page

    def tearDown(self):
        if getattr(self, "_orig_rte", None) is not None:
            MastScheduler.runtime_error = self._orig_rte
        Gui.clients = {}
        Gui.widget_list_sent = {}
        HandlerPage.story = None
        FrameContext.task = None
        FrameContext.page = None
        FrameContext.mast = None
        FrameContext.context = None
        HITS.clear()

    def present(self, n=1):
        for _ in range(n):
            # the mock sim exposes time_tick_counter read-only; physics owns the
            # backing field, and nothing runs physics in a unit test.
            sbs.sim._time_tick_counter += 30      # ~1 sim-second per present
            self.page.present(FakeEvent(CID, "gui_present"))

    def find_tag(self, text):
        want = text.strip().lower()
        for tag, entry in list(self.page.tag_map.items()):
            item = entry[0] if isinstance(entry, tuple) and entry else entry
            shown = props_display_text(getattr(item, "value", None))
            if shown and shown.strip().lower() == want:
                return tag
        self.fail(f"no widget showing {text!r}; on screen: {self.visible()}")

    def visible(self):
        out = []
        for tag, entry in list(self.page.tag_map.items()):
            item = entry[0] if isinstance(entry, tuple) and entry else entry
            shown = props_display_text(getattr(item, "value", None))
            if shown:
                out.append(shown.strip())
        return out

    def click(self, text="Press"):
        Gui.on_message(FakeEvent(client_id=CID, tag="gui_message",
                                 sub_tag=self.find_tag(text)))

    def builder(self):
        """The MessageTrigger's task -- whichever task built the widget."""
        entry = self.page.tag_map[self.find_tag("Press")]
        node = entry[1] if isinstance(entry, tuple) else entry
        return node.task


# --- fixtures ---------------------------------------------------------------
# Each builds one button showing "Press" and attaches one handler.

LIVE = """
gui_section("area: 5,5,95,95;")
gui_row()
b = gui_button("Press")
on gui_message(b):
    probe_hit("ran")
await gui()
"""

DEAD_TASK_SCHEDULE = """
gui_section("area: 5,5,95,95;")
await task_schedule(builder)
await gui()

== builder ==
    gui_row()
    b = gui_button("Press")
    on gui_message(b):
        probe_hit("ran")
    ->END
"""

DEAD_SUB_TASK_SCHEDULE = """
gui_section("area: 5,5,95,95;")
await sub_task_schedule(builder)
await gui()

== builder ==
    gui_row()
    b = gui_button("Press")
    on gui_message(b):
        probe_hit("ran")
    ->END
"""

DEAD_GUI_SUB_TASK_YIELD = """
gui_section("area: 5,5,95,95;")
await gui_sub_task_schedule(builder)
await gui()

== builder ==
    gui_row()
    b = gui_button("Press")
    on gui_message(b):
        probe_hit("ran")
    yield success
"""

DEAD_ON_PRESS_LABEL = """
gui_section("area: 5,5,95,95;")
await task_schedule(builder)
await gui()

== builder ==
    gui_row()
    b = gui_button("Press", on_press=pressed)
    ->END

== pressed ==
    probe_hit("on_press")
    ->END
"""

# on_press=<label> on a LIVE task is a JUMP that takes the task over -- the
# handler has to hand the console back, or present() raises "Did you set END or
# Yield the last GUI Task?". That is the existing contract, not a defect.
LIVE_ON_PRESS_LABEL = """
jump screen

== screen ==
    gui_section("area: 5,5,95,95;")
    gui_row()
    b = gui_button("Press", on_press=pressed)
    await gui()

== pressed ==
    probe_hit("on_press")
    jump screen
"""

DEAD_ON_PRESS_CALLABLE = """
gui_section("area: 5,5,95,95;")
await task_schedule(builder)
await gui()

== builder ==
    gui_row()
    b = gui_button("Press", on_press=probe_press)
    ->END
"""

DEAD_GUI_MESSAGE_CALLBACK = """
gui_section("area: 5,5,95,95;")
await task_schedule(builder)
await gui()

== builder ==
    gui_row()
    b = gui_button("Press")
    gui_message_callback(b, probe_cb)
    ->END
"""

DEAD_GUI_MESSAGE_LABEL_SLOW = """
gui_section("area: 5,5,95,95;")
await task_schedule(builder)
await gui()

== builder ==
    gui_row()
    b = gui_button("Press")
    gui_message(b, slow_handler)
    ->END

== slow_handler ==
    probe_hit("start")
    await delay_sim(seconds=1)
    probe_hit("finished")
    ->END
"""

DEAD_INLINE_BLOCK_SLOW = """
gui_section("area: 5,5,95,95;")
await task_schedule(builder)
await gui()

== builder ==
    gui_row()
    b = gui_button("Press")
    on gui_message(b):
        probe_hit("start")
        await delay_sim(seconds=1)
        probe_hit("finished")
    ->END
"""


class TestInlineBlock(_Base):
    """`on gui_message(w):` -- the form reported in #707."""

    def test_live_builder_runs_the_block(self):
        self.start(LIVE)
        self.click()
        self.assertEqual(HITS, ["ran"])
        self.assertEqual(self.errors, [])

    def test_dead_builder_via_task_schedule_drops_the_block(self):
        # AS OF TODAY: silently nothing. This is #707.
        self.start(DEAD_TASK_SCHEDULE)
        self.assertTrue(self.builder().done(), "the builder must really be dead")
        self.click()
        self.assertEqual(HITS, [],
                         "TODAY: the block is discarded because the builder ended")
        self.assertEqual(self.errors, [], "and nothing is reported anywhere")

    def test_dead_builder_via_sub_task_schedule_drops_the_block(self):
        self.start(DEAD_SUB_TASK_SCHEDULE)
        self.click()
        self.assertEqual(HITS, [])

    def test_dead_builder_via_gui_sub_task_yield_drops_the_block(self):
        # `yield success` sets ticker.done through yields_once, same as ->END.
        self.start(DEAD_GUI_SUB_TASK_YIELD)
        self.click()
        self.assertEqual(HITS, [])

    def test_dead_click_mutates_the_corpse(self):
        # push_inline_block runs BEFORE the done check that discards the jump,
        # so every dead click leaves pending_jump set and grows label_stack by
        # one PushData that nothing will ever pop.
        self.start(DEAD_TASK_SCHEDULE)
        builder = self.builder()
        self.click()
        self.click()
        self.assertEqual(len(builder.label_stack), 2,
                         "TODAY: each dead click leaks a label_stack entry")
        self.assertIsNotNone(builder.active_ticker.pending_jump,
                             "TODAY: the jump stays queued forever")

    def test_live_block_never_gives_the_gui_task_back(self):
        # Same root cause as tests/test_inline_block_return.py, on the GUI path:
        # the block's `on_end` node never pops, so the gui task parks there
        # instead of resuming its `await gui()`.
        self.start(LIVE)
        gui_task = self.page.gui_task
        self.assertEqual(len(gui_task.label_stack), 0)
        self.click()
        self.assertEqual(len(gui_task.label_stack), 1,
                         "TODAY: the inline push is never popped")
        self.click()
        self.assertEqual(len(gui_task.label_stack), 2,
                         "TODAY: it grows once per click")

    def test_dead_builder_slow_block_drops_it_too(self):
        self.start(DEAD_INLINE_BLOCK_SLOW)
        self.click()
        self.present(5)
        self.assertEqual(HITS, [])


class TestOnPress(_Base):
    """gui_button(on_press=...) -- MessageHandler, not MessageTrigger."""

    def test_live_on_press_label_runs(self):
        self.start(LIVE_ON_PRESS_LABEL)
        self.click()
        self.present(2)
        self.assertEqual(HITS, ["on_press"])

    def test_dead_on_press_label_does_nothing(self):
        # MessageHandler only calls task.jump() here -- it never ticks, and a
        # dead task is never ticked again by anyone.
        self.start(DEAD_ON_PRESS_LABEL)
        self.click()
        self.present(5)
        self.assertEqual(HITS, [],
                         "TODAY: on_press=<label> is dropped on a dead task")
        self.assertEqual(self.errors, [])

    def test_dead_on_press_callable_still_runs(self):
        # The only path with no task in it. Must stay green through every phase.
        self.start(DEAD_ON_PRESS_CALLABLE)
        self.click()
        self.assertEqual(HITS, ["callable"])


class TestCallbackForms(_Base):
    """The task-free path, and the sub-task path that stalls."""

    def test_dead_gui_message_callback_still_runs(self):
        self.start(DEAD_GUI_MESSAGE_CALLBACK)
        self.click()
        self.assertEqual(HITS, ["cb"])

    def test_dead_gui_message_label_runs_one_tick_then_stalls(self):
        # start_sub_task + tick_in_context gets exactly ONE tick regardless of
        # the parent's state, so a trivial handler looks like it works. The
        # sub-task is parented to the corpse, and only the parent's tick drives
        # sub-tasks -- so it never runs again.
        self.start(DEAD_GUI_MESSAGE_LABEL_SLOW)
        self.click()
        self.assertEqual(HITS, ["start"], "the one free tick runs the first line")
        self.present(10)
        self.assertEqual(HITS, ["start"],
                         "TODAY: it never resumes -- the parent that would tick it is dead")


if __name__ == "__main__":
    unittest.main()
