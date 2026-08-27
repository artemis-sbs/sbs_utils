"""The mock's engineering table must match what the engine actually reports.

CAPTURED, NOT INVENTED. `eng_control_label` appears in no shipData key - the engine builds
the table itself - so these values came off engine 1.3.7 through the dev queue on a
tsn_light_cruiser. That matters because the alternative was writing plausible labels from
memory, and a plausible-but-wrong table is worse than an empty one: it makes a headless run
look like it exercised engineering when it exercised a guess.

Until this landed the mock had NO controls at all, so every `range(30)` walk over
`eng_control_label` - LegendaryMissions autoplay's power loop, its can-turn check, and
`set_engineering_value` - iterated zero times headless and did nothing, silently.

Run:
    python -m unittest tests.test_mock_eng_controls
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs as sbs
from tests.reset_helper import reset_mock
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.procedural.helm import (helm_eng_controls, helm_set_power,
                                       helm_system_heat)
from sbs_utils.procedural.spawn import npc_spawn, player_spawn
from sbs_utils.spaceobject import SpaceObject

# Verbatim from the capture. Kept here as well as in the mock so a change to either side
# has to be deliberate.
ENGINE_TABLE = [
    ("BEAM", 0), ("TORP", 0),
    ("IMPULSE", 1), ("WARP", 1), ("MANEUVER", 1),
    ("SENSORS", 2),
    ("FRONT SHIELD", 3), ("REAR SHIELD", 3),
]


class MockEngControlTests(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(0, "test"))
        self.ship = player_spawn(0, 0, 0, "Artemis", "tsn", "tsn_light_cruiser")
        self.ds = self.ship.data_set

    def tearDown(self):
        SpaceObject.clear()
        FrameContext.context = None

    def test_the_table_matches_the_engine(self):
        got = [(label, sysi) for _i, label, sysi in helm_eng_controls(self.ship)]
        self.assertEqual(got, ENGINE_TABLE)

    def test_controls_map_many_to_one_onto_systems(self):
        """The detail that catches real bugs.

        Eight controls feed FOUR systems: two weapons on 0, three drive on 1, sensors on
        2, both shield facings on 3. Code that assumes one control per system, or stops
        at the first label match, leaves half a system unset.
        """
        systems = {sysi for _i, _l, sysi in helm_eng_controls(self.ship)}
        self.assertEqual(systems, {0, 1, 2, 3})
        drive = [l for _i, l, s in helm_eng_controls(self.ship) if s == 1]
        self.assertEqual(drive, ["IMPULSE", "WARP", "MANEUVER"])

    def test_set_power_reaches_both_shield_facings(self):
        """`set_engineering_value` stops at the first match and would set only FRONT."""
        self.assertEqual(helm_set_power(self.ship, "shield", 1.5), 2)

    def test_labels_are_upper_case_as_the_engine_reports_them(self):
        """Anything matching these must fold case; autoplay lowercases both sides."""
        for _i, label, _s in helm_eng_controls(self.ship):
            self.assertEqual(label, label.upper())

    def test_spawn_values_match_the_engine(self):
        self.assertEqual(self.ds.get("system_coolant_available", 0), 8)
        for s in range(4):
            self.assertEqual(self.ds.get("system_max_damage", s), 3.0)
            self.assertEqual(self.ds.get("system_damage", s), 0.0)
        for i in range(len(ENGINE_TABLE)):
            self.assertEqual(self.ds.get("eng_control_value", i), 1.0)

    def test_an_npc_gets_no_control_table(self):
        """Engineering is a player console; an NPC has no sliders to move."""
        npc = npc_spawn(1000, 0, 0, "Foe", "raider", "kralien_cruiser", "behav_npcship")
        self.assertEqual(list(helm_eng_controls(npc)), [])

    def test_heat_reads_through_the_control_to_its_system(self):
        self.ds.set("system_cur_heat", 0.8, 1)
        self.assertAlmostEqual(helm_system_heat(self.ship, "warp"), 0.8)
        self.assertAlmostEqual(helm_system_heat(self.ship, "beam"), 0.0)


if __name__ == "__main__":
    unittest.main()
