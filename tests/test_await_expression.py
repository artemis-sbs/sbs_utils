"""`await <expr>` where the expression is not a call — usually a variable holding
a Promise::

    choice = gui_button("Fire", on_press=Promise())
    await choice

This fell between the two nodes that handle ``await``: the block form's rule ends
in BLOCK_START, which requires a trailing colon, and ``FuncCommand`` requires a
CALL (its pattern demands parens). So a bare name matched neither and the line was
reported as "Unrecognized syntax" — which reads as a parser bug rather than an
unsupported form, because ``r = await choice`` compiles fine (Assign owns that
line).

The tests below pin the whole matrix, not just the new form: the point of a
language change is that the forms which already worked still do.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.mock import sbs
from sbs_utils.agent import clear_shared
from sbs_utils.futures import Promise
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.mast.mast import Mast
from sbs_utils.mast.mastscheduler import MastScheduler
import sbs_utils.mast_sbs.story_nodes as _story_nodes    # node registration order


class _TMastScheduler(MastScheduler):
    def runtime_error(self, message):
        raise AssertionError(f"RUNTIME ERROR: {message}")


class _FakeSim:
    def __init__(self):
        self.time_tick_counter = 0


class AwaitExpressionBase(unittest.TestCase):
    def compile(self, body, label="go"):
        clear_shared()
        mast = Mast()
        errors = mast.compile(f"== {label} ==\n{body}", "await_test", mast)
        return mast, errors

    def run_task(self, body, label="go", ticks=20, **variables):
        """Start the label with `variables` already in scope, then tick."""
        mast, errors = self.compile(body, label)
        self.assertFalse(errors, f"compile errors: {errors}")
        FrameContext.context = Context(_FakeSim(), sbs, FakeEvent())
        FrameContext.mast = mast
        self.runner = _TMastScheduler(mast)
        task = self.runner.start_task(label, inputs=dict(variables))
        self.tick(ticks)
        return task

    def tick(self, n=10):
        for _ in range(n):
            self.runner.tick()


class TestEveryAwaitFormCompiles(AwaitExpressionBase):
    """A language change earns its keep only if the old spellings are untouched."""

    FORMS = {
        "bare await var":      "    p = make()\n    await p\n    ->END\n",
        "bare await attr":     "    await obj.p\n    ->END\n",
        "bare await index":    "    await ps[0]\n    ->END\n",
        "assign await var":    "    p = make()\n    r = await p\n    ->END\n",
        "bare await call":     "    await make()\n    ->END\n",
        "assign await call":   "    r = await make()\n    ->END\n",
        "await call kwargs":   '    r = await make(a="x", b=1)\n    ->END\n',
    }

    def test_all_of_them(self):
        for name, body in self.FORMS.items():
            _mast, errors = self.compile(body, label=f"lbl_{abs(hash(name))}")
            self.assertFalse(errors, f"{name}: {errors}")


class TestBareAwaitActuallyWaits(AwaitExpressionBase):
    """Compiling is not the point — it has to SUSPEND, then resume."""

    def test_it_blocks_until_the_promise_resolves(self):
        prom = Promise()
        task = self.run_task(
            "    await the_promise\n    done = 1\n    ->END\n",
            ticks=10, the_promise=prom)
        self.assertIsNone(task.get_variable("done"),
                          "ran past an unresolved promise")

        prom.set_result("pressed")
        self.tick(10)
        self.assertEqual(task.get_variable("done"), 1,
                         "did not resume once the promise resolved")

    def test_an_already_resolved_promise_does_not_stall(self):
        prom = Promise()
        prom.set_result("pressed")
        task = self.run_task(
            "    await the_promise\n    done = 1\n    ->END\n",
            ticks=10, the_promise=prom)
        self.assertEqual(task.get_variable("done"), 1)

    def test_the_result_is_still_reachable_afterwards(self):
        # The bare form discards the value by design (there is nowhere to put it);
        # the promise still holds it, which is how the button case reads it back.
        prom = Promise()
        prom.set_result("Fire")
        task = self.run_task(
            "    await the_promise\n    answer = the_promise.result()\n    ->END\n",
            ticks=10, the_promise=prom)
        self.assertEqual(task.get_variable("answer"), "Fire")


class TestNothingElseWasCaptured(AwaitExpressionBase):
    """The new rule requires the literal `await`, so it cannot capture a line that
    parses today. These are the neighbours worth naming."""

    def test_a_bare_word_is_still_not_a_command(self):
        _mast, errors = self.compile("    justaword\n    ->END\n", "lbl_word")
        self.assertTrue(errors, "a stray word must still be an error")

    def test_assignment_is_untouched(self):
        _mast, errors = self.compile("    await_me = 1\n    ->END\n", "lbl_assign")
        self.assertFalse(errors, errors)

    def test_a_variable_named_like_the_keyword_is_fine(self):
        _mast, errors = self.compile(
            "    awaited = 1\n    r = awaited\n    ->END\n", "lbl_named")
        self.assertFalse(errors, errors)


if __name__ == "__main__":
    unittest.main()
