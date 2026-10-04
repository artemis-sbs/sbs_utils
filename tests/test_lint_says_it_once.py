"""Small things `sbs lint` got wrong about its own output.

Found by the lesson "Lint is your editor":

  * the text form counted columns from 0 and the compact form from 1, so one finding was
    `31:23` in one and `31:24` in the other - and an editor says `Col 24`
  * a story saved from Notepad in the Windows code page, with one curly quote in a note,
    was a traceback from the await check, printed after lint had said `clean`
  * a tool that leaves the logs alone left the compiler's logger with no handler, so
    Python printed its errors to stderr: a bare `Exception: ...` loose in lint's output

    python -m unittest tests.test_lint_says_it_once
"""
import contextlib
import io
import logging
import os
import tempfile
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401
from sbs_utils.mast.mast import Mast
from sbs_utils.procedural.amd_lint import AmdFinding, WARNING
from sbs_utils.procedural.await_lint import await_lint


class ColumnsCountFromOne(unittest.TestCase):
    def test_the_two_forms_agree(self):
        f = AmdFinding(31, WARNING, "non-ascii", "a curly quote", col=23, end_line=31, end_col=24)
        self.assertIn("line 31:24:", str(f))
        self.assertTrue(f.compact("mission.amd").startswith("mission.amd:31:24:"))

    def test_a_finding_with_no_column_names_the_line_alone(self):
        self.assertIn("line 31:", str(AmdFinding(31, WARNING, "x", "y")))
        self.assertNotIn("31:0", str(AmdFinding(31, WARNING, "x", "y")))


class AStoryInTheWindowsCodePage(unittest.TestCase):
    def test_the_await_check_reads_it(self):
        text = ("# The crew’s roster\n"
                "== wait ==\n"
                "    await delay_sim(1)\n"
                "    ->END\n")
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "story.mast")
            with open(path, "wb") as f:
                f.write(text.encode("cp1252"))
            Mast.leave_logs_alone = True
            self.addCleanup(setattr, Mast, "leave_logs_alone", False)
            self.assertEqual(await_lint(file_path=path), [])

    def test_windows_line_ends_are_not_sixteen_syntax_errors(self):
        # Reading the bytes (to choose the decoding) keeps the CR that a text-mode open
        # used to drop, and the compiler matches nothing on a line that ends in one.
        text = "== wait ==\r\n    await delay_sim(1)\r\n    x = 1\r\n    ->END\r\n"
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "story.mast")
            with open(path, "wb") as f:
                f.write(text.encode("utf-8"))
            Mast.leave_logs_alone = True
            self.addCleanup(setattr, Mast, "leave_logs_alone", False)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                found = await_lint(file_path=path)
            self.assertEqual(found, [])
            self.assertNotIn("Unrecognized syntax", out.getvalue())


class AToolThatLeavesTheLogsAlone(unittest.TestCase):
    def setUp(self):
        self.addCleanup(setattr, Mast, "leave_logs_alone", Mast.leave_logs_alone)
        self.kept = {}
        for name in ("mast.compile", "mast.runtime"):
            log = logging.getLogger(name)
            self.kept[name] = list(log.handlers)
            for handler in list(log.handlers):
                log.removeHandler(handler)
        self.addCleanup(self.restore)

    def restore(self):
        for name, handlers in self.kept.items():
            log = logging.getLogger(name)
            for handler in list(log.handlers):
                log.removeHandler(handler)
            for handler in handlers:
                log.addHandler(handler)

    def test_nothing_is_printed_in_their_place(self):
        Mast.leave_logs_alone = True
        Mast()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            logging.getLogger("mast.compile").error("Exception: unterminated string literal")
            logging.getLogger("mast.runtime").error("something at run time")
        self.assertEqual(err.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
