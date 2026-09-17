"""The comms selection-title annotator.

The comms panel says WHO you have selected. It has never said whether there is any point
hailing them, so the only way to find out a station has work is to hail every station.
This seam lets an addon add that, on a surface the crew are already reading.

The load-bearing test here is the FIRST one: with no annotator installed the title is
byte-for-byte what it has always been. Every shipped mission depends on that.

    python -m unittest tests.test_comms_selection_annotator
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs as sbs
from tests.reset_helper import reset_mock

from sbs_utils.procedural import comms as C
from sbs_utils.procedural.comms import (
    comms_selection_annotator, comms_selection_annotator_clear, _comms_annotate_title)


class AnnotatorTests(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        comms_selection_annotator_clear()

    def tearDown(self):
        comms_selection_annotator_clear()

    def test_no_annotator_leaves_the_title_untouched(self):
        """The back-compat guarantee: every mission that does not opt in sees exactly
        the title it saw before this existed."""
        self.assertEqual(_comms_annotate_title(1, 2, "DS 1"), "DS 1")
        self.assertEqual(_comms_annotate_title(1, 2, "DS 1 ship_to_ship"),
                         "DS 1 ship_to_ship")

    def test_an_installed_annotator_runs(self):
        comms_selection_annotator(lambda o, s, t: f"{t} - 2 jobs")
        self.assertEqual(_comms_annotate_title(1, 2, "DS 1"), "DS 1 - 2 jobs")

    def test_it_receives_both_ids(self):
        seen = {}

        def fn(o, s, t):
            seen.update({"o": o, "s": s, "t": t})
            return t

        comms_selection_annotator(fn)
        _comms_annotate_title(11, 22, "X")
        self.assertEqual(seen, {"o": 11, "s": 22, "t": "X"})

    def test_returning_none_keeps_the_original(self):
        comms_selection_annotator(lambda o, s, t: None)
        self.assertEqual(_comms_annotate_title(1, 2, "DS 1"), "DS 1")

    def test_a_raising_annotator_costs_only_the_decoration(self):
        """A decoration that throws must not cost the crew the comms panel."""
        comms_selection_annotator(lambda o, s, t: 1 / 0)
        self.assertEqual(_comms_annotate_title(1, 2, "DS 1"), "DS 1")

    def test_clearing_removes_it(self):
        comms_selection_annotator(lambda o, s, t: t + "!")
        comms_selection_annotator_clear()
        self.assertEqual(_comms_annotate_title(1, 2, "DS 1"), "DS 1")

    def test_a_mission_reset_clears_it(self):
        """One installed by the last mission would run on every comms selection of the
        next, against a world that no longer exists."""
        comms_selection_annotator(lambda o, s, t: t + "!")
        from sbs_utils.handlerhooks import reset_mission_state
        reset_mission_state()
        self.assertEqual(_comms_annotate_title(1, 2, "DS 1"), "DS 1")


if __name__ == "__main__":
    unittest.main()
