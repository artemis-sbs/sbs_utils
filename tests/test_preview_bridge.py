"""The live-preview bridge mapper (cosmos_dev.mission_runner._preview_story_args).

Maps an ``amd/preview`` payload to send_story_dialog(title, text, face, color) args
so an authored node renders live in a running session. Pure - the transport (HTTP
POST /debug/command -> the runner's `preview` debug action) needs a live session.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.mission_runner import _preview_story_args as args


class TestPreviewStoryArgs(unittest.TestCase):
    def test_dialogue_uses_speaker_card_and_first_line(self):
        self.assertEqual(
            args({"kind": "dialogue", "key": "hail",
                  "speaker": {"name": "Ashfang", "face": "sk;1", "color": "#f33"},
                  "lines": ["You are far from friends.", "second variant"]}),
            ("Ashfang", "You are far from friends.", "sk;1", "#f33"))

    def test_dialogue_falls_back_to_key_and_default_color(self):
        self.assertEqual(args({"kind": "dialogue", "key": "hail", "speaker": {}, "lines": []}),
                         ("hail", "", "", "#0cf"))

    def test_scan_title_and_tint(self):
        t, x, f, c = args({"kind": "scan", "role": "derelict", "lines": ["Gutted wreck."]})
        self.assertEqual((t, x, c), ("Scan: derelict", "Gutted wreck.", "#0aa"))
        self.assertEqual(f, "")

    def test_face_has_no_text(self):
        self.assertEqual(args({"kind": "face", "name": "Quill", "face": "te;2", "color": "#0cf"}),
                         ("Quill", "", "te;2", "#0cf"))

    def test_text_fallback_and_empty(self):
        self.assertEqual(args({"kind": "text", "key": "k", "display": "D", "body": "B"})[:2], ("D", "B"))
        self.assertEqual(args({}), ("", "", "", "#888"))


if __name__ == "__main__":
    unittest.main()
