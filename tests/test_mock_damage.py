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
from tests.reset_helper import reset_mock


def _drain():
    """Drain queued physics events, dropping the trailing options dict that damage
    events carry (e.g. {"sub_float": amount}) so these routing assertions stay focused
    on (tag, sub_tag, source, target). See test_damage_carries_amount_and_kind for the
    payload itself."""
    out = []
    while True:
        try:
            ev = sbs._pending_physics_events.get_nowait()
        except Exception:
            break
        if ev and isinstance(ev[-1], dict):
            ev = ev[:-1]
        out.append(ev)
    return out


def _drain_raw():
    out = []
    while True:
        try:
            out.append(sbs._pending_physics_events.get_nowait())
        except Exception:
            break
    return out


class TestMockDamage(unittest.TestCase):
    def setUp(self):
        self.sim = reset_mock(sbs)
        _drain()

    def tearDown(self):
        # set_beam_damages persists globally; reset so it doesn't affect other tests.
        sbs._beam_dmg_player = sbs._beam_dmg_npc = sbs._beam_dmg_station = None

    def _hulled(self, hp=100, abits=0x10, station=None):
        # Generic hull target. Armor is a STATION-only field in the engine, so a
        # non-player hull target is marked a station (armor death model) by default;
        # pass station=False for an NPC-ship firer (so its beam base is the NPC one).
        oid = self.sim.create_space_object("behav", "", abits)
        o = self.sim.space_objects[oid]
        o.data_set.set("armorMax", float(hp))
        o.data_set.set("armor", float(hp))
        mark = (not (abits & 0x20)) if station is None else station
        if mark:
            if Agent.get(oid) is None:
                ag = Agent(); ag.id = oid; ag.add()
            Agent.get(oid).add_role("station")
        return oid, o

    def _npc_ship(self, sys_max=4):
        # NPC ship: no armor; dies via system damage across the 4 SHPSYS.
        oid = self.sim.create_space_object("behav_npcship", "", 0x10)
        o = self.sim.space_objects[oid]
        for i in range(4):
            o.data_set.set("system_max_damage", float(sys_max), i)
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

    def test_damage_carries_amount_and_kind(self):
        # The damage event's trailing options dict carries sub_float (hit amount) and
        # the sub_tag carries the weapon kind, so //damage routes read EVENT.sub_float
        # / EVENT.sub_tag in the mock like the engine. The runner unpacks the dict onto
        # the FakeEvent (see mission_runner._drain_physics_events).
        oid, o = self._hulled(100)
        _drain_raw()
        sbs.apply_damage(oid, 30, source_id=999, kind="beam")
        ev = _drain_raw()
        self.assertEqual(ev, [("damage", "beam", 999, oid, {"sub_float": 30.0})])
        # Fatal hit keeps "destroyed" as sub_tag (the //damage/destroy signal) but
        # still reports the amount.
        oid2, o2 = self._hulled(10)
        _drain_raw()
        sbs.apply_damage(oid2, 25, source_id=999, kind="beam")
        ev2 = _drain_raw()
        self.assertEqual(ev2[0], ("damage", "destroyed", 999, oid2, {"sub_float": 25.0}))

    def test_npc_ship_destroyed_via_systems(self):
        # NPC ship has no armor; a lethal hit maxes all 4 SHPSYS -> npc_killed.
        oid, o = self._npc_ship(sys_max=4)
        _drain()
        sbs.apply_damage(oid, 1000, source_id=999)
        ev = _drain()
        self.assertEqual(ev, [
            ("damage", "destroyed", 999, oid),
            ("npc_killed", "", oid, oid),
        ])
        self.assertNotIn(oid, self.sim.space_objects)

    def test_npc_ship_partial_system_damage(self):
        # A non-lethal hit fills some system nodes (amount / _SYSTEM_NODE_HP),
        # spread across systems, and emits a plain damage event.
        oid, o = self._npc_ship(sys_max=4)
        _drain()
        sbs.apply_damage(oid, 12, source_id=1)            # 12 / 6 = 2 nodes
        self.assertEqual(_drain(), [("damage", "", 1, oid)])
        total = sum(o.data_set.get("system_damage", i) or 0 for i in range(4))
        self.assertEqual(total, 2)
        self.assertIn(oid, self.sim.space_objects)

    def test_npc_hull_scales_with_hullpoints(self):
        # Ship hullpoints is a small tier (~1-8) used as the per-SHPSYS node count,
        # so a ship dies after 4 x hullpoints nodes and heavier hulls soak more.
        oid = self.sim.create_space_object("behav_npcship", "", 0x10)
        o = self.sim.space_objects[oid]
        sbs._apply_ship_data_to_object(o, {"hullpoints": 8})
        caps = [o.data_set.get("system_max_damage", i) or 0 for i in range(4)]
        self.assertEqual(caps, [8.0, 8.0, 8.0, 8.0])       # 32 nodes total
        # A lighter hull -> fewer nodes -> dies faster.
        oid2 = self.sim.create_space_object("behav_npcship", "", 0x10)
        o2 = self.sim.space_objects[oid2]
        sbs._apply_ship_data_to_object(o2, {"hullpoints": 3})
        caps2 = [o2.data_set.get("system_max_damage", i) or 0 for i in range(4)]
        self.assertEqual(caps2, [3.0, 3.0, 3.0, 3.0])      # 12 nodes
        self.assertLess(sum(caps2), sum(caps))

    def test_npc_hull_falls_back_to_flat_16_without_hullpoints(self):
        oid = self.sim.create_space_object("behav_npcship", "", 0x10)
        o = self.sim.space_objects[oid]
        sbs._apply_ship_data_to_object(o, {})              # no hullpoints
        caps = [o.data_set.get("system_max_damage", i) or 0 for i in range(4)]
        self.assertEqual(sum(caps), 16)                    # flat 4 x 4

    def test_shields_per_facing_not_pooled(self):
        # Engine-like: a hit lands on ONE facing (toward the attacker) and only its
        # overflow reaches hull - the OTHER facing stays up. A hit bigger than the hit
        # facing but smaller than the total still leaks to hull (no pooling).
        oid, o = self._npc_ship(sys_max=4)
        o.data_set.set("shield_count", 2)
        o.data_set.set("shield_val", 120.0, 0); o.data_set.set("shield_max_val", 120.0, 0)
        o.data_set.set("shield_val", 120.0, 1); o.data_set.set("shield_max_val", 120.0, 1)
        # Attacker dead ahead -> hits the front facing (index 0).
        sid = self.sim.create_space_object("behav_npcship", "", 0x10)
        s = self.sim.space_objects[sid]; o._pos = sbs.vec3(0, 0, 0); s._pos = sbs.vec3(0, 0, 500)
        _drain()
        sbs.apply_damage(oid, 150, source_id=sid)          # > facing0 (120), < total (240)
        self.assertEqual(_drain(), [("damage", "", sid, oid)])
        self.assertEqual(o.data_set.get("shield_val", 0), 0.0)    # hit facing drained
        self.assertEqual(o.data_set.get("shield_val", 1), 120.0)  # far facing UNTOUCHED
        # 150 - 120 = 30 overflow -> 5 system nodes (30 / _SYSTEM_NODE_HP)
        self.assertEqual(sum(o.data_set.get("system_damage", i) or 0 for i in range(4)), 5)
        self.assertIn(oid, self.sim.space_objects)

    def test_hit_facing_picks_facing_by_bearing(self):
        # Attacker ahead -> front facing (0); behind -> rear facing (1) on a 2-facing ship.
        tid, t = self._npc_ship(sys_max=4); t._pos = sbs.vec3(0, 0, 0)   # faces +z by default
        ahead = self.sim.create_space_object("behav_npcship", "", 0x10)
        self.sim.space_objects[ahead]._pos = sbs.vec3(0, 0, 500)
        behind = self.sim.create_space_object("behav_npcship", "", 0x10)
        self.sim.space_objects[behind]._pos = sbs.vec3(0, 0, -500)
        self.assertEqual(sbs._hit_facing(t, self.sim.space_objects[ahead], 2), 0)
        self.assertEqual(sbs._hit_facing(t, self.sim.space_objects[behind], 2), 1)
        self.assertEqual(sbs._hit_facing(t, None, 2), 0)                 # unknown -> front
        self.assertEqual(sbs._hit_facing(t, self.sim.space_objects[behind], 1), 0)  # single facing

    def test_shield_overflow_hits_hull(self):
        # Overflow past the hit facing spills into system damage.
        oid, o = self._npc_ship(sys_max=4)
        o.data_set.set("shield_count", 2)
        o.data_set.set("shield_val", 50.0, 0)
        o.data_set.set("shield_val", 50.0, 1)
        _drain()
        sbs.apply_damage(oid, 50 + 12, source_id=0)        # source 0 -> facing 0; 50 shield + 12 hull
        self.assertEqual(_drain(), [("damage", "", 0, oid)])
        self.assertEqual(o.data_set.get("shield_val", 0), 0.0)
        self.assertEqual(o.data_set.get("shield_val", 1), 50.0)   # other facing stays up
        self.assertEqual(sum(o.data_set.get("system_damage", i) or 0 for i in range(4)), 2)

    def test_offense_factor_degrades_with_system_damage(self):
        # Death spiral: offense scales linearly with surviving system health,
        # floored at _OFFENSE_FLOOR.
        oid, o = self._npc_ship(sys_max=4)                 # 16 nodes
        self.assertEqual(sbs._offense_factor(o), 1.0)      # undamaged -> full
        for i in range(4):
            o.data_set.set("system_damage", 2.0, i)        # 8 / 16 damaged
        self.assertAlmostEqual(sbs._offense_factor(o), 0.5)
        for i in range(4):
            o.data_set.set("system_damage", 4.0, i)        # nearly destroyed
        self.assertEqual(sbs._offense_factor(o), sbs._OFFENSE_FLOOR)

    def test_offense_factor_station_uses_armor(self):
        oid, o = self._hulled(100)                          # armorMax 100, armor 100
        self.assertEqual(sbs._offense_factor(o), 1.0)
        o.data_set.set("armor", 40.0)
        self.assertAlmostEqual(sbs._offense_factor(o), 0.4)

    def test_damaged_firer_deals_less_beam_damage(self):
        # A half-wrecked NPC firer lands ~half the damage of a healthy one (death
        # spiral). Asserted relatively, so it's independent of the absolute base.
        def fire_once(sysdmg):
            tid, t = self._hulled(100); t._pos = sbs.vec3(0, 0, 500)
            nid = self.sim.create_space_object("behav_npcship", "", 0x10)
            n = self.sim.space_objects[nid]; n._pos = sbs.vec3(0, 0, 0)
            for i in range(4):
                n.data_set.set("system_max_damage", 4.0, i)
                n.data_set.set("system_damage", sysdmg, i)
            n.data_set.set("beamCount", 1); n.data_set.set("beamRange", 1000.0)
            n.data_set.set("beamDamage", 6.0); n.data_set.set("weapon_target_UID", tid)
            _drain()
            sbs._physics_beams(self.sim, [(nid, n), (tid, t)], dt=0.5)
            return 100.0 - (t.data_set.get("armor") or 0.0)
        full = fire_once(0.0)            # healthy firer
        half = fire_once(2.0)            # 50% system health
        self.assertGreater(full, 0.0)
        self.assertAlmostEqual(half, full * 0.5, delta=0.1)

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
        self.assertEqual(tags.count("passive_collision_start"), 1)   # terrain: one event
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
        self.assertIn(("damage", "beam", aid, tid), ev)   # sub_tag = weapon kind
        self.assertEqual(t.data_set.get("armor"), 72.5)   # 100 - (30/6)*5.5 NPC base
        # cooldown engaged -> no fire next tick
        sbs._physics_beams(self.sim, [(aid, a), (tid, t)], dt=0.5)
        self.assertEqual(_drain(), [])
        self.assertEqual(t.data_set.get("armor"), 72.5)

    def test_beam_out_of_range_no_fire(self):
        tid, t = self._hulled(100)
        t._pos = sbs.vec3(5000, 0, 0)             # outside range 1000
        aid, a = self._beamer(tid, rng=1000, dmg=30)
        _drain()
        sbs._physics_beams(self.sim, [(aid, a), (tid, t)], dt=0.5)
        self.assertEqual(_drain(), [])
        self.assertEqual(t.data_set.get("armor"), 100.0)

    def test_beam_kills_target(self):
        tid, t = self._hulled(20)                 # low hull (station)
        t._pos = sbs.vec3(500, 0, 0)
        aid, a = self._beamer(tid, rng=1000, dmg=30)
        _drain()
        sbs._physics_beams(self.sim, [(aid, a), (tid, t)], dt=0.5)
        self.assertEqual(self._tags(_drain()), ["damage", "station_killed"])
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
        self.assertIn(("damage", "beam", aid, tid), _drain())
        self.assertEqual(t.data_set.get("armor"), 72.5)   # 100 - (30/6)*5.5 NPC base

    def test_beam_in_arc_fires(self):
        tid, t = self._hulled(100); t._pos = sbs.vec3(0, 0, 500)   # in front, +Z
        aid, a = self._beamer(tid, rng=1000, dmg=30)
        a.data_set.set("beamArcWidth", 90.0)                       # narrow forward arc
        _drain()
        sbs._physics_beams(self.sim, [(aid, a), (tid, t)], dt=0.5)
        self.assertIn(("damage", "beam", aid, tid), _drain())

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
        nid, n = self._hulled(100, abits=0x10, station=False); n._pos = sbs.vec3(0, 0, 0)
        n.data_set.set("beamCount", 1); n.data_set.set("beamRange", 1000.0)
        n.data_set.set("beamDamage", 3.0); n.data_set.set("weapon_target_UID", tid2)
        _drain()
        sbs._physics_beams(self.sim, [(nid, n), (tid2, t2)], dt=0.5)
        self.assertEqual(t2.data_set.get("armor"), 98.0)          # 100 - 2

    def test_beam_fallback_uses_calibrated_category_base(self):
        # No set_beam_damages call -> per-shot = coeff * the engine's default base
        # (calibrated): NPC ~5.5, player ~8.5. coeff 1.0 here (beamDamage = load base).
        # NPC firer (abits 0x10):
        tid, t = self._hulled(100); t._pos = sbs.vec3(0, 0, 500)
        nid, n = self._hulled(100, abits=0x10, station=False); n._pos = sbs.vec3(0, 0, 0)
        n.data_set.set("beamCount", 1); n.data_set.set("beamRange", 1000.0)
        n.data_set.set("beamDamage", sbs._BEAM_LOAD_BASE)         # coeff 1.0
        n.data_set.set("weapon_target_UID", tid)
        _drain()
        sbs._physics_beams(self.sim, [(nid, n), (tid, t)], dt=0.5)
        self.assertAlmostEqual(t.data_set.get("armor"), 100 - sbs._BEAM_DEFAULT_NPC, delta=0.01)
        # Player firer (abits 0x20) hits harder:
        tid2, t2 = self._hulled(100); t2._pos = sbs.vec3(0, 0, 500)
        pid, p = self._hulled(100, abits=0x20); p._pos = sbs.vec3(0, 0, 0)
        p.data_set.set("beamCount", 1); p.data_set.set("beamRange", 1000.0)
        p.data_set.set("beamDamage", sbs._BEAM_LOAD_BASE)         # coeff 1.0
        p.data_set.set("weapon_target_UID", tid2)
        _drain()
        sbs._physics_beams(self.sim, [(pid, p), (tid2, t2)], dt=0.5)
        self.assertAlmostEqual(t2.data_set.get("armor"), 100 - sbs._BEAM_DEFAULT_PLAYER, delta=0.01)

    def test_heat_static_without_coolant_or_overpower(self):
        # Engine-calibrated (capture_heat): NO passive decay. With no overpower and no
        # coolant, heat holds - coolant is the only heat sink.
        aid, a = self._hulled(100)
        a.data_set.set("system_cur_heat", 0.6, 0)
        sbs._physics_heat([(aid, a)], dt=1.0)
        self.assertAlmostEqual(a.data_set.get("system_cur_heat", 0), 0.6, delta=1e-6)

    def test_coolant_cools_without_overpower(self):
        # Coolant removes heat even with no overpower (~_HEAT_COOL per unit per sec).
        aid, a = self._hulled(100)
        a.data_set.set("system_cur_heat", 0.5, 0)
        a.data_set.set("system_coolant_used", 3, 0)
        sbs._physics_heat([(aid, a)], dt=1.0)
        self.assertAlmostEqual(a.data_set.get("system_cur_heat", 0),
                               0.5 - 3 * sbs._HEAT_COOL, delta=1e-6)

    def test_overpower_300_caps_overpower(self):
        # Past 300% the engine goes sub-linear and the console can't exceed it, so the
        # mock clamps overpower at 2.0: value 5.0 heats the same as value 3.0.
        aid, a = self._hulled(100)
        a.data_set.set("eng_control_type_index", 0, 0)
        a.data_set.set("eng_control_value", 5.0, 0)        # 500% -> clamped to 300%
        sbs._physics_heat([(aid, a)], dt=1.0)
        self.assertAlmostEqual(a.data_set.get("system_cur_heat", 0),
                               sbs._HEAT_OVERPOWER_MAX * sbs._HEAT_GAIN, delta=1e-6)

    def test_overpower_raises_system_heat(self):
        # Engineering pushing a control above 100% heats the SHPSYS it feeds
        # (eng_control_type_index); other systems are untouched.
        aid, a = self._hulled(100)
        a.data_set.set("eng_control_value", 2.0, 0)        # 200%
        a.data_set.set("eng_control_type_index", 1, 0)     # feeds SHPSYS 1
        sbs._physics_heat([(aid, a)], dt=1.0)
        # net = overpower(1.0)*GAIN - 0 coolant - DECAY
        self.assertAlmostEqual(a.data_set.get("system_cur_heat", 1),
                               max(0.0, sbs._HEAT_GAIN - sbs._HEAT_DECAY), delta=1e-6)
        self.assertEqual(a.data_set.get("system_cur_heat", 0) or 0.0, 0.0)

    def test_coolant_offsets_overpower_heat(self):
        aid, a = self._hulled(100)
        a.data_set.set("eng_control_value", 3.0, 0)        # 300% -> overpower 2.0
        a.data_set.set("eng_control_type_index", 0, 0)
        a.data_set.set("system_coolant_used", 2, 0)        # 2 coolant units
        sbs._physics_heat([(aid, a)], dt=1.0)
        expected = max(0.0, 2.0 * sbs._HEAT_GAIN - 2 * sbs._HEAT_COOL - sbs._HEAT_DECAY)
        self.assertAlmostEqual(a.data_set.get("system_cur_heat", 0), expected, delta=1e-6)

    def test_sustained_overheat_fires_repeatedly(self):
        # While a system stays overheated, //damage/heat fires every interval (the
        # mission applies damage; the mock just keeps notifying). The mock does NOT
        # write system_damage itself.
        aid, a = self._hulled(100)
        a.data_set.set("system_cur_heat", 1.0, 2)
        a.data_set.set("eng_control_value", 3.0, 0)        # keep it pinned at full heat
        a.data_set.set("eng_control_type_index", 2, 0)
        _drain()
        fires = 0
        for _ in range(6):                                 # 6 x 0.5s = 3s ~ 3 intervals
            sbs._physics_heat([(aid, a)], dt=0.5)
            fires += sum(1 for e in _drain() if e[0] == "heat_critical_damage" and e[1] == "2")
        self.assertGreaterEqual(fires, 3)
        self.assertEqual(a.data_set.get("system_damage", 2) or 0.0, 0.0)  # mock doesn't damage

    def test_shield_regen_is_slow(self):
        # Single facing: regens at the full repair_rate_shields/s.
        aid, a = self._hulled(100)
        a.data_set.set("shield_count", 1)
        a.data_set.set("shield_max_val", 100.0, 0)
        a.data_set.set("shield_val", 40.0, 0)
        a.data_set.set("repair_rate_shields", 1.0)        # ~1/s, like the player
        sbs.resume_sim()
        for _ in range(60):                               # ~2 sim seconds
            sbs.physics_tick(1 / 30)
        sv = a.data_set.get("shield_val", 0)
        self.assertAlmostEqual(sv, 42.0, delta=0.3)       # ~ +1/s
        self.assertLessEqual(sv, 100.0)                   # clamped to max

    def test_shield_regen_divides_rate_across_facings(self):
        # The engine spreads repair_rate_shields across facings (measured): a 2-facing
        # ship with repair 1.0 regens a damaged facing at ~0.5/s, not the full 1.0/s.
        aid, a = self._hulled(100)
        a.data_set.set("shield_count", 2)
        for i in range(2):
            a.data_set.set("shield_max_val", 100.0, i)
        a.data_set.set("shield_val", 40.0, 0)             # facing 0 damaged
        a.data_set.set("shield_val", 100.0, 1)            # facing 1 full
        a.data_set.set("repair_rate_shields", 1.0)
        sbs.resume_sim()
        for _ in range(60):                               # ~2 sim seconds
            sbs.physics_tick(1 / 30)
        self.assertAlmostEqual(a.data_set.get("shield_val", 0), 41.0, delta=0.3)  # ~ +0.5/s
        self.assertLessEqual(a.data_set.get("shield_val", 1), 100.0)              # clamped


if __name__ == '__main__':
    unittest.main()
