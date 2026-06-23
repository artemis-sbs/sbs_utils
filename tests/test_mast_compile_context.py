"""Regression tests for per-compile block state (CompileContext).

if/match/await/on/for block tracking used to live as class attributes shared
across every compile, so an aborted compile (or a nested import) could leak
state into the next/outer compile. Each compile now gets its own CompileContext
reached via compile_info.ctx. These tests lock that isolation in.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()
import unittest

from sbs_utils.mast.mast import Mast, CompileContext
from sbs_utils.agent import clear_shared
from sbs_utils.mast_sbs import story_nodes  # noqa: F401  registers nodes
from sbs_utils.mast.mast_globals import MastGlobals
import sbs_utils.procedural.execution  # noqa: F401
import sbs_utils.procedural.gui  # noqa: F401
MastGlobals.import_python_module('sbs_utils.procedural.execution')
MastGlobals.import_python_module('sbs_utils.procedural.gui')

from sbs_utils.mast_sbs.story_nodes.button import Button
from sbs_utils.mast.core_nodes.await_cmd import Await
from sbs_utils.mast.core_nodes.conditional import IfStatements, MatchStatements
from sbs_utils.mast.core_nodes.on_change import OnChange
from sbs_utils.mast.core_nodes.on_signal import OnSignal
from sbs_utils.mast.core_nodes.loop import LoopStart


def compile_src(code):
    m = Mast()
    clear_shared()
    errors = m.compile(code, "test", m)
    return errors, m


# Aborts while an `await` block is still open: the inline-python node raises a
# SyntaxError during construction, so the compiler bails before the await closes.
BAD_OPEN_AWAIT = """
== bad ==
    await delay_sim(1):
        ~~ this is : not : valid python ~~
"""

# A button at label scope (no enclosing await) -- should be a stand-alone button
# with await_node None. If the previous aborted compile leaked its open await,
# this button would attach to that stale node instead.
GOOD_BUTTON = """
== good ==
    + "Click":
        log("hi")
"""

# Broad clean sample after an abort, to smoke-test all block types.
GOOD_BLOCKS = """
== blocks ==
    x = 0
    if x > 0:
        log("a")
    elif x < 0:
        log("b")
    else:
        log("c")
    for i in range(3):
        x += i
    match x:
        case 1:
            log("one")
        case _:
            log("other")
"""


class TestCompileContextIsolation(unittest.TestCase):
    def test_block_state_is_not_class_level(self):
        # Guards against re-introducing shared compile state on the node types.
        self.assertFalse(hasattr(IfStatements, "if_chains"))
        self.assertFalse(hasattr(MatchStatements, "chains"))
        self.assertFalse(hasattr(Await, "stack"))
        self.assertFalse(hasattr(OnChange, "stack"))
        self.assertFalse(hasattr(OnSignal, "stack"))
        self.assertFalse(hasattr(LoopStart, "loop_stack"))

    def test_each_compile_gets_fresh_context(self):
        a = CompileContext()
        b = CompileContext()
        self.assertIsNot(a.await_stack, b.await_stack)
        self.assertIsNot(a.if_chains, b.if_chains)
        self.assertIsNot(a.loop_stack, b.loop_stack)

    def test_aborted_await_does_not_leak_into_next_compile(self):
        e1, _ = compile_src(BAD_OPEN_AWAIT)
        self.assertTrue(len(e1) > 0, "compile 1 should have errored mid-await")

        e2, m2 = compile_src(GOOD_BUTTON)
        self.assertEqual(e2, [], f"compile 2 should be clean, got: {e2}")
        btn = next((c for c in m2.labels["good"].cmds if isinstance(c, Button)), None)
        self.assertIsNotNone(btn, "expected a Button in label 'good'")
        # The decisive check: a fresh context means no stale open await to grab.
        self.assertIsNone(btn.await_node,
                          "button picked up a stale await from the aborted compile")

    def test_clean_blocks_compile_after_abort(self):
        compile_src(BAD_OPEN_AWAIT)  # leave a deliberately messy prior compile
        errors, _ = compile_src(GOOD_BLOCKS)
        self.assertEqual(errors, [], f"block sample should compile clean, got: {errors}")


if __name__ == "__main__":
    unittest.main()
