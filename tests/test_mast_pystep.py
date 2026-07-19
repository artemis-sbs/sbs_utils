"""Phase 7 (experimental): prove the bdb-based Python stepper can step INTO a
Python function that a MAST eval/exec calls, park on its lines, inspect locals,
step, and run to completion — all headless, no VS Code.
"""
import os
import threading
import unittest

from cosmos_dev.mast_pystep import PyStepper

THIS_FILE = os.path.normcase(os.path.abspath(__file__))


def helper(a):
    b = a + 1          # first body line
    c = b * 2
    return c


def outer(n):
    total = 0
    for i in range(n):
        total = total + helper(i)
    return total


def _stop_in_this_file(fn):
    if not fn or fn.startswith("<"):
        return False
    return os.path.normcase(os.path.abspath(fn)) == THIS_FILE


class TestPyStepper(unittest.TestCase):
    def _run_async(self, stepper, code_str, glbls, is_exec=False):
        code = compile(code_str, "<string>", "exec" if is_exec else "eval")
        box = {}

        def run():
            box["r"] = (stepper.run_exec if is_exec else stepper.run_eval)(code, glbls, {})
        t = threading.Thread(target=run, daemon=True)
        t.start()
        return t, box

    def test_step_into_and_inspect(self):
        stepper = PyStepper(_stop_in_this_file)
        t, box = self._run_async(stepper, "helper(10)", {"helper": helper})

        # Parks on helper's first body line: `a` bound, `b` not yet.
        self.assertTrue(stepper.wait(3.0), "never parked in helper")
        self.assertEqual(stepper.location()["func"], "helper")
        self.assertEqual(stepper.variables().get("a"), 10)
        self.assertNotIn("b", stepper.variables())

        # Step one line -> `b` now assigned.
        stepper.step()
        self.assertTrue(stepper.wait(3.0))
        self.assertEqual(stepper.variables().get("b"), 11)

        # Continue to completion; eval result is (10+1)*2.
        stepper.cont()
        t.join(3.0)
        self.assertFalse(t.is_alive())
        self.assertEqual(box["r"], 22)

    def test_step_over_a_call(self):
        # `next` at the call line should run helper() without parking inside it.
        stepper = PyStepper(_stop_in_this_file)
        t, box = self._run_async(stepper, "outer(3)", {"outer": outer, "helper": helper})

        self.assertTrue(stepper.wait(3.0))
        self.assertEqual(stepper.location()["func"], "outer")   # total = 0
        stops_in_helper = 0
        # Walk with `next` a bunch; we should stay in outer, never park in helper.
        for _ in range(12):
            stepper.next()
            if not stepper.wait(3.0):
                break
            if stepper.location()["func"] == "helper":
                stops_in_helper += 1
        self.assertEqual(stops_in_helper, 0, "step-over parked inside the callee")
        stepper.cont()
        t.join(3.0)
        self.assertEqual(box["r"], outer(3))

    def test_exec_statements(self):
        stepper = PyStepper(_stop_in_this_file)
        t, box = self._run_async(stepper, "y = helper(5)", {"helper": helper}, is_exec=True)
        self.assertTrue(stepper.wait(3.0))
        self.assertEqual(stepper.location()["func"], "helper")
        stepper.cont()
        t.join(3.0)
        self.assertFalse(t.is_alive())


import unittest as _ut  # noqa


# --- Integration: step INTO Python from a real MAST run ---------------------
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()
from sbs_utils.mast.mast import Mast


def mast_pyhelper(a):
    b = a + 5
    return b * 2


Mast.make_global_var("mast_pyhelper", mast_pyhelper)  # callable from MAST eval

MAST_CODE = """
logger(var="output")
marker = 1
x = mast_pyhelper(10)
log("x is {x}")
"""


class TestStepIntoFromMast(unittest.TestCase):
    def tearDown(self):
        from sbs_utils.mast.mastscheduler import MastTicker
        MastTicker.on_enter_node = None

    def test_step_into_python_from_mast(self):
        from tests.test_mast_debug import build_runner, line_of, FILE
        from cosmos_dev.mast_debug import MastDebugCore, run_scheduler_in_thread
        errors, runner, mast = build_runner(MAST_CODE)
        self.assertEqual(errors, [])

        dbg = MastDebugCore().install(mast)
        dbg.enable_python_step(stop_in=_stop_in_this_file)
        try:
            bp = line_of(mast, "x = mast_pyhelper(10)")
            dbg.set_breakpoints(FILE, [bp])
            worker = run_scheduler_in_thread(runner, "main")

            # 1) stop at the MAST line (still MAST land)
            self.assertTrue(dbg.wait_for_pause(), "MAST breakpoint missed")
            self.assertEqual(dbg.location()["line"], bp)
            self.assertFalse(dbg.in_python)

            # 2) step in -> descend into the Python function MAST evaluates
            dbg.step_in()
            self.assertTrue(dbg.wait_for_pause(), "did not stop in Python")
            self.assertTrue(dbg.in_python, "not paused in Python")
            loc = dbg.location()
            self.assertEqual(loc["cmd"], "python")
            self.assertEqual(loc["label"], "mast_pyhelper")
            self.assertEqual(dbg.variables("Locals").get("a"), 10)

            # merged stack: Python frame on top, a MAST frame underneath
            st = dbg.stack()
            self.assertEqual(st[0]["label"], "mast_pyhelper")
            self.assertTrue(any(f.get("cmd") != "python" for f in st),
                            "no MAST frame under the Python frames")

            # 3) step a Python line -> b is now assigned
            dbg.step_in()
            self.assertTrue(dbg.wait_for_pause())
            self.assertEqual(dbg.variables("Locals").get("b"), 15)

            # 4) continue out of Python and finish the mission
            dbg.resume()
            worker.join(5.0)
            self.assertFalse(worker.is_alive(), "did not run to completion")
            self.assertEqual(runner.runtime_errors, [])
            # x = (10+5)*2 = 30
            out = runner.get_value("output", None)[0].getvalue()
            self.assertEqual(out, "x is 30\n")
        finally:
            dbg.uninstall()


if __name__ == "__main__":
    unittest.main()
