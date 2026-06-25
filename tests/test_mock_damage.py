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

    def tearDown(self):
        # set_beam_damages persists globally; reset so it doesn't affect other tests.
        sbs._beam_dmg_player = sbs._beam_dmg_npc = sbs._beam_dmg_station = None

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

    # --- beams -------------------------------------------------------------
    def _beamer(self, target_id, rng=1000, dmg=30, cycle=6.0):
        aid, a = self._hulled(100)
        a._pos = sbs.vec3(0, 0, 0)
        a.data_set.set("beamCount", 1)
        a.data_set.set("beamRange", float(rng))
        a.data_set.set("beamDamage", float(dmg))
        a.data_set.set("beamCycleTime", float(cycle))
        a.data_set.set("target_id", target_id)
        return aid, a

    def test_beam_fires_at_target_in_range(self):
        tid, t = self._hulled(100)
        t._pos = sbs.vec3(500, 0, 0)              # within range 1000
        aid, a = self._beamer(tid, rng=1000, dmg=30)
        _drain()
        sbs._physics_beams(self.sim, [(aid, a), (tid, t)], dt=0.5)
        ev = _drain()
        self.assertIn(("damage", "", aid, tid), ev)
        self.assertEqual(t.data_set.get("armor"), 70.0)
        # cooldown engaged -> no fire next tick
        sbs._physics_beams(self.sim, [(aid, a), (tid, t)], dt=0.5)
        self.assertEqual(_drain(), [])
        self.assertEqual(t.data_set.get("armor"), 70.0)

    def test_beam_out_of_range_no_fire(self):
        tid, t = self._hulled(100)
        t._pos = sbs.vec3(5000, 0, 0)             # outside range 1000
        aid, a = self._beamer(tid, rng=1000, dmg=30)
        _drain()
        sbs._physics_beams(self.sim, [(aid, a), (tid, t)], dt=0.5)
        self.assertEqual(_drain(), [])
        self.assertEqual(t.data_set.get("armor"), 100.0)

    def test_beam_kills_target(self):
        tid, t = self._hulled(20)                 # low hull
        t._pos = sbs.vec3(500, 0, 0)
        aid, a = self._beamer(tid, rng=1000, dmg=30)
        _drain()
        sbs._physics_beams(self.sim, [(aid, a), (tid, t)], dt=0.5)
        self.assertEqual(self._tags(_drain()), ["damage", "npc_killed"])
        self.assertNotIn(tid, self.sim.space_objects)

    def test_beam_no_target_no_fire(self):
        aid, a = self._beamer(0)                  # target_id 0
        _drain()
        sbs._physics_beams(self.sim, [(aid, a)], dt=0.5)
        self.assertEqual(_drain(), [])

    def test_beam_uses_weapon_target_uid(self):
        # player-style: weapon_target_UID set (no target_id) -> still fires
        tid, t = self._hulled(100); t._pos = sbs.vec3(0, 0, 500)   # dead ahead (+Z)
        aid, a = self._hulled(100); a._pos = sbs.vec3(0, 0, 0)
        a.data_set.set("beamCount", 1)
        a.data_set.set("beamRange", 1000.0)
        a.data_set.set("beamDamage", 30.0)
        a.data_set.set("weapon_target_UID", tid)
        _drain()
        sbs._physics_beams(self.sim, [(aid, a), (tid, t)], dt=0.5)
        self.assertIn(("damage", "", aid, tid), _drain())
        self.assertEqual(t.data_set.get("armor"), 70.0)

    def test_beam_in_arc_fires(self):
        tid, t = self._hulled(100); t._pos = sbs.vec3(0, 0, 500)   # in front, +Z
        aid, a = self._beamer(tid, rng=1000, dmg=30)
        a.data_set.set("beamArcWidth", 90.0)                       # narrow forward arc
        _drain()
        sbs._physics_beams(self.sim, [(aid, a), (tid, t)], dt=0.5)
        self.assertIn(("damage", "", aid, tid), _drain())

    def test_beam_out_of_arc_no_fire(self):
        tid, t = self._hulled(100); t._pos = sbs.vec3(500, 0, 0)   # 90 deg off forward (+X)
        aid, a = self._beamer(tid, rng=1000, dmg=30)
        a.data_set.set("beamArcWidth", 90.0)                       # forward arc -> target outside
        _drain()
        sbs._physics_beams(self.sim, [(aid, a), (tid, t)], dt=0.5)
        self.assertEqual(_drain(), [])
        self.assertEqual(t.data_set.get("armor"), 100.0)

    def test_system_overheat_fires_heat_critical(self):
        # System heat is engineering (system_cur_heat), not combat: driving a
        # system past critical fires heat_critical_damage with that SHPSYS index.
        aid, a = self._hulled(100)
        a.data_set.set("system_cur_heat", 1.5, 0)   # WEAPONS system overheated
        _drain()
        sbs._physics_heat([(aid, a)], dt=0.1)
        self.assertIn(("heat_critical_damage", "0", aid, aid), _drain())

    def test_set_beam_damages_base_times_coeff(self):
        # set_beam_damages makes per-shot = category base * per-beam coeff, where
        # coeff = beamDamage / _BEAM_LOAD_BASE (beamDamage is coeff*base at load).
        sbs.set_beam_damages(0, 7.0, 4.0, 2.0)
        # player firer (abits 0x20), coeff 1.0 (beamDamage 6.0) -> 7*1 = 7
        tid, t = self._hulled(100); t._pos = sbs.vec3(0, 0, 500)
        pid, p = self._hulled(100, abits=0x20); p._pos = sbs.vec3(0, 0, 0)
        p.data_set.set("beamCount", 1); p.data_set.set("beamRange", 1000.0)
        p.data_set.set("beamDamage", 6.0); p.data_set.set("weapon_target_UID", tid)
        _drain()
        sbs._physics_beams(self.sim, [(pid, p), (tid, t)], dt=0.5)
        self.assertEqual(t.data_set.get("armor"), 93.0)           # 100 - 7
        # npc firer (abits 0x10), coeff 0.5 (beamDamage 3.0) -> 4*0.5 = 2
        tid2, t2 = self._hulled(100); t2._pos = sbs.vec3(0, 0, 500)
        nid, n = self._hulled(100, abits=0x10); n._pos = sbs.vec3(0, 0, 0)
        n.data_set.set("beamCount", 1); n.data_set.set("beamRange", 1000.0)
        n.data_set.set("beamDamage", 3.0); n.data_set.set("weapon_target_UID", tid2)
        _drain()
        sbs._physics_beams(self.sim, [(nid, n), (tid2, t2)], dt=0.5)
        self.assertEqual(t2.data_set.get("armor"), 98.0)          # 100 - 2

    def test_beam_falls_back_to_beamDamage_without_set_beam_damages(self):
        # No set_beam_damages call -> beamDamage used as-is (unit tests rely on this).
        tid, t = self._hulled(100); t._pos = sbs.vec3(0, 0, 500)
        aid, a = self._beamer(tid, rng=1000, dmg=30)
        _drain()
        sbs._physics_beams(self.sim, [(aid, a), (tid, t)], dt=0.5)
        self.assertEqual(t.data_set.get("armor"), 70.0)           # 100 - 30 (beamDamage)

    def test_system_heat_decays(self):
        aid, a = self._hulled(100)
        a.data_set.set("system_cur_heat", 0.6, 0)
        sbs._physics_heat([(aid, a)], dt=1.0)
        self.assertAlmostEqual(a.data_set.get("system_cur_heat", 0), 0.6 - sbs._HEAT_DECAY)


if __name__ == '__main__':
    unittest.main()
