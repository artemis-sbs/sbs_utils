"""Setting a dropdown's selection from script must reach the screen (LM #568).

`_present` sends `self.values` and nothing else, so any writer that does not
land in that string is invisible. `update()` used to write a `props` attribute
nothing reads, and the `value` setter wrote only `_value` -- both silent no-ops.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from sbs_utils.helpers import FakeEvent, props_display_text, split_props
from sbs_utils.pages.layout.dropdown import Dropdown

LIST = "list:One,Two,Three;"


def _gui(sub_tag, value_tag=""):
    return FakeEvent(client_id=0, tag="gui_message", sub_tag=sub_tag,
                     value_tag=value_tag)


class TestDropdownSelection(unittest.TestCase):

    def test_constructor_seeds_value_from_props(self):
        dd = Dropdown("dd", "$text:One;" + LIST)
        self.assertEqual("One", dd.value)

    def test_constructor_seeds_value_from_bare_text_spelling(self):
        dd = Dropdown("dd", "text:One;" + LIST)
        self.assertEqual("One", dd.value)

    def test_update_changes_what_is_sent(self):
        dd = Dropdown("dd", "$text:One;" + LIST)
        dd.update("$text:Two;" + LIST)
        self.assertEqual("Two", props_display_text(dd.values))
        self.assertEqual("Two", dd.value)

    def test_value_setter_changes_what_is_sent(self):
        dd = Dropdown("dd", "$text:One;" + LIST)
        dd.value = "Two"
        self.assertEqual("Two", props_display_text(dd.values))
        self.assertEqual("Two", dd.value)

    def test_value_setter_keeps_the_option_list(self):
        dd = Dropdown("dd", "$text:One;" + LIST)
        dd.value = "Three"
        self.assertIn("One,Two,Three", dd.values)

    def test_value_setter_keeps_other_props(self):
        dd = Dropdown("dd", "$text:One;" + LIST + "color:red;")
        dd.value = "Two"
        self.assertIn("color:red", dd.values)

    def test_value_setter_does_not_duplicate_the_text_prop(self):
        # An author who wrote `text:` gets `text:` back, not a second answer.
        dd = Dropdown("dd", "text:One;" + LIST)
        dd.value = "Two"
        self.assertNotIn("$text", dd.values)
        parsed = split_props(dd.values, "$text")
        self.assertEqual(["text", "list"], list(parsed))

    def test_value_survives_a_colon_in_the_label(self):
        dd = Dropdown("dd", "$text:One;list:One,Warp: 3;")
        dd.value = "Warp: 3"
        self.assertEqual("Warp: 3", props_display_text(dd.values))

    def test_engine_selection_lands_in_values_too(self):
        # A click must not leave `values` showing the old label, or the next
        # present() puts the dropdown back where it was.
        dd = Dropdown("dd", "$text:One;" + LIST)
        dd.on_message(_gui("dd", "Three"))
        self.assertEqual("Three", dd.value)
        self.assertEqual("Three", props_display_text(dd.values))


if __name__ == "__main__":
    unittest.main()
