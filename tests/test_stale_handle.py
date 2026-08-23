"""A deleted agent must not hand out its engine handles any more.

An Agent instance routinely outlives the C++ object it describes - a route task
holds SPAWNED for its whole life, a console task snapshots a roster into a list,
a Modifier stores its target. `_data_set` / `_engine_object` are raw pointers
into memory the engine frees on delete, so a write through a stale instance
lands in whatever now owns that block.

That is what crashed the engine on 2026-08-23: three dumps, all faulting in
ObjectDataBlob::Set on a std::map whose head pointer had been recycled into
other data (zeroes, an ASCII string, packed ints). Dropping the id out of
Agent.all was never enough, because a caller holding the instance never consults
Agent.all - so `->END if to_object(x) is None` was silently inert whenever x was
an object rather than an id.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from cosmos_dev.mock import sbs
from sbs_utils.agent import Agent, CloseData, SpawnData
from sbs_utils.helpers import FrameContext, Context
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural.query import to_object, to_blob
from sbs_utils.procedural.spawn import npc_spawn


class FakeEvent:
    def __init__(self):
        self.client_id = 0
        self.tag = ""
        self.sub_tag = ""
        self.parent_id = 0
        self.origin_id = 0
        self.selected_id = 0
        self.value_tag = ""
        self.extra_tag = ""
        self.extra_extra_tag = ""
        self.sub_float = 0.0
        self.source_point = None
        self.event_time = 0


class TestStaleHandle(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        SpaceObject.clear()

    def _spawn(self, name="Scout"):
        return npc_spawn(0, 0, 0, name, "tsn", "tsn_scout", "behav_npcship")

    def test_live_agent_resolves_and_has_a_blob(self):
        """The control. Without this the rest could pass for the wrong reason."""
        spawned = self._spawn()
        obj = to_object(spawned.id)
        self.assertIsNotNone(obj)
        self.assertIsNotNone(obj.data_set)
        self.assertIsNotNone(to_blob(obj))

    def test_to_object_on_a_deleted_agent_is_none(self):
        """The guard every mission writes. It used to return the dead instance."""
        spawned = self._spawn()
        obj = to_object(spawned.id)
        obj.delete_object()
        self.assertIsNone(to_object(obj))

    def test_deleted_agent_drops_its_engine_handles(self):
        spawned = self._spawn()
        obj = to_object(spawned.id)
        self.assertIsNotNone(obj.data_set)
        obj.delete_object()
        self.assertIsNone(obj.data_set)
        self.assertIsNone(obj.engine_object)

    def test_to_blob_on_a_deleted_agent_is_none(self):
        """`blob = to_blob(x)` then `blob.set(...)` is the crashing shape."""
        spawned = self._spawn()
        obj = to_object(spawned.id)
        obj.delete_object()
        self.assertIsNone(to_blob(obj))

    def test_to_blob_on_a_deleted_spawn_data_is_none(self):
        """SpawnData caches the raw blob at spawn and used to return it blind."""
        spawned = self._spawn()
        self.assertIsNotNone(to_blob(spawned))
        to_object(spawned.id).delete_object()
        self.assertIsNone(to_blob(spawned))
        self.assertIsNone(to_object(spawned))

    def test_to_object_on_a_deleted_close_data_is_none(self):
        """CloseData caches py_object the same way closest() hands it out."""
        spawned = self._spawn()
        obj = to_object(spawned.id)
        close = CloseData(obj.id, obj, 100.0)
        self.assertIsNotNone(to_object(close))
        obj.delete_object()
        self.assertIsNone(to_object(close))

    def test_deleting_by_id_also_tombstones_the_instance(self):
        """Agent.remove_id is the other removal path (grid objects use it)."""
        spawned = self._spawn()
        obj = to_object(spawned.id)
        Agent.remove_id(obj.id)
        self.assertIsNone(to_object(obj))
        self.assertIsNone(obj.data_set)

    def test_respawn_rearms_a_reused_instance(self):
        """add() must clear the tombstone or a recycled instance stays dead."""
        spawned = self._spawn()
        obj = to_object(spawned.id)
        obj.delete_object()
        self.assertIsNone(to_object(obj))
        obj.add()
        self.assertIs(to_object(obj), obj)

    def test_live_agents_cost_no_instance_attribute(self):
        """_alive must stay a CLASS attribute for live agents - this sits on the
        per-tick query path and object_exists regressed measurably once from
        doing real work here."""
        spawned = self._spawn()
        obj = to_object(spawned.id)
        self.assertNotIn("_alive", vars(obj))
        obj.delete_object()
        self.assertIn("_alive", vars(obj))


if __name__ == "__main__":
    unittest.main()


class _RecordingSbs:
    """Captures send_client_widget_rects calls."""
    def __init__(self):
        self.rects = []

    def send_client_widget_rects(self, client_id, widget, *coords):
        self.rects.append((client_id, widget, coords))


class TestRetireDroppedEngineWidgets(unittest.TestCase):
    """An engine widget cannot be un-declared, so one dropped from a console's
    widget list carries on drawing against whatever object the console was last
    pointed at. When that object has been deleted the engine walks freed memory -
    a client died in ViewGridObjectListDraw that way, two minutes after the
    mission ended, still drawing the Engineering grid list for a dead ship.
    """
    def _retire(self, prev, current):
        from sbs_utils.mast_sbs.maststorypage import StoryPage
        rec = _RecordingSbs()
        StoryPage._retire_dropped_engine_widgets(prev, current, 7, rec)
        return [w for _cid, w, _c in rec.rects]

    def test_widgets_dropped_from_the_list_are_pushed_offscreen(self):
        retired = self._retire(("engineering", "ship_internal_view^grid_object_list"),
                               ("", ""))
        self.assertCountEqual(retired, ["ship_internal_view", "grid_object_list"])

    def test_widgets_still_declared_are_left_alone(self):
        retired = self._retire(("engineering", "ship_internal_view^grid_object_list"),
                               ("helm", "ship_internal_view"))
        self.assertEqual(retired, ["grid_object_list"])

    def test_no_previous_list_retires_nothing(self):
        self.assertEqual(self._retire(None, ("helm", "2dview")), [])

    def test_unchanged_widgets_retire_nothing(self):
        self.assertEqual(self._retire(("helm", "2dview"), ("weapons", "2dview")), [])

    def test_offscreen_rect_is_outside_the_visible_area(self):
        from sbs_utils.mast_sbs.maststorypage import StoryPage
        rec = _RecordingSbs()
        StoryPage._retire_dropped_engine_widgets(("engi", "grid_object_list"), ("", ""), 7, rec)
        _cid, _w, coords = rec.rects[0]
        self.assertTrue(all(c >= 100 for c in coords), coords)
