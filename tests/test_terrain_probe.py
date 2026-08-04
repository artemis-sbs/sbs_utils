"""Phase 0 terrain-burst probe.

The probe's whole point is to run in a REAL Cosmos session, so the one thing these
tests must guarantee is that it cannot crash or leave the terrain module patched --
a probe that breaks spawning would burn an engine session to learn nothing.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import os
import tempfile
import unittest

from cosmos_dev.mock import sbs as mock_sbs
from sbs_utils.helpers import FrameContext, Context
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.delete_queue import DeleteQueue
from sbs_utils.procedural import terrain as terrain_mod
from sbs_utils.procedural.roles import role
from sbs_utils.procedural.terrain import terrain_spawn_asteroid_box
from sbs_utils.procedural.terrain_probe import (
    terrain_probe_start, terrain_probe_mark, terrain_probe_stop,
    terrain_probe_active)


class FakeEvent:
    client_id = 0
    tag = ""
    sub_tag = ""
    origin_id = 0
    selected_id = 0
    parent_id = 0
    value_tag = ""
    extra_tag = ""
    extra_extra_tag = ""
    sub_float = 0.0
    source_point = None
    event_time = 0


class ProbeBase(unittest.TestCase):
    def setUp(self):
        mock_sbs.create_new_sim()
        SpaceObject.clear()
        TickDispatcher.clear()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "terrain_burst.log")
        self.orig_spawn = terrain_mod.terrain_spawn
        self.orig_npc = terrain_mod.npc_spawn

    def tearDown(self):
        terrain_probe_stop()
        TickDispatcher.clear()
        DeleteQueue.clear()
        FrameContext.context = None

    def advance(self, ticks):
        for _ in range(ticks):
            TickDispatcher.dispatch_tick()
            mock_sbs.sim._time_tick_counter += 1

    def read(self):
        with open(self.path) as f:
            return f.read()


class TestProbe(ProbeBase):
    def test_records_a_section_and_restores_spawn(self):
        terrain_probe_start(self.path)
        self.assertTrue(terrain_probe_active())
        # patched while running
        self.assertIsNot(terrain_mod.terrain_spawn, self.orig_spawn)

        terrain_probe_mark("asteroids")
        terrain_spawn_asteroid_box(0, 0, 0, 4000, density=2)
        terrain_probe_mark("done")
        self.advance(5)
        terrain_probe_stop()

        # unpatched afterwards -- this is the one that protects the engine session
        self.assertIs(terrain_mod.terrain_spawn, self.orig_spawn)
        self.assertIs(terrain_mod.npc_spawn, self.orig_npc)
        self.assertFalse(terrain_probe_active())

        report = self.read()
        self.assertIn("== sections ==", report)
        self.assertIn("asteroids", report)
        self.assertIn("== frame periods ==", report)

    def test_object_count_matches_spawns(self):
        # Count asteroids, not Agent.all -- the probe's own TickTask is an Agent.
        before = len(role("asteroid"))
        terrain_probe_start(self.path)
        terrain_probe_mark("asteroids")
        terrain_spawn_asteroid_box(0, 0, 0, 4000, density=2)
        terrain_probe_stop()
        created = len(role("asteroid")) - before
        self.assertGreater(created, 0)

        # the "objects" column is the count of leaf spawn calls the probe timed
        line = [l for l in self.read().splitlines() if l.startswith("asteroids")][0]
        counted = int(line.split()[4])
        self.assertEqual(counted, created)

    def test_spawning_still_works_while_probing(self):
        """The wrapper must be transparent: same object count, probe on or off."""
        import random
        random.seed(11)
        terrain_spawn_asteroid_box(0, 0, 0, 4000, density=2)
        plain = len(role("asteroid"))

        SpaceObject.clear()
        random.seed(11)
        terrain_probe_start(self.path)
        terrain_spawn_asteroid_box(0, 0, 0, 4000, density=2)
        terrain_probe_stop()
        probed = len(role("asteroid"))

        self.assertGreater(plain, 0)
        self.assertEqual(plain, probed)

    def test_stop_without_start_is_safe(self):
        self.assertFalse(terrain_probe_active())
        terrain_probe_stop()
        terrain_probe_mark("nothing")
        self.assertFalse(terrain_probe_active())


if __name__ == "__main__":
    unittest.main()
