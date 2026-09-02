"""A torpedo type listed at count 0 must still be grantable.

shipData's `torpedostart` writes `{key}_MAX = 0` AND puts the key into
`torpedo_types_available` (ship_data.py), so a hull that declares `Nuke: 0` arrives
already listed with no capacity. `torpedo_make_available` used to write the capacity
only when it was ADDING the key to that list, which made it a permanent no-op for
exactly those keys - the tube drew, hard-capped at 0/0, and no station or prefab could
ever grant it. Both LegendaryMissions call sites guard with "only if _MAX is 0", so they
were asking for precisely the case that was refused.

Reported from the Gamma with a Q playtest, 2026-09-01 (GWQ-5).
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest
import cosmos_dev.mock.sbs as sbs
from tests.reset_helper import reset_mock


class TorpedoAvailabilityTests(unittest.TestCase):
    def setUp(self):
        self.sim = reset_mock(sbs)
        from sbs_utils.helpers import FrameContext, Context
        FrameContext.context = Context(self.sim, sbs, None)

    def _player(self):
        from sbs_utils.procedural.spawn import player_spawn
        from sbs_utils.procedural.query import to_id
        return to_id(player_spawn(0, 0, 0, "Artemis", "tsn", "tsn_light_cruiser"))

    def test_a_type_listed_at_zero_can_still_be_granted(self):
        from sbs_utils.procedural.torpedoes import torpedo_make_available
        from sbs_utils.procedural.query import to_object
        pid = self._player()
        po = to_object(pid)
        # What shipData leaves behind for `torpedostart: [{Nuke: 0}]`.
        po.data_set.set("torpedo_types_available", "Homing,Nuke", 0)
        po.data_set.set("Nuke_MAX", 0, 0)
        po.data_set.set("Nuke_NUM", 0, 0)

        torpedo_make_available(pid, "Nuke", 4)

        self.assertEqual(po.data_set.get("Nuke_MAX", 0), 4,
                         "capacity must be written even when the key was already listed")
        self.assertEqual(po.data_set.get("Nuke_NUM", 0), 4)
        # And the list is not corrupted by re-granting an entry it already holds.
        self.assertEqual(po.data_set.get("torpedo_types_available", 0), "Homing,Nuke")

    def test_fill_false_grants_capacity_without_rounds(self):
        from sbs_utils.procedural.torpedoes import torpedo_make_available
        from sbs_utils.procedural.query import to_object
        pid = self._player()
        po = to_object(pid)
        po.data_set.set("torpedo_types_available", "Beacon", 0)
        po.data_set.set("Beacon_MAX", 0, 0)
        po.data_set.set("Beacon_NUM", 0, 0)

        torpedo_make_available(pid, "Beacon", 6, fill=False)

        self.assertEqual(po.data_set.get("Beacon_MAX", 0), 6)
        self.assertEqual(po.data_set.get("Beacon_NUM", 0), 0,
                         "fabricate-only types get capacity but no loaded rounds")

    def test_the_first_type_does_not_get_a_leading_comma(self):
        from sbs_utils.procedural.torpedoes import torpedo_make_available
        from sbs_utils.procedural.query import to_object
        pid = self._player()
        po = to_object(pid)
        po.data_set.set("torpedo_types_available", "", 0)

        torpedo_make_available(pid, "Homing", 8)

        self.assertEqual(po.data_set.get("torpedo_types_available", 0), "Homing")

    def test_a_new_type_is_still_appended(self):
        from sbs_utils.procedural.torpedoes import torpedo_make_available
        from sbs_utils.procedural.query import to_object
        pid = self._player()
        po = to_object(pid)
        po.data_set.set("torpedo_types_available", "Homing", 0)

        torpedo_make_available(pid, "Quantum", 5)

        self.assertEqual(po.data_set.get("torpedo_types_available", 0), "Homing,Quantum")
        self.assertEqual(po.data_set.get("Quantum_MAX", 0), 5)


if __name__ == "__main__":
    unittest.main()
