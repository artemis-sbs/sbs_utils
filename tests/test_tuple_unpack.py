"""Tuple unpacking in MAST assignments: `a, b = expr`.

Previously unsupported (the Assign node set a var literally named "a, b"); now the
runtime binds each plain name via the normal per-name write-back. These are runtime
tests (compile + tick a real story) mirroring test_mast_runtime.py's harness.
`for a, b in ...` is a separate (Loop-node) concern and NOT covered here.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from sbs_utils.mast.mast import Mast
from sbs_utils.mast.mastscheduler import MastScheduler
from sbs_utils.mast_sbs import story_nodes  # noqa: F401  (registers Cosmos nodes)
from sbs_utils.agent import Agent, clear_shared
from sbs_utils.mast.mast_globals import MastGlobals
from sbs_utils.helpers import FrameContext, Context, FakeEvent

import sbs_utils.procedural.execution as ex  # noqa: F401
MastGlobals.import_python_module('sbs_utils.procedural.execution')

from cosmos_dev.mock import sbs


class _TMastScheduler(MastScheduler):
    def runtime_error(self, message):
        raise AssertionError(f"RUNTIME ERROR: {message}")


class _FakeSim:
    def __init__(self):
        self.time_tick_counter = 0


def _run(code, start_label="main"):
    mast = Mast()
    clear_shared()
    errors = mast.compile(code, "tup_test", mast)
    FrameContext.context = Context(_FakeSim(), sbs, FakeEvent())
    FrameContext.mast = mast
    runner = _TMastScheduler(mast)
    if not errors:
        runner.start_task(start_label)
        for _ in range(20):
            if not runner.tick():
                break
    return errors, runner


def _out(runner):
    return runner.get_value("output", None)[0].getvalue()


class TestTupleUnpack(unittest.TestCase):
    def test_pair_from_literal(self):
        errors, runner = _run('logger(var="output")\na, b = 3, 7\nlog(str(a))\nlog(str(b))\n->END\n')
        self.assertEqual(errors, [])
        self.assertEqual(_out(runner), "3\n7\n")

    def test_from_variable_tuple(self):
        errors, runner = _run('logger(var="output")\nt = (5, 9)\na, b = t\nlog(str(a + b))\n->END\n')
        self.assertEqual(errors, [])
        self.assertEqual(_out(runner), "14\n")

    def test_three_names_from_list(self):
        errors, runner = _run('logger(var="output")\nx, y, z = [1, 2, 3]\nlog(str(z))\n->END\n')
        self.assertEqual(errors, [])
        self.assertEqual(_out(runner), "3\n")

    def test_single_assign_of_tuple_still_binds_whole(self):
        # No comma on the LHS -> normal assignment; x holds the whole tuple.
        errors, runner = _run('logger(var="output")\nx = 1, 2\nlog(str(x))\n->END\n')
        self.assertEqual(errors, [])
        self.assertEqual(_out(runner), "(1, 2)\n")

    def test_shared_scope_unpack(self):
        errors, runner = _run('logger(var="output")\nshared a, b = 11, 22\nlog(str(a))\n->END\n')
        self.assertEqual(errors, [])
        self.assertEqual(_out(runner), "11\n")
        self.assertEqual(Agent.SHARED.get_inventory_value("a"), 11)
        self.assertEqual(Agent.SHARED.get_inventory_value("b"), 22)


class TestForTupleUnpack(unittest.TestCase):
    def test_for_enumerate(self):
        code = ('logger(var="output")\ntotal = 0\n'
                'for i, v in enumerate([10, 20, 30]):\n    total = total + i + v\n'
                'log(str(total))\n->END\n')                 # (0+10)+(1+20)+(2+32)? no: 10,21,32 -> 63
        errors, runner = _run(code)
        self.assertEqual(errors, [])
        self.assertEqual(_out(runner), "63\n")

    def test_for_pairs(self):
        code = ('logger(var="output")\ntotal = 0\n'
                'for k, v in [[1, 2], [3, 4]]:\n    total = total + k * v\n'
                'log(str(total))\n->END\n')                 # 1*2 + 3*4 = 14
        errors, runner = _run(code)
        self.assertEqual(errors, [])
        self.assertEqual(_out(runner), "14\n")

    def test_for_single_name_regression(self):
        code = ('logger(var="output")\ntotal = 0\n'
                'for x in [1, 2, 3]:\n    total = total + x\n'
                'log(str(total))\n->END\n')                 # 6
        errors, runner = _run(code)
        self.assertEqual(errors, [])
        self.assertEqual(_out(runner), "6\n")

    def test_for_while_form_regression(self):
        code = ('logger(var="output")\nn = 0\n'
                'for x while n < 3:\n    n = n + 1\n'
                'log(str(n))\n->END\n')                      # while n<3 -> n ends 3
        errors, runner = _run(code)
        self.assertEqual(errors, [])
        self.assertEqual(_out(runner), "3\n")


if __name__ == '__main__':
    unittest.main(exit=False)
