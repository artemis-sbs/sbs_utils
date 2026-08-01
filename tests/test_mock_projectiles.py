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
from tests.reset_helper import reset_mock


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
        self.sim = reset_mock(sbs)
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

    def test_mine_shoots_out_stern_then_deploys_and_triggers(self):
        # A Mine drops out the stern and coasts to its distance, INERT in flight; on
        # reaching its distance it stops and DEPLOYS as a stationary armed proximity
        # mine that detonates (its growing-ring blast) when a ship comes within range.
        sid, s = self._hulled(pos=(0, 0, 0))              # firer
        sbs.launch_missile(sid, sid, kind="Mine", speed=600.0, max_range=1000.0)
        self.assertEqual(len(sbs._projectiles), 1)
        self.assertEqual(sbs._projectiles[0]["kind"], "missile")   # flying, not yet armed
        self.assertTrue(sbs._projectiles[0]["is_mine"])
        # Fly until it reaches its distance and deploys (600*0.5*4 = 1200 > 1000).
        deployed = False
        for _ in range(5):
            sbs._physics_projectiles(self.sim, dt=0.5)
            if sbs._projectiles and sbs._projectiles[0]["kind"] == "mine":
                deployed = True
                break
        self.assertTrue(deployed, "mine should deploy (kind 'mine') after reaching its distance")
        self.assertEqual(len(sbs._blasts), 0)             # armed but nothing in range yet
        mp = sbs._projectiles[0]["pos"]
        # An enemy drifts within the trigger radius of the DEPLOYED mine -> detonate.
        eid, e = self._hulled(100, pos=(mp.x + 200, mp.y, mp.z))   # within _TORP_MINE_TRIGGER (400)
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

    def test_homing_reacquires_nearest_when_target_gone(self):
        # A homing torp whose selected target dies mid-flight re-acquires the nearest
        # object and homes onto it (here the bystander) - "if target is gone, find
        # closest".
        sid, s = self._hulled(pos=(0, 0, 0))
        tid, t = self._hulled(100, pos=(5000, 0, 0))          # original target (+x)
        bid, b = self._hulled(100, pos=(900, 0, 0))           # nearest after target gone
        sbs.launch_missile(sid, tid, damage=40, speed=600.0)
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

    def test_no_selection_flies_straight_no_reacquire(self):
        # Fired with no weapon selection -> flies straight (+z); it must NOT home onto
        # a nearby ship. Re-acquire is only for a homing torp whose SELECTED target
        # died, so target_id stays 0 here.
        sid, s = self._hulled(pos=(0, 0, 0))
        nid, n = self._hulled(100, pos=(3000, 0, 0))      # off the +z flight path
        sbs.launch_missile(sid, 0, kind="Homing", speed=600.0)   # no target
        self.assertEqual(sbs._projectiles[0]["target_id"], 0)
        self.assertFalse(sbs._projectiles[0]["had_target"])
        for _ in range(4):
            sbs._physics_projectiles(self.sim, dt=0.5)
            if sbs._projectiles:
                self.assertEqual(sbs._projectiles[0]["target_id"], 0)  # never re-acquired
        self.assertEqual(n.data_set.get("armor"), 100.0)  # bystander off-path: untouched

    def test_homing_tracks_a_moving_target(self):
        # A homing torp re-homes each tick, so it curves to follow a target that moves
        # off the original launch bearing and still connects.
        sid, s = self._hulled(pos=(0, 0, 0))
        tid, t = self._hulled(100, pos=(0, 0, 3000))      # ahead (+z)
        sbs.launch_missile(sid, tid, damage=40, speed=600.0)
        _drain()
        hit = False
        for k in range(40):
            t._pos = sbs.vec3(2000, 0, 3000 + k * 50)     # drifts +x while torp flies
            sbs._physics_projectiles(self.sim, dt=0.5)
            if any(e[0] == "damage" for e in _drain()):
                hit = True
                break
        self.assertTrue(hit, "homing torp should track the moving target and hit it")

    def test_torpedo_damages_npc_ship(self):
        # Regression: NPC ships have no armorMax (they take system_damage). A torp must
        # still detonate on them - _nearest_hittable used to match only armorMax>0, so
        # torps homed onto NPCs forever and oscillated near them without ever damaging.
        sid, s = self._hulled(pos=(0, 0, 0))
        nid = self.sim.create_space_object("behav_npcship", "", 0x10)
        n = self.sim.space_objects[nid]
        for i in range(4):
            n.data_set.set("system_max_damage", 4.0, i)
        n._pos = sbs.vec3(200, 0, 0)
        _drain()
        sbs.launch_missile(sid, nid, damage=30)
        sbs._physics_projectiles(self.sim, dt=0.5)
        dmg = [e for e in _drain() if e[0] == "damage" and e[3] == nid]
        self.assertTrue(dmg, "torp should detonate on the NPC ship")
        self.assertEqual(len(sbs._projectiles), 0)            # consumed on impact
        self.assertGreater(sum(n.data_set.get("system_damage", i) or 0 for i in range(4)), 0)

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

    # --- the fire_torpedo wrapper + launch_torpedo type selection -----------
    def test_fire_torpedo_selects_type_by_kind(self):
        from sbs_utils.helpers import FrameContext, Context
        from sbs_utils.procedural.spawn import player_spawn, npc_spawn
        from sbs_utils.procedural.query import to_id, to_object
        from sbs_utils.procedural.torpedoes import fire_torpedo, torpedo_make_available
        FrameContext.context = Context(self.sim, sbs, None)   # the wrapper needs a context
        p = player_spawn(0, 0, 0, "Artemis", "tsn", "tsn_light_cruiser"); pid = to_id(p)
        t = npc_spawn(500, 0, 0, "Foe", "raider", "tsn_light_cruiser", "behav_npcship")
        po = to_object(pid)
        po.data_set.set("torpedo_tube_count", 1, 0)
        po.data_set.set("weapon_target_UID", to_id(t), 0)
        # a clean, known loadout (override any shipData starting torps)
        po.data_set.set("torpedo_types_available", "Homing,Nuke,EMP", 0)
        for k in ("Homing", "Nuke", "EMP"):
            po.data_set.set(f"{k}_NUM", 3, 0)

        _drain()
        fire_torpedo(pid, "Nuke")                            # kind -> that tube fires
        kinds = [e[5] for e in _drain() if e[0] == "player_launches_missile"]
        self.assertEqual(kinds, ["Nuke"])
        self.assertEqual(po.data_set.get("Nuke_NUM"), 2)     # only the Nuke was spent
        self.assertEqual(po.data_set.get("Homing_NUM"), 3)

        fire_torpedo(pid)                                    # default -> first loaded (Homing)
        self.assertEqual(po.data_set.get("Homing_NUM"), 2)

        fire_torpedo(pid, "Mine")                            # unloaded -> falls back to Homing
        self.assertEqual(po.data_set.get("Homing_NUM"), 1)
        self.assertEqual(len(sbs._projectiles), 3)          # every call fired


class TestTorpedoOrphanFizzle(unittest.TestCase):
    """_TORP_ORPHAN_LIFE kills a warhead whose TARGET died (the "orange torp sitting in
    space"). It must not kill a torpedo that never had a target - an unaimed shot flies
    straight for its full life. Both branches key off `had_target`, exactly like the
    re-acquire beside them; without that guard every unaimed torpedo died 1.5s after
    launch and torpedoes read as not firing at all."""

    def setUp(self):
        self.sim = reset_mock(sbs)
        _drain()

    def _fire(self, with_target):
        s = self.sim.create_space_object("behav_playership", "tsn_battle_cruiser", 0x20)
        self.sim.space_objects[s]._pos = sbs.vec3(0.0, 0.0, 0.0)
        tid = 0
        if with_target:
            t = self.sim.create_space_object("behav_npcship", "torgoth_destroyer", 0x10)
            self.sim.space_objects[t]._pos = sbs.vec3(0.0, 0.0, 5000.0)
            tid = t
        sbs.resume_sim()
        sbs.launch_missile(s, tid, "Homing")
        if with_target:
            sbs.delete_object(tid)      # target dies right after launch -> a true orphan
        return s

    def _alive_after(self, seconds):
        for _ in range(int(30 * seconds)):
            sbs.physics_tick(1.0 / 30.0)
        return len(sbs._projectiles)

    def test_unaimed_torpedo_keeps_flying(self):
        self._fire(with_target=False)
        self.assertGreater(self._alive_after(4.0), 0,
                           "a torpedo fired with no selection must fly straight, not fizzle")

    def test_orphaned_torpedo_still_fizzles(self):
        self._fire(with_target=True)
        self.assertEqual(self._alive_after(3.0), 0,
                         "a warhead whose target died must still fizzle (_TORP_ORPHAN_LIFE)")


class TestTorpedoOutrunsFirer(unittest.TestCase):
    """A warhead must always pull ahead of the ship that fired it.

    Torpedo speed is a flat 600 u/s and does not inherit launcher velocity, while a
    player does 180 u/s on impulse and 180 + (pt-1)*450 on warp. From warp 2 (630 u/s)
    the ship outran its own torpedo immediately: the torp fell behind the chase cam and
    was never seen, which reads as torpedoes not firing.
    """

    def setUp(self):
        self.sim = reset_mock(sbs)
        _drain()

    def _ship_at(self, throttle):
        s = self.sim.create_space_object("behav_playership", "tsn_battle_cruiser", 0x20)
        o = self.sim.space_objects[s]
        o._pos = sbs.vec3(0.0, 0.0, 0.0)
        o.data_set.set("playerThrottle", throttle, 0)
        sbs.resume_sim()
        for _ in range(30 * 30):          # ramp to steady state
            sbs.physics_tick(1.0 / 30.0)
        return s, abs(o._cur_speed)

    def _launch_speed(self, sid, kind="Homing"):
        sbs._projectiles.clear()
        sbs.launch_missile(sid, 0, kind)
        return sbs._projectiles[0]["speed"]

    def test_torpedo_outpaces_ship_at_warp(self):
        for throttle in (2.0, 3.0, 5.0):
            with self.subTest(throttle=throttle):
                sid, ship_speed = self._ship_at(throttle)
                torp = self._launch_speed(sid)
                self.assertGreater(torp, ship_speed,
                                   f"at throttle {throttle} the ship ({ship_speed:.0f} u/s) "
                                   f"outruns its torpedo ({torp:.0f} u/s)")
                self.setUp()

    def test_impulse_keeps_the_flat_speed(self):
        """Below the floor nothing changes - a slow ship must not slow its torpedo."""
        sid, ship_speed = self._ship_at(1.0)
        self.assertEqual(self._launch_speed(sid), 600.0)

    def test_mine_is_exempt(self):
        """Mines coast out the stern by design; the floor must not accelerate them."""
        sid, _ = self._ship_at(3.0)
        self.assertEqual(self._launch_speed(sid, kind="Mine"), 600.0)


class TestWarheadArmingAndSelfBlast(unittest.TestCase):
    """A warhead spawns AT the launcher with a 300u contact radius, so without an arming
    distance it detonated on the first physics tick against anything alongside the firing
    ship - the intended target then took nothing. Conversely a blast is indiscriminate:
    detonate a nuke close enough and the firer is inside its own blast."""

    def setUp(self):
        self.sim = reset_mock(sbs)
        _drain()
        self.firer = self.sim.create_space_object("behav_playership", "tsn_battle_cruiser", 0x20)
        fo = self.sim.space_objects[self.firer]
        fo._pos = sbs.vec3(0.0, 0.0, 0.0); fo._side = "tsn"

    def _shields(self, oid):
        ds = self.sim.space_objects[oid].data_set
        n = int(ds.get("shield_count", 0) or 0)
        return sum((ds.get("shield_val", i) or 0.0) for i in range(n))

    def _add(self, x, z, side, tick="behav_npcship", hull="torgoth_destroyer", abits=0x10):
        oid = self.sim.create_space_object(tick, hull, abits)
        o = self.sim.space_objects[oid]
        o._pos = sbs.vec3(float(x), 0.0, float(z)); o._side = side
        return oid

    def _fire(self, kind, target, seconds=30):
        sbs.resume_sim()
        sbs.launch_missile(self.firer, target, kind)
        for _ in range(int(30 * seconds)):
            sbs.physics_tick(1.0 / 30.0)

    def test_point_blank_shot_at_a_real_target_still_detonates(self):
        """The fuse is inert against BYSTANDERS only - never against the aimed-at ship,
        so close-range torpedoing keeps working."""
        target = self._add(0, 200, "torgoth")
        t0 = self._shields(target)
        self._fire("Homing", target)
        self.assertLess(self._shields(target), t0,
                        "a torpedo must still detonate on the ship it was aimed at, at any range")

    def test_warhead_is_inert_until_it_clears_the_launcher(self):
        wingman = self._add(200, 0, "tsn", "behav_playership", "tsn_battle_cruiser", 0x20)
        target = self._add(0, 5000, "torgoth")
        w0, t0 = self._shields(wingman), self._shields(target)
        self._fire("Homing", target)
        self.assertAlmostEqual(self._shields(wingman), w0, places=1,
                               msg="a torp must not detonate on a ship hugging the launcher")
        self.assertLess(self._shields(target), t0, "it should reach the intended target instead")

    def test_projectile_spawns_clear_of_the_hull(self):
        """Born at the ship's centre, a projectile starts inside its own launcher and any
        blast it triggers is centred on the firer. It must leave from outside the hull."""
        import math
        target = self._add(0, 5000, "torgoth")
        sbs._projectiles.clear()
        sbs.launch_missile(self.firer, target, "Homing")
        p = sbs._projectiles[0]["pos"]
        fo = self.sim.space_objects[self.firer]._pos
        off = math.dist((p.x, p.y, p.z), (fo.x, fo.y, fo.z))
        self.assertGreater(off, sbs._TORP_LAUNCH_CLEARANCE,
                           "projectile must spawn beyond the hull, not at the ship centre")
        # ...and ABOVE it: the directional clearance is near-horizontal for a same-altitude
        # target, so only the vertical rise reliably keeps the torp off its own hull.
        self.assertAlmostEqual(p.y - fo.y, sbs._TORP_LAUNCH_RISE, places=1,
                               msg="projectile must launch above the firer, not through it")

    def test_homing_never_damages_its_firer_at_any_range(self):
        """Single-hit warheads have no blast, so the firer must be untouched however
        close the target is."""
        for dist in (400, 800, 1500, 3000):
            with self.subTest(dist=dist):
                self.setUp()
                target = self._add(0, dist, "torgoth")
                f0 = self._shields(self.firer)
                self._fire("Homing", target)
                self.assertAlmostEqual(self._shields(self.firer), f0, places=1)

    def test_nuke_never_catches_its_own_firer(self):
        """A blast excludes the ship that fired it. Making blasts indiscriminate was tried
        and reverted: self-damage was reported BEFORE that change, so it was never the
        cause, and the change turned every close-range nuke into a self-hit."""
        target = self._add(0, 600, "torgoth")
        f0 = self._shields(self.firer)
        self._fire("Nuke", target)
        self.assertAlmostEqual(self._shields(self.firer), f0, places=1,
                               msg="a nuke must not damage the ship that launched it")

    def test_distant_nuke_spares_the_firer(self):
        target = self._add(0, 5000, "torgoth")
        f0 = self._shields(self.firer)
        self._fire("Nuke", target)
        self.assertAlmostEqual(self._shields(self.firer), f0, places=1,
                               msg="a nuke well outside blast radius must not touch the firer")


if __name__ == '__main__':
    unittest.main()
