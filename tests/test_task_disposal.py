"""Finished MAST tasks must leave the Agent registries — and be collectable.

A MastAsyncTask is an Agent: __init__ calls self.add(), registering it in
Agent.all, in Agent.roles under "__MAST_TASK__", and in Agent._has_inventory under
every variable name it holds. Historically nothing ever called remove(), so a
finished task was dropped from the scheduler's `tasks` list but stayed in the
registries forever — a busy mission grew Agent.all without bound (measured 47k
agents on LegendaryMissions, 92% of them finished tasks).

Two distinct claims are tested here, because dropping the registry entry is NOT
by itself enough to free the memory:
  1. dispose() unregisters the task from all three class-level registries.
  2. The task object is then actually reclaimed. A task holds itself four ways
     (the "mast_task" inventory value, both tickers, root_task), so these are
     reference CYCLES — refcounting alone will not free them and only Python's
     cyclic collector can. The weakref tests below pin that down.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import gc
import unittest
import weakref

from sbs_utils.mast.mast import Mast
from sbs_utils.mast.mastscheduler import MastScheduler, MastAsyncTask
from sbs_utils.mast_sbs import story_nodes  # noqa: F401  (registers Cosmos nodes)
from sbs_utils.agent import Agent, clear_shared
from sbs_utils.mast.mast_globals import MastGlobals
from sbs_utils.helpers import FrameContext, Context, FakeEvent

import sbs_utils.procedural.execution as ex  # noqa: F401
MastGlobals.import_python_module('sbs_utils.procedural.execution')
MastGlobals.import_python_module('sbs_utils.procedural.timers')   # delay_sim

from cosmos_dev.mock import sbs


class _TMastScheduler(MastScheduler):
    def runtime_error(self, message):
        raise AssertionError(f"RUNTIME ERROR: {message}")


class _FakeSim:
    def __init__(self):
        self.time_tick_counter = 0


def _tasks_in_registry():
    return [a for a in Agent.all.values() if isinstance(a, MastAsyncTask)]


def _build(code):
    mast = Mast()
    clear_shared()
    errors = mast.compile(code, "dispose_test", mast)
    FrameContext.context = Context(_FakeSim(), sbs, FakeEvent())
    FrameContext.mast = mast
    return errors, _TMastScheduler(mast)


def _run_out(runner, ticks=40):
    # Advance the fake sim clock, or delay_sim() never elapses and a task that
    # awaits one simply never finishes (which looks exactly like a disposal bug).
    sim = FrameContext.context.sim
    for _ in range(ticks):
        sim.time_tick_counter += 30      # ~1 sim-second per tick
        if not runner.tick():
            break


class TestTaskDisposal(unittest.TestCase):
    def setUp(self):
        Agent.clear()
        gc.collect()

    def test_finished_task_leaves_agent_all(self):
        errors, runner = _build('x = 1\n->END\n')
        self.assertEqual(errors, [])
        runner.start_task("main")
        _run_out(runner)
        self.assertEqual(runner.tasks, [], "task should leave the scheduler list")
        self.assertEqual(_tasks_in_registry(), [],
                         "a finished task must not linger in Agent.all")

    def test_burst_of_tasks_returns_to_baseline(self):
        # The shape that actually leaked: a loop spawning short-lived tasks.
        errors, runner = _build(
            '=== spawner\n'
            '    logger(var="output")\n'
            '    for i in range(25):\n'
            '        task_schedule(worker)\n'
            '    ->END\n'
            '=== worker\n'
            '    log("w")\n'
            '    ->END\n'
        )
        self.assertEqual(errors, [])
        base = len(Agent.all)
        runner.start_task("spawner")
        _run_out(runner, ticks=80)
        out = runner.get_value("output", None)[0].getvalue()
        self.assertEqual(out.count("w"), 25, "all workers must actually run")
        self.assertEqual(_tasks_in_registry(), [],
                         "25 finished tasks must all be unregistered")
        self.assertLessEqual(len(Agent.all), base,
                             "Agent.all must return to its pre-burst size")

    def test_disposed_task_is_actually_collected(self):
        """The registry entry is not the only reference — prove the object dies.

        A task holds itself (mast_task inventory, mast_ticker, py_ticker,
        root_task), so it is only reclaimable by the CYCLIC collector. If some
        other structure (a scheduler list, dependent_tasks, a promise) still held
        it, this weakref would survive gc.collect() and the test would fail.

        A SECOND task is run first: `scheduler.active_task` still points at the
        most recently ticked task, so the newest one is legitimately pinned. That
        pointer is left alone on purpose (callers read it after a run), and it
        holds one task, not a growing set — so the check is that an older task is
        freed once active_task has moved on.
        """
        errors, runner = _build('x = 1\n->END\n=== later\n    z = 2\n    ->END\n')
        self.assertEqual(errors, [])
        task = runner.start_task("main")
        ref = weakref.ref(task)
        _run_out(runner)
        del task
        runner.start_task("later")      # active_task moves off the task under test
        _run_out(runner)
        gc.collect()
        self.assertIsNone(ref(), "a finished task must be reclaimable, not just unregistered")

    def test_dispose_purges_role_and_inventory_registries(self):
        """Agent.all is one of THREE registries; the id must leave all of them."""
        errors, runner = _build('some_task_var = 42\n->END\n')
        self.assertEqual(errors, [])
        task = runner.start_task("main")
        tid = task.id
        # add_role() lowercases; set_inventory_value() only strips. Assert the
        # registries as they are actually keyed, not as the source spells them.
        self.assertIn(tid, Agent.roles.collection_set("__mast_task__"))
        self.assertIn(tid, Agent._has_inventory.collection_set("some_task_var"))
        _run_out(runner)
        self.assertNotIn(tid, Agent.roles.collection_set("__mast_task__"),
                         "__MAST_TASK__ role entry must be purged")
        self.assertNotIn(tid, Agent._has_inventory.collection_set("some_task_var"),
                         "inventory-key registry entry must be purged")

    def test_dispose_is_idempotent(self):
        errors, runner = _build('x = 1\n->END\n')
        self.assertEqual(errors, [])
        task = runner.start_task("main")
        _run_out(runner)
        task.dispose()   # already disposed by the scheduler
        task.dispose()
        self.assertEqual(_tasks_in_registry(), [])

    def test_revived_task_reregisters(self):
        """jump_restart_task revives a finished task; it must rejoin Agent.all."""
        errors, runner = _build('x = 1\n->END\n=== second\n    x = 2\n    ->END\n')
        self.assertEqual(errors, [])
        task = runner.start_task("main")
        _run_out(runner)
        self.assertNotIn(task.id, Agent.all, "finished task starts out disposed")
        task.jump_restart_task("second")
        self.assertIn(task.id, Agent.all,
                      "a revived task must be registered again, or lookups silently miss it")


class TestSweepBackstop(unittest.TestCase):
    """sweep_finished() catches tasks that never pass through the done-list.

    Real missions start tasks from routes, comms, science and overlays, and some
    of those run to completion in place (unscheduled) or as a sub-task whose
    parent stops ticking. Those never reach the two disposal points, so the sweep
    on the GarbageCollector cadence is what actually bounds Agent.all.
    """

    def setUp(self):
        Agent.clear()
        gc.collect()

    def test_sweep_disposes_an_unscheduled_finished_task(self):
        errors, runner = _build('x = 1\n->END\n=== side\n    q = 9\n    ->END\n')
        self.assertEqual(errors, [])
        host = runner.start_task("main")
        # unscheduled -> never enters scheduler.tasks, so normal disposal can't see it
        stray = host.start_task("side", defer=True, inherit=False, unscheduled=True)
        stray.tick_in_context()
        self.assertTrue(stray.done(), "the stray task should have finished")
        self.assertIn(stray.id, Agent.all, "and it lingers until something sweeps it")

        swept = MastAsyncTask.sweep_finished()
        self.assertGreaterEqual(swept, 1)
        self.assertNotIn(stray.id, Agent.all, "sweep must unregister a finished task")

    def test_sweep_leaves_running_tasks_alone(self):
        errors, runner = _build('=== waiter\n    await delay_sim(30)\n    ->END\n')
        self.assertEqual(errors, [])
        task = runner.start_task("waiter")
        runner.tick()
        self.assertFalse(task.done(), "task is still awaiting")
        MastAsyncTask.sweep_finished()
        self.assertIn(task.id, Agent.all, "a RUNNING task must never be swept")


class TestSubTaskDisposal(unittest.TestCase):
    def setUp(self):
        Agent.clear()
        gc.collect()

    def test_finished_sub_tasks_are_disposed(self):
        errors, runner = _build(
            '=== parent\n'
            '    sub_task_schedule(child)\n'
            '    await delay_sim(0)\n'
            '    ->END\n'
            '=== child\n'
            '    y = 1\n'
            '    ->END\n'
        )
        self.assertEqual(errors, [])
        runner.start_task("parent")
        _run_out(runner, ticks=60)
        self.assertEqual(_tasks_in_registry(), [],
                         "sub-tasks must be unregistered along with their parent")


if __name__ == "__main__":
    unittest.main()
