"""
Mock physics collision-event tests.

Pins the event tags the mock emits so the handler routes them correctly
(handlerhooks dispatches passive_collision_start/end and
interactive_collision_start/end; an unrecognized tag prints "Unhandled event").

Contract (per the engine):
  - collision involving a STATIC terrain object -> passive_collision_start/end
  - collision between two DYNAMIC (active) objects -> interactive_collision_start/end
  - start fires on contact entry, end on contact exit
  - both id orderings are emitted (each object sees itself as origin)
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest
import cosmos_dev.mock.sbs as sbs
from tests.reset_helper import reset_mock


def _drain():
    out = []
    while True:
        try:
            out.append(sbs._pending_physics_events.get_nowait())
        except Exception:
            break
    return out


class TestMockCollision(unittest.TestCase):
    def setUp(self):
        self.sim = reset_mock(sbs)
        _drain()

    def _obj(self, abits, pos, er):
        oid = self.sim.create_space_object("behav", "", abits)
        o = self.sim.space_objects[oid]
        o._pos = sbs.vec3(*pos)
        o._exclusion_radius = er
        return oid, o

    @staticmethod
    def _tags(events):
        return sorted(e[0] for e in events)

    @staticmethod
    def _origins(events):
        return sorted(e[2] for e in events)

    def test_interactive_start_then_end(self):
        # two active (0x10) objects overlapping (dist 50 < 100+100)
        a_id, a = self._obj(0x10, (0, 0, 0), 100)
        b_id, b = self._obj(0x10, (50, 0, 0), 100)
        active = [(a_id, a), (b_id, b)]
        _drain()

        # entry -> two interactive_collision_start (both orderings)
        sbs._physics_collision(self.sim, active)
        ev = _drain()
        self.assertEqual(self._tags(ev),
                         ["interactive_collision_start", "interactive_collision_start"])
        self.assertEqual(self._origins(ev), sorted([a_id, b_id]))

        # still overlapping next frame -> no new events
        sbs._physics_collision(self.sim, active)
        self.assertEqual(_drain(), [])

        # move apart -> exit -> two interactive_collision_end
        b._pos = sbs.vec3(10000, 0, 0)
        sbs._physics_collision(self.sim, active)
        ev = _drain()
        self.assertEqual(self._tags(ev),
                         ["interactive_collision_end", "interactive_collision_end"])
        self.assertEqual(self._origins(ev), sorted([a_id, b_id]))

    def test_passive_with_static_terrain(self):
        # active object overlapping a static terrain object (abits 0 -> terrain)
        a_id, a = self._obj(0x10, (0, 0, 0), 100)
        t_id, t = self._obj(0x00, (50, 0, 0), 100)
        active = [(a_id, a)]
        _drain()

        sbs._physics_collision(self.sim, active)
        ev = _drain()
        # Terrain contact fires ONCE: origin = terrain, selected = ship.
        self.assertEqual(self._tags(ev), ["passive_collision_start"])
        self.assertEqual(ev[0][2], t_id)   # origin_id = terrain
        self.assertEqual(ev[0][3], a_id)   # selected_id = ship

        # separate -> single passive_collision_end (origin = terrain)
        a._pos = sbs.vec3(10000, 0, 0)
        sbs._physics_collision(self.sim, active)
        ev = _drain()
        self.assertEqual(self._tags(ev), ["passive_collision_end"])
        self.assertEqual(ev[0][2], t_id)

    def test_interaction_radius_fires_interactive(self):
        # A terrain object with a data_set interactionradius (pickups) fires INTERACTIVE
        # collision (so the upgrade-collection route runs) - purely data-driven, no
        # exclusion_radius==0 or behaviour check. Its exclusion_radius is 0 (not solid).
        a_id, a = self._obj(0x10, (0, 0, 0), 100)              # active player/ship
        p_id = self.sim.create_space_object("behav_pickup", "", 0x00)   # terrain pickup
        p = self.sim.space_objects[p_id]
        p._pos = sbs.vec3(150, 0, 0)                            # within 100 + 100
        p.data_set.set("interactionradius", 100.0)             # interactive contact radius
        _drain()
        sbs._physics_collision(self.sim, [(a_id, a)])
        ev = _drain()
        # ONE event: origin = pickup (COLLISION_ORIGIN_ID for the collection route),
        # selected = ship.
        self.assertEqual(self._tags(ev), ["interactive_collision_start"])
        self.assertEqual(ev[0][2], p_id)   # origin_id = pickup
        self.assertEqual(ev[0][3], a_id)   # selected_id = ship

    def test_pickup_art_loads_interactionradius_from_shipdata(self):
        # A pickup spawned with a real pickup art loads its interactionradius from
        # shipData by art id (no behav/special-casing), and that drives the interactive
        # collision so the collection route can fire.
        uid = self.sim.create_space_object("behav_pickup", "alien_1a", 0x00)
        u = self.sim.space_objects[uid]
        ir = u.data_set.get("interactionradius") or 0.0
        self.assertGreater(ir, 0.0, "pickup art should carry interactionradius from shipData")
        self.assertEqual(u._exclusion_radius, 0.0)             # not solid
        u._pos = sbs.vec3(ir * 0.5, 0, 0)                      # well within interaction radius
        a_id, a = self._obj(0x10, (0, 0, 0), 50)
        _drain()
        sbs._physics_collision(self.sim, [(a_id, a)])
        self.assertIn("interactive_collision_start", self._tags(_drain()))

    def test_no_end_event_when_object_deleted_on_collect(self):
        # When the collection route deletes the pickup on interactive_collision_start,
        # the next tick must NOT fire a spurious interactive_collision_end for the gone
        # object (the contact ended by destruction, not separation).
        a_id, a = self._obj(0x10, (0, 0, 0), 100)
        p_id = self.sim.create_space_object("behav_pickup", "", 0x00)
        p = self.sim.space_objects[p_id]
        p._pos = sbs.vec3(150, 0, 0); p.data_set.set("interactionradius", 100.0)
        sbs._physics_collision(self.sim, [(a_id, a)])
        self.assertEqual(self._tags(_drain()), ["interactive_collision_start"])
        sbs.delete_object(p_id)                                 # collected
        sbs._physics_collision(self.sim, [(a_id, a)])           # pickup gone
        self.assertEqual(_drain(), [])                          # no end event

    def test_ship_is_not_stopped_by_a_pickup(self):
        # A pickup must NOT physically stop or slow a ship: mock collision only emits
        # events (no push/brake). A ship driven into a pickup flies straight through at
        # constant cruise; an interactive collision fires (so a //collision/interactive
        # collection route can grab it). The "stuck on a pickup" seen in missions was
        # the autoplay throttling down on approach + the old passive-collision bug +
        # the altitude render gap - NOT mock physics.
        pid = self.sim.create_space_object("behav_playership", "tsn_light_cruiser", 0x20)
        p = self.sim.space_objects[pid]; p._pos = sbs.vec3(0, 0, 0); p._exclusion_radius = 50
        uid = self.sim.create_space_object("behav_pickup", "carapaction_coil", 0x00)
        u = self.sim.space_objects[uid]; u._pos = sbs.vec3(0, 0, 3000)
        u.data_set.set("interactionradius", 200.0)     # interactive grab radius
        p.data_set.set("playerThrottle", 1.0)          # cruise forward (+z) into it
        sbs.resume_sim()
        saw_collision = False
        for _ in range(700):                            # ~17s at 180 u/s reaches 3000
            sbs.physics_tick(dt=1 / 30)
            if any(e[0] == "interactive_collision_start" for e in _drain()):
                saw_collision = True
            if p._pos.z > 3300:
                break
        self.assertGreater(p._pos.z, 3300)              # flew through, not stopped
        self.assertTrue(saw_collision)                  # interactive collision fired
        self.assertAlmostEqual(p._cur_speed, 180.0, delta=1.0)   # constant cruise, no brake
        self.assertIn(uid, self.sim.space_objects)      # no collection route here -> stays

    def test_no_event_when_not_overlapping(self):
        a_id, a = self._obj(0x10, (0, 0, 0), 100)
        b_id, b = self._obj(0x10, (5000, 0, 0), 100)
        _drain()
        sbs._physics_collision(self.sim, [(a_id, a), (b_id, b)])
        self.assertEqual(_drain(), [])


if __name__ == '__main__':
    unittest.main()
