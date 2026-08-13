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
from sbs_utils.mast.mastscheduler import MastAsyncTask
from sbs_utils.mast.core_nodes.on_change import OnChangeRuntimeNode
from sbs_utils.agent import Agent
from sbs_utils.agent import clear_shared
from sbs_utils.gui import Gui
from sbs_utils.helpers import FrameContext, Context, FakeEvent, props_display_text
from sbs_utils.procedural.gui.message import (dead_handler_sites_clear,
                                              dead_handler_site_count)

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
        dead_handler_sites_clear()
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
        self._restore_flags()

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
        """A click the way the engine delivers one.

        handlerhooks._cosmos_event_handler does `Gui.on_message(event)` and then
        `tick_the_rest(event)` in the same breath, so a tick ALWAYS follows a
        click and two clicks can never land between ticks. Dispatching without
        the tick produces states the engine cannot reach -- which is exactly the
        mistake that made an unreachable "rapid click" defect look real.
        """
        self.click_raw(text)
        self.present(1)                      # tick_the_rest -> Gui.present

    def click_raw(self, text="Press"):
        """Just the dispatch, for asserting on the state before the tick."""
        Gui.on_message(FakeEvent(client_id=CID, tag="gui_message",
                                 sub_tag=self.find_tag(text)))

    def setUp(self):
        # Characterization classes describe behavior with the #707 fix DISABLED.
        # Pin it: these must not silently start testing the default.
        self._revive = MastAsyncTask.revive_ended_handlers
        self._pop = OnChangeRuntimeNode.pop_inline_block_on_end
        MastAsyncTask.revive_ended_handlers = False
        OnChangeRuntimeNode.pop_inline_block_on_end = False

    def _restore_flags(self):
        MastAsyncTask.revive_ended_handlers = self._revive
        OnChangeRuntimeNode.pop_inline_block_on_end = self._pop

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

    def test_dead_click_does_not_mutate_the_corpse(self):
        # push_inline_block used to run BEFORE the done check that discards the
        # jump, so every dead click left pending_jump set and grew label_stack
        # by one PushData that nothing would ever pop.
        self.start(DEAD_TASK_SCHEDULE)
        builder = self.builder()
        self.click()
        self.click()
        self.assertEqual(len(builder.label_stack), 0,
                         "a dropped click must not touch the finished task")
        self.assertIsNone(builder.active_ticker.pending_jump)

    def test_dead_click_warns_once_per_site(self):
        # The silence is most of what made #707 hard to place. One warning per
        # SOURCE SITE, not per click and not per rebuilt widget.
        self.start(DEAD_TASK_SCHEDULE)
        dead_handler_sites_clear()
        with self.assertLogs("mast.runtime", level="WARNING") as caught:
            self.click()
        self.assertEqual(len(caught.output), 1)
        self.assertIn("already ended", caught.output[0])
        self.assertIn("gui_message_callback", caught.output[0],
                      "the warning must name the way out")
        self.assertEqual(dead_handler_site_count(), 1)
        self.click()
        self.click()
        self.assertEqual(dead_handler_site_count(), 1, "still one site, not three")

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

    def test_dead_on_press_sub_task_runs_one_tick_then_stalls(self):
        self.start(DEAD_ON_PRESS_SUB_TASK_SLOW)
        self.click()
        self.assertEqual(HITS, ["start"])
        self.present(10)
        self.assertEqual(HITS, ["start"],
                         "TODAY: the sub-task is parented to a corpse")

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


DEAD_ON_PRESS_SUB_TASK_SLOW = """
gui_section("area: 5,5,95,95;")
await task_schedule(builder)
await gui()

== builder ==
    gui_row()
    b = gui_button("Press", on_press=slow_handler, is_sub_task=True)
    ->END

== slow_handler ==
    probe_hit("start")
    await delay_sim(seconds=1)
    probe_hit("finished")
    ->END
"""

DEAD_SCOPE = """
gui_section("area: 5,5,95,95;")
await task_schedule(builder)
await gui()

== builder ==
    local = 10
    gui_row()
    b = gui_button("Press")
    on gui_message(b):
        probe_hit(local)
        local = local + 1
    ->END
"""

TWO_SCREENS = """
jump screen_one

== screen_one ==
    gui_section("area: 5,5,95,95;")
    await task_schedule(builder)
    gui_row()
    n = gui_button("Next", on_press=screen_two)
    await gui()

== builder ==
    gui_row()
    b = gui_button("Press")
    on gui_message(b):
        probe_hit("start")
        await delay_sim(seconds=5)
        probe_hit("finished")
    ->END

== screen_two ==
    gui_section("area: 5,5,95,95;")
    gui_row()
    gui_text("SECOND")
    await gui()
"""


class _Fixed(_Base):
    """Both behavior flags ON -- this is what the fix does."""

    def setUp(self):
        super().setUp()                      # saves the real defaults
        MastAsyncTask.revive_ended_handlers = True
        OnChangeRuntimeNode.pop_inline_block_on_end = True


class TestRevivedInlineBlock(_Fixed):
    def test_dead_builder_runs_the_block(self):
        self.start(DEAD_TASK_SCHEDULE)
        self.click()
        self.assertEqual(HITS, ["ran"])
        self.assertEqual(self.errors, [])

    def test_it_runs_once_per_click_not_twice(self):
        # The revive and the pop both touch the same push/jump machinery; a
        # double-fire is the obvious way for them to interact badly.
        self.start(DEAD_TASK_SCHEDULE)
        self.click()
        self.click()
        self.click()
        self.assertEqual(HITS, ["ran", "ran", "ran"])

    def test_every_dead_form_runs(self):
        for code in (DEAD_TASK_SCHEDULE, DEAD_SUB_TASK_SCHEDULE,
                     DEAD_GUI_SUB_TASK_YIELD):
            with self.subTest(code=code.splitlines()[3]):
                self.start(code)
                self.click()
                self.assertEqual(HITS, ["ran"])

    def test_the_block_still_sees_the_builders_scope(self):
        # This is why the task is revived in place rather than replaced: the
        # block was written against the builder's locals, and writes have to
        # land where its author expects.
        self.start(DEAD_SCOPE)
        builder = self.builder()
        self.click()
        self.click()
        self.assertEqual(HITS, [10, 11])
        self.assertEqual(builder.get_variable("local"), 12)

    def test_an_awaiting_block_finishes(self):
        self.start(DEAD_INLINE_BLOCK_SLOW)
        self.click()
        self.assertEqual(HITS, ["start"])
        self.present(4)
        self.assertEqual(HITS, ["start", "finished"],
                         "a revived task must keep getting ticks")

    def test_the_builder_ends_again_and_is_disposed(self):
        self.start(DEAD_TASK_SCHEDULE)
        builder = self.builder()
        self.click()
        self.present(3)
        self.assertTrue(builder.done(), "it must not be left running")
        self.assertNotIn(builder, self.page.gui_task.sub_tasks,
                         "and must not stay parented to the gui task")
        self.assertNotIn(builder.id, Agent.all,
                         "and must leave the Agent registry again")

    def test_repeat_clicks_do_not_stack_up_sub_tasks(self):
        self.start(DEAD_TASK_SCHEDULE)
        for _ in range(5):
            self.click()
            self.present(1)
        self.assertLessEqual(len(self.page.gui_task.sub_tasks), 1)

    def test_a_new_gui_ends_a_handler_still_awaiting(self):
        self.start(TWO_SCREENS)
        self.click("Press")
        self.assertEqual(HITS, ["start"])
        revived = self.builder()
        self.click("Next")          # rebuilds the page onto screen_two
        self.present(3)
        self.assertTrue(revived.done(),
                        "a revived handler belongs to the GUI that owned the widget")
        self.assertEqual(HITS, ["start"], "so it must not finish after the swap")

    def test_live_builder_is_unaffected_and_returns_to_await_gui(self):
        self.start(LIVE)
        gui_task = self.page.gui_task
        self.click()
        self.click()
        self.assertEqual(HITS, ["ran", "ran"])
        self.assertEqual(len(gui_task.label_stack), 0,
                         "the inline push must be balanced by a pop")


class TestRepeatClicks(_Fixed):
    """Pressing the same button over and over.

    An earlier version of this file dispatched clicks without the tick the
    engine always performs, and found a state where the task parked on the
    block's end node with nothing to resume. That state is unreachable:
    handlerhooks calls tick_the_rest immediately after Gui.on_message, so a
    second click cannot arrive before the first block's return has been taken.
    The scenario was an artifact of the harness.
    """

    def test_repeat_clicks_stay_correct(self):
        self.start(LIVE)
        for _ in range(10):
            self.click()
        self.assertEqual(HITS, ["ran"] * 10)
        self.assertEqual(len(self.page.gui_task.label_stack), 0,
                         "every push must be balanced by a pop")

    def test_repeat_clicks_on_a_revived_builder_leave_nothing_behind(self):
        self.start(DEAD_TASK_SCHEDULE)
        builder = self.builder()
        for _ in range(10):
            self.click()
        self.present(2)
        self.assertEqual(HITS, ["ran"] * 10)
        self.assertTrue(builder.done(), "it must end again after each wake")
        self.assertEqual(len(builder.label_stack), 0)
        self.assertNotIn(builder, self.page.gui_task.sub_tasks)
        self.assertNotIn(builder.id, Agent.all, "and not accumulate in the registry")


SELF_TICKING_PANEL = """
jump repaint

== repaint ==
    gui_section("area: 5,5,95,95;")
    gui_row()
    b = gui_button("Press")
    on gui_message(b):
        probe_hit("pressed")
    await gui(timeout=delay_sim(seconds=1))
    probe_hit("tick")
    jump repaint
"""


class TestSelfTickingPanel(_Fixed):
    """The user-visible face of the inline-block pop.

    A panel that repaints itself -- a live countdown, a refreshing status --
    only advances because the task comes back to `await gui(timeout=...)`. A
    handler block that falls off its end used to park the task on the block's
    end node, so ONE press froze the panel permanently.

    Measured: without the pop, self-ticks after a press go 3 -> 0. With it, the
    panel keeps ticking.

    Note what HIDES this: an `on signal ...:` block ending in `jump` escapes
    before reaching the end node and un-parks the task. LegendaryMissions'
    items/item_gui.mast has exactly that, which is why its Activate countdown
    kept working either way -- and why this shape, not that one, is the
    regression test.
    """

    def test_a_press_does_not_freeze_the_self_tick(self):
        self.start(SELF_TICKING_PANEL)
        self.present(4)
        before = HITS.count("tick")
        self.assertGreater(before, 0, "the panel must be self-ticking to begin with")
        self.click()
        self.present(6)
        self.assertGreater(HITS.count("tick") - before, 0,
                           "pressing a button must not stop the panel repainting")
        self.assertIn("pressed", HITS)


class TestReviveRefusals(_Fixed):
    """A task that died badly stays dead."""

    def test_a_crashed_builder_is_not_revived(self):
        self.start(DEAD_TASK_SCHEDULE)
        builder = self.builder()
        builder.active_ticker.errored = True
        with self.assertLogs("mast.runtime", level="WARNING"):
            self.click()
        self.assertEqual(HITS, [], "a task that crashed must not be resumed")

    def test_a_canceled_builder_is_not_revived(self):
        self.start(DEAD_TASK_SCHEDULE)
        builder = self.builder()
        builder._canceled = True
        with self.assertLogs("mast.runtime", level="WARNING"):
            self.click()
        self.assertEqual(HITS, [], "a deliberately killed task must stay dead")


class TestRevivedOtherForms(_Fixed):
    def test_dead_on_press_label_runs(self):
        self.start(DEAD_ON_PRESS_LABEL)
        self.click()
        self.assertEqual(HITS, ["on_press"])

    def test_dead_gui_message_label_finishes_instead_of_stalling(self):
        self.start(DEAD_GUI_MESSAGE_LABEL_SLOW)
        self.click()
        self.assertEqual(HITS, ["start"])
        self.present(4)
        self.assertEqual(HITS, ["start", "finished"])

    def test_dead_on_press_sub_task_finishes_instead_of_stalling(self):
        self.start(DEAD_ON_PRESS_SUB_TASK_SLOW)
        self.click()
        self.assertEqual(HITS, ["start"])
        self.present(4)
        self.assertEqual(HITS, ["start", "finished"])

    def test_the_task_free_paths_are_untouched(self):
        self.start(DEAD_ON_PRESS_CALLABLE)
        self.click()
        self.assertEqual(HITS, ["callable"])
        self.start(DEAD_GUI_MESSAGE_CALLBACK)
        self.click()
        self.assertEqual(HITS, ["cb"])


if __name__ == "__main__":
    unittest.main()
