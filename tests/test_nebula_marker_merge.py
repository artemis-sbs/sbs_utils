"""Nebula cluster markers are never created and destroyed in the same frame.

The cluster spawner used to place one `nebula_marker` per cluster and then delete the
redundant ones immediately afterwards, inside the same frame. The engine defers adding a
newly spawned object (`Simulation::objectToAddList`), so an object freed before that
add-pass runs can land in `SuperContainer::allList` as a dangling pointer -- which the
per-object slow tick then dereferences. That is the ObjectDataBlob crash-to-desktop
(`ObjectDataBlob::Get` -> `map::operator[]` under `Simulation::Tick`).

The merge is now decided BEFORE anything is spawned, so a marker that would be merged
away is never created. These tests pin that, and pin the merge results the old code
produced so the rewrite is not a behavior change.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.mock import sbs as mock_sbs
from sbs_utils.helpers import FrameContext, Context
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.delete_queue import DeleteQueue
from sbs_utils.vec import Vec3
from sbs_utils.procedural import terrain as terrain_mod
from sbs_utils.procedural.query import object_exists
from sbs_utils.procedural.roles import role


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


class TestNebulaMarkerMerge(unittest.TestCase):
    def setUp(self):
        mock_sbs.create_new_sim()
        SpaceObject.clear()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())
        # Record every marker the run creates, so the test can assert none of them
        # was destroyed again before the frame ended.
        self.spawned = []
        self._real_spawn = terrain_mod._nebula_marker_spawn

        def _recording_spawn(x, y, z, name, color):
            obj = self._real_spawn(x, y, z, name, color)
            self.spawned.append(obj.id)
            return obj

        terrain_mod._nebula_marker_spawn = _recording_spawn

    def tearDown(self):
        terrain_mod._nebula_marker_spawn = self._real_spawn
        DeleteQueue.clear()
        FrameContext.context = None

    def _place(self, positions, colors):
        """The merge itself -- pure, so these cases are exact."""
        terrain_mod._nebula_markers_place(positions, colors, "neb")

    def test_no_marker_is_created_then_destroyed(self):
        """THE POINT OF THE REWRITE. Every marker the run creates outlives the run.

        Goes through the real spawner: `count` clusters are drawn from `points`
        (terrain_value 1 -> 6..12 of them), all inside the merge distance, so the
        old code spawned one marker each and deleted all but one in this frame.
        """
        pts = [Vec3(i * 400, 0, 0) for i in range(12)]
        nebs = terrain_mod.terrain_spawn_nebula_clusters(
            1, points=pts, marker=True, name="neb")
        self.assertTrue(nebs, "no nebulae were spawned at all")
        self.assertTrue(self.spawned, "no markers were spawned at all")
        for mid in self.spawned:
            self.assertTrue(object_exists(mid),
                            f"marker {mid} was created and destroyed in one frame")
        self.assertFalse(DeleteQueue.has_pending(),
                         "a delete was queued during cluster spawn")

    def test_spawner_places_one_marker_per_group(self):
        """End to end: near clusters leave exactly one marker, and it is the one
        that was spawned -- not one survivor out of many."""
        pts = [Vec3(i * 400, 0, 0) for i in range(12)]
        terrain_mod.terrain_spawn_nebula_clusters(1, points=pts, marker=True, name="neb")
        self.assertEqual(1, len(role("nebula_marker")))
        self.assertEqual(1, len(self.spawned))

    def test_close_clusters_collapse_to_one_marker(self):
        """Three near origins fold into a single marker."""
        self._place([Vec3(0, 0, 0), Vec3(2000, 0, 0), Vec3(4000, 0, 0)],
                    ["red", "blue", "red"])
        self.assertEqual(1, len(role("nebula_marker")))
        self.assertEqual(1, len(self.spawned))

    def test_far_clusters_keep_their_own_markers(self):
        """Beyond the merge distance nothing is folded."""
        self._place([Vec3(0, 0, 0), Vec3(60000, 0, 0), Vec3(120000, 0, 0)],
                    ["red", "blue", "green"])
        self.assertEqual(3, len(role("nebula_marker")))

    def test_merge_distance_is_exclusive(self):
        """`<` not `<=`, matching the closest_list test this replaced."""
        self._place([Vec3(0, 0, 0), Vec3(15000, 0, 0)], ["red", "blue"])
        self.assertEqual(2, len(role("nebula_marker")))
        SpaceObject.clear()
        self.spawned.clear()
        self._place([Vec3(0, 0, 0), Vec3(14999, 0, 0)], ["red", "blue"])
        self.assertEqual(1, len(role("nebula_marker")))

    def test_merged_marker_counts_and_labels_every_cluster(self):
        """cluster_counts totals the folded clusters; the label lists their colors
        once each."""
        self._place([Vec3(0, 0, 0), Vec3(2000, 0, 0), Vec3(4000, 0, 0)],
                    ["red", "blue", "red"])
        marker = SpaceObject.get(list(role("nebula_marker"))[0])
        counts = marker.get_inventory_value("cluster_counts")
        self.assertEqual({"red": 2, "blue": 1}, counts)
        self.assertEqual("red,blue", marker.get_inventory_value("cluster_color"))

    def test_merged_marker_sits_at_the_folded_midpoint(self):
        """Position folding is unchanged: mid = (mid + next) * 0.5, in order."""
        self._place([Vec3(0, 0, 0), Vec3(2000, 0, 0), Vec3(4000, 0, 0)],
                    ["red", "blue", "green"])
        marker = SpaceObject.get(list(role("nebula_marker"))[0])
        # (0+2000)/2 = 1000, then (1000+4000)/2 = 2500
        self.assertAlmostEqual(2500.0, Vec3(marker.pos).x, places=3)

    def test_an_older_marker_absorbs_a_new_cluster(self):
        """A marker from an EARLIER frame is still folded into -- and is the one
        kept, so nothing spawned this frame is destroyed."""
        self._place([Vec3(0, 0, 0)], ["red"])
        first = list(role("nebula_marker"))[0]
        self.spawned.clear()
        self._place([Vec3(2000, 0, 0)], ["blue"])
        self.assertEqual([first], list(role("nebula_marker")))
        self.assertEqual([], self.spawned, "a redundant marker was spawned anyway")
        marker = SpaceObject.get(first)
        self.assertEqual({"red": 1, "blue": 1}, marker.get_inventory_value("cluster_counts"))

    def test_marker_false_places_nothing(self):
        """marker=False is still honored."""
        pts = [Vec3(i * 400, 0, 0) for i in range(12)]
        terrain_mod.terrain_spawn_nebula_clusters(1, points=pts, marker=False, name="neb")
        self.assertEqual(0, len(role("nebula_marker")))
        self.assertEqual([], self.spawned)


if __name__ == "__main__":
    unittest.main()
