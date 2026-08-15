"""A gui_input must answer gui_update(), and a scripted value must repaint.

Found while proving LM #664 was not a library bug. `TextInput` was the only
value-bearing widget with no `update()` override, so it inherited
`Column.update`'s `pass`: `gui_update("tag", props)` parsed, found the widget,
"updated" it and re-sent it with its OLD props. The `value` setter had the same
shape of hole -- it wrote `_value` and never dirty-marked, so text assigned from
script sat there until something else forced a full repaint.

The player-typing path is deliberately NOT included in that: re-sending the box
on every keystroke fights the cursor.

    python -m unittest tests.test_gui_input_update
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from sbs_utils.helpers import FakeEvent
from sbs_utils.pages.layout.dirty import Dirty
from sbs_utils.pages.layout.text_input import TextInput

CID = 7


def _input(props="$text:`Initial Value`;"):
    w = TextInput("105", props)
    w.client_id = CID          # Dirty.mark_dirty ignores a client-less item
    return w


def _dirty(w):
    return w in Dirty.dirty.get(CID, set())


class TextInputUpdateTests(unittest.TestCase):

    def setUp(self):
        Dirty.dirty = {}

    # --- construction (unchanged behavior, pinned) -------------------------

    def test_constructor_takes_the_quoted_value(self):
        self.assertEqual("Initial Value", _input().value)

    def test_constructor_takes_the_bare_value(self):
        self.assertEqual("Initial Value", _input("$text:Initial Value;").value)

    def test_constructor_keeps_the_other_props(self):
        w = _input("$text:`Bob`;desc:name;")
        self.assertEqual("Bob", w.value)
        self.assertIn("desc:name", w.props)

    def test_present_string_carries_the_value_back_quoted(self):
        self.assertEqual("$text:`Bob`;", _input("$text:`Bob`;")._text_prop())

    # --- update() ----------------------------------------------------------

    def test_update_changes_the_styling_that_is_sent(self):
        w = _input()
        w.update("font:gui-3;")
        self.assertIn("font:gui-3", w.props)

    def test_update_without_a_text_key_keeps_the_players_value(self):
        # The text in a typein belongs to the player -- restyling the box must
        # not wipe what someone is in the middle of typing.
        w = _input()
        w.update("font:gui-3;")
        self.assertEqual("Initial Value", w.value)

    def test_update_with_a_text_key_replaces_the_value(self):
        w = _input()
        w.update("$text:`Changed`;")
        self.assertEqual("Changed", w.value)

    def test_update_with_an_empty_text_key_clears_the_value(self):
        w = _input()
        w.update("$text:;")
        self.assertEqual("", w.value)

    def test_update_repaints(self):
        w = _input()
        w.update("font:gui-3;")
        self.assertTrue(_dirty(w))

    def test_update_is_not_a_no_op(self):
        # The whole bug in one assertion: Column.update's `pass` left both the
        # props and the dirty set untouched.
        w = _input()
        before = w.props
        w.update("desc:call sign;")
        self.assertNotEqual(before, w.props)

    # --- value setter ------------------------------------------------------

    def test_value_setter_changes_what_is_sent(self):
        w = _input()
        w.value = "Bob"
        self.assertEqual("$text:`Bob`;", w._text_prop())

    def test_value_setter_repaints(self):
        w = _input()
        w.value = "Bob"
        self.assertTrue(_dirty(w))

    def test_value_setter_strips_the_quote_delimiter(self):
        w = _input()
        w.value = "Bo`b"
        self.assertEqual("Bob", w.value)

    # --- typing (must NOT repaint) -----------------------------------------

    def test_typing_does_not_repaint(self):
        # Re-sending the box mid-word would fight the player's cursor; they can
        # already see what they typed.
        w = _input()
        w.on_message(FakeEvent(CID, "gui_message", sub_tag="105",
                               value_tag="Bob"))
        self.assertEqual("Bob", w.value)
        self.assertFalse(_dirty(w))

    def test_typing_a_quote_delimiter_is_pushed_back(self):
        # Sanitisation CHANGED the string, so the box no longer matches what we
        # stored and has to be corrected.
        w = _input()
        w.on_message(FakeEvent(CID, "gui_message", sub_tag="105",
                               value_tag="Bo`b"))
        self.assertEqual("Bob", w.value)
        self.assertTrue(_dirty(w))

    def test_a_message_for_another_widget_is_ignored(self):
        w = _input()
        w.on_message(FakeEvent(CID, "gui_message", sub_tag="999",
                               value_tag="Bob"))
        self.assertEqual("Initial Value", w.value)


if __name__ == "__main__":
    unittest.main()
