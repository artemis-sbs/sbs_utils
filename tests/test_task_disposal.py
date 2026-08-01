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

    def test_dispose_purges_the_role_registry(self):
        """Agent.all is one of THREE registries; the id must leave the role one too."""
        errors, runner = _build('some_task_var = 42\n->END\n')
        self.assertEqual(errors, [])
        task = runner.start_task("main")
        tid = task.id
        # add_role() lowercases, so assert the registry as it is actually keyed.
        self.assertIn(tid, Agent.roles.collection_set("__mast_task__"))
        _run_out(runner)
        self.assertNotIn(tid, Agent.roles.collection_set("__mast_task__"),
                         "__MAST_TASK__ role entry must be purged")

    def test_task_vars_never_enter_the_global_inventory_index(self):
        """A task's variables are local scope, not searchable game state.

        has_inventory(key) exists to find OBJECTS. Tasks used to register every
        variable they held, which made that index thousands of collections wide
        and let a query like has_inventory("ship_id") return task ids next to
        real ships. Reads and writes of the task's own scope are unaffected.
        """
        errors, runner = _build('some_task_var = 42\n->END\n')
        self.assertEqual(errors, [])
        task = runner.start_task("main")
        self.assertNotIn(task.id, Agent._has_inventory.collection_set("some_task_var"),
                         "a task variable must not appear in the global inventory index")
        # ...but the value itself still reads back normally.
        task.set_inventory_value("local_thing", 7)
        self.assertEqual(task.get_inventory_value("local_thing"), 7)
        self.assertNotIn(task.id, Agent._has_inventory.collection_set("local_thing"))

    def test_real_agents_still_populate_the_inventory_index(self):
        """The opt-out is tasks only — ordinary agents must keep working."""
        a = Agent()
        a.id = 4242
        a.add()
        a.set_inventory_value("__BRAIN__", object())
        self.assertIn(a.id, Agent._has_inventory.collection_set("__BRAIN__"),
                      "a normal agent must still be findable by inventory key")
        a.remove()
        self.assertNotIn(a.id, Agent._has_inventory.collection_set("__BRAIN__"),
                         "and must be purged on remove")


class TestRoleIndex(unittest.TestCase):
    """The per-object role index is an index for REMOVAL only.

    Agent.roles stays the authority for every role query, so set operations
    (role("a") & role("b"), has_role, subtraction) must behave exactly as before.
    """

    def setUp(self):
        Agent.clear()
        gc.collect()

    def _agent(self, aid, roles):
        a = Agent()
        a.id = aid
        a.add()
        a.add_role(roles)
        return a

    def test_set_queries_are_unchanged(self):
        self._agent(1, "enemy, ship")
        self._agent(2, "friendly, ship")
        self._agent(3, "enemy")
        self.assertEqual(Agent.roles.collection_set("ship"), {1, 2})
        self.assertEqual(Agent.roles.collection_set("enemy"), {1, 3})
        # intersection / subtraction, the shapes missions actually use
        self.assertEqual(Agent.roles.collection_set("enemy")
                         & Agent.roles.collection_set("ship"), {1})
        self.assertEqual(Agent.roles.collection_set("ship")
                         - Agent.roles.collection_set("enemy"), {2})

    def test_comma_list_indexes_every_role(self):
        a = self._agent(7, "alpha, beta,gamma")
        self.assertEqual(a._own_roles, {"alpha", "beta", "gamma"})
        for r in ("alpha", "beta", "gamma"):
            self.assertIn(7, Agent.roles.collection_set(r))

    def test_remove_role_keeps_index_in_step(self):
        a = self._agent(8, "alpha, beta")
        a.remove_role("alpha")
        self.assertEqual(a._own_roles, {"beta"})
        self.assertNotIn(8, Agent.roles.collection_set("alpha"))
        self.assertIn(8, Agent.roles.collection_set("beta"))
        self.assertTrue(a.has_role("beta"))
        self.assertFalse(a.has_role("alpha"))

    def test_remove_purges_every_role_the_agent_held(self):
        a = self._agent(9, "alpha, beta, gamma")
        a.remove()
        for r in ("alpha", "beta", "gamma"):
            self.assertNotIn(9, Agent.roles.collection_set(r),
                             f"role {r} must be purged on remove")

    def test_index_matches_registry_after_churn(self):
        """Drift between the index and the registry is the failure mode to catch."""
        a = self._agent(11, "a1, a2")
        a.add_role("a3")
        a.remove_role("a2")
        a.add_role("a2")
        a.remove_role("nonexistent")
        in_registry = {r for r in Agent.roles.collections
                       if 11 in Agent.roles.collection_set(r)}
        self.assertEqual(a._own_roles, in_registry,
                         "per-object role index drifted from Agent.roles")

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


class TestTaskAsDataRecord(unittest.TestCase):
    """A tagged task is a RECORD and must outlive its own execution.

    procedural/prefab.py sets `prefab = FrameContext.task`, so a prefab IS its
    task. LegendaryMissions' `prefab_torpedo_type` runs once and then tags itself
    ('torpedo_definition' + the torpedo key); docking's rearm step resolves the
    type via role(key) & role("torpedo_definition") long afterwards. Disposing
    those tasks deleted the whole torpedo registry, and the only visible symptom
    was that docked ships stopped being resupplied with torpedoes - caught by
    LM_TestRange (refit_rearms_depleted_torp), NOT by any unit test.
    """

    def setUp(self):
        Agent.clear()
        gc.collect()

    def _finished_task(self, runner, label="main"):
        task = runner.start_task(label)
        _run_out(runner)
        return task

    def test_tagged_task_survives_disposal(self):
        errors, runner = _build('x = 1\n->END\n')
        self.assertEqual(errors, [])
        task = runner.start_task("main")
        task.add_role("torpedo_definition")
        task.add_role("homing")
        _run_out(runner)
        self.assertIn(task.id, Agent.all,
                      "a tagged (record) task must NOT be disposed")
        self.assertIn(task.id, Agent.roles.collection_set("torpedo_definition"))
        self.assertIn(task.id, Agent.roles.collection_set("homing"),
                      "the role registry IS the lookup - it must survive")

    def test_untagged_task_is_still_disposed(self):
        """The gate must not disable the leak fix for ordinary tasks."""
        errors, runner = _build('x = 1\n->END\n')
        self.assertEqual(errors, [])
        task = self._finished_task(runner)
        self.assertNotIn(task.id, Agent.all,
                         "an untagged task is ordinary execution - still disposed")

    def test_sweep_spares_a_record_task(self):
        errors, runner = _build('x = 1\n->END\n')
        self.assertEqual(errors, [])
        task = runner.start_task("main")
        task.add_role("torpedo_definition")
        _run_out(runner)
        MastAsyncTask.sweep_finished()
        self.assertIn(task.id, Agent.all,
                      "the sweep backstop must respect records too")

    def test_tagging_joins_the_inventory_index(self):
        """A record is looked up like any agent, so it must be findable by key.

        Excluding tasks from the has_inventory index is a perf win for the
        thousands of short-lived route/comms tasks, but a record has to be in it -
        including values set BEFORE it was tagged, hence the backfill.
        """
        errors, runner = _build('x = 1\n->END\n')
        self.assertEqual(errors, [])
        task = runner.start_task("main")
        task.set_inventory_value("torp_speed", 10)      # set BEFORE tagging
        self.assertNotIn(task.id, Agent._has_inventory.collection_set("torp_speed"),
                         "an untagged task stays out of the index")
        task.add_role("torpedo_definition")             # now it is a record
        self.assertIn(task.id, Agent._has_inventory.collection_set("torp_speed"),
                      "tagging must backfill values set before the tag")
        task.set_inventory_value("torp_damage", 35)     # and after
        self.assertIn(task.id, Agent._has_inventory.collection_set("torp_damage"))


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
