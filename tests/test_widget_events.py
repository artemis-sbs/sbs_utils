"""
Tests that widget on_message handlers respond correctly to FakeEvent objects.

Event field mapping confirmed by EventLoggerMission run:
  - All widget events use event.tag == "gui_message"
  - event.sub_tag == widget numeric tag ID (auto-assigned)
  - Dropdown: event.value_tag = selected string
  - Slider:   event.sub_float = raw float (even for gui_int_slider)
  - Checkbox: no value field — handler toggles self.value
  - TextInput: event.value_tag = cumulative string (fires every keystroke)
  - Icon (click_tag): event.sub_tag == widget.click_tag string, not the widget's own tag
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from sbs_utils.helpers import FakeEvent
from sbs_utils.pages.layout.button import Button
from sbs_utils.pages.layout.checkbox import Checkbox
from sbs_utils.pages.layout.clickable import Clickable
from sbs_utils.pages.layout.column import Column
from sbs_utils.pages.layout.dropdown import Dropdown
from sbs_utils.pages.layout.slider import Slider
from sbs_utils.pages.layout.text_input import TextInput


def _gui(sub_tag, value_tag="", sub_float=0.0, client_id=0):
    """Build a gui_message FakeEvent."""
    ev = FakeEvent(client_id=client_id, tag="gui_message", sub_tag=sub_tag,
                   value_tag=value_tag)
    ev.sub_float = sub_float
    return ev


# ---------------------------------------------------------------------------
# is_message_for — widget routing
# ---------------------------------------------------------------------------

class TestIsMessageFor(unittest.TestCase):

    def test_button_matches_own_tag(self):
        btn = Button("btn1", "Click")
        self.assertTrue(btn.is_message_for(_gui("btn1")))

    def test_button_rejects_other_tag(self):
        btn = Button("btn1", "Click")
        self.assertFalse(btn.is_message_for(_gui("other")))

    def test_dropdown_matches_own_tag(self):
        dd = Dropdown("dd1", "list: a, b")
        self.assertTrue(dd.is_message_for(_gui("dd1")))

    def test_slider_matches_own_tag(self):
        sl = Slider("sl1", 5.0, "low:0;high:10;")
        self.assertTrue(sl.is_message_for(_gui("sl1")))

    def test_checkbox_matches_own_tag(self):
        cb = Checkbox("cb1", "text: Toggle;")
        self.assertTrue(cb.is_message_for(_gui("cb1")))

    def test_text_input_matches_own_tag(self):
        ti = TextInput("ti1", "")
        self.assertTrue(ti.is_message_for(_gui("ti1")))

    def test_column_matches_click_tag(self):
        col = Column()
        col.tag = "widget_tag"
        col.click_tag = "icon_click_test"
        self.assertTrue(col.is_message_for(_gui("icon_click_test")))

    def test_column_matches_own_tag_when_click_tag_set(self):
        col = Column()
        col.tag = "widget_tag"
        col.click_tag = "icon_click_test"
        self.assertTrue(col.is_message_for(_gui("widget_tag")))

    def test_column_rejects_unrelated_tag(self):
        col = Column()
        col.tag = "widget_tag"
        col.click_tag = "icon_click_test"
        self.assertFalse(col.is_message_for(_gui("nope")))


# ---------------------------------------------------------------------------
# Dropdown
# ---------------------------------------------------------------------------

class TestDropdownOnMessage(unittest.TestCase):

    def test_updates_value_from_value_tag(self):
        dd = Dropdown("dd1", "list: alpha, beta, gamma")
        dd.on_message(_gui("dd1", value_tag="beta"))
        self.assertEqual(dd.value, "beta")

    def test_wrong_tag_leaves_value_unchanged(self):
        dd = Dropdown("dd1", "list: alpha, beta")
        dd.on_message(_gui("other", value_tag="beta"))
        self.assertEqual(dd.value, "")

    def test_successive_changes_take_last_value(self):
        dd = Dropdown("dd1", "list: alpha, beta, gamma")
        dd.on_message(_gui("dd1", value_tag="alpha"))
        dd.on_message(_gui("dd1", value_tag="gamma"))
        self.assertEqual(dd.value, "gamma")


# ---------------------------------------------------------------------------
# Slider
# ---------------------------------------------------------------------------

class TestSliderOnMessage(unittest.TestCase):

    def test_updates_value_from_sub_float(self):
        sl = Slider("sl1", 0.0, "low:0;high:10;")
        sl.on_message(_gui("sl1", sub_float=4.9))
        self.assertAlmostEqual(sl.value, 4.9, places=5)

    def test_int_slider_truncates_float(self):
        sl = Slider("sl1", 0, "low:0;high:10;", is_int=True)
        sl.on_message(_gui("sl1", sub_float=4.9))
        self.assertEqual(sl.value, 4)
        self.assertIsInstance(sl.value, int)

    def test_wrong_tag_leaves_value_unchanged(self):
        sl = Slider("sl1", 5.0, "low:0;high:10;")
        sl.on_message(_gui("other", sub_float=9.0))
        self.assertAlmostEqual(sl.value, 5.0, places=5)

    def test_zero_is_a_valid_update(self):
        sl = Slider("sl1", 5.0, "low:0;high:10;")
        sl.on_message(_gui("sl1", sub_float=0.0))
        self.assertAlmostEqual(sl.value, 0.0, places=5)


# ---------------------------------------------------------------------------
# Checkbox
# ---------------------------------------------------------------------------

class TestCheckboxOnMessage(unittest.TestCase):

    def _make(self, initial=False):
        cb = Checkbox("cb1", "text: Toggle;")
        cb._value = initial   # bypass string quirk in __init__
        return cb

    def test_toggles_false_to_true(self):
        cb = self._make(False)
        cb.on_message(_gui("cb1"))
        self.assertTrue(cb.value)

    def test_toggles_true_to_false(self):
        cb = self._make(True)
        cb.on_message(_gui("cb1"))
        self.assertFalse(cb.value)

    def test_double_toggle_restores_original(self):
        cb = self._make(False)
        cb.on_message(_gui("cb1"))
        cb.on_message(_gui("cb1"))
        self.assertFalse(cb.value)

    def test_wrong_tag_does_not_toggle(self):
        cb = self._make(False)
        cb.on_message(_gui("other"))
        self.assertFalse(cb.value)

    def test_wrong_event_type_does_not_toggle(self):
        cb = self._make(False)
        ev = FakeEvent(client_id=0, tag="not_gui_message", sub_tag="cb1")
        cb.on_message(ev)
        self.assertFalse(cb.value)


# ---------------------------------------------------------------------------
# TextInput
# ---------------------------------------------------------------------------

class TestTextInputOnMessage(unittest.TestCase):

    def test_sets_value_from_value_tag(self):
        ti = TextInput("ti1", "")
        ti.on_message(_gui("ti1", value_tag="hello"))
        self.assertEqual(ti.value, "hello")

    def test_each_keystroke_updates_cumulatively(self):
        ti = TextInput("ti1", "")
        for text in ("h", "he", "hel", "hello world"):
            ti.on_message(_gui("ti1", value_tag=text))
        self.assertEqual(ti.value, "hello world")

    def test_wrong_tag_leaves_value_unchanged(self):
        ti = TextInput("ti1", "")
        ti.on_message(_gui("other", value_tag="ignored"))
        self.assertEqual(ti.value, "")


# ---------------------------------------------------------------------------
# Icon / click_tag path through Column.on_message
# ---------------------------------------------------------------------------

class TestClickTagOnMessage(unittest.TestCase):

    def setUp(self):
        Clickable.clicked = {}

    def test_click_tag_registers_in_clickable(self):
        col = Column()
        col.tag = "widget_tag"
        col.click_tag = "icon_click_test"
        col.on_message(_gui("icon_click_test", client_id=1))
        self.assertIs(Clickable.clicked.get(1), col)

    def test_regular_tag_does_not_register_in_clickable(self):
        col = Column()
        col.tag = "widget_tag"
        col.click_tag = "icon_click_test"
        col.on_message(_gui("widget_tag", client_id=1))
        self.assertIsNone(Clickable.clicked.get(1))

    def test_unrelated_tag_does_not_register_in_clickable(self):
        col = Column()
        col.tag = "widget_tag"
        col.click_tag = "icon_click_test"
        col.on_message(_gui("nope", client_id=1))
        self.assertIsNone(Clickable.clicked.get(1))

    def test_click_tag_scoped_to_client_id(self):
        col = Column()
        col.tag = "w"
        col.click_tag = "clic"
        col.on_message(_gui("clic", client_id=7))
        self.assertIs(Clickable.clicked.get(7), col)
        self.assertIsNone(Clickable.clicked.get(1))


if __name__ == "__main__":
    unittest.main()
