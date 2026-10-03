"""An author's line survives a widget that treats its text as a template.

`gui_text_area` fills `{name}` in the text it is given. A spoken line from an .amd file is
not a template: `Call me {Captain}, everyone does.` raised `NameError: name 'Captain' is
not defined` against the screen's own `await gui()`, in the engine, and the console that
was drawing the call stopped drawing (2026-10-03).

The check that matters is against the REAL formatter - the one the widget calls - not a
recorder that hands the text back.

    python -m unittest tests.test_gui_text_literal
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401
from sbs_utils.mast.mast_node import compile_format_string
from sbs_utils.procedural.gui.text import gui_text_literal


def as_the_widget_formats(text):
    """What `task.compile_and_format_string` does, without needing a task."""
    if isinstance(text, str) and "{" in text:
        return eval(compile_format_string(text), {}, {})
    return text


class LiteralTests(unittest.TestCase):
    LINES = (
        "Call me {Captain}, everyone does.",
        "Eleven years on this lane {and counting.",
        "A closing brace } on its own",
        "{}",
        "Nested {{already doubled}}",
        "No braces at all.",
        "",
    )

    def test_every_line_comes_out_as_it_went_in(self):
        for line in self.LINES:
            self.assertEqual(as_the_widget_formats(gui_text_literal(line)), line, line)

    def test_the_fixture_is_real_an_unescaped_name_raises(self):
        with self.assertRaises(NameError):
            as_the_widget_formats("Call me {Captain}, everyone does.")

    def test_markdown_is_left_alone(self):
        line = "![](face://abc?height=72) **Bold** and a [link](ref://k)"
        self.assertEqual(gui_text_literal(line), line)

    def test_it_takes_anything_printable(self):
        self.assertEqual(gui_text_literal(None), "None")
        self.assertEqual(gui_text_literal(7), "7")


class TheScreensUseItTests(unittest.TestCase):
    """Every place an author's prose reaches a formatting text area."""

    def source(self, module):
        import inspect
        return inspect.getsource(module)

    def test_the_hail_screens(self):
        from sbs_utils.procedural.gui import hail_gui
        src = self.source(hail_gui)
        self.assertNotIn("gui_text_area(line", src)
        self.assertIn("gui_text_area(gui_text_literal(line)", src)
        self.assertIn("gui_text_literal(hail_transcript_text(entry))", src)

    def test_the_boarding_handheld(self):
        from sbs_utils.procedural.gui import xess
        src = self.source(xess)
        self.assertNotIn("gui_text_area(line)", src)


if __name__ == "__main__":
    unittest.main()
