"""A label is not a variable (LM #544).

A label used to be registered into `Agent.SHARED` -- it WAS a shared variable named
after itself. So this compiled clean and broke at runtime:

    watcher = 0

    === watcher

...and it broke harder than it looks. An unscoped assign goes through
`set_value_keep_scope`, which asks `get_value` where the name currently lives, finds the
Label in `Agent.SHARED`, concludes `Scope.SHARED`, and writes THERE. Not a shadow: the
label was destroyed for every task, permanently, and `task_schedule(watcher)` then died
in `do_jump` with `AttributeError: 'int' object has no attribute 'name'` -- naming
neither the label nor the assignment.

Labels now live in the per-story `Mast.label_symbols` and reach expressions as eval
GLOBALS, which gives them exactly the right precedence: `task_schedule(watcher)` still
resolves, a task variable of the same name shadows it for reads, and no write can ever
land on one.

The compiler additionally names the collision, order-independently -- the label may be
later in the file, or in another addon entirely.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import os
import tempfile
import unittest
import zipfile

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  registers node types
from sbs_utils.mast.mast import Mast
from sbs_utils.mast.mast_globals import MastGlobals
from sbs_utils.agent import Agent, clear_shared


def compile_str(code, name="label_ns_test"):
    Agent.clear()
    clear_shared()
    m = Mast()
    return m, m.compile(code, name, m)


def compile_story(files, entry="story.mast"):
    """Compile a whole story from disk, so the post-compile validation hook runs.

    `_validate_label_names` fires from `_from_file`, once, after every import and addon
    has compiled -- that is what makes it order-independent, and a bare `compile()` call
    never reaches it.
    """
    Agent.clear()
    clear_shared()
    tmp = tempfile.mkdtemp()
    for fn, src in files.items():
        with open(os.path.join(tmp, fn), "w", encoding="utf-8") as f:
            f.write(src)
    m = Mast()
    return m, m.from_file(os.path.join(tmp, entry), m)


def joined(errors):
    return "\n".join(errors)


class TestLabelsLeftTheVariableNamespace(unittest.TestCase):
    def test_a_label_is_not_in_agent_shared(self):
        m, errors = compile_str("== watcher ==\n    ->END\n")
        self.assertEqual([], errors)
        self.assertIsNone(Agent.SHARED.get_inventory_value("watcher"),
                          "a label must not occupy the shared variable namespace")

    def test_the_label_is_in_the_story_table(self):
        m, _ = compile_str("== watcher ==\n    ->END\n")
        self.assertIn("watcher", m.label_symbols)
        self.assertIs(m.labels["watcher"], m.label_symbols["watcher"])

    def test_a_label_resolves_as_an_expression_global(self):
        """What `task_schedule(watcher)` depends on. 281 sites across LM and OU pass a
        bare label identifier, so this is the load-bearing half."""
        m, _ = compile_str("== watcher ==\n    ->END\n")
        self.assertIn("watcher", m.eval_globals)
        self.assertIs(m.label_symbols["watcher"], m.eval_globals["watcher"])

    def test_builtins_stay_live_in_eval_globals(self):
        """The cache holds a REFERENCE to MastGlobals.globals, so a function registered
        after the story compiled is still visible."""
        m, _ = compile_str("== watcher ==\n    ->END\n")
        gl = m.eval_globals
        MastGlobals.globals["_late_registered_fn"] = lambda: None
        try:
            self.assertIn("_late_registered_fn", gl["__builtins__"])
        finally:
            MastGlobals.globals.pop("_late_registered_fn", None)

    def test_the_cache_is_rebuilt_when_a_label_arrives(self):
        m, _ = compile_str("== first_one ==\n    ->END\n")
        self.assertIn("first_one", m.eval_globals)          # builds the cache
        m.compile("== second_one ==\n    ->END\n", "more", m)
        self.assertIn("second_one", m.eval_globals,
                      "a label compiled after the cache was built must still resolve")

    def test_inline_labels_are_not_in_the_namespace(self):
        """An inline label lives in its parent label's own dict, so it never was."""
        m, errors = compile_str("== outer ==\n    x = 1\n---- ready\n    ->END\n")
        self.assertEqual([], errors)
        self.assertNotIn("ready", m.label_symbols)


class TestTheCollisionIsNamed(unittest.TestCase):
    def test_assignment_before_the_label(self):
        """The reported shape. The label is not yet known when the assign compiles,
        which is exactly why the check runs after the whole story is in."""
        _m, errors = compile_story({
            "story.mast": "== setup ==\n    watcher = 0\n    ->END\n"
                          "== watcher ==\n    ->END\n"})
        text = joined(errors)
        self.assertIn("'watcher' is a label", text)
        self.assertIn("task_schedule(watcher)", text)
        self.assertIn("Line 2", text)

    def test_assignment_in_a_different_file(self):
        """Order-independence across files, not just within one."""
        _m, errors = compile_story({
            "story.mast": "import other.mast\n== watcher ==\n    ->END\n",
            "other.mast": "== setup ==\n    watcher = 0\n    ->END\n"})
        self.assertIn("'watcher' is a label", joined(errors))

    def test_shared_scope_is_caught_too(self):
        _m, errors = compile_story({
            "story.mast": "== setup ==\n    shared watcher = 0\n    ->END\n"
                          "== watcher ==\n    ->END\n"})
        self.assertIn("'watcher' is a label", joined(errors))

    def test_default_is_exempt(self):
        """Matches the sibling guard in assign.py and the lint: `default` is the
        legitimate 'this module may not be loaded' fallback."""
        _m, errors = compile_story({
            "story.mast": "== setup ==\n    default watcher = 0\n    ->END\n"
                          "== watcher ==\n    ->END\n"})
        self.assertEqual([], errors)

    def test_an_unrelated_name_is_clean(self):
        _m, errors = compile_story({
            "story.mast": "== setup ==\n    counter = 0\n    ->END\n"
                          "== watcher ==\n    ->END\n"})
        self.assertEqual([], errors)

    def test_an_attribute_target_is_not_a_name(self):
        """`obj.watcher = 0` assigns a field, not the label."""
        _m, errors = compile_story({
            "story.mast": "== setup ==\n    obj = 1\n    obj.watcher = 0\n    ->END\n"
                          "== watcher ==\n    ->END\n"})
        self.assertEqual([], errors)


class TestWhatMustNotChange(unittest.TestCase):
    def test_a_route_label_cannot_collide(self):
        """Routes register under mangled names (`__route__.../id`) that no assignment
        target can spell, so they are out of reach by construction."""
        m, errors = compile_str(
            "//signal/go\n    ->END\n== setup ==\n    go = 1\n    ->END\n")
        self.assertEqual([], errors)
        self.assertNotIn("go", m.label_symbols)

    def test_jump_is_unaffected_by_a_same_named_variable(self):
        """`jump` captures the name as a literal string and never evaluates it, so it
        was never exposed to this at all. Pinned so a future change cannot make it so."""
        from sbs_utils.mast.core_nodes.jump_cmd import Jump
        m, _ = compile_str("== setup ==\n    jump watcher\n== watcher ==\n    ->END\n")
        jumps = [c for c in m.labels["setup"].cmds if isinstance(c, Jump)]
        self.assertTrue(jumps)
        self.assertEqual("watcher", jumps[0].label)

    def test_recompiling_does_not_leak_between_stories(self):
        """The per-story table dies with its Mast, so the reused-interpreter trap
        (`works on run 1, fails on run 2`) cannot apply to labels."""
        m1, e1 = compile_str("== watcher ==\n    ->END\n")
        m2 = Mast()
        e2 = m2.compile("== watcher ==\n    ->END\n", "second", m2)
        self.assertEqual([], e1)
        self.assertEqual([], e2, "a second story must not collide with the first's labels")
        self.assertNotIn("watcher", Agent.SHARED.inventory.collections)


class TestTheLintRule(unittest.TestCase):
    def test_flags_a_hard_assign_over_a_label(self):
        from sbs_utils.procedural.namespace_lint import namespace_lint_project
        found = namespace_lint_project([], [
            ("a/story.mast", "== watcher ==\n    ->END\n"),
            ("a/other.mast", "== setup ==\n    watcher = 0\n"),
        ], [])
        codes = [f.code for _p, f in found]
        self.assertIn("ns-label-collision", codes)

    def test_default_and_inline_labels_are_ignored(self):
        from sbs_utils.procedural.namespace_lint import namespace_lint_project
        found = namespace_lint_project([], [
            ("a/story.mast", "== watcher ==\n    ->END\n---- ready\n"),
            ("a/other.mast", "== setup ==\n    default watcher = 0\n    ready = 1\n"),
        ], [])
        self.assertEqual([], [f.code for _p, f in found])

    def test_suppressible(self):
        from sbs_utils.procedural.namespace_lint import namespace_lint_project
        found = namespace_lint_project([], [
            ("a/story.mast", "== watcher ==\n    ->END\n"),
            ("a/other.mast", "== setup ==\n    watcher = 0  # lint: allow ns-label-collision\n"),
        ], [])
        self.assertEqual([], [f.code for _p, f in found])


if __name__ == '__main__':
    unittest.main()
