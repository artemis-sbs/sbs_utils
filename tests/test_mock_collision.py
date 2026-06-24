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
        sbs.create_new_sim()
        self.sim = sbs.sim
        sbs._contact_pairs.clear()
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
        self.assertEqual(self._tags(ev),
                         ["passive_collision_start", "passive_collision_start"])
        self.assertEqual(self._origins(ev), sorted([a_id, t_id]))

        # separate -> passive_collision_end
        a._pos = sbs.vec3(10000, 0, 0)
        sbs._physics_collision(self.sim, active)
        self.assertEqual(self._tags(_drain()),
                         ["passive_collision_end", "passive_collision_end"])

    def test_no_event_when_not_overlapping(self):
        a_id, a = self._obj(0x10, (0, 0, 0), 100)
        b_id, b = self._obj(0x10, (5000, 0, 0), 100)
        _drain()
        sbs._physics_collision(self.sim, [(a_id, a), (b_id, b)])
        self.assertEqual(_drain(), [])


if __name__ == '__main__':
    unittest.main()
