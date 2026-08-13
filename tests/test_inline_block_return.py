"""An `on ...:` inline block must give the task back when the block ends.

CHARACTERIZATION -- these tests pin behavior as it is TODAY (LM issue #707
investigation), so any later change is measured rather than guessed.

`on change x:` / `on gui_message(w):` compile to an inline block inside the
running label. Entering it is push_inline_block(); leaving it is supposed to be
the pop in OnChangeRuntimeNode.poll(), which is gated on `self.is_running`.

But MastTicker.next() builds a FRESH runtime node for every command, so the
block's terminating `on_end` node gets a different OnChangeRuntimeNode instance
than the one `run()` set is_running on -- the pop never fires. The end node has
no `end_node` either, so poll() returns OK_RUN_AGAIN forever and the task parks
on `on_end`: it never resumes what it was doing, never ends, and grows
label_stack by one entry per trip through the block.

Blocks whose body ends in `jump` or `->END` leave before reaching `on_end`,
which is why this has stayed hidden.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from sbs_utils.mast.mast import Mast
from sbs_utils.mast.mastscheduler import MastScheduler, MastAsyncTask
from sbs_utils.mast_sbs import story_nodes  # noqa: F401  (registers Cosmos nodes)
from sbs_utils.mast.core_nodes.on_change import OnChangeRuntimeNode
from sbs_utils.agent import Agent, clear_shared
from sbs_utils.mast.mast_globals import MastGlobals
from sbs_utils.helpers import FrameContext, Context, FakeEvent

MastGlobals.import_python_module('sbs_utils.procedural.execution')
MastGlobals.import_python_module('sbs_utils.procedural.timers')   # delay_sim

from cosmos_dev.mock import sbs


class _TMastScheduler(MastScheduler):
    def runtime_error(self, message):
        raise AssertionError(f"RUNTIME ERROR: {message}")


class _FakeSim:
    def __init__(self):
        self.time_tick_counter = 0


def _build(code):
    mast = Mast()
    clear_shared()
    errors = mast.compile(code, "inline_block_test", mast)
    FrameContext.context = Context(_FakeSim(), sbs, FakeEvent())
    FrameContext.mast = mast
    return errors, _TMastScheduler(mast)


def _tick(runner, ticks=1):
    sim = FrameContext.context.sim
    for _ in range(ticks):
        sim.time_tick_counter += 30      # ~1 sim-second per tick
        runner.tick()


# The block body falls off the end -- no jump, no ->END.
FALL_OFF = """
hits = []
counter = 0
on change counter:
    hits.append(counter)
counter = 1
await delay_sim(seconds=2)
hits.append("resumed")
->END
"""

# Same shape, but the body jumps out of the block.
JUMPS_OUT = """
hits = []
counter = 0
on change counter:
    hits.append(counter)
    jump finish
counter = 1
await delay_sim(seconds=2)
hits.append("resumed")
->END

== finish ==
    hits.append("jumped")
    ->END
"""


class TestInlineBlockReturn(unittest.TestCase):
    def setUp(self):
        Agent.clear()

    def tearDown(self):
        FrameContext.task = None
        FrameContext.page = None
        FrameContext.mast = None
        FrameContext.context = None
        Agent.clear()

    def _start(self, code):
        errors, runner = _build(code)
        self.assertEqual(errors, [], f"compile errors: {errors}")
        task = runner.start_task("main")
        return runner, task

    def test_block_that_falls_off_the_end_runs_once(self):
        runner, task = self._start(FALL_OFF)
        _tick(runner, 3)
        hits = task.get_variable("hits")
        # Flag-agnostic: what follows the block differs, the block itself must
        # run exactly once either way.
        self.assertEqual(hits[:1], [1],
                         "the on-change block body must run when the value changes")
        self.assertEqual(hits.count(1), 1)

    def test_block_that_falls_off_the_end_never_gives_the_task_back(self):
        # AS OF TODAY: the task parks on the `on_end` node forever -- the await
        # is never resumed, "resumed" is never appended, the task never ends.
        runner, task = self._start(FALL_OFF)
        _tick(runner, 20)
        self.assertEqual(task.get_variable("hits"), [1],
                         "TODAY: the await never resumes, so 'resumed' never lands")
        self.assertFalse(task.done(), "TODAY: the task never finishes")
        self.assertIn(task, runner.tasks, "TODAY: it stays scheduled forever")

    def test_block_that_falls_off_the_end_leaks_a_label_stack_entry(self):
        # push_inline_block appends PushData; nothing ever pops it.
        runner, task = self._start(FALL_OFF)
        _tick(runner, 5)
        self.assertEqual(len(task.label_stack), 1,
                         "TODAY: the inline push is never popped")
        self.assertEqual(task.active_ticker.pop_on_jump, 1)

    def test_block_that_jumps_out_leaves_cleanly(self):
        # The escape hatch every shipped block uses. Must behave identically
        # before and after any fix.
        runner, task = self._start(JUMPS_OUT)
        _tick(runner, 6)
        self.assertEqual(task.get_variable("hits"), [1, "jumped"])
        self.assertTrue(task.done(), "a block that jumps out ends normally")


class TestInlineBlockReturnFixed(TestInlineBlockReturn):
    """The same stories with OnChangeRuntimeNode.pop_inline_block_on_end ON.

    Inherits the fixtures but overrides every assertion that changes, so a case
    nobody remembered to override is still exercised against the flag.
    """

    def setUp(self):
        super().setUp()
        self._flag = OnChangeRuntimeNode.pop_inline_block_on_end
        OnChangeRuntimeNode.pop_inline_block_on_end = True

    def tearDown(self):
        OnChangeRuntimeNode.pop_inline_block_on_end = self._flag
        super().tearDown()

    def test_block_that_falls_off_the_end_never_gives_the_task_back(self):
        # FIXED: the block pops, the await resumes, the task finishes.
        runner, task = self._start(FALL_OFF)
        _tick(runner, 20)
        self.assertEqual(task.get_variable("hits"), [1, "resumed"],
                         "the await must resume once the block ends")
        self.assertTrue(task.done(), "and the task must finish")
        self.assertNotIn(task, runner.tasks, "and leave the scheduler")

    def test_block_that_falls_off_the_end_leaks_a_label_stack_entry(self):
        # FIXED: the push is balanced by a pop.
        runner, task = self._start(FALL_OFF)
        _tick(runner, 5)
        self.assertEqual(len(task.label_stack), 0)
        self.assertEqual(task.active_ticker.pop_on_jump, 0)

    def test_block_runs_once_per_change_not_repeatedly(self):
        # The pop must not re-enter the block: resuming at the same command
        # would run the body again on every tick.
        runner, task = self._start(FALL_OFF)
        _tick(runner, 20)
        self.assertEqual(task.get_variable("hits").count(1), 1)


if __name__ == "__main__":
    unittest.main()
