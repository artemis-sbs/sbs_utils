"""Diagnostics for an unbalanced await stack (LegendaryMissions #124).

The compiler tracks open `await ...:` blocks on a per-compile stack so buttons
and `=` inline labels can attach to the block they belong to. When that stack
got out of balance the failure used to be silent or misleading:

  * an `=` inline label with nothing open raised a bare IndexError, surfaced as
    "Exception: list index out of range" against the inline label -- which is
    almost never where the real fault is;
  * an await that never closed at all was dropped with no word to the author,
    even though the task waiting on it can never continue;
  * a `*`/`+` button with no await block and no navigation being built is
    discarded at runtime, and the console just showed nothing.

These tests lock in that each of those now says what is wrong. They also guard
the other direction: well-formed code must stay quiet.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()
import logging
import unittest

from sbs_utils.mast.mast import Mast
from sbs_utils.agent import clear_shared
from sbs_utils.mast_sbs import story_nodes  # noqa: F401  registers nodes
from sbs_utils.mast.mast_globals import MastGlobals
import sbs_utils.procedural.execution  # noqa: F401
import sbs_utils.procedural.gui  # noqa: F401
MastGlobals.import_python_module('sbs_utils.procedural.execution')
MastGlobals.import_python_module('sbs_utils.procedural.gui')

from sbs_utils.mast_sbs.story_nodes.button import Button, ButtonRuntimeNode
from sbs_utils.procedural.gui import ButtonPromise


def compile_src(code, name="await_stack_test"):
    m = Mast()
    clear_shared()
    return m.compile(code, name, m), m


def joined(errors):
    return "\n".join(errors)


# An `=` inline label at label scope: nothing is open for it to attach to.
INLINE_NO_AWAIT = """
== inline_orphan ==
    x = 1
=my_inline:
    y = 2
"""

# The shape from the issue: a block whose indentation leaves the stack dirty,
# then something later in the file that needs the stack.
UNBALANCED_THEN_INLINE = """
== unbalanced_one ==
    await gui():
        * "hi":
            y = 2
== unbalanced_two ==
    z = 1
=another:
    q = 1
"""

# `await gui():` promising a block that never arrives -- the next line dedents
# all the way back to column 0, so the await is still open when the new label
# starts.
AWAIT_NO_BODY = """
== open_one ==
    await gui():
== open_two ==
    x = 1
"""

# The LegendaryMissions pause-screen shape: the button is at the await's own
# indent rather than under it. No block is pushed, so the await is still on the
# stack at the next label -- yet the button attaches to it and sets dedent_loc,
# and the screen works. Must stay quiet.
BUTTON_AT_AWAIT_INDENT = """
== pause_like ==
    await gui():
    + "Resume":
        log("resumed")

    jump pause_like
== after_pause ==
    x = 1
"""

# Well formed: the await opens, takes a button, and closes on the dedent.
WELL_FORMED = """
== fine_one ==
    await gui():
        * "hi":
            y = 2
    z = 3
== fine_two ==
    w = 1
"""


class TestAwaitStackCompileDiagnostics(unittest.TestCase):
    def test_inline_label_without_await_names_the_cause(self):
        errors, _ = compile_src(INLINE_NO_AWAIT)
        self.assertTrue(errors, "an orphaned '=' inline label should not compile")
        text = joined(errors)
        self.assertIn("no open 'await' block", text)
        self.assertIn("=my_inline:", text)
        # The old failure mode -- a bare IndexError -- must not come back.
        self.assertNotIn("list index out of range", text)

    def test_unbalanced_block_then_inline_label(self):
        errors, _ = compile_src(UNBALANCED_THEN_INLINE)
        self.assertTrue(errors)
        text = joined(errors)
        self.assertIn("no open 'await' block", text)
        self.assertNotIn("list index out of range", text)

    def test_await_left_open_at_label_warns_and_keeps_compiling(self):
        with self.assertLogs("mast.compile", level="WARNING") as captured:
            errors, _ = compile_src(AWAIT_NO_BODY)
        text = "\n".join(captured.output)
        self.assertIn("never closed", text)
        # It must point at the await itself (line 3 of the source, 1-based with
        # the leading newline), not at the label that tripped over it.
        self.assertIn(":3:", text)
        self.assertIn("open_two", text)
        # A warning, not an error: failing the compile here would take the whole
        # story down, and the rest of the file may be perfectly good.
        self.assertEqual([], errors)

    def test_button_at_the_awaits_own_indent_is_not_flagged(self):
        # Widespread in shipped missions: the button sits at the await's OWN
        # indent, so no block is ever pushed and the await stays on the stack --
        # but the button attaches and sets dedent_loc, and the screen works.
        # This must not warn, or every mission using the shape gets noise.
        logger = logging.getLogger("mast.compile")
        records = []

        class Collect(logging.Handler):
            def emit(self, record):
                records.append(record)

        handler = Collect(level=logging.WARNING)
        logger.addHandler(handler)
        try:
            errors, _ = compile_src(BUTTON_AT_AWAIT_INDENT)
        finally:
            logger.removeHandler(handler)
        self.assertEqual([], errors)
        self.assertEqual([], [r.getMessage() for r in records])

    def test_well_formed_await_block_is_silent(self):
        logger = logging.getLogger("mast.compile")
        records = []

        class Collect(logging.Handler):
            def emit(self, record):
                records.append(record)

        handler = Collect(level=logging.WARNING)
        logger.addHandler(handler)
        try:
            errors, _ = compile_src(WELL_FORMED)
        finally:
            logger.removeHandler(handler)
        self.assertEqual([], errors)
        self.assertEqual([], [r.getMessage() for r in records],
                         "a balanced await block must not warn")


class _StubTask:
    """Only what ButtonRuntimeNode.enter touches."""
    active_label = "stub_label"


class TestNavigatingPromiseTeardown(unittest.TestCase):
    def test_navigating_promise_is_declared(self):
        # Read by button.py / comms.py / science.py before any navigation has
        # ever been built; it must exist and read as "no navigation in progress".
        self.assertIsNone(ButtonPromise.navigating_promise)

    def test_navigation_teardown_survives_a_raise(self):
        from sbs_utils.helpers import FrameContext

        class Boom(ButtonPromise):
            def __init__(self):
                # Deliberately not calling super().__init__ -- this test only
                # drives build_navigation_buttons' teardown.
                self.path = "boom"
                self.task = None
                self.nav_sub_task_promise = None

        promise = Boom()
        ButtonPromise.navigation_map["boom"] = ["not-a-label"]
        saved_task, saved_page = FrameContext.task, FrameContext.page
        try:
            with self.assertRaises(Exception):
                promise.build_navigation_buttons()
            # A route body that raises must not leave the navigation latch set:
            # every later stand-alone button would be swallowed by a dead promise.
            self.assertIsNone(ButtonPromise.navigating_promise)
            self.assertIs(saved_task, FrameContext.task)
            self.assertIs(saved_page, FrameContext.page)
        finally:
            ButtonPromise.navigation_map.pop("boom", None)
            FrameContext.task, FrameContext.page = saved_task, saved_page


class TestOrphanButtonRuntimeWarning(unittest.TestCase):
    def setUp(self):
        self._saved = ButtonPromise.navigating_promise
        ButtonPromise.navigating_promise = None

    def tearDown(self):
        ButtonPromise.navigating_promise = self._saved

    def _button(self):
        # A compiled `+ "Click"` that ended up with no await block.
        button = Button(message="Click", button="+", loc=0)
        button.await_node = None
        button.file_num = None
        button.line_num = 12
        return button

    def test_button_with_nowhere_to_go_warns(self):
        node = self._button()
        with self.assertLogs("mast", level="WARNING") as captured:
            ButtonRuntimeNode().enter(None, _StubTask(), node)
        text = "\n".join(captured.output)
        self.assertIn("never be shown", text)
        self.assertIn("12", text)

    def test_warning_is_once_per_node(self):
        node = self._button()
        with self.assertLogs("mast", level="WARNING") as captured:
            ButtonRuntimeNode().enter(None, _StubTask(), node)
            # Buttons re-enter on every present; the console must not fill the
            # log with the same line every frame.
            for _ in range(5):
                ButtonRuntimeNode().enter(None, _StubTask(), node)
        self.assertEqual(1, len(captured.output))

    def test_button_inside_navigation_does_not_warn(self):
        # The legitimate no-await case: comms/science navigation is being built,
        # and the button is collected by the navigating promise.
        collected = []

        class FakeNav:
            def add_nav_button(self, b):
                collected.append(b)

        ButtonPromise.navigating_promise = FakeNav()
        node = self._button()
        logger = logging.getLogger("mast")
        records = []

        class Collect(logging.Handler):
            def emit(self, record):
                records.append(record)

        handler = Collect(level=logging.WARNING)
        logger.addHandler(handler)
        try:
            ButtonRuntimeNode().enter(None, _StubTask(), node)
        finally:
            logger.removeHandler(handler)
        self.assertEqual(1, len(collected))
        self.assertEqual([], [r.getMessage() for r in records])


if __name__ == '__main__':
    unittest.main()
