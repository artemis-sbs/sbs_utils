from cosmos_dev.mock import sbs as sbs
import unittest

from sbs_utils.spaceobject import SpaceObject
from sbs_utils.gridobject import GridObject
from sbs_utils.objects import Npc
from sbs_utils.delete_queue import DeleteQueue
from sbs_utils.procedural.query import to_object, object_exists
from sbs_utils.procedural.space_objects import delete_object, delete_objects_box
from sbs_utils.procedural.grid import grid_delete_object
from sbs_utils.agent import Agent
from sbs_utils.fs import test_set_exe_dir
from sbs_utils.helpers import FrameContext, Context, FakeEvent

test_set_exe_dir()


def engine_alive(id):
    """Raw engine liveness, bypassing the tombstone short-circuit in object_exists."""
    return FrameContext.context.sim.space_object_exists(id) != 0


def grid_alive(host_id, gid):
    """Raw engine liveness of a grid object, bypassing the tombstone."""
    hm = FrameContext.context.sbs.get_hull_map(host_id)
    return hm is not None and hm.get_grid_object_by_id(gid) is not None


class TestDeleteQueue(unittest.TestCase):
    def setUp(self):
        SpaceObject.clear()
        DeleteQueue.clear()
        test_set_exe_dir()
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())

    def spawn_npc(self, name="DS1"):
        sd = Npc().spawn(0, 0, 0, name, "tsn", "Starbase", "behav_spaceport")
        return sd.py_object

    def spawn_grid(self, host_id, name="Room", tag="r1"):
        go = GridObject()
        go.spawn(host_id, name, tag, 1, 1, 5, "white", "room")
        return go

    def test_delete_is_deferred_not_immediate(self):
        obj = self.spawn_npc()
        oid = obj.id
        self.assertTrue(object_exists(oid))
        self.assertTrue(engine_alive(oid))

        obj.delete_object()

        # Tombstoned immediately: logically gone to every guarded caller...
        self.assertFalse(object_exists(oid), "object_exists must report gone at once")
        self.assertIsNone(to_object(oid), "to_object must resolve to None at once")
        self.assertIsNone(Agent.get(oid), "agent dropped from Agent.all at once")
        self.assertTrue(DeleteQueue.is_pending(oid))

        # ...but the native memory is STILL ALIVE (this is the whole point:
        # another task holding the object this tick reads valid memory, no UAF).
        self.assertTrue(engine_alive(oid), "native object must survive until drain")

    def test_drain_frees_the_native_object(self):
        obj = self.spawn_npc()
        oid = obj.id
        obj.delete_object()
        self.assertTrue(engine_alive(oid))

        DeleteQueue.drain()

        self.assertFalse(engine_alive(oid), "drain must free the native object")
        self.assertFalse(DeleteQueue.has_pending())
        self.assertFalse(object_exists(oid))

    def test_double_delete_is_a_noop(self):
        obj = self.spawn_npc()
        oid = obj.id
        obj.delete_object()
        # Second delete via the procedural entry: agent already gone -> skipped.
        delete_object(oid)
        DeleteQueue.drain()
        # A second drain on an already-freed id must not raise.
        DeleteQueue.drain()
        self.assertFalse(engine_alive(oid))

    def test_box_delete_routes_through_queue(self):
        a = self.spawn_npc("A")
        b = self.spawn_npc("B")
        aid, bid = a.id, b.id

        delete_objects_box(0, 0, 0, 100, 100, 100, broad_type=0xffff)

        # Both tombstoned at once, both still natively alive until the drain.
        self.assertFalse(object_exists(aid))
        self.assertFalse(object_exists(bid))
        self.assertTrue(engine_alive(aid))
        self.assertTrue(engine_alive(bid))
        self.assertTrue(DeleteQueue.is_pending(aid))
        self.assertTrue(DeleteQueue.is_pending(bid))

        DeleteQueue.drain()
        self.assertFalse(engine_alive(aid))
        self.assertFalse(engine_alive(bid))

    def test_clear_drops_pending_without_freeing(self):
        obj = self.spawn_npc()
        oid = obj.id
        obj.delete_object()
        self.assertTrue(DeleteQueue.is_pending(oid))

        DeleteQueue.clear()   # fresh mission / recompile

        self.assertFalse(DeleteQueue.has_pending())
        self.assertFalse(DeleteQueue.is_pending(oid))

    # ----- grid objects -----------------------------------------------------

    def test_grid_delete_is_deferred_not_immediate(self):
        host = self.spawn_npc("Host")
        go = self.spawn_grid(host.id)
        gid = go.id
        self.assertTrue(grid_alive(host.id, gid))

        go.delete_object()

        # Tombstoned immediately...
        self.assertIsNone(Agent.get(gid), "grid agent dropped from Agent.all at once")
        self.assertIsNone(to_object(gid), "to_object must resolve to None at once")
        self.assertTrue(DeleteQueue.is_pending(gid))
        # ...but the native grid object is STILL ALIVE until the drain.
        self.assertTrue(grid_alive(host.id, gid), "native grid object must survive until drain")

    def test_grid_drain_frees_the_native_object(self):
        host = self.spawn_npc("Host")
        go = self.spawn_grid(host.id)
        gid = go.id
        go.delete_object()
        self.assertTrue(grid_alive(host.id, gid))

        DeleteQueue.drain()

        self.assertFalse(grid_alive(host.id, gid), "drain must free the native grid object")
        self.assertFalse(DeleteQueue.has_pending())

    def test_has_pending_covers_grid_only(self):
        # Regression: the handler drain gate must fire when ONLY grid deletes are
        # queued (an early version checked _pending, missing _pending_grid).
        host = self.spawn_npc("Host")
        go = self.spawn_grid(host.id)
        go.delete_object()
        self.assertFalse(DeleteQueue._pending, "no space-object deletes queued")
        self.assertTrue(DeleteQueue.has_pending(), "grid-only queue must report pending")

    def test_grid_delete_object_helper_defers(self):
        # The procedural helper works on a bare id (the id-based call sites).
        host = self.spawn_npc("Host")
        go = self.spawn_grid(host.id)
        gid = go.id

        grid_delete_object(host.id, gid)

        self.assertIsNone(Agent.get(gid))
        self.assertTrue(DeleteQueue.is_pending(gid))
        self.assertTrue(grid_alive(host.id, gid))

        DeleteQueue.drain()
        self.assertFalse(grid_alive(host.id, gid))

    def test_grid_clear_drops_pending_without_freeing(self):
        host = self.spawn_npc("Host")
        go = self.spawn_grid(host.id)
        gid = go.id
        go.delete_object()
        self.assertTrue(DeleteQueue.is_pending(gid))

        DeleteQueue.clear()

        self.assertFalse(DeleteQueue.has_pending())
        self.assertFalse(DeleteQueue.is_pending(gid))
        # Still natively alive — clear drops the queue, it does not free.
        self.assertTrue(grid_alive(host.id, gid))


if __name__ == "__main__":
    unittest.main()
