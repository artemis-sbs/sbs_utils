"""A ship picker whose filter matches nothing.

Reported from Gamma with a Q as a runtime error on the console-select screen:

    IndexError in expression:
         gui_content(spick, style="tag:sh_ship_picker", var="ship_type")
    list index out of range
    ship = self.ships[self.cur]     shippicker.py:202

The chain is worth writing down, because no part of it looks like a crash on its own.
`EXTRA_SHIP_DATA` is off by default (the v1.3.4 engine cannot do it), so
`ship_data.add_extra` loaded nothing and the TNG mod's hulls did not exist. The party
profile's `PLAYABLE_RACES` names only TNG races, so LM's `valid_interiors` - which keeps
a hull only if `settings_race_is_playable(side)` - kept none of the stock hulls either.
The picker was then handed an empty `ship_keys`, filtered every ship out, and indexed
`[0]` of an empty list.

Two fixes, and the split matters: the picker must not crash on an empty list whatever
the reason (here), and `add_extra` must SAY it is disabled instead of returning False in
silence (test_extra_ship_data_setting), because the silence is what made an IndexError
the first anyone heard of it.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from sbs_utils.pages.widgets.shippicker import ShipPicker


class PickerBase(unittest.TestCase):
    def picker(self, **kw):
        return ShipPicker(0, 0, "tag", **kw)


class TestNothingMatchesTheFilter(PickerBase):
    """The reported crash. A filter is allowed to match nothing - that is a
    misconfiguration to report, not an exception to raise on the console screen every
    player passes through."""

    def setUp(self):
        self.p = self.picker(roles="no_such_role_anywhere")

    def test_the_list_really_is_empty(self):
        """If this ever stops being true the rest of the class proves nothing."""
        self.assertEqual(self.p.ships, [])

    def test_GET_SELECTED_DOES_NOT_RAISE(self):
        self.assertIsNone(self.p.get_selected())

    def test_get_selected_name_does_not_raise_either(self):
        """The other unguarded index, one line apart. Fixing only the one in the
        traceback leaves the crash a keystroke away."""
        self.assertIsNone(self.p.get_selected_name())

    def test_an_empty_key_list_is_the_reported_case(self):
        """LM hands `ship_keys=valid_interiors`, and an empty set is exactly what the
        race filter produced with the mod's hulls missing."""
        p = self.picker(ship_keys=set())
        self.assertEqual(p.ships, [])
        self.assertIsNone(p.get_selected())

    def test_a_stale_index_past_the_end_is_survivable(self):
        """`cur` is kept across a re-filter, so a narrowing filter can leave it
        pointing past the end even when the list is not empty."""
        p = self.picker()
        p.cur = len(p.ships) + 5
        self.assertIsNone(p.get_selected())


class TestTheOrdinaryCaseIsUntouched(PickerBase):
    """The guard must not cost the picker its job."""

    def test_an_unfiltered_picker_still_has_ships(self):
        p = self.picker()
        self.assertTrue(p.ships, "no ship data at all - fixture problem, not a fix")

    def test_and_still_selects_one(self):
        p = self.picker()
        self.assertIsNotNone(p.get_selected())

    def test_and_still_names_it(self):
        p = self.picker()
        self.assertIsNotNone(p.get_selected_name())


if __name__ == "__main__":
    unittest.main()
