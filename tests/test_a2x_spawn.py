"""Tests for a2x object creation: pure mappings + one mock-backed spawn."""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import cosmos_dev.mock.sbs as sbs
from tests.reset_helper import reset_mock
from sbs_utils.procedural.a2x.spawn import (
    pickup_key, monster_art, monster_role, create_enemy, create_monster,
    create_anomaly, destroy,
)
from sbs_utils.procedural.query import to_object, to_id
from sbs_utils.procedural.roles import has_role


class A2xSpawnPureTests(unittest.TestCase):
    def test_pickup_key_mapping(self):
        self.assertEqual(pickup_key(0), "hidens_powercell")
        self.assertEqual(pickup_key(4), "tauron_focuser")
        self.assertEqual(pickup_key(7), "secret_codecase")
        self.assertIsNone(pickup_key(8))  # beacon: no direct Cosmos pickup

    def test_monster_art_real_vs_placeholder(self):
        self.assertEqual(monster_art(0), "monster_charbdis")  # classic, real
        self.assertEqual(monster_art(8), "wreck")             # derelict, real
        self.assertEqual(monster_art(1), "monster_charbdis")  # whale -> placeholder

    def test_monster_role_seam(self):
        self.assertEqual(monster_role(1), "creature_whale")
        self.assertEqual(monster_role(8), "creature_derelict")
        self.assertEqual(monster_role(99), "creature_unknown")


class A2xSpawnMockTests(unittest.TestCase):
    def setUp(self):
        self.sim = reset_mock(sbs)

    def test_create_enemy_uses_flipped_coords(self):
        so = create_enemy(98000, 7, 98000, "biomech_a", name="TB1")
        obj = to_object(so)
        self.assertIsNotNone(obj)
        # 2.8 (98000,*,98000) mirrors to Cosmos (2000,*,2000)
        p = obj.engine_object.pos
        self.assertAlmostEqual(p.x, 2000, delta=1)
        self.assertAlmostEqual(p.z, 2000, delta=1)

    def test_create_monster_tags_creature_role(self):
        so = create_monster(70000, 0, 40000, monster_type=1, name="Willy")
        self.assertTrue(has_role(to_id(so), "creature_whale"))

    def test_destroy_issues_delete(self):
        # delete is deferred to GC, so just confirm destroy found the object and
        # issued the delete (returns True).
        so = create_enemy(0, 0, 0, "kralien_cruiser", name="Doomed")
        self.assertTrue(destroy(so))

    def test_destroy_missing_returns_false(self):
        self.assertFalse(destroy(123456789))

    def test_create_anomaly_spawns_via_core_pickup(self):
        # No item/ labels registered, so art falls back to placeholder, but the
        # pickup object must still spawn at the flipped coords with the upgrade key.
        so = create_anomaly(95000, 10, 50000, 0, name="Energy")
        obj = to_object(so)
        self.assertIsNotNone(obj)
        from sbs_utils.procedural.inventory import get_inventory_value
        self.assertEqual(get_inventory_value(to_id(so), "item_key"), "hidens_powercell")

    def test_create_anomaly_beacon_returns_none(self):
        self.assertIsNone(create_anomaly(0, 0, 0, 8))


class CorePickupSpawnTests(unittest.TestCase):
    def setUp(self):
        self.sim = reset_mock(sbs)

    def test_core_pickup_spawn_importable_and_works(self):
        # pickup_spawn now lives in core (moved from LegendaryMissions).
        from sbs_utils.procedural.items import pickup_spawn
        obj = pickup_spawn(0, 0, 0, "vigoranium_nodule")
        self.assertIsNotNone(obj)
        from sbs_utils.procedural.inventory import get_inventory_value
        self.assertEqual(get_inventory_value(obj.id, "item_key"), "vigoranium_nodule")


if __name__ == "__main__":
    unittest.main()
