"""A map can say what the crew flies, and it takes effect at mission SELECT.

GWQ-15: "set the hull at mission select (and disable Helm from changing it). If not on
mission select, then much sooner than after Q's intro. That is too late and confuses
people."

A map that reshaped its crew from its own BODY did it after the console-select screen, so
everyone spent that screen looking at a ship they were about to stop flying. A `Crew:`
block is published by `map_apply_crew` and picked up by `player_roster_apply`, both of
which the server panel runs while it is the only thing on screen.

The trap this is really guarding is the one that made `Defaults:` unusable here: it is
SET-IF-ABSENT, so an operator browsing the picker would have pinned whichever map they
looked at first and flown every later trial in that ship.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir

test_set_exe_dir()

from cosmos_dev.mock import sbs  # noqa: E402,F401
from sbs_utils.procedural.execution import get_shared_variable  # noqa: E402
from sbs_utils.procedural.maps import map_apply_crew, map_get_crew  # noqa: E402


class FakeMap:
    """Stands in for a @map label: metadata reaches code as inventory values."""

    def __init__(self, values):
        self._values = values

    def get_inventory_value(self, key, default=None):
        return self._values.get(key, default)


class MapCrewMetadataTest(unittest.TestCase):
    def test_reads_the_crew_block(self):
        m = FakeMap({"Crew": {"hull": "tng_fed_defiant", "side": "federation"}})
        self.assertEqual(map_get_crew(m), {"hull": "tng_fed_defiant", "side": "federation"})

    def test_lowercase_key_is_accepted(self):
        m = FakeMap({"crew": {"hull": "x"}})
        self.assertEqual(map_get_crew(m), {"hull": "x"})

    def test_no_block_is_none(self):
        self.assertIsNone(map_get_crew(FakeMap({})))


class MapApplyCrewTest(unittest.TestCase):
    def tearDown(self):
        map_apply_crew(None)

    def test_publishes_hull_and_side(self):
        map_apply_crew(FakeMap({"Crew": {"hull": "tng_fed_defiant", "side": "federation"}}))
        self.assertEqual(get_shared_variable("CREW_HULL"), "tng_fed_defiant")
        self.assertEqual(get_shared_variable("CREW_SIDE"), "federation")

    def test_a_second_map_REPLACES_the_first(self):
        """The whole reason this is not a `Defaults:` entry.

        Set-if-absent would leave the operator flying the first trial they browsed.
        """
        map_apply_crew(FakeMap({"Crew": {"hull": "tng_fed_defiant"}}))
        map_apply_crew(FakeMap({"Crew": {"hull": "tng_fed_intrepid"}}))
        self.assertEqual(get_shared_variable("CREW_HULL"), "tng_fed_intrepid")

    def test_a_map_with_no_crew_block_CLEARS_it(self):
        """A stale hull left behind is the same bug wearing a different hat."""
        map_apply_crew(FakeMap({"Crew": {"hull": "tng_fed_defiant"}}))
        map_apply_crew(FakeMap({}))
        self.assertFalse(get_shared_variable("CREW_HULL"))

    def test_none_clears_too(self):
        map_apply_crew(FakeMap({"Crew": {"hull": "tng_fed_defiant"}}))
        map_apply_crew(None)
        self.assertFalse(get_shared_variable("CREW_HULL"))

    def test_a_partial_block_only_sets_what_it_names(self):
        map_apply_crew(FakeMap({"Crew": {"hull": "tng_fed_defiant"}}))
        self.assertEqual(get_shared_variable("CREW_HULL"), "tng_fed_defiant")
        self.assertFalse(get_shared_variable("CREW_SIDE"))


class CrewOverrideTest(unittest.TestCase):
    """The roster's side of it - which hull actually wins."""

    def tearDown(self):
        map_apply_crew(None)

    def test_an_unloaded_hull_is_ignored(self):
        """Swapping a player onto a key shipData has never heard of is worse than
        flying the wrong ship - and a map naming a modded hull on a stock install is
        the ordinary way to get here."""
        from sbs_utils.procedural.player_roster import _crew_override
        map_apply_crew(FakeMap({"Crew": {"hull": "definitely_not_a_hull_9f3"}}))
        self.assertIsNone(_crew_override("CREW_HULL"))

    def test_the_side_is_not_hull_checked(self):
        from sbs_utils.procedural.player_roster import _crew_override
        map_apply_crew(FakeMap({"Crew": {"side": "klingon"}}))
        self.assertEqual(_crew_override("CREW_SIDE", check_hull=False), "klingon")

    def test_unset_is_none(self):
        from sbs_utils.procedural.player_roster import _crew_override
        map_apply_crew(None)
        self.assertIsNone(_crew_override("CREW_HULL"))


if __name__ == "__main__":
    unittest.main()
