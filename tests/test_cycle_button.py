"""gui_cycle_button / CycleButton - a button that cycles its states.

The control exists because a setting with a handful of states wants ONE touch target,
not one per option. What these pin is the two things that make it that control rather
than a button with a label:

* a press ADVANCES and WRAPS, and the handler that runs afterwards sees the NEW state
* advancing marks only this widget dirty, so it shows its own new state without the
  panel around it being rebuilt - a control that needs its parent redrawn stops
  working the moment the parent redraws for some other reason

    python -m unittest discover -s tests -p "test_cycle_button.py"
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from sbs_utils.helpers import FakeEvent
from sbs_utils.pages.layout.cycle_button import CycleButton, CYCLE_GLYPH

STATES = ["icons", "circles", "diamonds"]


def _press(button, tag=None):
    """The engine's message for a press of this button."""
    event = FakeEvent(1, "gui_message")
    event.sub_tag = tag if tag is not None else button.tag
    button.on_message(event)
    return button


class TheStateCycles(unittest.TestCase):
    def test_it_starts_on_the_first_state(self):
        self.assertEqual(CycleButton("t", STATES).state, "icons")

    def test_a_press_advances_one(self):
        b = CycleButton("t", STATES)
        _press(b)
        self.assertEqual(b.state, "circles")

    def test_the_last_state_wraps_to_the_first(self):
        b = CycleButton("t", STATES)
        for _ in range(len(STATES)):
            _press(b)
        self.assertEqual(b.state, "icons")

    def test_two_states_toggle(self):
        """The shape Engineering's View tab uses."""
        b = CycleButton("t", ["icons", "circles"])
        _press(b)
        self.assertEqual(b.state, "circles")
        _press(b)
        self.assertEqual(b.state, "icons")

    def test_advance_returns_the_new_state(self):
        self.assertEqual(CycleButton("t", STATES).advance(), "circles")

    def test_advance_can_step_backwards(self):
        b = CycleButton("t", STATES)
        self.assertEqual(b.advance(-1), "diamonds")

    def test_a_message_for_another_widget_does_not_advance_it(self):
        b = CycleButton("t", STATES)
        _press(b, tag="somebody_else")
        self.assertEqual(b.state, "icons")


class TheDegenerateListsAreNotErrors(unittest.TestCase):
    """A caller building states from data can legitimately end up with one or none,
    and `% 0` would raise inside a present."""

    def test_one_state_is_a_no_op(self):
        b = CycleButton("t", ["icons"])
        _press(b)
        self.assertEqual(b.state, "icons")

    def test_no_states_does_not_raise(self):
        b = CycleButton("t", [])
        _press(b)
        self.assertEqual(b.state, "")

    def test_none_does_not_raise(self):
        self.assertEqual(CycleButton("t", None).state, "")

    def test_blank_entries_are_dropped(self):
        b = CycleButton("t", ["icons", "  ", "", "circles"])
        self.assertEqual(b.states, ["icons", "circles"])

    def test_entries_are_stripped(self):
        """A comma string from MAST arrives with spaces - "icons, circles"."""
        self.assertEqual(CycleButton("t", ["icons", " circles "]).states,
                         ["icons", "circles"])


class TheSeededValue(unittest.TestCase):
    def test_value_seeds_the_shown_state(self):
        self.assertEqual(CycleButton("t", STATES, value="diamonds").state, "diamonds")

    def test_an_unknown_value_falls_back_to_the_first(self):
        """The value usually comes from saved settings. A console that refused to
        draw because a state was renamed would be worse than one showing a state."""
        self.assertEqual(CycleButton("t", STATES, value="hexagons").state, "icons")

    def test_a_seeded_button_advances_from_there(self):
        b = CycleButton("t", STATES, value="circles")
        _press(b)
        self.assertEqual(b.state, "diamonds")


class SettingTheStateDirectly(unittest.TestCase):
    """Seeding from stored settings must not look like a press."""

    def test_setting_state_does_not_fire_handlers(self):
        fired = []
        b = CycleButton("t", STATES)
        b.on_message_cb = lambda event, sender: fired.append(sender.state)
        b.state = "diamonds"
        self.assertEqual(b.state, "diamonds")
        self.assertEqual(fired, [])

    def test_setting_an_unknown_state_is_ignored(self):
        b = CycleButton("t", STATES, value="circles")
        b.state = "hexagons"
        self.assertEqual(b.state, "circles")

    def test_setting_the_state_changes_what_is_drawn(self):
        b = CycleButton("t", STATES)
        b.state = "diamonds"
        self.assertIn("diamonds", b.value)


class TheHandlerSeesTheNewState(unittest.TestCase):
    """THE POINT OF THE CONTROL. A handler asking `.state` is asking what the button
    now says - answering with the old one would make every caller compensate."""

    def test_the_callback_sees_the_state_after_the_press(self):
        seen = []
        b = CycleButton("t", STATES)
        b.on_message_cb = lambda event, sender: seen.append(sender.state)
        _press(b)
        self.assertEqual(seen, ["circles"])

    def test_the_callback_fires_once_per_press(self):
        seen = []
        b = CycleButton("t", STATES)
        b.on_message_cb = lambda event, sender: seen.append(sender.state)
        _press(b)
        _press(b)
        self.assertEqual(seen, ["circles", "diamonds"])

    def test_a_one_state_button_still_notifies(self):
        """It did not change, but it WAS pressed - swallowing that would make a
        single-option control feel dead."""
        seen = []
        b = CycleButton("t", ["icons"])
        b.on_message_cb = lambda event, sender: seen.append(sender.state)
        _press(b)
        self.assertEqual(seen, ["icons"])


class WhatItDraws(unittest.TestCase):
    def test_the_props_carry_the_state_and_the_glyph(self):
        b = CycleButton("t", STATES)
        self.assertIn("icons", b.value)
        self.assertIn(CYCLE_GLYPH, b.value)

    def test_the_props_move_with_the_state(self):
        b = CycleButton("t", STATES)
        _press(b)
        self.assertIn("circles", b.value)
        self.assertNotIn("icons", b.value)

    def test_the_glyph_can_be_changed(self):
        self.assertIn("+", CycleButton("t", STATES, glyph="+").value)

    def test_the_props_are_ascii(self):
        """This reaches an engine-rendered surface, which is ASCII only."""
        CycleButton("t", STATES).value.encode("ascii")
        CycleButton("t", ["a"], glyph=CYCLE_GLYPH).value.encode("ascii")

    def test_a_state_with_a_colon_is_wrapped_not_read_as_a_property(self):
        """Props are `key:value;` pairs, so a bare colon in a state would be read as
        a property - the trap grid node names hit.

        Button's own `value` setter backtick-wraps `$text`, which is what protects
        it. This asserts the wrapping rather than the absence of the colon: escaping
        the state BEFORE handing it over produced double backticks and a malformed
        props string, which is how this test first failed.
        """
        b = CycleButton("t", ["scale 1:1", "fit"])
        self.assertIn("$text:`scale 1:1", b.value)
        self.assertNotIn("``", b.value)

    def test_a_backtick_in_a_state_cannot_close_the_wrapping_early(self):
        b = CycleButton("t", ["we`ird", "fit"])
        self.assertNotIn("``", b.value)
        self.assertIn("weird", b.value)

    def _dirty_calls(self, region_tag):
        b = CycleButton("t", STATES)
        b.region_tag = region_tag
        calls = []
        b.mark_layout_dirty = lambda: calls.append("layout")
        b.mark_visual_dirty = lambda: calls.append("visual")
        return b, calls

    def test_inside_a_region_a_press_sends_NOTHING(self):
        """THE BUG, three rounds of it, ending in one button showing two labels.

        A widget re-sent into a region out of band paints wrong - `Button.value`
        says so in a comment older than this control. Its own workaround, a LAYOUT
        mark, is out of band too and re-sends the whole sub-section. Neither is
        safe; the region owner has to repaint.
        """
        b, calls = self._dirty_calls("somewhere$$")
        b.advance()
        self.assertEqual(calls, [], "a press painted into the region out of band")

    def test_inside_a_region_the_state_still_advances(self):
        """Going quiet must not stop it working - the tab repaints and reads this."""
        b, _calls = self._dirty_calls("somewhere$$")
        b.advance()
        self.assertEqual(b.state, "circles")

    def test_setting_the_state_in_a_region_sends_nothing_either(self):
        b, calls = self._dirty_calls("somewhere$$")
        b.state = "diamonds"
        self.assertEqual(calls, [])
        self.assertEqual(b.state, "diamonds")

    def test_outside_a_region_it_updates_itself(self):
        """The page's top-level layout has no region, and the dirty system works
        there - going silent everywhere would break the ordinary case."""
        b, calls = self._dirty_calls("")
        b.advance()
        self.assertEqual(calls, ["visual"])

    def test_advancing_always_goes_through_mark_value_dirty(self):
        """Whatever it decides to do, it must decide - the region check lives there."""
        b = CycleButton("t", STATES)
        marked = []
        b.mark_value_dirty = lambda **kw: marked.append(kw)
        b.advance()
        self.assertTrue(marked, "advancing bypassed mark_value_dirty")


class TheStateListCanBeReplaced(unittest.TestCase):
    def test_update_keeps_the_shown_state_when_it_survives(self):
        b = CycleButton("t", STATES, value="circles")
        b.update(["icons", "circles"])
        self.assertEqual(b.state, "circles")

    def test_update_falls_back_when_the_state_is_gone(self):
        b = CycleButton("t", STATES, value="diamonds")
        b.update(["icons", "circles"])
        self.assertEqual(b.state, "icons")

    def test_update_changes_what_a_press_cycles_through(self):
        b = CycleButton("t", STATES)
        b.update(["on", "off"])
        _press(b)
        self.assertEqual(b.state, "off")
        _press(b)
        self.assertEqual(b.state, "on")


class ButtonQuotesItsTextExactlyOnce(unittest.TestCase):
    """A Button and a Text take the same props string, so they must quote it the same
    way. `Button.value` used to wrap `$text` unconditionally while `Text.update`
    skipped text that was already quoted - so a caller who ran a dynamic label through
    `gui_text_escape` (correct, and required for a label that may contain a colon) got
    DOUBLE backticks and the engine drew them: buttons reading ``do work order now``.

    Reported from a bridge on Engineering's grid orders, 2026-09-22.
    """

    def _button(self, props):
        from sbs_utils.pages.layout.button import Button
        return Button("t", props)

    def test_plain_text_is_quoted(self):
        self.assertIn("$text:`hello`", self._button("$text:hello;").value)

    def test_already_quoted_text_is_left_alone(self):
        from sbs_utils.helpers import gui_text_escape
        value = self._button(f"$text:{gui_text_escape('do work order now')};").value
        self.assertIn("$text:`do work order now`", value)
        self.assertNotIn("``", value)

    def test_an_escaped_label_with_a_colon_survives(self):
        """Why a caller escapes at all: a bare colon reads as a style property."""
        from sbs_utils.helpers import gui_text_escape
        value = self._button(f"$text:{gui_text_escape('scale 1:1')};color:red;").value
        self.assertIn("scale 1:1", value)
        self.assertNotIn("``", value)

    def test_empty_text_becomes_a_MATCHED_empty_pair(self):
        """Not a change - `Text` does the same. What matters is that the quotes are
        balanced; a single stray backtick is what draws one in the box."""
        value = self._button("$text:;").value
        self.assertIn("$text:``;", value)
        self.assertEqual(value.count("`") % 2, 0)


if __name__ == "__main__":
    unittest.main()
