"""Tests for a2x_set_object_property (2.8 property -> Cosmos data_set/engine)."""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import cosmos_dev.mock.sbs as sbs
from tests.reset_helper import reset_mock
from sbs_utils.procedural.a2x.props import (
    set_object_property, object_property_mapped, object_property_key,
    set_special, special_ability_mapped,
    addto_object_property, copy_object_property, set_ship_text,
    set_relative_position,
)
from sbs_utils.procedural.a2x.spawn import create_enemy
from sbs_utils.procedural.query import to_object, get_data_set_value, to_id


class A2xPropsPureTests(unittest.TestCase):
    def test_mapped_lookup(self):
        self.assertTrue(object_property_mapped("hasSurrendered"))
        self.assertFalse(object_property_mapped("pirateRepWithStations"))

    def test_key_for_data_props(self):
        self.assertEqual(object_property_key("shieldStateBack"), ("shield_val", 1))
        self.assertEqual(object_property_key("energy"), ("energy", 0))
        self.assertIsNone(object_property_key("angleDelta"))  # engine, not data
        self.assertIsNone(object_property_key("notARealProp"))


class A2xPropsMockTests(unittest.TestCase):
    def setUp(self):
        self.sim = reset_mock(sbs)
        self.so = create_enemy(0, 0, 0, "kralien_cruiser", name="X")

    def test_data_set_scalar(self):
        self.assertTrue(set_object_property(self.so, "energy", 250))
        self.assertEqual(get_data_set_value(to_id(self.so), "energy"), 250)

    def test_data_set_array_index(self):
        self.assertTrue(set_object_property(self.so, "shieldStateBack", 80))
        self.assertEqual(get_data_set_value(to_id(self.so), "shield_val", 1), 80)

    def test_torpedo_store(self):
        self.assertTrue(set_object_property(self.so, "missileStoresNuke", 4))
        self.assertEqual(get_data_set_value(to_id(self.so), "Nuke_NUM"), 4)

    def test_engine_attr(self):
        self.assertTrue(set_object_property(self.so, "rollDelta", 0.003))
        self.assertAlmostEqual(to_object(self.so).engine_object.steer_roll, 0.003)

    def test_unmapped_returns_false(self):
        self.assertFalse(set_object_property(self.so, "surrenderChance", 50))

    def test_set_special_ability_on(self):
        self.assertEqual(set_special(self.so, "LowVis", on=True), "elite_low_vis")
        self.assertEqual(get_data_set_value(to_id(self.so), "elite_low_vis"), 1)

    def test_set_special_ability_clear(self):
        set_special(self.so, "Drones", on=False)
        self.assertEqual(get_data_set_value(to_id(self.so), "elite_drone_launcher"), 0)

    def test_set_special_unmapped_ability(self):
        self.assertIsNone(set_special(self.so, "Cloak"))
        self.assertFalse(special_ability_mapped("HET"))

    def test_addto_object_property(self):
        set_object_property(self.so, "energy", 100)
        self.assertTrue(addto_object_property(self.so, "energy", 50))
        self.assertEqual(get_data_set_value(to_id(self.so), "energy"), 150)

    def test_copy_object_property(self):
        b = create_enemy(0, 0, 0, "kralien_cruiser", name="Y")
        set_object_property(self.so, "shieldStateFront", 60)
        self.assertTrue(copy_object_property(self.so, b, "shieldStateFront"))
        self.assertEqual(get_data_set_value(to_id(b), "shield_val", 0), 60)

    def test_set_position_applies_flip(self):
        # 2.8 positionX=30000 -> Cosmos pos.x = 100000-30000 = 70000; Y unchanged
        set_object_property(self.so, "positionX", 30000)
        set_object_property(self.so, "positionY", 12)
        p = to_object(self.so).engine_object.pos
        self.assertAlmostEqual(p.x, 70000, delta=1)
        self.assertAlmostEqual(p.y, 12, delta=1)

    def test_addto_position_negates_on_flipped_axis(self):
        set_object_property(self.so, "positionZ", 40000)  # -> pos.z = 60000
        addto_object_property(self.so, "positionZ", 1000)  # 2.8 +1000 -> Cosmos -1000
        self.assertAlmostEqual(to_object(self.so).engine_object.pos.z, 59000, delta=1)

    def test_set_relative_position(self):
        # create_enemy flips coords, so the ref sits at Cosmos (95000,*,95000).
        b = create_enemy(5000, 0, 5000, "kralien_cruiser", name="Ref")
        rp = to_object(b).engine_object.pos
        self.assertTrue(set_relative_position(self.so, b, 90, 1000))
        p = to_object(self.so).engine_object.pos
        self.assertAlmostEqual(p.x, rp.x + 1000, delta=1)  # 90deg -> +x
        self.assertAlmostEqual(p.z, rp.z, delta=1)

    def test_set_ship_text(self):
        self.assertTrue(set_ship_text(self.so, name="Ghost", race="Kralien",
                                      ship_class="Cruiser"))
        self.assertEqual(get_data_set_value(to_id(self.so), "name_tag"), "Ghost")
        self.assertEqual(get_data_set_value(to_id(self.so), "hull_name"), "Cruiser")


if __name__ == "__main__":
    unittest.main()
