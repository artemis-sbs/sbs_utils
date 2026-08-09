"""mount primitive - the weld registry, lifecycle, and cleanup.

The PHYSICS is engine-native and engine-verified: `LM_TestRange/maps/test_tractor_mount.mast`
measured a mount held at exactly 200.0u and exactly 0.0 deg off the host's nose while the
host's heading swung 51 deg. The mock's _physics_tractors is only our model of that, so
asking it "does the weld hold?" would be circular.

What these cover is the Python we own: that the engine call is made once with the right
offset, that host<->mount bookkeeping survives detach/delete/id-recycle, and that
`delete_with_host` is honored per mount.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.mock import sbs
from tests.reset_helper import reset_mock
from sbs_utils.procedural.query import object_exists, to_id, to_object
from sbs_utils.procedural.spawn import npc_spawn
from sbs_utils.procedural import mount as mt


class MountTestBase(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        self.host = to_id(npc_spawn(0, 0, 0, "Host", "tsn", "tsn_light_cruiser", "behav_npcship"))
        self.pod = to_id(npc_spawn(0, 0, 0, "Pod", "tsn", "tsn_fighter", "behav_station"))

    def tearDown(self):
        mt.mount_clear_all()

    def _connected(self, host, mount):
        try:
            return sbs.sim.GetTractorConnection(host, mount) is not None
        except Exception:
            return False


class TestMountAttach(MountTestBase):
    def test_attach_creates_the_engine_connection(self):
        self.assertEqual(mt.mount_attach(self.host, self.pod, (0, 0, 200)), self.pod)
        self.assertTrue(self._connected(self.host, self.pod))

    def test_attach_records_both_directions(self):
        mt.mount_attach(self.host, self.pod, (0, 0, 200))
        self.assertEqual(mt.mount_host_of(self.pod), self.host)
        self.assertIn(self.pod, mt.mount_list(self.host))
        self.assertTrue(mt.mount_is(self.pod))

    def test_offset_round_trips(self):
        mt.mount_attach(self.host, self.pod, (10, -20, 30))
        off = mt.mount_offset(self.host, self.pod)
        self.assertEqual((off.x, off.y, off.z), (10, -20, 30))

    def test_offset_accepts_a_vec3(self):
        mt.mount_attach(self.host, self.pod, sbs.vec3(1, 2, 3))
        off = mt.mount_offset(self.host, self.pod)
        self.assertEqual((off.x, off.y, off.z), (1, 2, 3))

    def test_attach_to_missing_object_returns_none(self):
        self.assertIsNone(mt.mount_attach(self.host, 0))
        self.assertIsNone(mt.mount_attach(0, self.pod))

    def test_cannot_mount_something_on_itself(self):
        self.assertIsNone(mt.mount_attach(self.host, self.host))

    def test_set_offset_moves_it(self):
        mt.mount_attach(self.host, self.pod, (0, 0, 200))
        # The engine connection carries its offset from creation, so this must
        # re-create it - a silent no-op here would leave the mount where it was.
        self.assertIsNotNone(mt.mount_set_offset(self.host, self.pod, (0, 0, 500)))
        off = mt.mount_offset(self.host, self.pod)
        self.assertEqual(off.z, 500)
        self.assertTrue(self._connected(self.host, self.pod))


class TestMountSpawn(MountTestBase):
    def test_spawn_creates_and_welds(self):
        mid = mt.mount_spawn(self.host, "tsn_fighter", (0, 0, 120), name="Turret")
        self.assertIsNotNone(mid)
        self.assertEqual(mt.mount_host_of(mid), self.host)
        self.assertTrue(self._connected(self.host, mid))

    def test_spawn_inherits_the_host_side(self):
        mid = mt.mount_spawn(self.host, "tsn_fighter", (0, 0, 120))
        self.assertEqual(to_object(mid).side, to_object(self.host).side)

    def test_ring_spawns_the_requested_count(self):
        ids = mt.mount_ring(self.host, "tsn_fighter", 4, radius=100)
        self.assertEqual(len(ids), 4)
        self.assertEqual(len(mt.mount_list(self.host)), 4)

    def test_ring_offsets_are_distinct(self):
        ids = mt.mount_ring(self.host, "tsn_fighter", 4, radius=100)
        offs = {(round(mt.mount_offset(self.host, i).x, 3),
                 round(mt.mount_offset(self.host, i).z, 3)) for i in ids}
        self.assertEqual(len(offs), 4)

    def test_ring_on_a_missing_host_is_empty(self):
        self.assertEqual(mt.mount_ring(0, "tsn_fighter", 4), [])


class TestMountDetach(MountTestBase):
    def test_detach_drops_the_connection_and_the_links(self):
        mt.mount_attach(self.host, self.pod, (0, 0, 200))
        mt.mount_detach(self.host, self.pod)
        self.assertFalse(self._connected(self.host, self.pod))
        self.assertIsNone(mt.mount_host_of(self.pod))
        self.assertNotIn(self.pod, mt.mount_list(self.host))
        self.assertTrue(object_exists(self.pod))

    def test_detach_can_delete(self):
        mt.mount_attach(self.host, self.pod, (0, 0, 200))
        mt.mount_detach(self.host, self.pod, delete=True)
        self.assertFalse(object_exists(self.pod))

    def test_detach_without_naming_the_host(self):
        mt.mount_attach(self.host, self.pod, (0, 0, 200))
        mt.mount_detach(None, self.pod)
        self.assertIsNone(mt.mount_host_of(self.pod))

    def test_detach_all_honors_each_mounts_own_flag(self):
        keep = to_id(npc_spawn(0, 0, 0, "Keep", "tsn", "tsn_fighter", "behav_station"))
        mt.mount_attach(self.host, self.pod, (0, 0, 200), delete_with_host=True)
        mt.mount_attach(self.host, keep, (0, 0, -200), delete_with_host=False)
        mt.mount_detach_all(self.host, delete=None)
        self.assertFalse(object_exists(self.pod))
        self.assertTrue(object_exists(keep))

    def test_detach_all_can_force_keep(self):
        mt.mount_attach(self.host, self.pod, (0, 0, 200), delete_with_host=True)
        mt.mount_detach_all(self.host, delete=False)
        self.assertTrue(object_exists(self.pod))

    def test_clear_all_releases_without_deleting(self):
        mt.mount_attach(self.host, self.pod, (0, 0, 200))
        mt.mount_clear_all()
        self.assertEqual(mt.mount_count(), 0)
        self.assertTrue(object_exists(self.pod))


class TestMountLifecycle(MountTestBase):
    def test_count_tracks_live_welds(self):
        self.assertEqual(mt.mount_count(), 0)
        mt.mount_attach(self.host, self.pod, (0, 0, 200))
        self.assertEqual(mt.mount_count(), 1)
        mt.mount_detach(self.host, self.pod)
        self.assertEqual(mt.mount_count(), 0)

    def test_destroyed_host_takes_its_mounts_with_it(self):
        mt.mount_attach(self.host, self.pod, (0, 0, 200), delete_with_host=True)
        mt._mount_on_destroy(to_object(self.host))
        self.assertFalse(object_exists(self.pod))
        self.assertEqual(mt.mount_count(), 0)

    def test_destroyed_host_leaves_debris_when_asked(self):
        mt.mount_attach(self.host, self.pod, (0, 0, 200), delete_with_host=False)
        mt._mount_on_destroy(to_object(self.host))
        self.assertTrue(object_exists(self.pod))
        self.assertIsNone(mt.mount_host_of(self.pod))

    def test_destroyed_mount_is_removed_from_its_host(self):
        mt.mount_attach(self.host, self.pod, (0, 0, 200))
        mt._mount_on_destroy(to_object(self.pod))
        self.assertNotIn(self.pod, mt.mount_list(self.host))

    def test_deleting_the_mount_object_leaves_no_live_weld(self):
        # Agent._remove purges the deleted agent's own links, which is why this module
        # keeps no module-level registry that could outlive the object.
        mt.mount_attach(self.host, self.pod, (0, 0, 200))
        sbs.delete_object(self.pod)
        self.assertEqual(mt.mount_count(), 0)

    def test_a_deleted_host_reads_as_no_host(self):
        # A scripted delete fires no destroy event, so the dangling link must not be
        # mistaken for a live weld.
        mt.mount_attach(self.host, self.pod, (0, 0, 200))
        sbs.delete_object(self.host)
        self.assertIsNone(mt.mount_host_of(self.pod))
        self.assertEqual(mt.mount_count(), 0)

    def test_prune_orphans_cleans_up_after_a_scripted_delete(self):
        mt.mount_attach(self.host, self.pod, (0, 0, 200), delete_with_host=True)
        sbs.delete_object(self.host)
        self.assertEqual(mt.mount_prune_orphans(), [self.pod])
        self.assertFalse(object_exists(self.pod))

    def test_prune_orphans_leaves_debris_mounts_alone(self):
        mt.mount_attach(self.host, self.pod, (0, 0, 200), delete_with_host=False)
        sbs.delete_object(self.host)
        mt.mount_prune_orphans()
        self.assertTrue(object_exists(self.pod))
        self.assertIsNone(mt.mount_host_of(self.pod))

    def test_prune_ignores_healthy_mounts(self):
        mt.mount_attach(self.host, self.pod, (0, 0, 200))
        self.assertEqual(mt.mount_prune_orphans(), [])
        self.assertTrue(object_exists(self.pod))

    def test_host_of_an_unmounted_object_is_none(self):
        self.assertIsNone(mt.mount_host_of(self.pod))
        self.assertFalse(mt.mount_is(self.pod))


if __name__ == "__main__":
    unittest.main()
