"""Scan text an AUTHOR wrote is not a format string.

Found by the lesson "Things quests point at". A scan record in an `.amd` may hold a
placeholder the object's inventory fills in:

    % The flight log is aboard, sealed in the locker of {pilot}.

`science_scan_tab` leaves an unfilled `{pilot}` in place and calls that harmless. It was
not: the generic science route assigned the text to a variable (a string assignment is
re-read as a format string), put it through `<scan>` (formatted again) and into
`scan_results` (formatted a third time). So `{pilot}` was a NameError against a library
file, the tab was never stored, lint was clean - and `{SCIENCE_SELECTED.name}` written in
a scan record was RUN.

`scan_results(text, literal=True)` is what the generic route calls now. The route itself
is LegendaryMissions' (`science_scans/science.mast`); the run that proves the whole path
is a mission with such a record under `mission_runner --test`, which fails without this
and passes with it.

    python -m unittest tests.test_scan_results_literal
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401
from sbs_utils.helpers import FrameContext
from sbs_utils.procedural.science import scan_results


class _Promise:
    def __init__(self):
        self.got = None

    def set_scan_results(self, text):
        self.got = text


class _Task:
    """What `scan_results` asks of the running task, and nothing more. The formatter
    behaves like MAST's: a name it cannot resolve raises."""

    def __init__(self):
        self.promise = _Promise()
        self.formatted = 0

    def get_variable(self, name, default=None):
        return {"__SCAN_TAB__": "intel", "BUTTON_PROMISE": self.promise}.get(name, default)

    def compile_and_format_string(self, text):
        self.formatted += 1
        return eval('f"""' + text + '"""', {"hp": 40})


class ScanResultsTests(unittest.TestCase):
    def setUp(self):
        self.task = _Task()
        was = FrameContext.task
        FrameContext.task = self.task
        self.addCleanup(setattr, FrameContext, "task", was)

    def test_an_unfilled_placeholder_reaches_the_screen_as_written(self):
        scan_results("Sealed in the locker of {pilot}.", literal=True)
        self.assertEqual(self.task.promise.got, "Sealed in the locker of {pilot}.")
        self.assertEqual(self.task.formatted, 0)

    def test_an_expression_in_author_text_is_not_run(self):
        scan_results("{__import__('os').getcwd()}", literal=True)
        self.assertEqual(self.task.promise.got, "{__import__('os').getcwd()}")

    def test_a_lone_brace_is_not_an_error(self):
        scan_results("Reading {incomplete", literal=True)
        self.assertEqual(self.task.promise.got, "Reading {incomplete")

    def test_a_script_still_gets_its_variables_filled_in(self):
        scan_results("Hull at {hp}")
        self.assertEqual(self.task.promise.got, "Hull at 40")

    def test_without_literal_an_unknown_name_still_raises(self):
        """The old behavior, kept: this is what a script author expects of a typo."""
        with self.assertRaises(NameError):
            scan_results("Sealed in the locker of {pilot}.")


if __name__ == "__main__":
    unittest.main()
