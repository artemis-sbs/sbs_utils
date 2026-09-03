"""The HULL decides what it carries, and nothing may overrule it.

shipData's `torpedostart` is a per-hull declaration and the stock data means it
precisely: a `tsn_fighter` is `Homing 5, Nuke 0, EMP 0, Mine 0, PShock 0, Tag 0`, and a
`tsn_shuttle` is zero of everything. `ship_data.py` writes `{key}_MAX` and the
available-types list from exactly that, so a declared 0 means "this hull does not carry
this round" - not "nobody has filled it in yet".

THIS FILE USED TO ASSERT THE OPPOSITE, and that is worth keeping in view. It was written
alongside a change that moved the capacity write OUT of the "am I adding this key"
branch, so a type already listed could have its capacity granted anyway (GWQ-5,
2026-09-03). That reads reasonable in isolation and is wrong in context:
LegendaryMissions' spawn loop grants every type matching the ship's SIDE, guarded on
`counts[1] == 0` - which a declared zero satisfies. Every hull shipData said carried none
of something was handed ten of it, and a shuttle came out armed. Reported the same day
as a Galaxy showing Homing/Nuke/EMP/Mine/PShock all at 10/10 beside its real Photon
16/16.

The tests written with that change asserted the behavior it introduced, so they passed by
construction and would have kept passing while the bug shipped. They now pin the rule the
stock data has always expressed.
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

    def test_a_type_the_hull_declares_at_zero_stays_at_zero(self):
        """The bug. A fighter declaring `Nuke: 0` must not come out with ten."""
        from sbs_utils.procedural.torpedoes import torpedo_make_available
        from sbs_utils.procedural.query import to_object
        pid = self._player()
        po = to_object(pid)
        # What shipData leaves behind for `torpedostart: [{Homing: 5}, {Nuke: 0}]`.
        po.data_set.set("torpedo_types_available", "Homing,Nuke", 0)
        po.data_set.set("Nuke_MAX", 0, 0)
        po.data_set.set("Nuke_NUM", 0, 0)

        torpedo_make_available(pid, "Nuke", 10)

        self.assertEqual(po.data_set.get("Nuke_MAX", 0), 0,
                         "the hull said it carries no Nukes and was overruled")
        self.assertEqual(po.data_set.get("Nuke_NUM", 0), 0)

    def test_a_declared_capacity_is_not_raised_either(self):
        """`PShock: 2` on a light cruiser is a number, not a starting point."""
        from sbs_utils.procedural.torpedoes import torpedo_make_available
        from sbs_utils.procedural.query import to_object
        pid = self._player()
        po = to_object(pid)
        po.data_set.set("torpedo_types_available", "PShock", 0)
        po.data_set.set("PShock_MAX", 2, 0)
        po.data_set.set("PShock_NUM", 2, 0)

        torpedo_make_available(pid, "PShock", 10)

        self.assertEqual(po.data_set.get("PShock_MAX", 0), 2)
        self.assertEqual(po.data_set.get("PShock_NUM", 0), 2)

    def test_a_type_the_hull_does_NOT_list_is_still_grantable(self):
        """The case that has to keep working: a mod adding Quantum to a Defiant, or a
        prefab handing out a round the base hull never declared."""
        from sbs_utils.procedural.torpedoes import torpedo_make_available
        from sbs_utils.procedural.query import to_object
        pid = self._player()
        po = to_object(pid)
        po.data_set.set("torpedo_types_available", "Homing", 0)

        torpedo_make_available(pid, "Quantum", 4)

        self.assertEqual(po.data_set.get("Quantum_MAX", 0), 4)
        self.assertEqual(po.data_set.get("Quantum_NUM", 0), 4)
        self.assertEqual(po.data_set.get("torpedo_types_available", 0), "Homing,Quantum")

    def test_fill_false_grants_capacity_without_rounds(self):
        """A fabricate-only type (the Beacon) gets its tube and no loaded rounds.

        Granted through the not-listed branch, which is how it arrives in practice - no
        stock hull declares a Beacon, because it is a LegendaryMissions type.
        """
        from sbs_utils.procedural.torpedoes import torpedo_make_available
        from sbs_utils.procedural.query import to_object
        pid = self._player()
        po = to_object(pid)
        po.data_set.set("torpedo_types_available", "Homing", 0)

        torpedo_make_available(pid, "Beacon", 6, fill=False)

        self.assertEqual(po.data_set.get("Beacon_MAX", 0), 6)
        # `None`, not 0: with fill=False nothing writes _NUM at all. And the second
        # argument to data_set.get is an INDEX, not a default - so there is no
        # tidier way to say "no rounds" than accepting either.
        self.assertFalse(po.data_set.get("Beacon_NUM", 0),
                         "fabricate-only types get capacity but no loaded rounds")

    def test_re_granting_a_listed_type_does_not_corrupt_the_list(self):
        from sbs_utils.procedural.torpedoes import torpedo_make_available
        from sbs_utils.procedural.query import to_object
        pid = self._player()
        po = to_object(pid)
        po.data_set.set("torpedo_types_available", "Homing,Nuke", 0)

        torpedo_make_available(pid, "Nuke", 4)

        self.assertEqual(po.data_set.get("torpedo_types_available", 0), "Homing,Nuke")

    def test_the_first_type_does_not_get_a_leading_comma(self):
        from sbs_utils.procedural.torpedoes import torpedo_make_available
        from sbs_utils.procedural.query import to_object
        pid = self._player()
        po = to_object(pid)
        po.data_set.set("torpedo_types_available", "", 0)

        torpedo_make_available(pid, "Homing", 8)

        self.assertEqual(po.data_set.get("torpedo_types_available", 0), "Homing")


if __name__ == "__main__":
    unittest.main()
