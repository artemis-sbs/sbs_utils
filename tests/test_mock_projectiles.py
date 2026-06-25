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
        self.assertIn(("damage", "", sid, tid), _drain())
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
        self.assertIn(("damage", "", sid, tid), _drain())
        self.assertEqual(t.data_set.get("armor"), 85.0)

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

    # --- autonomous NPC fire -----------------------------------------------
    def test_npc_autonomous_torpedo_fire(self):
        aid, a = self._hulled(pos=(0, 0, 0))
        a.data_set.set("torpedo_tube_count", 1)
        tid, t = self._hulled(100, pos=(1000, 0, 0))      # within _TORP_RANGE
        a.data_set.set("target_id", tid)
        _drain()
        sbs._physics_launchers(self.sim, [(aid, a)], dt=0.5)
        ev = _drain()
        self.assertEqual([e[0] for e in ev], ["player_launches_missile"])
        self.assertEqual(len(sbs._projectiles), 1)
        # cooldown -> no immediate refire
        sbs._physics_launchers(self.sim, [(aid, a)], dt=0.5)
        self.assertEqual([e for e in _drain() if e[0] == "player_launches_missile"], [])

    def test_launcher_uses_weapon_target_uid(self):
        # player-style weapon target drives missile launch too
        aid, a = self._hulled(pos=(0, 0, 0))
        a.data_set.set("torpedo_tube_count", 1)
        tid, t = self._hulled(100, pos=(1000, 0, 0))
        a.data_set.set("weapon_target_UID", tid)
        _drain()
        sbs._physics_launchers(self.sim, [(aid, a)], dt=0.5)
        self.assertEqual([e[0] for e in _drain()], ["player_launches_missile"])

    def test_npc_autonomous_drone_fire(self):
        aid, a = self._hulled(pos=(0, 0, 0))
        a.data_set.set("drone_damage", 15.0)
        a.data_set.set("drone_launch_max_range", 3000.0)
        tid, t = self._hulled(100, pos=(1000, 0, 0))
        a.data_set.set("target_id", tid)
        _drain()
        sbs._physics_launchers(self.sim, [(aid, a)], dt=0.5)
        self.assertEqual([e[0] for e in _drain()], ["ship_launches_drone"])

    def test_no_fire_out_of_range(self):
        aid, a = self._hulled(pos=(0, 0, 0))
        a.data_set.set("torpedo_tube_count", 1)
        tid, t = self._hulled(100, pos=(99999, 0, 0))     # beyond _TORP_RANGE
        a.data_set.set("target_id", tid)
        _drain()
        sbs._physics_launchers(self.sim, [(aid, a)], dt=0.5)
        self.assertEqual(_drain(), [])
        self.assertEqual(len(sbs._projectiles), 0)


if __name__ == '__main__':
    unittest.main()
