"""Tests for a2x_set_object_property (2.8 property -> Cosmos data_set/engine)."""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import cosmos_dev.mock.sbs as sbs
from tests.reset_helper import reset_mock
from sbs_utils.procedural.a2x.props import (
    set_object_property, object_property, object_property_mapped, object_property_key,
    set_special, special_ability_mapped,
    addto_object_property, copy_object_property, set_ship_text,
    set_relative_position, set_fleet_coeff, fleet_coeff_mapped, set_side_value,
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

    def test_object_property_reads_back(self):
        # the read counterpart of set_object_property: data slot, array index, engine attr
        set_object_property(self.so, "energy", 250)
        self.assertEqual(object_property(self.so, "energy"), 250)
        set_object_property(self.so, "shieldStateBack", 80)
        self.assertEqual(object_property(self.so, "shieldStateBack"), 80)
        set_object_property(self.so, "rollDelta", 0.003)
        self.assertAlmostEqual(object_property(self.so, "rollDelta"), 0.003)

    def test_object_property_pos_flip_roundtrips(self):
        # positionX is coordinate-flipped on both set and read; a round-trip is identity
        set_object_property(self.so, "positionX", 12345)
        self.assertEqual(object_property(self.so, "positionX"), 12345)

    def test_object_property_unmapped_is_none(self):
        self.assertIsNone(object_property(self.so, "surrenderChance"))

    def test_top_speed_maps_to_speed_coeff(self):
        # 2.8 topSpeed (already a 0-1 coeff) -> the NPC speed_coeff, 1:1
        self.assertTrue(set_object_property(self.so, "topSpeed", 0.5))
        self.assertEqual(get_data_set_value(to_id(self.so), "speed_coeff"), 0.5)
        self.assertEqual(object_property(self.so, "topSpeed"), 0.5)

    def test_turn_rate_uses_engine_key(self):
        # regression: engine steering reads "turn_rate", NOT the old dead "turnRate" key
        self.assertTrue(set_object_property(self.so, "turnRate", 0.3))
        self.assertEqual(get_data_set_value(to_id(self.so), "turn_rate"), 0.3)
        self.assertIn(get_data_set_value(to_id(self.so), "turnRate"), (None, 0, 0.0))

    def test_current_real_speed_reads_object_speed(self):
        # currentRealSpeed reads the physics-driven space_object.cur_speed (read side)
        to_object(self.so).cur_speed = 42.0
        self.assertEqual(object_property(self.so, "currentRealSpeed"), 42.0)

    def test_torpedo_type_stores(self):
        # PShock / Tag are LM torpedo types now; ECM ~ EMP; Shk = plasma shock
        for prop, key in (("missileStoresPShock", "PShock_NUM"), ("missileStoresTag", "Tag_NUM"),
                          ("missileStoresECM", "EMP_NUM"), ("countShk", "PShock_NUM")):
            self.assertTrue(set_object_property(self.so, prop, 4))
            self.assertEqual(get_data_set_value(to_id(self.so), key), 4)

    def test_push_radius_maps_to_exclusion_radius(self):
        self.assertTrue(set_object_property(self.so, "pushRadius", 250.0))
        self.assertEqual(to_object(self.so).exclusion_radius, 250.0)
        self.assertEqual(object_property(self.so, "pushRadius"), 250.0)

    def test_addto_obj_form(self):
        # addto on an obj-form prop (would IndexError before the "obj" branch)
        to_object(self.so).exclusion_radius = 100.0
        self.assertTrue(addto_object_property(self.so, "pushRadius", 50.0))
        self.assertEqual(to_object(self.so).exclusion_radius, 150.0)

    def test_set_special_ability_on(self):
        self.assertEqual(set_special(self.so, "LowVis", on=True), "elite_low_vis")
        self.assertEqual(get_data_set_value(to_id(self.so), "elite_low_vis"), 1)

    def test_set_special_ability_clear(self):
        set_special(self.so, "Drones", on=False)
        self.assertEqual(get_data_set_value(to_id(self.so), "elite_drone_launcher"), 0)

    def test_set_special_scripted_ability_adds_role(self):
        # Cloak is a scripted LM ability -> adds the elite/cloak role
        from sbs_utils.procedural.roles import has_role
        self.assertEqual(set_special(self.so, "Cloak"), "elite/cloak")
        self.assertTrue(has_role(to_id(self.so), "elite/cloak"))
        self.assertTrue(special_ability_mapped("HET"))

    def test_set_special_engine_ability_sets_flag(self):
        self.assertEqual(set_special(self.so, "LowVis"), "elite_low_vis")
        self.assertEqual(get_data_set_value(to_id(self.so), "elite_low_vis"), 1)

    def test_set_special_unknown_ability(self):
        self.assertIsNone(set_special(self.so, "NotAnAbility"))

    def test_addto_object_property(self):
        set_object_property(self.so, "energy", 100)
        self.assertTrue(addto_object_property(self.so, "energy", 50))
        self.assertEqual(get_data_set_value(to_id(self.so), "energy"), 150)

    def test_copy_object_property(self):
        b = create_enemy(0, 0, 0, "kralien_cruiser", name="Y")
        set_object_property(self.so, "shieldStateFront", 60)
        self.assertTrue(copy_object_property(self.so, b, "shieldStateFront"))
        self.assertEqual(get_data_set_value(to_id(b), "shield_val", 0), 60)

    def test_fleet_coeff_npc(self):
        # self.so is an NPC enemy; nonPlayerSpeed=200 -> speed_coeff 2.0 on all NPCs
        self.assertTrue(fleet_coeff_mapped("nonPlayerSpeed"))
        n = set_fleet_coeff("nonPlayerSpeed", 200)
        self.assertGreaterEqual(n, 1)
        self.assertAlmostEqual(get_data_set_value(to_id(self.so), "speed_coeff"), 2.0)

    def test_fleet_coeff_unknown(self):
        self.assertEqual(set_fleet_coeff("notAThing", 100), -1)

    def test_set_side_value(self):
        # self.so was created as side "enemy"; sideValue 2 -> "friendly"
        self.assertTrue(set_side_value(self.so, 2))
        self.assertEqual(to_object(self.so).side, "friendly")
        set_side_value(self.so, 1)
        self.assertEqual(to_object(self.so).side, "enemy")

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


class A2xTopSpeedBehaviorTests(unittest.TestCase):
    """Behavioral proof (against the reverse-engineered mock engine physics) that
    ``speed_coeff`` -- the key a2x maps 2.8 ``topSpeed`` to (see
    test_top_speed_maps_to_speed_coeff) -- actually scales an NPC's top speed:
    cruise = throttle * BASE_TOP_SPEED(36) * speed_coeff. (The mock keeps physics
    objects and a2x-queryable objects in separate worlds, so this drives a native
    physics NPC and sets speed_coeff directly; the key test proves the a2x half.)"""

    def setUp(self):
        self.sim = reset_mock(sbs)

    def _npc(self, speed_coeff):
        oid = self.sim.create_space_object("behav_npcship", "", 0x10)  # 0x10 = NPC
        o = self.sim.space_objects[oid]
        o._pos = sbs.vec3(0.0, 0.0, 0.0)
        ds = o.data_set
        ds.set("target_pos_x", 0.0); ds.set("target_pos_y", 0.0); ds.set("target_pos_z", 1e7)
        ds.set("throttle", 1.0); ds.set("turn_rate", 2.0)
        ds.set("speed_coeff", speed_coeff)                     # topSpeed maps here
        return o

    def test_speed_coeff_scales_npc_cruise(self):
        for coeff, expect in ((1.0, 36.0), (0.5, 18.0), (0.25, 9.0)):
            o = self._npc(coeff)
            for _ in range(3000):
                sbs._npcship_steer(o, 1 / 60)                  # engine speed model
            self.assertAlmostEqual(o.cur_speed, expect, delta=0.5,
                                   msg=f"speed_coeff={coeff} -> cur_speed {o.cur_speed}")


if __name__ == "__main__":
    unittest.main()
