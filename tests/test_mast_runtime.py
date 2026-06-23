"""
Runtime characterization tests for the MAST execution layer.

These are GOLDEN-MASTER tests: they pin the runtime's *current* observable
behavior (even where it may be buggy) so that behavior-preserving refactors
(e.g. get_symbols() perf work) are provably safe, and gated bug-fixes have a
documented before/after. See MAST_RUNTIME_IMPROVEMENTS.md.

Three areas previously uncovered by the suite:
  - StoryScheduler scope resolution (SHARED/CLIENT/ASSIGNED/NORMAL)  -> guards P1
  - PyMAST (PyTicker) fall-through                                   -> guards T3.1
  - on_change runtime (run_on_change)                               -> guards P2
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()  # fix exe_dir/script_dir before anything touches paths

import unittest

from sbs_utils.mast.mast import Mast, Scope
from sbs_utils.mast.mastscheduler import MastScheduler, PollResults
from sbs_utils.mast_sbs.maststoryscheduler import StoryScheduler
from sbs_utils.mast_sbs import story_nodes  # registers Cosmos MAST nodes (explicit)
from sbs_utils.agent import Agent, clear_shared
from sbs_utils.mast.label import label
from sbs_utils.mast.mast_globals import MastGlobals
from sbs_utils.helpers import FrameContext, Context, FakeEvent

import sbs_utils.procedural.execution as ex
import sbs_utils.procedural.timers as timers
MastGlobals.import_python_module('sbs_utils.procedural.execution')
MastGlobals.import_python_module('sbs_utils.procedural.timers')

from cosmos_dev.mock import sbs


# ---------------------------------------------------------------------------
# Minimal runner harness (mirrors test_mast.py; kept self-contained per the
# one-harness-per-file convention).
# ---------------------------------------------------------------------------
class _TMastScheduler(MastScheduler):
    def runtime_error(self, message):
        print(f"RUNTIME ERROR: {message}")
        assert False, message


class _FakeSim:
    def __init__(self):
        self.time_tick_counter = 0

    def tick(self):
        self.time_tick_counter += 30


def _mast_run(code=None, start_label=None):
    mast = Mast()
    clear_shared()
    errors = []
    if code:
        errors = mast.compile(code, "rt_test", mast)
    else:
        mast.clear("rt_test", None)
    if start_label is None:
        start_label = "main"
    FrameContext.context = Context(_FakeSim(), sbs, FakeEvent())
    FrameContext.mast = mast
    runner = _TMastScheduler(mast)
    if len(errors) == 0:
        runner.start_task(start_label)
    return errors, runner, mast


def _register_agent(agent_id):
    a = Agent()
    a.id = agent_id
    a.add()
    return a


# ===========================================================================
# 1. StoryScheduler scope resolution  (guards P1: get_value / get_symbols)
# ===========================================================================
class TestStorySchedulerScope(unittest.TestCase):
    CLIENT_ID = 1001
    SHIP_ID = 2001

    def setUp(self):
        Agent.clear()
        clear_shared()
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        self.mast = Mast()
        self.sched = StoryScheduler(self.mast)
        self.sched.client_id = self.CLIENT_ID
        self.client = _register_agent(self.CLIENT_ID)
        self.ship = _register_agent(self.SHIP_ID)
        sbs.assign_client_to_ship(self.CLIENT_ID, self.SHIP_ID)

    def tearDown(self):
        Agent.clear()
        clear_shared()

    # --- single-source reads -------------------------------------------------
    def test_unknown_when_absent(self):
        self.assertEqual(self.sched.get_value("nope_xyz"), (None, Scope.UNKNOWN))

    def test_shared_scope(self):
        Agent.SHARED.set_inventory_value("sk", "sv")
        self.assertEqual(self.sched.get_value("sk"), ("sv", Scope.SHARED))

    def test_client_scope(self):
        self.client.set_inventory_value("ck", "cv")
        self.assertEqual(self.sched.get_value("ck"), ("cv", Scope.CLIENT))

    def test_assigned_scope(self):
        self.ship.set_inventory_value("ak", "av")
        self.assertEqual(self.sched.get_value("ak"), ("av", Scope.ASSIGNED))

    def test_scheduler_normal_scope(self):
        self.sched.set_inventory_value("nk", "nv")
        self.assertEqual(self.sched.get_value("nk"), ("nv", Scope.NORMAL))

    # --- precedence (SHARED > CLIENT > ASSIGNED > NORMAL) --------------------
    def test_shared_beats_client(self):
        Agent.SHARED.set_inventory_value("k", "shared")
        self.client.set_inventory_value("k", "client")
        self.assertEqual(self.sched.get_value("k"), ("shared", Scope.SHARED))

    def test_client_beats_assigned(self):
        self.client.set_inventory_value("k", "client")
        self.ship.set_inventory_value("k", "assigned")
        self.assertEqual(self.sched.get_value("k"), ("client", Scope.CLIENT))

    def test_assigned_beats_scheduler(self):
        self.ship.set_inventory_value("k", "assigned")
        self.sched.set_inventory_value("k", "normal")
        self.assertEqual(self.sched.get_value("k"), ("assigned", Scope.ASSIGNED))

    # --- writes --------------------------------------------------------------
    def test_set_shared_writes_shared(self):
        self.assertEqual(self.sched.set_value("k", "v", Scope.SHARED), Scope.SHARED)
        self.assertEqual(Agent.SHARED.get_inventory_value("k"), "v")

    def test_set_client_writes_client(self):
        self.assertEqual(self.sched.set_value("k", "v", Scope.CLIENT), Scope.CLIENT)
        self.assertEqual(self.client.get_inventory_value("k"), "v")

    def test_set_assigned_writes_ship(self):
        self.assertEqual(self.sched.set_value("k", "v", Scope.ASSIGNED), Scope.ASSIGNED)
        self.assertEqual(self.ship.get_inventory_value("k"), "v")

    def test_set_normal_is_unhandled_at_scheduler(self):
        # CURRENT behavior: StoryScheduler.set_value only handles
        # SHARED/CLIENT/ASSIGNED; anything else returns UNKNOWN and writes nothing.
        self.assertEqual(self.sched.set_value("k", "v", Scope.NORMAL), Scope.UNKNOWN)
        self.assertIsNone(self.sched.get_inventory_value("k"))

    # --- get_symbols (the actual P1 target) ---------------------------------
    def test_get_symbols_excludes_client_and_ship(self):
        # CURRENT behavior: get_symbols() unions SHARED + scheduler inventory
        # ONLY. Client and assigned-ship inventories are NOT in the eval
        # namespace (the client/ship union is commented out). Any get_symbols
        # optimization MUST preserve this exact set.
        Agent.SHARED.set_inventory_value("sym_shared", 1)
        self.sched.set_inventory_value("sym_sched", 2)
        self.client.set_inventory_value("sym_client", 3)
        self.ship.set_inventory_value("sym_ship", 4)
        syms = self.sched.get_symbols()
        self.assertIn("sym_shared", syms)
        self.assertIn("sym_sched", syms)
        self.assertNotIn("sym_client", syms)
        self.assertNotIn("sym_ship", syms)


# ===========================================================================
# 2. PyMAST fall-through  (guards T3.1: the `fallthrough - False` typo)
# ===========================================================================
class TestPyMastFallThrough(unittest.TestCase):
    """
    PyMAST links consecutive @label() functions in the same module: when a
    generator finishes without jump/pop/END it 'falls through' to the next.

    The `fallthrough` flag in PyTicker.tick() is meant to be cleared once the
    generator yields at least once (only an explicit yield-then-end should reach
    the fall-through branch via the flag). A known typo (`fallthrough - False`)
    leaves it set. These tests pin the CURRENT observable result so any fix to
    that line is a deliberate, reviewed behavior change.
    """

    def test_fallthrough_after_yield(self):
        @label()
        def ft_first():
            ex.logger(var='output')
            ex.log("first")
            yield PollResults.OK_RUN_AGAIN
            ex.log("first-end")
            # ends with no jump/pop/END

        @label()
        def ft_second():
            ex.log("second")
            yield PollResults.OK_END

        errors, runner, _ = _mast_run(code=None, start_label=ft_first)
        self.assertEqual(errors, [])
        for _ in range(20):
            if not runner.tick():
                break
        out = runner.get_value("output", None)[0].getvalue()
        # LOCKED to current behavior (see module docstring).
        self.assertEqual(out, "first\nfirst-end\nsecond\n")


# ===========================================================================
# 3. on_change runtime  (guards P2: run_on_change)
# ===========================================================================
class TestOnChangeRuntime(unittest.TestCase):
    def test_on_change_fires_when_value_changes(self):
        # Characterizes that the on_change block runs exactly once per detected
        # change of the watched expression (and not when it is unchanged). We
        # log a constant marker rather than rely on {} interpolation, which is
        # NOT applied for inline-block runs in this path.
        code = """
logger(var="output")
shared chg = 0
on change chg:
    log("hit")
await delay_test(999)
"""
        errors, runner, mast = _mast_run(code=code)
        self.assertEqual(errors, [])
        runner.tick()                                   # register on_change (chg==0)
        runner.tick()                                   # no change -> no fire
        Agent.SHARED.set_inventory_value("chg", 5)
        runner.tick()                                   # change -> fires once
        runner.tick()                                   # no change -> no fire
        Agent.SHARED.set_inventory_value("chg", 9)
        runner.tick()                                   # change -> fires once
        out = runner.get_value("output", None)[0].getvalue()
        # LOCKED to current behavior: one fire per change, none when unchanged.
        self.assertEqual(out, "hit\nhit\n")


if __name__ == '__main__':
    unittest.main(exit=False)
