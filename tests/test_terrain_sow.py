"""Terrain sowing: the creation burst spread over seconds instead of one frame.

The load-bearing claim is IDENTITY -- a sowed field must contain exactly the same
objects, in the same places, as the same call made inline. That is what makes the
feature safe to turn on: it changes when terrain appears, never what appears. It
holds because each queued cluster carries the RNG state it was queued under.

The second claim is that opting out costs nothing: with no sow scope open, every
terrain_* call spawns inline exactly as before.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import random
import unittest

from cosmos_dev.mock import sbs as mock_sbs
from sbs_utils.helpers import FrameContext, Context
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.tickdispatcher import TickDispatcher, DripQueue
from sbs_utils.delete_queue import DeleteQueue
from sbs_utils.vec import Vec3
from sbs_utils.procedural.roles import role
from sbs_utils.procedural.query import to_object_list
from sbs_utils.procedural.terrain import (
    terrain_asteroid_clusters, terrain_spawn_asteroid_box,
    terrain_spawn_nebula_sphere,
    terrain_sow_begin, terrain_sow_end, terrain_sow_flush,
    terrain_sow_pending, terrain_sow_reset, NEB_SOW_CHUNK)


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


class SowBase(unittest.TestCase):
    def setUp(self):
        mock_sbs.create_new_sim()
        SpaceObject.clear()
        TickDispatcher.clear()
        terrain_sow_reset()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())

    def tearDown(self):
        terrain_sow_reset()
        TickDispatcher.clear()
        DeleteQueue.clear()
        FrameContext.context = None

    def advance(self, ticks):
        for _ in range(ticks):
            TickDispatcher.dispatch_tick()
            mock_sbs.sim._time_tick_counter += 1

    def field(self, role_name="asteroid"):
        """Positions of the spawned field, order-independent."""
        return sorted((round(o.pos.x, 4), round(o.pos.y, 4), round(o.pos.z, 4))
                      for o in to_object_list(role(role_name)))


class TestIdentity(SowBase):
    """What sowing guarantees, stated exactly.

    PER CALL: a sowed terrain call creates exactly what that call would have
    created inline. That is the safety property -- deferring a cluster does not
    change it.

    ACROSS a multi-cluster call it is deterministic but not identical to inline,
    and that is inherent to deferring: inline, cluster N's spawn consumes RNG that
    cluster N+1's plan then reads. Cluster CENTRES are drawn up front, so the
    field's macro layout is preserved; what shifts is each cluster's rock count and
    scales. This is why sowing is opt-in per map -- you do not run a map both ways.
    """

    def test_single_cluster_identical_to_inline(self):
        random.seed(99)
        terrain_spawn_asteroid_box(2000, 0, -3000, 8000, density=2)
        inline = self.field()
        self.assertGreater(len(inline), 20)

        SpaceObject.clear()
        random.seed(99)
        terrain_sow_begin(over=6)
        terrain_spawn_asteroid_box(2000, 0, -3000, 8000, density=2)
        terrain_sow_flush()
        sowed = self.field()

        self.assertEqual(inline, sowed)

    def test_whole_field_is_deterministic(self):
        random.seed(99)
        terrain_sow_begin(over=6)
        terrain_asteroid_clusters(3)
        terrain_sow_flush()
        first = self.field()
        self.assertGreater(len(first), 100)

        SpaceObject.clear()
        terrain_sow_reset()
        random.seed(99)
        terrain_sow_begin(over=6)
        terrain_asteroid_clusters(3)
        terrain_sow_flush()

        self.assertEqual(first, self.field())

    def test_drain_order_does_not_change_the_field(self):
        """Drip or flush, the same objects in the same places."""
        random.seed(7)
        terrain_sow_begin(over=6)
        terrain_asteroid_clusters(3)
        terrain_sow_flush()
        flushed = self.field()

        SpaceObject.clear()
        terrain_sow_reset()
        random.seed(7)
        terrain_sow_begin(over=1)
        terrain_asteroid_clusters(3)
        self.advance(TickDispatcher.tps + 2)

        self.assertEqual(terrain_sow_pending(), 0)
        self.assertEqual(flushed, self.field())

    def test_nebula_field_identical_to_inline(self):
        random.seed(1234)
        terrain_spawn_nebula_sphere(1000, 0, 2000, radius=9000, density_scale=2.0)
        inline = self.field("nebula")
        self.assertGreater(len(inline), 5)

        SpaceObject.clear()
        random.seed(1234)
        terrain_sow_begin(over=6)
        terrain_spawn_nebula_sphere(1000, 0, 2000, radius=9000, density_scale=2.0)
        terrain_sow_flush()
        sowed = self.field("nebula")

        self.assertEqual(inline, sowed)

    def test_draining_does_not_disturb_the_caller_rng(self):
        """The queue borrows the global stream per item and puts it back."""
        random.seed(5)
        terrain_sow_begin(over=6)
        terrain_asteroid_clusters(2)
        control = [random.random() for _ in range(3)]

        SpaceObject.clear()
        terrain_sow_reset()
        random.seed(5)
        terrain_sow_begin(over=6)
        terrain_asteroid_clusters(2)
        terrain_sow_flush()
        after = [random.random() for _ in range(3)]

        self.assertEqual(control, after)


class TestDeferral(SowBase):
    def test_nothing_spawns_at_call_time(self):
        random.seed(3)
        terrain_sow_begin(over=6)
        terrain_asteroid_clusters(3)
        self.assertEqual(len(role("asteroid")), 0)
        self.assertGreater(terrain_sow_pending(), 1)

    def test_drains_within_the_window(self):
        random.seed(3)
        terrain_sow_begin(over=2)
        terrain_asteroid_clusters(3)
        queued = terrain_sow_pending()
        self.assertGreater(queued, 1)

        self.advance(2 * TickDispatcher.tps + 2)

        self.assertEqual(terrain_sow_pending(), 0)
        self.assertGreater(len(role("asteroid")), 100)

    def test_work_is_actually_spread_over_ticks(self):
        """The point of the feature: no single tick does the whole burst."""
        random.seed(3)
        terrain_sow_begin(over=2)
        terrain_asteroid_clusters(3)
        total = terrain_sow_pending()

        per_tick = []
        prev = 0
        for _ in range(2 * TickDispatcher.tps + 2):
            self.advance(1)
            now = len(role("asteroid"))
            per_tick.append(now - prev)
            prev = now

        busy = [n for n in per_tick if n > 0]
        self.assertGreater(len(busy), 5, "work landed in too few ticks to be a drip")
        self.assertLess(max(per_tick), prev, "one tick created the whole field")
        self.assertEqual(len(busy), total)  # one cluster per busy tick

    def test_nearest_first(self):
        """Clusters near the focus are created before distant ones."""
        q = terrain_sow_begin(over=6, focus=Vec3(0, 0, 0))
        random.seed(1)
        terrain_spawn_asteroid_box(80000, 0, 80000, 2000, density=1)
        terrain_spawn_asteroid_box(500, 0, 500, 2000, density=1)
        self.assertEqual(q.pending(), 2)

        q.run_slice()
        while q.pending() == 2:      # let the accumulator reach one item
            q.run_slice()
        near = [o for o in to_object_list(role("asteroid"))
                if abs(o.pos.x) < 40000]
        far = [o for o in to_object_list(role("asteroid"))
               if abs(o.pos.x) >= 40000]
        self.assertGreater(len(near), 0)
        self.assertEqual(len(far), 0)


class TestNebulaChunking(SowBase):
    """Nebula is the expensive terrain (~5x an asteroid per object), so a whole
    cluster is too big an atom to queue -- it gets split."""

    def test_cluster_is_split_into_several_units(self):
        random.seed(21)
        terrain_sow_begin(over=10)
        terrain_spawn_nebula_sphere(0, 0, 0, radius=9000, density_scale=2.0)
        self.assertGreater(terrain_sow_pending(), 1)

    def test_no_unit_creates_more_than_the_chunk_size(self):
        random.seed(21)
        terrain_sow_begin(over=10)
        terrain_spawn_nebula_sphere(0, 0, 0, radius=9000, density_scale=2.0)
        q = terrain_sow_begin(over=10)   # same queue

        biggest = 0
        prev = 0
        while q.pending():
            q._run(1)
            now = len(role("nebula"))
            biggest = max(biggest, now - prev)
            prev = now
        self.assertGreater(prev, NEB_SOW_CHUNK)      # more than one chunk's worth
        self.assertLessEqual(biggest, NEB_SOW_CHUNK)

    def test_chunking_is_deterministic(self):
        random.seed(21)
        terrain_sow_begin(over=10)
        terrain_spawn_nebula_sphere(500, 0, -500, radius=9000, density_scale=2.0)
        terrain_sow_flush()
        first = self.field("nebula")
        self.assertGreater(len(first), NEB_SOW_CHUNK)

        SpaceObject.clear()
        terrain_sow_reset()
        random.seed(21)
        terrain_sow_begin(over=10)
        terrain_spawn_nebula_sphere(500, 0, -500, radius=9000, density_scale=2.0)
        terrain_sow_flush()

        self.assertEqual(first, self.field("nebula"))

    def test_chunks_do_not_replay_the_previous_chunk(self):
        """The trap this design exists to avoid.

        Every chunk of a cluster is queued in the same instant, so they all carry
        the SAME RNG snapshot. If a chunk drew its own per-object values it would
        reproduce the previous chunk's exactly -- visible in-game as the same
        height/size pattern repeating every 8 nebulae. Pre-drawing the whole plan
        is what prevents it.
        """
        random.seed(21)
        terrain_sow_begin(over=10)
        terrain_spawn_nebula_sphere(0, 0, 0, radius=9000, density_scale=2.0)
        terrain_sow_flush()

        # id order is spawn order
        ys = [round(o.pos.y, 6) for o in
              sorted(to_object_list(role("nebula")), key=lambda o: o.id)]
        self.assertGreater(len(ys), NEB_SOW_CHUNK * 2)

        first = ys[:NEB_SOW_CHUNK]
        second = ys[NEB_SOW_CHUNK:NEB_SOW_CHUNK * 2]
        self.assertNotEqual(first, second)


class TestOptIn(SowBase):
    """Nothing changes unless a map asks for it."""

    def test_default_is_immediate(self):
        random.seed(3)
        terrain_asteroid_clusters(3)
        self.assertGreater(len(role("asteroid")), 100)
        self.assertEqual(terrain_sow_pending(), 0)

    def test_sow_end_returns_to_immediate(self):
        terrain_sow_begin(over=6)
        terrain_sow_end()
        random.seed(3)
        terrain_asteroid_clusters(3)
        self.assertGreater(len(role("asteroid")), 100)
        self.assertEqual(terrain_sow_pending(), 0)


class TestReset(SowBase):
    def test_reset_drops_queued_work(self):
        random.seed(3)
        terrain_sow_begin(over=6)
        terrain_asteroid_clusters(3)
        self.assertGreater(terrain_sow_pending(), 0)

        terrain_sow_reset()

        self.assertEqual(terrain_sow_pending(), 0)
        # and sowing is off, so the next mission's terrain is immediate again
        random.seed(3)
        terrain_asteroid_clusters(3)
        self.assertGreater(len(role("asteroid")), 100)

    def test_registered_with_the_reset_ledger(self):
        from sbs_utils.handlerhooks import reset_mission_audit
        random.seed(3)
        terrain_sow_begin(over=6)
        terrain_asteroid_clusters(3)
        # the audit reports non-zero containers by name
        self.assertIn("terrain sow", reset_mission_audit())


class TestDripQueue(SowBase):
    """The generic half, independent of terrain."""

    def test_failing_item_does_not_stop_the_queue(self):
        done = []

        def boom():
            raise ValueError("nope")

        q = DripQueue(over=1, name="test")
        q.add(boom)
        q.add(done.append, ("ok",))
        q.flush()

        self.assertEqual(done, ["ok"])
        self.assertEqual(q.errors, 1)

    def test_clear_runs_nothing(self):
        done = []
        q = DripQueue(over=1, name="test")
        q.add(done.append, ("no",))
        q.clear()
        q.run_slice()
        self.assertEqual(done, [])
        self.assertEqual(q.pending(), 0)

    def test_items_added_mid_drain_still_run(self):
        done = []
        q = DripQueue(over=1, name="test")
        for i in range(4):
            q.add(done.append, (i,))
        self.advance(TickDispatcher.tps // 2)
        q.add(done.append, (99,))
        self.advance(TickDispatcher.tps * 2)
        self.assertEqual(sorted(done), [0, 1, 2, 3, 99])


if __name__ == "__main__":
    unittest.main()
