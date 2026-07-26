"""Addon dependency directives: `provides` / `requires` / `suggests`.

An addon declares capability tokens it provides and the ones it requires (hard)
or suggests (soft). The compiler collects `provides` into an order-independent
union as each file compiles, then validates `requires`/`suggests` once the whole
set has compiled (_validate_requirements): an unmet `requires` is a compile error,
an unmet `suggests` is a warning only. These directives are compile-time no-ops at
runtime (like `import`).

    python -m unittest tests.test_addon_requires
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from sbs_utils.mast.mast import Mast
from sbs_utils.mast.mastscheduler import MastScheduler
from sbs_utils.mast_sbs import story_nodes  # noqa: F401  (registers Cosmos nodes)
from sbs_utils.agent import clear_shared
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


def _compile(code):
    """Compile a MAST string; return (mast, errors). Collection happens here."""
    mast = Mast()
    clear_shared()
    errors = mast.compile(code, "dep_test", mast)
    return mast, errors


def _run(code, start_label="main"):
    """Compile + tick a story (to prove the directives are runtime no-ops)."""
    mast, errors = _compile(code)
    FrameContext.context = Context(_FakeSim(), sbs, FakeEvent())
    FrameContext.mast = mast
    runner = _TMastScheduler(mast)
    if not errors:
        runner.start_task(start_label)
        for _ in range(20):
            if not runner.tick():
                break
    return errors, runner


class ProvidesRequiresCollectionTests(unittest.TestCase):
    def test_provides_collected(self):
        mast, errors = _compile("provides hangar\n")
        self.assertEqual(errors, [])
        self.assertIn("hangar", mast.provides)

    def test_provides_multiple_tokens_on_one_line(self):
        mast, _ = _compile("provides casino, casino.bar\n")
        self.assertIn("casino", mast.provides)
        self.assertIn("casino.bar", mast.provides)

    def test_requires_and_suggests_collected(self):
        mast, _ = _compile("requires admiral\nsuggests hangar\n")
        kinds = {tok: kind for (tok, kind, *_rest) in mast.requires}
        self.assertEqual(kinds.get("admiral"), "requires")
        self.assertEqual(kinds.get("hangar"), "suggests")

    def test_dotted_capability_token(self):
        mast, _ = _compile("requires hangar.sortie_board\n")
        toks = [t for (t, *_r) in mast.requires]
        self.assertIn("hangar.sortie_board", toks)

    def test_trailing_comment_allowed(self):
        mast, errors = _compile("provides hangar   # the flight deck\n")
        self.assertEqual(errors, [])
        self.assertIn("hangar", mast.provides)


class ValidationBarrierTests(unittest.TestCase):
    def test_unmet_requires_is_an_error(self):
        mast, _ = _compile("requires admiral\n")
        errs = mast._validate_requirements()
        self.assertEqual(len(errs), 1)
        self.assertIn("admiral", errs[0])

    def test_met_requires_passes(self):
        mast, _ = _compile("provides admiral\nrequires admiral\n")
        self.assertEqual(mast._validate_requirements(), [])

    def test_provides_order_independent(self):
        # `requires` appears BEFORE its `provides` in source; still satisfied,
        # because validation runs after the whole union is collected.
        mast, _ = _compile("requires admiral\nprovides admiral\n")
        self.assertEqual(mast._validate_requirements(), [])

    def test_unmet_suggests_never_errors(self):
        mast, _ = _compile("suggests hangar\n")
        self.assertEqual(mast._validate_requirements(), [])

    def test_manifest_accessor(self):
        mast, _ = _compile("provides a\nrequires b\n")
        m = mast.get_manifest()
        self.assertIn("a", m["provides"])
        self.assertEqual([t for (t, *_r) in m["requires"]], ["b"])


class GuardAndBackwardCompatTests(unittest.TestCase):
    def test_indented_directive_is_rejected(self):
        # A directive under a label (indented) is a compile error - top level only.
        _mast, errors = _compile("=== setup\n    requires admiral\n")
        self.assertTrue(errors, "indented 'requires' should be a compile error")
        self.assertTrue(any("top level" in e for e in errors))

    def test_requires_as_variable_name_still_assigns(self):
        # `requires = 5` has no token after the keyword, so it is NOT a directive;
        # it must still parse as a normal assignment (backward compatible).
        mast, errors = _compile("requires = 5\n")
        self.assertEqual(errors, [])
        self.assertEqual(mast.requires, [], "must not be collected as a dependency")

    def test_directive_is_runtime_noop(self):
        # A provides/requires line mixed with real code must not corrupt the task:
        # the story still runs and produces output.
        code = (
            "provides demo\n"
            "requires demo\n"
            'log("hello")\n'
        )
        errors, runner = _run(code)
        self.assertEqual(errors, [])


class EndToEndFromFileTests(unittest.TestCase):
    """Drive the REAL compile path (Mast.from_file), the one both the runtime and
    `sbs lint` / `--test` use: a story plus a sibling addon folder discovered via
    find_imports. Proves the end-of-compile barrier fires and is order-independent
    (the story `requires` X before the addon that `provides` X is even imported)."""

    def setUp(self):
        import tempfile
        self.dir = tempfile.mkdtemp(prefix="mast_dep_")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.dir, ignore_errors=True)

    def _write(self, relpath, content):
        import os
        full = os.path.join(self.dir, relpath)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            f.write(content)

    def _compile_story(self, story_name="story.mast"):
        clear_shared()
        mast = Mast()
        mast.basedir = self.dir
        errors = mast.from_file(story_name, None)
        return mast, errors

    def test_requires_satisfied_by_imported_addon(self):
        # story requires X BEFORE the addon that provides X is imported: still clean,
        # because the barrier runs after the whole set compiles.
        self._write("story.mast", "requires demo_cap\n")
        self._write("demo_addon/__init__.mast", "provides demo_cap\n")
        mast, errors = self._compile_story()
        self.assertIn("demo_cap", mast.provides)
        self.assertEqual(errors, [], f"expected clean compile, got {errors}")

    def test_unmet_requires_fails_the_real_compile(self):
        self._write("story.mast", "requires missing_cap\n")
        _mast, errors = self._compile_story()
        self.assertTrue(errors, "unmet requires must fail the compile")
        self.assertTrue(any("missing_cap" in e for e in errors))

    def test_unmet_suggests_compiles_clean(self):
        self._write("story.mast", "suggests optional_cap\n")
        _mast, errors = self._compile_story()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
