"""
Mock projectile-weapon tests (missiles + drones).

Both missiles and drones are projectiles: launching emits the engine launch
event (so handlerhooks routes //launch/missile and //launch/drone) AND spawns a
homing projectile that deals hull damage on impact (via apply_damage).
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


class TestMockProjectiles(unittest.TestCase):
    def setUp(self):
        Agent.clear()
        clear_shared()
        sbs.create_new_sim()
        self.sim = sbs.sim
        _drain()

    def _hulled(self, hp=100, pos=(0, 0, 0)):
        # Armor target = a station (armor is station-only in the engine), so impacts
        # reduce armor and a lethal hit emits station_killed.
        oid = self.sim.create_space_object("behav", "", 0x10)
        o = self.sim.space_objects[oid]
        o.data_set.set("armorMax", float(hp))
        o.data_set.set("armor", float(hp))
        o._pos = sbs.vec3(*pos)
        if Agent.get(oid) is None:
            ag = Agent(); ag.id = oid; ag.add()
        Agent.get(oid).add_role("station")
        return oid, o

    # --- launch helpers emit the right events + register a projectile -------
    def test_launch_missile_event_and_impact(self):
        sid, s = self._hulled(pos=(0, 0, 0))
        tid, t = self._hulled(100, pos=(100, 0, 0))   # within hit radius
        _drain()
        sbs.launch_missile(sid, tid, damage=30)
        self.assertEqual(_drain(),
                         [("player_launches_missile", "", sid, tid, sid, "Homing")])
        self.assertEqual(len(sbs._projectiles), 1)
        sbs._physics_projectiles(self.sim, dt=0.5)        # impacts (close)
        # sub_tag = torp kind ("Homing"), sub_float = the hit amount.
        self.assertIn(("damage", "Homing", sid, tid, {"sub_float": 30.0}), _drain())
        self.assertEqual(t.data_set.get("armor"), 70.0)
        self.assertEqual(len(sbs._projectiles), 0)        # consumed

    def test_launch_drone_event(self):
        sid, s = self._hulled(pos=(0, 0, 0))
        tid, t = self._hulled(100, pos=(100, 0, 0))
        _drain()
        sbs.launch_drone(sid, tid, damage=15)
        self.assertEqual(_drain(),
                         [("ship_launches_drone", "", sid, tid, sid, "drone")])
        sbs._physics_projectiles(self.sim, dt=0.5)
        self.assertIn(("damage", "drone", sid, tid, {"sub_float": 15.0}), _drain())
        self.assertEqual(t.data_set.get("armor"), 85.0)

    def test_torp_profile_by_kind(self):
        # Per LM torpedo_prefabs (damage, blast_radius, effect): Homing 35 single-target;
        # Nuke/Mine a lingering 'blast' field (per_ripple 5); EMP one-shot 'emp' (0 hull).
        self.assertEqual(sbs._torp_profile("Homing"), (sbs._TORP_DAMAGE, 0.0, "single"))
        self.assertEqual(sbs._torp_profile("Nuke"), (sbs._TORP_BLAST_PER_RIPPLE, sbs._TORP_BLAST_RADIUS, "blast"))
        self.assertEqual(sbs._torp_profile("Mine"), (sbs._TORP_BLAST_PER_RIPPLE, sbs._TORP_BLAST_RADIUS, "blast"))
        self.assertEqual(sbs._torp_profile("EMP"), (0.0, sbs._TORP_BLAST_RADIUS, "emp"))

    def test_torp_profile_reads_mission_shared_string(self):
        # The mock reads each torp's definition from the engine shared string that
        # torpedo_type() writes, so a mission's custom def overrides the defaults
        # (decoupled from LegendaryMissions). Format: 'warhead:..;damage:..;...'.
        sbs.set_shared_string("Nuke", "warhead:blast;damage:9;blast_radius:500;behavior:homing;lifetime:8;")
        self.assertEqual(sbs._torp_profile("Nuke"), (9.0, 500.0, "blast"))
        # A standard custom torp (single hit -> no blast radius):
        sbs.set_shared_string("Zap", "warhead:standard;damage:42;")
        self.assertEqual(sbs._torp_profile("Zap"), (42.0, 0.0, "single"))
        # reduce_shields -> emp effect regardless of damage field:
        sbs.set_shared_string("Pulse", "warhead:blast,reduce_shields;damage:99;blast_radius:700;")
        self.assertEqual(sbs._torp_profile("Pulse"), (0.0, 700.0, "emp"))
        # No shared string -> LM-equivalent default (Homing single 35):
        self.assertEqual(sbs._torp_profile("Homing"), (sbs._TORP_DAMAGE, 0.0, "single"))

    def test_bad_torp_string_degrades_and_is_detectable(self):
        # A malformed torp def must not crash the mock: bad numerics fall back to the
        # default, unknown warheads degrade to a single hit - and torp_validate reports
        # the problems so a mission author can catch them.
        sbs.set_shared_string("Junk", "warhead:plasmaXX;damage:abc;blast_radius:nope;behavior:wat;")
        # _torp_profile must not raise; bad damage -> default, unknown warhead -> single
        dmg, radius, effect = sbs._torp_profile("Junk")
        self.assertEqual(effect, "single")
        self.assertEqual(dmg, sbs._TORP_DAMAGE)           # bad damage -> default
        problems = sbs.torp_validate("Junk")
        self.assertTrue(any("damage" in p for p in problems))
        self.assertTrue(any("warhead" in p for p in problems))
        self.assertTrue(any("behaviour" in p for p in problems))
        # A clean def reports no problems; an undefined one is fine (uses defaults).
        sbs.set_shared_string("Good", "warhead:blast;damage:5;blast_radius:1000;behavior:homing;")
        self.assertEqual(sbs.torp_validate("Good"), [])
        self.assertEqual(sbs.torp_validate("NeverDefined"), [])

    def test_emp_reduce_shields_halves_each_facing(self):
        # The EMP one-shot AoE halves each facing's CURRENT shields within the blast
        # radius (0 hull); ships outside the radius are untouched.
        nid, n = self._hulled(1000, pos=(0, 0, 0))        # in radius
        n.data_set.set("shield_count", 2)
        n.data_set.set("shield_val", 100.0, 0); n.data_set.set("shield_val", 60.0, 1)
        fid, f = self._hulled(1000, pos=(1500, 0, 0))     # outside 1000 radius
        f.data_set.set("shield_count", 1); f.data_set.set("shield_val", 80.0, 0)
        _drain()
        sbs._apply_emp(sbs.vec3(0, 0, 0), 1000.0, source_id=999)
        self.assertEqual(n.data_set.get("shield_val", 0), 50.0)   # halved
        self.assertEqual(n.data_set.get("shield_val", 1), 30.0)   # halved
        self.assertEqual(n.data_set.get("armor"), 1000)           # 0 hull
        self.assertEqual(f.data_set.get("shield_val", 0), 80.0)   # outside radius: untouched

    def test_blast_growing_ring_accumulates(self):
        # A lingering Nuke/Mine blast: the ring grows over the lifetime, so a centred
        # target is caught from the start and accumulates ~per_ripple*ripples (~120),
        # while an off-centre target is reached late by the ring and takes much less.
        cid, c = self._hulled(10000, pos=(0, 0, 0))       # at the epicentre
        oid, o = self._hulled(10000, pos=(800, 0, 0))     # off-centre (reached late)
        sbs._register_blast(sbs.vec3(0, 0, 0), sbs._TORP_BLAST_PER_RIPPLE, sbs._TORP_BLAST_RADIUS, 999)
        sbs.resume_sim()
        # run the full blast lifetime
        for _ in range(int(sbs._TORP_BLAST_LIFETIME / sbs._TORP_BLAST_RIPPLE_INTERVAL) + 1):
            sbs._physics_blasts(self.sim, sbs._TORP_BLAST_RIPPLE_INTERVAL)
        centre_dmg = 10000 - c.data_set.get("armor")
        off_dmg = 10000 - o.data_set.get("armor")
        self.assertGreater(centre_dmg, 100.0)             # centred ~ full accumulation (~120)
        self.assertGreater(centre_dmg, 2 * off_dmg)       # far less to the off-centre target
        self.assertGreater(off_dmg, 0.0)                  # but the ring did reach it

    def test_mine_is_placed_and_proximity_triggered(self):
        # A Mine is placed at the firing ship, stays put, and only detonates (its
        # growing-ring blast) when ANOTHER ship comes within the trigger radius.
        sid, s = self._hulled(pos=(0, 0, 0))              # firer (mine dropped here)
        sbs.launch_missile(sid, sid, kind="Mine")
        self.assertEqual(len(sbs._projectiles), 1)
        self.assertEqual(sbs._projectiles[0]["kind"], "mine")
        # No other ship nearby -> it just sits, no blast.
        sbs._physics_projectiles(self.sim, dt=1.0)
        self.assertEqual(len(sbs._blasts), 0)
        self.assertEqual(len(sbs._projectiles), 1)
        # An enemy drifts within the trigger radius -> the mine detonates.
        eid, e = self._hulled(100, pos=(300, 0, 0))       # within _TORP_MINE_TRIGGER (400)
        sbs._physics_projectiles(self.sim, dt=1.0)
        self.assertEqual(len(sbs._projectiles), 0)        # mine consumed
        self.assertEqual(len(sbs._blasts), 1)             # blast registered

    def test_projectile_travels_then_impacts(self):
        sid, s = self._hulled(pos=(0, 0, 0))
        tid, t = self._hulled(100, pos=(5000, 0, 0))      # far -> multiple ticks
        _drain()
        sbs.launch_missile(sid, tid, damage=40, speed=600.0)
        hit = False
        for _ in range(50):
            sbs._physics_projectiles(self.sim, dt=0.5)
            if any(e[0] == "damage" for e in _drain()):
                hit = True
                break
        self.assertTrue(hit)
        self.assertEqual(t.data_set.get("armor"), 60.0)

    def test_drone_fizzles_if_target_gone(self):
        # Drones home; if the target is gone the drone fizzles.
        sid, s = self._hulled(pos=(0, 0, 0))
        tid, t = self._hulled(100, pos=(5000, 0, 0))
        sbs.launch_drone(sid, tid)
        _drain()
        sbs.delete_object(tid)                            # target removed mid-flight
        sbs._physics_projectiles(self.sim, dt=0.5)
        self.assertEqual([e for e in _drain() if e[0] == "damage"], [])
        self.assertEqual(len(sbs._projectiles), 0)

    def test_missile_flies_straight_and_hits_bystander_in_path(self):
        # Non-homing: the missile fires toward the target's launch point and keeps
        # flying straight; with the original target gone it still hits whatever it
        # passes within range (the next closest thing in its path).
        sid, s = self._hulled(pos=(0, 0, 0))
        tid, t = self._hulled(100, pos=(5000, 0, 0))          # aim point (+x)
        bid, b = self._hulled(100, pos=(900, 0, 0))           # bystander in the path
        sbs.launch_missile(sid, tid, damage=40, speed=600.0)  # dir locked to +x
        sbs.delete_object(tid)                                # original target gone
        _drain()
        hit = False
        for _ in range(20):
            sbs._physics_projectiles(self.sim, dt=0.5)
            if any(e[0] == "damage" for e in _drain()):
                hit = True
                break
        self.assertTrue(hit)
        self.assertEqual(b.data_set.get("armor"), 60.0)       # hit the bystander
        self.assertEqual(len(sbs._projectiles), 0)            # consumed on impact

    def test_projectile_kills_and_emits_killed(self):
        sid, s = self._hulled(pos=(0, 0, 0))
        tid, t = self._hulled(20, pos=(100, 0, 0))
        sbs.launch_missile(sid, tid, damage=40)
        _drain()                                          # consume the launch event
        sbs._physics_projectiles(self.sim, dt=0.5)
        tags = [e[0] for e in _drain()]
        self.assertEqual(tags, ["damage", "station_killed"])
        self.assertNotIn(tid, self.sim.space_objects)

    # --- autonomous fire: torpedoes are PLAYER-only, drones are NPC (elite) -----
    def _player(self, pos=(0, 0, 0)):
        # A player firer (abits PLAYER 0x20) - torpedoes are player-exclusive.
        oid = self.sim.create_space_object("behav_playership", "", 0x20)
        o = self.sim.space_objects[oid]
        o._pos = sbs.vec3(*pos)
        return oid, o

    def test_loader_sets_torpedo_tube_count_from_tubecount(self):
        oid = self.sim.create_space_object("behav_playership", "", 0x20)
        o = self.sim.space_objects[oid]
        sbs._apply_ship_data_to_object(o, {"tubecount": 4})
        self.assertEqual(o.data_set.get("torpedo_tube_count"), 4)

    def test_player_autonomous_torpedo_fire(self):
        aid, a = self._player(pos=(0, 0, 0))
        a.data_set.set("torpedo_tube_count", 1)
        a.data_set.set("torpedo_types_available", "Homing", 0)
        a.data_set.set("Homing_NUM", 3, 0); a.data_set.set("Homing_VAL", 3, 0)
        tid, t = self._hulled(100, pos=(1000, 0, 0))      # within _TORP_RANGE
        a.data_set.set("weapon_target_UID", tid)
        _drain()
        sbs._physics_launchers(self.sim, [(aid, a)], dt=0.5)
        self.assertEqual([e[0] for e in _drain()], ["player_launches_missile"])
        self.assertEqual(len(sbs._projectiles), 1)
        # firing spent one round: NUM and VAL both decremented.
        self.assertEqual(a.data_set.get("Homing_NUM", 0), 2)
        self.assertEqual(a.data_set.get("Homing_VAL", 0), 2)
        # cooldown -> no immediate refire
        sbs._physics_launchers(self.sim, [(aid, a)], dt=0.5)
        self.assertEqual([e for e in _drain() if e[0] == "player_launches_missile"], [])

    def test_player_torpedo_out_of_ammo_no_fire(self):
        # Tubes loaded but the only type is empty -> no launch, no projectile.
        aid, a = self._player(pos=(0, 0, 0))
        a.data_set.set("torpedo_tube_count", 1)
        a.data_set.set("torpedo_types_available", "Homing", 0)
        a.data_set.set("Homing_NUM", 0, 0); a.data_set.set("Homing_VAL", 0, 0)
        tid, t = self._hulled(100, pos=(1000, 0, 0))
        a.data_set.set("weapon_target_UID", tid)
        _drain()
        sbs._physics_launchers(self.sim, [(aid, a)], dt=0.5)
        self.assertEqual(_drain(), [])
        self.assertEqual(len(sbs._projectiles), 0)

    def test_missile_culled_at_max_range(self):
        # A missile that hits nothing is removed once it flies its launch range
        # (not left to drift for its full lifetime).
        sid, s = self._hulled(pos=(0, 0, 0))
        tid, t = self._hulled(100, pos=(0, 0, 50000))     # far away, never hit
        _drain()
        sbs.launch_missile(sid, tid, kind="Homing", speed=600.0, max_range=1000.0)
        self.assertEqual(len(sbs._projectiles), 1)
        for _ in range(10):                               # 600*0.5*10 = 3000 > 1000
            sbs._physics_projectiles(self.sim, dt=0.5)
        self.assertEqual(len(sbs._projectiles), 0)

    def test_npc_does_not_fire_torpedoes(self):
        # NPCs never torpedo, even with tubes loaded (torpedoes are player-exclusive).
        aid, a = self._hulled(pos=(0, 0, 0))              # NPC (abits 0x10)
        a.data_set.set("torpedo_tube_count", 1)
        tid, t = self._hulled(100, pos=(1000, 0, 0))
        a.data_set.set("target_id", tid)
        _drain()
        sbs._physics_launchers(self.sim, [(aid, a)], dt=0.5)
        self.assertEqual(_drain(), [])
        self.assertEqual(len(sbs._projectiles), 0)

    def test_npc_autonomous_drone_fire(self):
        # Drones fire only when elite_drone_launcher==1 (Torgoth/Ximni capability).
        aid, a = self._hulled(pos=(0, 0, 0))
        a.data_set.set("elite_drone_launcher", 1)
        a.data_set.set("drone_damage", 15.0)
        a.data_set.set("drone_launch_max_range", 3000.0)
        tid, t = self._hulled(100, pos=(1000, 0, 0))
        a.data_set.set("target_id", tid)
        _drain()
        sbs._physics_launchers(self.sim, [(aid, a)], dt=0.5)
        self.assertEqual([e[0] for e in _drain()], ["ship_launches_drone"])

    def test_no_drone_without_elite_flag(self):
        # drone_* values present but no elite_drone_launcher -> no drone fire.
        aid, a = self._hulled(pos=(0, 0, 0))
        a.data_set.set("drone_damage", 15.0)
        a.data_set.set("drone_launch_max_range", 3000.0)
        tid, t = self._hulled(100, pos=(1000, 0, 0))
        a.data_set.set("target_id", tid)
        _drain()
        sbs._physics_launchers(self.sim, [(aid, a)], dt=0.5)
        self.assertEqual(_drain(), [])

    def test_no_fire_out_of_range(self):
        # Elite drone NPC with target beyond drone_launch_max_range -> no fire.
        aid, a = self._hulled(pos=(0, 0, 0))
        a.data_set.set("elite_drone_launcher", 1)
        a.data_set.set("drone_launch_max_range", 3000.0)
        tid, t = self._hulled(100, pos=(99999, 0, 0))     # beyond range
        a.data_set.set("target_id", tid)
        _drain()
        sbs._physics_launchers(self.sim, [(aid, a)], dt=0.5)
        self.assertEqual(_drain(), [])
        self.assertEqual(len(sbs._projectiles), 0)


if __name__ == '__main__':
    unittest.main()
