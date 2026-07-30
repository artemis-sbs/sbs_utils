"""Player-slot identity: creating a player ship is idempotent per SLOT.

`//shared/signal` guarantees a route runs server-once per EMIT - it says nothing about
how often the signal is emitted, and init signals get re-emitted for all sorts of
reasons (two addons emitting one, a copy-pasted emit, an emit inside a loop, a
double-clicked Start button). Creating unkeyed then duplicates the whole roster: on the
LM console path a second run of `create_default_player_ships` made 16 ships, and a real
session was measured at 8 -> 33.

The fix is idempotency against the CURRENT world rather than a did-I-run flag, which is
what keeps the LEGITIMATE re-runs working: after a wipe the ships are gone and ensure
recreates them, a destroyed ship can be remade, a late joiner gets only its own slot,
and a route that failed halfway completes the set instead of doubling it.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import cosmos_dev.mock.sbs as sbs
from tests.reset_helper import reset_mock
from sbs_utils.procedural.spawn import (
    player_ensure, player_slot_id, player_slot_role, player_slots, players_reset,
)
from sbs_utils.procedural.a2x.spawn import create_player, player_ship
from sbs_utils.procedural.query import to_id_list, to_object, object_exists
from sbs_utils.procedural.roles import role, has_role
from sbs_utils.procedural.space_objects import delete_object


def _player_ids():
    return sorted(to_id_list(role("__player__")))


class PlayerEnsureTests(unittest.TestCase):
    def setUp(self):
        self.sim = reset_mock(sbs)

    def _ensure(self, slot, name=None):
        return player_ensure(slot, 0, 0, 0, "tsn_battle_cruiser",
                             name or f"Ship{slot}", "tsn")

    def test_second_ensure_returns_the_same_ship(self):
        first = self._ensure(0)
        second = self._ensure(0)
        self.assertEqual(second, first, "a re-emit must not spawn a second hull")
        self.assertEqual(len(_player_ids()), 1)

    def test_whole_roster_is_stable_across_a_second_run(self):
        for i in range(8):
            self._ensure(i)
        self.assertEqual(len(_player_ids()), 8)
        for i in range(8):
            self._ensure(i)
        self.assertEqual(len(_player_ids()), 8, "second init run duplicated the roster")

    def test_slot_lookup_and_stamp(self):
        sid = self._ensure(3)
        self.assertEqual(player_slot_id(3), sid)
        self.assertTrue(has_role(sid, player_slot_role(3)))
        self.assertIsNone(player_slot_id(4), "an empty slot resolves to None")
        self.assertEqual(player_slots(), {3: sid})

    def test_recreates_after_the_ship_is_gone(self):
        # The post-sim_create / destroyed-ship case: a did-I-run flag would leave the
        # mission with NO player ships, which ends the game instantly.
        first = self._ensure(0)
        delete_object(first)
        self.assertFalse(object_exists(first))
        second = self._ensure(0)
        self.assertNotEqual(second, first)
        self.assertEqual(len(_player_ids()), 1)

    def test_late_joiner_adds_only_its_own_slot(self):
        for i in range(3):
            self._ensure(i)
        before = _player_ids()
        added = self._ensure(3)
        self.assertEqual(len(_player_ids()), 4)
        self.assertNotIn(added, before, "existing slots must be untouched")

    def test_partial_set_completes_rather_than_doubling(self):
        # A route that died after 3 of 8 and got re-emitted "to fix it".
        for i in range(3):
            self._ensure(i)
        for i in range(8):
            self._ensure(i)
        self.assertEqual(len(_player_ids()), 8)

    def test_existing_ship_is_returned_untouched(self):
        first = self._ensure(0, name="Artemis")
        again = player_ensure(0, 9999, 9999, 9999, "tsn_light_cruiser", "Renamed", "tsn")
        self.assertEqual(again, first)
        self.assertEqual(to_object(first).name, "Artemis", "ensure must not reconfigure")

    def test_players_reset_frees_every_slot(self):
        for i in range(4):
            self._ensure(i)
        self.assertEqual(players_reset(), 4)
        self.assertEqual(_player_ids(), [])
        self.assertIsNone(player_slot_id(0))
        # ...and a re-init rebuilds the roster cleanly (the intentional-reset path).
        for i in range(4):
            self._ensure(i)
        self.assertEqual(len(_player_ids()), 4)


class A2xCreatePlayerSlotTests(unittest.TestCase):
    def setUp(self):
        self.sim = reset_mock(sbs)

    def test_slot_makes_create_player_idempotent(self):
        a = create_player(0, 0, 0, "tsn_light_cruiser", name="Artemis", side="tsn", slot=0)
        b = create_player(0, 0, 0, "tsn_light_cruiser", name="Artemis", side="tsn", slot=0)
        self.assertEqual(a, b)
        self.assertEqual(len(_player_ids()), 1)
        self.assertTrue(has_role(a, "default_player_ship"))

    def test_without_a_slot_behaviour_is_unchanged(self):
        a = create_player(0, 0, 0, "tsn_light_cruiser", name="A", side="tsn")
        b = create_player(0, 0, 0, "tsn_light_cruiser", name="B", side="tsn")
        self.assertNotEqual(a, b, "the unslotted path must still mint a new hull")
        self.assertEqual(len(_player_ids()), 2)

    def test_player_ship_resolves_by_stamp_not_position(self):
        # Stamped slots survive anything else spawning: slot 1 stays slot 1 even though
        # it was created LAST and therefore has the highest id.
        s0 = create_player(0, 0, 0, "tsn_light_cruiser", name="Zero", side="tsn", slot=0)
        s1 = create_player(0, 0, 0, "tsn_light_cruiser", name="One", side="tsn", slot=1)
        self.assertEqual(player_ship(0), s0)
        self.assertEqual(player_ship(1), s1)
        delete_object(s0)
        recreated = create_player(0, 0, 0, "tsn_light_cruiser", name="Zero", side="tsn", slot=0)
        self.assertEqual(player_ship(0), recreated, "slot must follow the stamp")
        self.assertEqual(player_ship(1), s1, "an unrelated slot must not shift")

    def test_unstamped_ships_fall_back_to_id_order(self):
        a = create_player(0, 0, 0, "tsn_light_cruiser", name="A", side="tsn")
        b = create_player(0, 0, 0, "tsn_light_cruiser", name="B", side="tsn")
        self.assertEqual(player_ship(0), min(a, b))
        self.assertEqual(player_ship(1), max(a, b))
        self.assertIsNone(player_ship(5))

    def test_single_ship_arena_still_pins(self):
        # Mirrors A2xTestRange/maps/test_convert_player.mast.
        p = create_player(0, 0, 0, "tsn_light_cruiser", name="Artemis", side="tsn")
        self.assertEqual(player_ship(0), p)
        self.assertIsNone(player_ship(5))


if __name__ == "__main__":
    unittest.main()
