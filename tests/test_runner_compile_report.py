"""A story that never COMPILED must not be reported as a pass.

`StoryPage.start_story` creates the scheduler only when there are no compiler errors,
so a story that failed to compile schedules no task at all: zero labels, nothing
spawned, both logs empty - and the run printed "PASS - no runtime errors", which is
true, because there was no runtime. The compiler's message sat on the page and nothing
read it.

That is not hypothetical. An addon `requires` no mission satisfied took 22 missions to
zero labels, and the runner's own hint sent the search after a multi-line literal
instead of the one line that said what was wrong.

    python -m unittest tests.test_runner_compile_report
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from cosmos_dev import mission_runner as MR
from sbs_utils.gui import Gui


class FakePage:
    def __init__(self, errors):
        self.compiler_errors = list(errors)


class FakeHolder:
    def __init__(self, page):
        self.page = page


class ReadingTheCompilersWords(unittest.TestCase):
    def setUp(self):
        self._prev = dict(Gui.clients)

    def tearDown(self):
        Gui.clients.clear()
        Gui.clients.update(self._prev)

    def set_page(self, errors):
        Gui.clients.clear()
        Gui.clients[0] = FakeHolder(FakePage(errors))

    def test_it_reads_them_off_the_server_page(self):
        self.set_page(["Error: Unmet dependency: requires 'grav_tether'"])
        self.assertEqual(len(MR._compiler_errors()), 1)
        self.assertIn("Unmet dependency", MR._compiler_errors()[0])

    def test_a_clean_page_has_none(self):
        self.set_page([])
        self.assertEqual(MR._compiler_errors(), [])

    def test_no_page_at_all_is_not_an_error(self):
        # Lint, tooling and a run that died early all reach here.
        Gui.clients.clear()
        self.assertEqual(MR._compiler_errors(), [])

    def test_a_page_without_the_attribute_is_not_an_error(self):
        Gui.clients.clear()
        Gui.clients[0] = FakeHolder(object())
        self.assertEqual(MR._compiler_errors(), [])


class TheHintNamesTheRealCauses(unittest.TestCase):
    def test_an_unmet_requires_is_one_of_the_suggestions(self):
        # The hint used to offer only "a lib failed to load" or "a parse desync", so the
        # one cause that had actually happened was the one it did not mention.
        self.assertIn("requires", MR._NOTHING_RAN)

    def test_it_still_names_the_other_two(self):
        self.assertIn("mastlibs failed to load", MR._NOTHING_RAN)
        self.assertIn("parse error", MR._NOTHING_RAN)


if __name__ == "__main__":
    unittest.main()
