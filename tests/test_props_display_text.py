import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.helpers import props_display_text, props_font, gui_text_escape


class TestPropsDisplayText(unittest.TestCase):
    """props_display_text is the inverse of the $text:`...` quoting.

    Measurement needs the glyphs the engine will actually draw, with the style
    props stripped off.
    """

    def test_quoted_text(self):
        self.assertEqual(props_display_text("$text:`Hello`;font:gui-2;"), "Hello")

    def test_unquoted_text(self):
        self.assertEqual(props_display_text("$text:Hello;font:gui-2;"), "Hello")

    def test_bare_text_key(self):
        self.assertEqual(props_display_text("text:Hello;"), "Hello")

    def test_bare_label_no_colon(self):
        # gui_text("Hello") before normalization -- no key at all.
        self.assertEqual(props_display_text("Hello"), "Hello")

    def test_colon_and_semicolon_inside_backticks_are_literal(self):
        # split_props treats a backticked value as opaque (issue #569).
        msg = "$text:`Warp: 3; ready`;font:gui-2;"
        self.assertEqual(props_display_text(msg), "Warp: 3; ready")

    def test_round_trips_with_gui_text_escape(self):
        raw = "Status: green"
        msg = f"$text:{gui_text_escape(raw)};color:red;"
        self.assertEqual(props_display_text(msg), raw)

    def test_empty_and_none(self):
        self.assertEqual(props_display_text(None), "")
        self.assertEqual(props_display_text(""), "")
        self.assertEqual(props_display_text("$text:;font:gui-2;"), "")

    def test_props_only_no_text(self):
        self.assertEqual(props_display_text("font:gui-2;color:red;"), "")


class TestPropsFont(unittest.TestCase):
    """A font in the widget's own props wins over the cascade.

    present() appends the cascade props AFTER the message, so the engine sees
    the widget's own value last. Measurement must agree or it measures in a
    different font than it renders.
    """

    def test_own_font_wins(self):
        self.assertEqual(props_font("$text:`Hi`;font:gui-4;", "gui-2"), "gui-4")

    def test_falls_back_to_cascade(self):
        self.assertEqual(props_font("$text:`Hi`;color:red;", "gui-2"), "gui-2")

    def test_empty_font_value_falls_back(self):
        self.assertEqual(props_font("$text:`Hi`;font:;", "gui-2"), "gui-2")

    def test_none_props(self):
        self.assertEqual(props_font(None, "gui-2"), "gui-2")
        self.assertIsNone(props_font(None))


if __name__ == "__main__":
    unittest.main()
