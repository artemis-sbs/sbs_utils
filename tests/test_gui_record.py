"""A GUI transcript records the WIDGET, not just the tag.

That distinction is the whole reason to record from inside the library. A widget tag is
`str(int)`, handed out in page-build order - an ordinal. Add one row above a button and
every tag below it shifts, so a transcript of raw tags describes a layout that no longer
exists. Recording the label instead means the transcript still identifies the same control
after the page is edited, and that is only possible because `Layout.on_message` knows which
widget the event was for.

The off-by-default tests matter as much as the recording ones: this sits on the GUI event
path in the shipped library, so a mission that never asked to record must pay a boolean and
touch no disk.
"""

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import json
import os
import unittest

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  (settle node import order)
import cosmos_dev.mock.sbs as mock
from sbs_utils.helpers import FrameContext
from sbs_utils.procedural import gui_record as R


class _Event:
    def __init__(self, sub_tag, client_id=1, value_tag=None, sub_float=None):
        self.sub_tag = sub_tag
        self.client_id = client_id
        self.value_tag = value_tag
        self.sub_float = sub_float


class _Widget:
    """Stands in for a layout widget: the label lives in `message`, as on a real button."""
    def __init__(self, tag, message=None, click_tag=None):
        self.tag = tag
        self.message = message
        self.click_tag = click_tag


class _Ctx:
    sbs = mock


class _Base(unittest.TestCase):
    def setUp(self):
        self._saved = FrameContext.context
        FrameContext.context = _Ctx()
        R.gui_record_reset()
        mock.set_command_line([])

    def tearDown(self):
        R.gui_record_reset()
        FrameContext.context = self._saved
        mock.set_command_line([])
        path = os.path.join(os.path.dirname(__file__), "..", "records")
        # only remove what a test made
        for name in ("t_record.jsonl", "session.jsonl"):
            p = os.path.normpath(os.path.join(path, name))
            if os.path.exists(p):
                os.remove(p)

    def _lines(self):
        path = R.gui_record_path()
        if not path or not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as f:
            return [json.loads(l) for l in f if l.strip()]


class TestOffByDefault(_Base):
    def test_no_argument_means_no_recording(self):
        self.assertFalse(R.gui_record_enabled())
        self.assertIsNone(R.gui_record_path())

    def test_the_hooks_are_harmless_when_off(self):
        """These run on every GUI event in the shipped library."""
        R.gui_record_begin(_Event("7"))
        R.gui_record_note(_Event("7"), _Widget("7", "Fire"))
        R.gui_record_end()
        self.assertEqual(R.gui_record_count(), 0)


class TestRecording(_Base):
    def setUp(self):
        super().setUp()
        mock.set_command_line(["record=t_record"])

    def test_an_interaction_is_written(self):
        R.gui_record_begin(_Event("7", client_id=42))
        R.gui_record_end()
        lines = self._lines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["tag"], "7")
        self.assertEqual(lines[0]["client"], "42")

    def test_the_label_is_recorded_not_just_the_tag(self):
        """The point of the exercise. A transcript saying 'tag 7' rots; 'Fire' does not."""
        ev = _Event("7")
        R.gui_record_begin(ev)
        R.gui_record_note(ev, _Widget("7", "text:Fire;"))
        R.gui_record_end()
        entry = self._lines()[0]
        self.assertIn("Fire", entry["label"])
        self.assertEqual(entry["kind"], "_Widget")

    def test_a_value_bearing_change_keeps_its_value(self):
        ev = _Event("9", value_tag="Large", sub_float=2.0)
        R.gui_record_begin(ev)
        R.gui_record_end()
        entry = self._lines()[0]
        self.assertEqual(entry["value"], "Large")
        self.assertEqual(entry["float"], 2.0)

    def test_a_click_tag_is_marked(self):
        ev = _Event("menu")
        R.gui_record_begin(ev)
        R.gui_record_note(ev, _Widget("3", "icon", click_tag="menu"))
        R.gui_record_end()
        self.assertTrue(self._lines()[0].get("click"))

    def test_interactions_are_numbered_in_order(self):
        for tag in ("1", "2", "3"):
            R.gui_record_begin(_Event(tag))
            R.gui_record_end()
        self.assertEqual([e["seq"] for e in self._lines()], [1, 2, 3])
        self.assertEqual(R.gui_record_count(), 3)

    def test_an_unmatched_widget_is_not_noted(self):
        """Layout.on_message recurses through containers; only the target should annotate."""
        ev = _Event("7")
        R.gui_record_begin(ev)
        R.gui_record_note(ev, _Widget("7", "Fire"))
        R.gui_record_end()
        self.assertEqual(self._lines()[0]["kind"], "_Widget")


class TestTheRealChokepoint(_Base):
    """Drive the ACTUAL `Gui.on_message`, not a stand-in.

    The hook first went into `handlerhooks`' `case "gui_message"`, which looked right and
    recorded nothing: `cosmos_dev`'s exerciser and the mockgui bridge both call
    `Gui.on_message` directly, so handlerhooks is one CALLER rather than the chokepoint.
    Nothing in the unit tests above would have noticed - they call the recorder's functions
    themselves. This one calls the real entry point, so moving the hook back out fails it.

    No client is registered, which is deliberate: the dispatch finds nothing to deliver to,
    and an interaction should still be transcribed. A transcript that only records events
    that landed somewhere is useless for the case worth investigating - a click that did
    nothing.
    """

    def test_gui_on_message_writes_a_line(self):
        from sbs_utils.gui import Gui
        mock.set_command_line(["record=t_record"])
        Gui.on_message(_Event("7", client_id=5))
        lines = self._lines()
        self.assertEqual(len(lines), 1,
                         "Gui.on_message did not record - is the hook still on it?")
        self.assertEqual(lines[0]["tag"], "7")

    def test_still_silent_when_not_recording(self):
        from sbs_utils.gui import Gui
        mock.set_command_line([])
        Gui.on_message(_Event("7", client_id=5))
        self.assertEqual(R.gui_record_count(), 0)


class TestReset(_Base):
    def test_reset_closes_the_transcript_and_clears_the_count(self):
        mock.set_command_line(["record=t_record"])
        R.gui_record_begin(_Event("1"))
        R.gui_record_end()
        self.assertEqual(R.gui_record_count(), 1)
        R.gui_record_reset()
        self.assertEqual(R.gui_record_count(), 0)
        # Enablement is RE-RESOLVED, not cleared: a mission restart keeps the same launch
        # arguments, so a run that was recording should carry on recording. What must not
        # survive is the sequence number and the open handle.
        self.assertTrue(R.gui_record_enabled(),
                        "record= still on the command line, so recording resumes")
        mock.set_command_line([])
        R.gui_record_reset()
        self.assertFalse(R.gui_record_enabled(),
                         "with the argument gone, the next mission does not record")

    def test_registered_in_the_reset_ledger(self):
        from sbs_utils.handlerhooks import _RESET_PROBES
        self.assertIn("gui_record", _RESET_PROBES)


if __name__ == "__main__":
    unittest.main()
