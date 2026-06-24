"""
Mock hull-damage model tests (Tier A1).

Pins the events the mock emits for damage/destruction so handlerhooks routes
them correctly:
  - non-fatal hit            -> "damage"            (origin=source, selected=target)
  - fatal hit                -> "damage"/"destroyed" (//damage/destroy + removal)
                                + "npc_killed" or "station_killed" (//damage/killed)
Hull lives in data_set "armor"; only objects with armorMax>0 are damageable.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest
import cosmos_dev.mock.sbs as sbs
from sbs_utils.agent import Agent, clear_shared


def _drain():
    out = []
    while True:
        try:
            out.append(sbs._pending_physics_events.get_nowait())
        except Exception:
            break
    return out


class TestMockDamage(unittest.TestCase):
    def setUp(self):
        Agent.clear()
        clear_shared()
        sbs.create_new_sim()
        self.sim = sbs.sim
        sbs._contact_pairs.clear()
        _drain()

    def _hulled(self, hp=100, abits=0x10):
        oid = self.sim.create_space_object("behav", "", abits)
        o = self.sim.space_objects[oid]
        o.data_set.set("armorMax", float(hp))
        o.data_set.set("armor", float(hp))
        return oid, o

    @staticmethod
    def _tags(ev):
        return [e[0] for e in ev]

    def test_non_fatal_damage(self):
        oid, o = self._hulled(100)
        _drain()
        sbs.apply_damage(oid, 30, source_id=999)
        ev = _drain()
        self.assertEqual(ev, [("damage", "", 999, oid)])
        self.assertEqual(o.data_set.get("armor"), 70.0)
        self.assertIn(oid, self.sim.space_objects)        # still alive

    def test_fatal_npc_killed(self):
        oid, o = self._hulled(50)
        _drain()
        sbs.apply_damage(oid, 80, source_id=999)
        ev = _drain()
        self.assertEqual(ev, [
            ("damage", "destroyed", 999, oid),            # -> //damage/destroy + remove agent
            ("npc_killed", "", oid, oid),                 # -> //damage/killed
        ])
        self.assertNotIn(oid, self.sim.space_objects)     # removed from sim

    def test_fatal_station_killed(self):
        oid, o = self._hulled(50)
        a = Agent(); a.id = oid; a.add(); a.add_role("station")
        _drain()
        sbs.apply_damage(oid, 80)
        ev = _drain()
        self.assertEqual(ev, [
            ("damage", "destroyed", 0, oid),
            ("station_killed", "", oid, oid),
        ])

    def test_no_hull_is_invulnerable(self):
        oid = self.sim.create_space_object("behav", "", 0x10)  # no armorMax
        _drain()
        sbs.apply_damage(oid, 9999)
        self.assertEqual(_drain(), [])
        self.assertIn(oid, self.sim.space_objects)

    def test_mine_collision_applies_damage(self):
        aid, a = self._hulled(100)
        a._pos = sbs.vec3(0, 0, 0); a._exclusion_radius = 100
        mid = self.sim.create_space_object("behav_mine", "", 0x00)  # terrain
        m = self.sim.space_objects[mid]
        m._pos = sbs.vec3(50, 0, 0); m._exclusion_radius = 100
        m.data_set.set("damage_done", 25)
        _drain()
        sbs._physics_collision(self.sim, [(aid, a)])
        tags = self._tags(_drain())
        self.assertEqual(tags.count("passive_collision_start"), 2)
        self.assertIn("damage", tags)
        self.assertEqual(a.data_set.get("armor"), 75.0)

    def test_plain_asteroid_collision_no_damage(self):
        aid, a = self._hulled(100)
        a._pos = sbs.vec3(0, 0, 0); a._exclusion_radius = 100
        rid = self.sim.create_space_object("behav_asteroid", "", 0x00)
        r = self.sim.space_objects[rid]
        r._pos = sbs.vec3(50, 0, 0); r._exclusion_radius = 100   # no damage_done
        _drain()
        sbs._physics_collision(self.sim, [(aid, a)])
        tags = self._tags(_drain())
        self.assertNotIn("damage", tags)
        self.assertEqual(a.data_set.get("armor"), 100.0)


if __name__ == '__main__':
    unittest.main()
