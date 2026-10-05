"""Three small things the markdown lesson's re-measure and the editor lesson's pilot found.

* A line holding only `#` in a quest's description - a manuscript's scene break - showed
  the CREW `Document syntax issue line number 5 #` in place of the whole description.
* The editor's checker linted the open buffer without saying which file it was, so every
  check that asks "does the story read this section?" returned at once, and seven kinds
  of finding that `sbs lint` prints were never underlined.
* The stand-in's pid file outlived a killed runner; the next run force-killed whatever
  program Windows had since given that number to.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import os
import sys
import unittest
from unittest import mock

import cosmos_dev.mock.sbs as mock_sbs
sys.modules.setdefault("sbs", mock_sbs)

from cosmos_dev import mission_runner
from sbs_utils.pages.layout.text_area import TextArea
from sbs_utils.procedural import amd_lsp


class ALineOfHashes(unittest.TestCase):
    def style(self, line):
        area = TextArea.__new__(TextArea)
        area.styles = {}
        area._callout_key = None
        return area.get_markdown_line_style(line, None)

    def test_a_lone_hash_does_not_raise(self):
        for line in ("#", "##", "###", "#   "):
            with self.subTest(line=line):
                self.style(line)                      # used to raise IndexError

    def test_a_lone_hash_is_not_a_heading(self):
        for line in ("#", "##"):
            with self.subTest(line=line):
                got = self.style(line)
                key = got[0] if isinstance(got, tuple) else got
                self.assertFalse(str(key).startswith("h"), got)

    def test_a_heading_is_still_a_heading(self):
        self.assertEqual(self.style("# Orders"), ("h1", " Orders"))
        self.assertEqual(self.style("##Orders"), ("h2", "Orders"))

    def test_a_lone_hyphen_is_not_a_list_item(self):
        got = self.style("-")
        key = got[0] if isinstance(got, tuple) else got
        self.assertNotEqual(key, "ul")


class TheEditorSaysWhichFileItIs(unittest.TestCase):
    def test_the_path_reaches_lint(self):
        seen = {}

        def fake(file_path=None, content=None, **kw):
            seen["file_path"], seen["content"] = file_path, content
            return []
        index = {"mast": [], "known": set(), "mast_index": None}
        with mock.patch("sbs_utils.procedural.amd_lint.amd_lint", fake):
            amd_lsp._diagnostics("# [A](a)\n", index, "C:/m/MyMission/mission.amd")
        self.assertEqual(seen["file_path"], "C:/m/MyMission/mission.amd")
        self.assertEqual(seen["content"], "# [A](a)\n")      # the BUFFER is what is linted

    def test_the_caller_passes_it(self):
        import inspect
        self.assertIn("_diagnostics(text, _index_for(uri, docs), _uri_to_path(uri))",
                      inspect.getsource(amd_lsp))


class AStalePidFile(unittest.TestCase):
    def test_a_process_that_is_not_python_is_left_alone(self):
        import tempfile
        tag = "test_what_lesson_four_found"
        pidfile = os.path.join(tempfile.gettempdir(), f"cosmos_dev_runner_{tag}.pid")
        with open(pidfile, "w") as f:
            f.write("4242")
        self.addCleanup(lambda: os.path.isfile(pidfile) and os.remove(pidfile))
        killed = []
        with mock.patch.object(mission_runner, "_pid_alive", lambda pid: True), \
                mock.patch.object(mission_runner, "_is_python", lambda pid: False), \
                mock.patch.object(mission_runner, "_kill_tree", killed.append), \
                mock.patch("atexit.register", lambda f: None):
            mission_runner._ensure_single_runner(tag)
        self.assertEqual(killed, [])

    def test_this_process_is_python(self):
        self.assertTrue(mission_runner._is_python(os.getpid()))

    def test_a_number_nobody_has_is_not(self):
        self.assertFalse(mission_runner._is_python(2 ** 31 - 7))


if __name__ == "__main__":
    unittest.main()
