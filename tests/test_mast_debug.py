"""Phase 0 tests for the MAST debug core (cosmos_dev/mast_debug.py).

Proves the pause / step / inspect mechanics against the mock scheduler with no
DAP and no VS Code: breakpoints stop the tick thread at the right source line,
the paused state exposes the correct call stack + variables, stepping advances a
source line, jumps update the active label, and the debugger co-exists with
MastCoverage on the shared on_enter_node seam.

See MAST_DEBUGGER_PLAN.md sections 11-12.
"""
from sbs_utils.mast.mast import Mast, Scope
from sbs_utils.mast.mastscheduler import MastScheduler
from sbs_utils.agent import clear_shared
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()  # fix exe_dir / script_dir before anything touches paths

import unittest
from sbs_utils.mast_sbs import story_nodes  # noqa: F401  (register story nodes)
from sbs_utils.mast.mast_globals import MastGlobals
MastGlobals.import_python_module('sbs_utils.procedural.execution')
MastGlobals.import_python_module('sbs_utils.procedural.timers')
MastGlobals.import_python_module('sbs_utils.procedural.gui')
MastGlobals.import_python_module('sbs_utils.procedural.signal')

# Bind `log` to mast_log so "{x}" interpolates via mast scope (matches
# test_mast.py; the bare module `log` defaults use_mast_scope=False).
from sbs_utils.procedural.execution import mast_log
Mast.make_global_var("log", mast_log)

from cosmos_dev.mock import sbs as sbs
from cosmos_dev.mast_debug import MastDebugCore, run_scheduler_in_thread
from cosmos_dev.coverage import MastCoverage
from sbs_utils.helpers import FrameContext, Context, FakeEvent

# include_code=True makes cmd.line hold raw source text, so tests can locate a
# statement's line number by content instead of hard-coding (off-by-one proof).
Mast.include_code = True

FILE = "story.mast"


class RecordingScheduler(MastScheduler):
    """Like the test scheduler in test_mast.py but records runtime errors on the
    worker thread instead of asserting (an assert there wouldn't fail the test
    thread cleanly)."""
    def __init__(self, mast):
        super().__init__(mast)
        self.runtime_errors = []

    def runtime_error(self, message):
        self.runtime_errors.append(message)


class FakeSim:
    def __init__(self):
        self.time_tick_counter = 0

    def tick(self):
        self.time_tick_counter += 30


def build_runner(code, filename=FILE):
    """Compile + wire a scheduler WITHOUT starting the task (the worker thread
    starts it, because start_task ticks once immediately)."""
    mast = Mast()
    clear_shared()
    errors = mast.compile(code, filename, mast)
    FrameContext.context = Context(FakeSim(), sbs, FakeEvent())
    FrameContext.mast = mast
    runner = RecordingScheduler(mast)
    return errors, runner, mast


def line_of(mast, marker):
    """Line number of the first compiled node whose source text contains marker."""
    for label in mast.labels.values():
        for cmd in getattr(label, "cmds", None) or []:
            line = getattr(cmd, "line", None)
            if line and marker in line and getattr(cmd, "line_num", None) is not None:
                return cmd.line_num
    raise AssertionError(f"no node found for marker {marker!r}")


def logged(runner):
    out = runner.get_value("output", None)
    assert out is not None, "logger(var='output') produced no stream"
    return out[0].getvalue()


CODE = """
logger(var="output")
x = 1
x = 2
log("x is {x}")
jump second

=== second ===
y = 10
log("done {y}")
"""


# A short counted loop for conditional / hit-count / logpoint tests.
LOOP5_CODE = """
logger(var="output")
total = 0
for i in range(5):
    total = total + i
log("done {total}")
"""

# For set-variable: break at `gate = 1` (a later line), so the change lands
# before the log's args are evaluated. (The on_enter seam fires AFTER a node's
# enter(), and log() interpolates {x} in enter() — so a set only affects lines
# not yet entered.)
SETVAR_CODE = """
logger(var="output")
x = 5
gate = 1
log("x is {x}")
"""


class TestMastDebugCore(unittest.TestCase):
    def tearDown(self):
        # Make sure a failed test never leaves the class-level seam installed.
        from sbs_utils.mast.mastscheduler import MastTicker
        MastTicker.on_enter_node = None

    def test_breakpoint_step_and_inspect(self):
        errors, runner, mast = build_runner(CODE)
        self.assertEqual(errors, [])

        dbg = MastDebugCore().install(mast)
        try:
            bp_x2 = line_of(mast, "x = 2")
            bp_y = line_of(mast, "y = 10")
            ln_logx = line_of(mast, 'log("x is')
            ln_logdone = line_of(mast, 'log("done')

            resolved = dbg.set_breakpoints(FILE, [bp_x2, bp_y])
            self.assertEqual(resolved, sorted([bp_x2, bp_y]))

            worker = run_scheduler_in_thread(runner, "main")

            # -- stop 1: breakpoint on `x = 2`, BEFORE it executes -> x == 1 ----
            self.assertTrue(dbg.wait_for_pause(), "never hit first breakpoint")
            loc = dbg.location()
            self.assertEqual(loc["line"], bp_x2)
            self.assertEqual(loc["label"], "main")
            self.assertEqual(loc["reason"], "breakpoint")
            self.assertEqual(dbg.variables("Task").get("x"), 1)

            # call stack: single top frame at the current node
            stack = dbg.stack()
            self.assertEqual(len(stack), 1)
            self.assertEqual(stack[0]["label"], "main")
            self.assertEqual(stack[0]["line"], bp_x2)

            # -- step over -> next source line `log("x is {x}")`, x now 2 -------
            dbg.step_over()
            self.assertTrue(dbg.wait_for_pause(), "step over did not stop")
            loc = dbg.location()
            self.assertEqual(loc["line"], ln_logx)
            self.assertEqual(loc["reason"], "step")
            self.assertEqual(dbg.variables("Task").get("x"), 2)

            # -- resume -> runs log, jumps to `second`, stops at `y = 10` -------
            dbg.resume()
            self.assertTrue(dbg.wait_for_pause(), "never hit second breakpoint")
            loc = dbg.location()
            self.assertEqual(loc["line"], bp_y)
            self.assertEqual(loc["label"], "second")   # jump updated the label
            self.assertIsNone(dbg.variables("Task").get("y"))  # not set yet

            # -- step over -> `log("done {y}")`, y now 10 -----------------------
            dbg.step_over()
            self.assertTrue(dbg.wait_for_pause(), "step over (2) did not stop")
            self.assertEqual(dbg.location()["line"], ln_logdone)
            self.assertEqual(dbg.variables("Task").get("y"), 10)

            # -- resume to completion -------------------------------------------
            dbg.resume()
            worker.join(timeout=5.0)
            self.assertFalse(worker.is_alive(), "worker did not finish")
            self.assertEqual(runner.runtime_errors, [])
            self.assertEqual(logged(runner), "x is 2\ndone 10\n")
        finally:
            dbg.uninstall()

    def test_breakpoint_on_blank_line_binds_to_next_node(self):
        errors, runner, mast = build_runner(CODE)
        self.assertEqual(errors, [])
        dbg = MastDebugCore().install(mast)
        try:
            # The blank line just before `=== second ===`.
            blank = line_of(mast, "jump second") + 1
            code_line = line_of(mast, "y = 10")
            resolved = dbg.set_breakpoints(FILE, [blank])
            # A BP on a line with no node resolves forward to the next node.
            self.assertEqual(resolved, [code_line])
        finally:
            dbg.uninstall()

    def test_stack_reports_caller_frames(self):
        # Within one task, extra call-stack frames come from inline blocks
        # (buttons / event handlers / `await ...:` bodies) via push_inline_block,
        # which store a PushData on task.label_stack. Those constructs are
        # GUI/async-driven and fiddly to complete headlessly, so here we drive a
        # real task to a real breakpoint, then assert the debugger's frame walk
        # over a genuine PushData reports both frames and the frame-local scope.
        from sbs_utils.mast.mastscheduler import PushData
        errors, runner, mast = build_runner(CODE)
        self.assertEqual(errors, [])
        dbg = MastDebugCore().install(mast)
        try:
            bp_x2 = line_of(mast, "x = 2")
            ln_y = line_of(mast, "y = 10")
            dbg.set_breakpoints(FILE, [bp_x2])
            worker = run_scheduler_in_thread(runner, "main")
            self.assertTrue(dbg.wait_for_pause())

            task = dbg.location()["task_id"]  # sanity: we have a stop
            self.assertIsNotNone(task)
            paused_task = dbg._cur[0]

            # Single frame before any push.
            self.assertEqual(len(dbg.stack()), 1)

            # Simulate an inline-call frame: a caller parked in `second` with a
            # frame-local var. (This is exactly what push_inline_block records.)
            paused_task.label_stack.append(PushData("second", 0, {"local_z": 99}))
            try:
                stack = dbg.stack()
                self.assertEqual(len(stack), 2)
                self.assertEqual(stack[0]["line"], bp_x2)        # innermost = live node
                self.assertEqual(stack[1]["label"], "second")    # caller frame
                self.assertEqual(stack[1]["line"], ln_y)         # resolved from its loc
                # Frame scope reads the innermost label_stack frame's data.
                self.assertEqual(dbg.variables("Frame"), {"local_z": 99})
            finally:
                paused_task.label_stack.pop()   # restore before resuming

            dbg.resume()
            worker.join(timeout=5.0)
            self.assertFalse(worker.is_alive())
            self.assertEqual(runner.runtime_errors, [])
            self.assertEqual(logged(runner), "x is 2\ndone 10\n")
        finally:
            dbg.uninstall()

    def test_step_mode_predicate(self):
        # Depth-based step logic (in / over / out), unit-tested directly so it
        # doesn't depend on any MAST construct. Mirrors _step_satisfied.
        class FakeTask:
            def __init__(self, depth):
                self.label_stack = [None] * depth

        dbg = MastDebugCore()
        t = FakeTask(2)

        # Never re-stop on the same source line.
        dbg._step = {"mode": "out", "task": t, "depth": 2, "line": (0, 5)}
        self.assertFalse(dbg._step_satisfied(t, (0, 5)))

        # A different task never satisfies the current step.
        self.assertFalse(dbg._step_satisfied(FakeTask(0), (0, 7)))

        # step out: stop only when depth drops below the start depth.
        self.assertFalse(dbg._step_satisfied(t, (0, 7)))          # depth 2, not < 2
        t.label_stack = [None]                                    # depth 1
        self.assertTrue(dbg._step_satisfied(t, (0, 7)))

        # step over: stop at depth <= start depth (same frame or shallower).
        dbg._step = {"mode": "over", "task": t, "depth": 1, "line": (0, 5)}
        t.label_stack = [None, None]                              # depth 2 > 1
        self.assertFalse(dbg._step_satisfied(t, (0, 7)))
        t.label_stack = [None]                                    # depth 1
        self.assertTrue(dbg._step_satisfied(t, (0, 7)))

        # step in: stop at the very next new line, any depth.
        dbg._step = {"mode": "in", "task": t, "depth": 5, "line": (0, 5)}
        t.label_stack = [None] * 9                                # deeper
        self.assertTrue(dbg._step_satisfied(t, (0, 7)))

    def test_conditional_breakpoint(self):
        errors, runner, mast = build_runner(LOOP5_CODE)
        self.assertEqual(errors, [])
        dbg = MastDebugCore().install(mast)
        try:
            bp = line_of(mast, "total = total + i")
            dbg.set_breakpoints(FILE, [{"line": bp, "condition": "i == 3"}])
            worker = run_scheduler_in_thread(runner, "main")
            self.assertTrue(dbg.wait_for_pause(), "conditional breakpoint never hit")
            self.assertEqual(dbg.variables("Task").get("i"), 3)   # stopped only at i==3
            self.assertEqual(dbg.variables("Task").get("total"), 3)  # 0+1+2, i=3 not yet added
            dbg.resume()
            worker.join(timeout=5.0)
            self.assertFalse(worker.is_alive())
        finally:
            dbg.uninstall()

    def test_hit_condition_breakpoint(self):
        errors, runner, mast = build_runner(LOOP5_CODE)
        self.assertEqual(errors, [])
        dbg = MastDebugCore().install(mast)
        try:
            bp = line_of(mast, "total = total + i")
            dbg.set_breakpoints(FILE, [{"line": bp, "hitCondition": "==3"}])
            worker = run_scheduler_in_thread(runner, "main")
            self.assertTrue(dbg.wait_for_pause(), "hit-condition breakpoint never hit")
            self.assertEqual(dbg.variables("Task").get("i"), 2)   # 3rd hit is i=2 (0,1,2)
            dbg.resume()
            worker.join(timeout=5.0)
            self.assertFalse(worker.is_alive())
        finally:
            dbg.uninstall()

    def test_logpoint_does_not_stop(self):
        errors, runner, mast = build_runner(LOOP5_CODE)
        self.assertEqual(errors, [])
        logs = []
        dbg = MastDebugCore().install(mast)
        dbg.on_output = logs.append
        try:
            bp = line_of(mast, "total = total + i")
            dbg.set_breakpoints(FILE, [{"line": bp, "logMessage": "i={i} total={total}"}])
            worker = run_scheduler_in_thread(runner, "main")
            worker.join(timeout=5.0)                 # a logpoint never pauses
            self.assertFalse(worker.is_alive(), "logpoint should not have stopped the run")
            self.assertEqual(logs, [
                "i=0 total=0", "i=1 total=0", "i=2 total=1",
                "i=3 total=3", "i=4 total=6",
            ])
            self.assertEqual(runner.runtime_errors, [])
        finally:
            dbg.uninstall()

    def test_set_variable_affects_execution(self):
        errors, runner, mast = build_runner(SETVAR_CODE)
        self.assertEqual(errors, [])
        dbg = MastDebugCore().install(mast)
        try:
            bp = line_of(mast, "gate = 1")
            dbg.set_breakpoints(FILE, [bp])
            worker = run_scheduler_in_thread(runner, "main")
            self.assertTrue(dbg.wait_for_pause())
            self.assertEqual(dbg.variables("Task").get("x"), 5)
            # Overwrite x; the not-yet-entered log line will interpolate the new value.
            self.assertEqual(dbg.set_variable("Task", "x", "42"), 42)
            self.assertEqual(dbg.variables("Task").get("x"), 42)
            dbg.resume()
            worker.join(timeout=5.0)
            self.assertFalse(worker.is_alive())
            self.assertEqual(logged(runner), "x is 42\n")
        finally:
            dbg.uninstall()

    def test_coexists_with_coverage(self):
        errors, runner, mast = build_runner(CODE)
        self.assertEqual(errors, [])

        cov = MastCoverage().install()          # taps on_enter_node first
        dbg = MastDebugCore().install(mast)     # chains coverage's hook
        try:
            worker = run_scheduler_in_thread(runner, "main")
            # No breakpoints set -> runs straight through; coverage still records.
            worker.join(timeout=5.0)
            self.assertFalse(worker.is_alive())
            self.assertEqual(runner.runtime_errors, [])
            # Coverage saw nodes on both labels via the chained hook.
            self.assertIn("main", cov.labels_hit)
            self.assertIn("second", cov.labels_hit)
            self.assertEqual(logged(runner), "x is 2\ndone 10\n")
        finally:
            dbg.uninstall()
            cov.uninstall()


if __name__ == '__main__':
    unittest.main()
