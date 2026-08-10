"""docking proximity gate - how close is close enough to be offered a dock.

These cover the two pure functions the gas-giant work added, and they exist mainly to pin
the BACKWARD-COMPATIBLE half: docking.py is load-bearing for every mission, and a brain
that says nothing new must search exactly the 2000u it always searched.

The gate is metadata on the brain's label, so the unit under test is "read the metadata,
produce a center distance". A stub label is the honest fixture for that - a real MAST
compile would be testing the compiler.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.mock import sbs
from tests.reset_helper import reset_mock
from sbs_utils.procedural.query import to_object
from sbs_utils.procedural.spawn import npc_spawn, terrain_spawn
from sbs_utils.procedural import docking as dk


class _StubLabel:
    """Stands in for a compiled MAST label's metadata lookup."""

    def __init__(self, **meta):
        self._meta = meta

    def get_inventory_value(self, key, default=None):
        return self._meta.get(key, default)


def _brain(**meta):
    return dk._DockingBrain(_StubLabel(**meta), None)


class DockingGateTestBase(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        self.station = to_object(npc_spawn(0, 0, 0, "Base", "tsn",
                                           "starbase_command", "behav_station"))
        self.station.engine_object.exclusion_radius = 200.0
        self.giant = to_object(terrain_spawn(0, 0, 0, "Giant", "#,gasgiant",
                                             "planet", "behav_planet"))
        self.giant.engine_object.exclusion_radius = 8000.0


class TestGate(DockingGateTestBase):
    def test_a_brain_saying_nothing_gets_the_historic_600(self):
        self.assertEqual(dk._docking_gate(_brain(), self.station), 600)

    def test_distance_is_a_plain_center_range(self):
        self.assertEqual(dk._docking_gate(_brain(distance=900), self.station), 900)

    def test_surface_distance_is_measured_from_the_hull(self):
        gate = dk._docking_gate(_brain(surface_distance=1000), self.giant)
        self.assertEqual(gate, 9000)

    def test_surface_distance_scales_with_the_body(self):
        # The whole point: one brain serves giants of any size without re-tuning.
        small = to_object(terrain_spawn(0, 0, 0, "Small", "#,gasgiant",
                                        "planet", "behav_planet"))
        small.engine_object.exclusion_radius = 3000.0
        b = _brain(surface_distance=1000)
        self.assertEqual(dk._docking_gate(b, self.giant), 9000)
        self.assertEqual(dk._docking_gate(b, small), 4000)

    def test_surface_distance_wins_over_distance(self):
        gate = dk._docking_gate(_brain(distance=600, surface_distance=1000), self.giant)
        self.assertEqual(gate, 9000)

    def test_a_missing_npc_degrades_to_the_bare_surface_distance(self):
        self.assertEqual(dk._docking_gate(_brain(surface_distance=1000), None), 1000)


class TestReach(DockingGateTestBase):
    def test_station_only_pairs_still_search_exactly_2000(self):
        pairs = {self.station.id: _brain()}
        self.assertEqual(dk._docking_reach(pairs), dk.DOCKING_DEFAULT_REACH)

    def test_a_gate_below_the_floor_does_not_shrink_the_search(self):
        pairs = {self.station.id: _brain(distance=300)}
        self.assertEqual(dk._docking_reach(pairs), dk.DOCKING_DEFAULT_REACH)

    def test_a_gas_giant_widens_the_search_to_reach_it(self):
        # Without this the broad phase prunes the giant away before anything is measured,
        # and a body 16000u across can never be docked with at all.
        pairs = {self.giant.id: _brain(surface_distance=1000)}
        self.assertEqual(dk._docking_reach(pairs), 9000)

    def test_the_widest_brain_wins_when_a_player_has_both(self):
        pairs = {self.station.id: _brain(),
                 self.giant.id: _brain(surface_distance=1000)}
        self.assertEqual(dk._docking_reach(pairs), 9000)

    def test_no_pairs_reads_as_the_floor(self):
        self.assertEqual(dk._docking_reach({}), dk.DOCKING_DEFAULT_REACH)


if __name__ == "__main__":
    unittest.main()
