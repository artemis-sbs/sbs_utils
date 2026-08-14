"""A MAST expression that RAISES must not look like one that returned None.

`None` is a legal MAST value, so the old `eval_code() -> None` on failure was
indistinguishable from a real result: the node carried on and assigned None,
took the `else:` branch, or iterated None into a second unrelated error. These
tests pin the replacement contract:

  - the node stops at the first failure (no cascade, no None written)
  - the report names the exception TYPE and quotes the MAST expression
  - `eval_code()` itself still returns None, for every existing caller
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()  # fix exe_dir/script_dir before anything touches paths

import unittest

from sbs_utils.mast.mast import Mast, Scope
from sbs_utils.mast.mastscheduler import MastScheduler, PollResults
from sbs_utils.mast.mast_node import EVAL_ERROR, mast_compile, mast_expr_source
from sbs_utils.mast_sbs import story_nodes  # registers Cosmos MAST nodes (explicit)
from sbs_utils.agent import Agent, clear_shared
from sbs_utils.mast.mast_globals import MastGlobals
from sbs_utils.helpers import FrameContext, Context, FakeEvent

import sbs_utils.procedural.execution as ex
MastGlobals.import_python_module('sbs_utils.procedural.execution')

from cosmos_dev.mock import sbs


class _CollectingScheduler(MastScheduler):
    """Collects runtime errors instead of printing them, so tests can count them."""
    def __init__(self, mast):
        super().__init__(mast)
        self.errors_seen = []

    def runtime_error(self, message):
        self.errors_seen.append(message)


class _FakeSim:
    def __init__(self):
        self.time_tick_counter = 0

    def tick(self):
        self.time_tick_counter += 30


_UNSET = "<unset>"


def _run(code, ticks=20):
    """Compile and run a MAST snippet, returning (scheduler, task, compile errors).

    Variables live in the TASK, not the scheduler, so tests read them off the
    returned task - asserting against the scheduler would pass vacuously.
    """
    Agent.clear()
    clear_shared()
    mast = Mast()
    errors = mast.compile(code, "eval_err_test", mast)
    FrameContext.context = Context(_FakeSim(), sbs, FakeEvent())
    FrameContext.mast = mast
    runner = _CollectingScheduler(mast)
    task = None
    if not errors:
        task = runner.start_task("main")
        for _ in range(ticks):
            if not runner.tick():
                break
    return runner, task, errors


class TestEvalFailureStopsTheNode(unittest.TestCase):
    def tearDown(self):
        Agent.clear()
        clear_shared()

    def test_assign_does_not_write_none(self):
        runner, task, errors = _run("""
x = undefined_name_xyz()
""")
        self.assertEqual(errors, [])
        self.assertEqual(len(runner.errors_seen), 1, runner.errors_seen)
        # The variable must NOT exist: a None here is the misleading result.
        self.assertNotIn("x", task.get_symbols())

    def test_error_names_type_and_expression(self):
        runner, task, _ = _run("""
x = undefined_name_xyz()
""")
        msg = runner.errors_seen[0]
        self.assertIn("NameError", msg)
        self.assertIn("undefined_name_xyz", msg)
        self.assertIn("in expression:", msg)
        # The old report printed the source line as the literal word "None".
        self.assertNotIn("\nNone\n", msg)

    def test_if_does_not_fall_to_else(self):
        runner, task, errors = _run("""
if undefined_name_xyz():
    took = "then"
else:
    took = "else"
""")
        self.assertEqual(errors, [])
        self.assertEqual(len(runner.errors_seen), 1, runner.errors_seen)
        self.assertEqual(task.get_variable("took", _UNSET), _UNSET)

    def test_for_reports_once_not_twice(self):
        # Old behavior: eval failed -> None -> iter(None) -> a second TypeError
        # reported against the same line, which is the one the author saw.
        runner, task, errors = _run("""
for i in undefined_name_xyz():
    y = 1
""")
        self.assertEqual(errors, [])
        self.assertEqual(len(runner.errors_seen), 1, runner.errors_seen)
        self.assertIn("NameError", runner.errors_seen[0])

    def test_jump_if_does_not_silently_continue(self):
        runner, task, errors = _run("""
jump somewhere if undefined_name_xyz()
after = "ran"
== somewhere ==
landed = "yes"
""")
        self.assertEqual(errors, [])
        self.assertEqual(len(runner.errors_seen), 1, runner.errors_seen)
        self.assertEqual(task.get_variable("after", _UNSET), _UNSET)
        self.assertEqual(task.get_variable("landed", _UNSET), _UNSET)

    def test_working_none_assignment_still_works(self):
        runner, task, errors = _run("""
x = None
y = 5
""")
        self.assertEqual(errors, [])
        self.assertEqual(runner.errors_seen, [])
        # x IS set - to None. get_variable() cannot tell that from "absent" (the
        # very ambiguity behind this change), so ask the symbol table.
        self.assertIn("x", task.get_symbols())
        self.assertIsNone(task.get_symbols()["x"])
        self.assertEqual(task.get_variable("y", _UNSET), 5)


class TestEvalCodeApi(unittest.TestCase):
    def setUp(self):
        Agent.clear()
        clear_shared()
        self.mast = Mast()
        self.mast.clear("api_test", None)
        FrameContext.context = Context(_FakeSim(), sbs, FakeEvent())
        FrameContext.mast = self.mast
        self.runner = _CollectingScheduler(self.mast)
        self.task = self.runner.start_task("main")

    def tearDown(self):
        Agent.clear()
        clear_shared()

    def test_eval_code_still_returns_none(self):
        code = mast_compile("undefined_name_xyz()", "eval")
        self.assertIsNone(self.task.eval_code(code))

    def test_eval_code_checked_returns_sentinel(self):
        code = mast_compile("undefined_name_xyz()", "eval")
        self.assertIs(self.task.eval_code_checked(code), EVAL_ERROR)

    def test_sentinel_is_falsy(self):
        # A caller that forgets to check reads a failure as false, never as true.
        self.assertFalse(EVAL_ERROR)

    def test_success_path_unchanged(self):
        code = mast_compile("1 + 1", "eval")
        self.assertEqual(self.task.eval_code_checked(code), 2)
        self.assertEqual(self.runner.errors_seen, [])


class TestExpressionSource(unittest.TestCase):
    def test_source_recovered_from_code_object(self):
        code = mast_compile("a_var + 1", "eval")
        self.assertEqual(mast_expr_source(code), "a_var + 1")

    def test_traceback_carries_the_expression(self):
        import traceback
        code = mast_compile("undefined_name_xyz + 1", "eval")
        try:
            eval(code, {"__builtins__": {}}, {})
        except NameError:
            text = traceback.format_exc()
        self.assertIn("undefined_name_xyz + 1", text)

    def test_identical_expressions_share_one_entry(self):
        from sbs_utils.mast import mast_node
        before = mast_node.mast_expr_source_count()
        mast_compile("shared_expr_test_zz", "eval")
        mast_compile("shared_expr_test_zz", "eval")
        self.assertEqual(mast_node.mast_expr_source_count(), before + 1)

    def test_clear_empties_the_registry_and_linecache(self):
        import linecache
        from sbs_utils.mast import mast_node
        code = mast_compile("cleared_expr_test_zz", "eval")
        name = code.co_filename
        self.assertIn(name, linecache.cache)
        mast_node.mast_expr_sources_clear()
        self.assertEqual(mast_node.mast_expr_source_count(), 0)
        self.assertNotIn(name, linecache.cache)


class TestScopeKeywordHint(unittest.TestCase):
    def setUp(self):
        Agent.clear()
        clear_shared()

    def tearDown(self):
        Agent.clear()
        clear_shared()

    def test_reading_a_scope_keyword_explains_itself(self):
        # `assigned = ...` assigns to NOTHING (it parses as the 'assigned' scope
        # with an empty target), and the NameError lands on the line that READS
        # it - which is why the hint belongs in the error.
        runner, task, errors = _run("""
assigned = 5
ok = assigned
""")
        self.assertEqual(errors, [])
        self.assertEqual(len(runner.errors_seen), 1, runner.errors_seen)
        self.assertIn("scope keyword", runner.errors_seen[0])


if __name__ == '__main__':
    unittest.main()
