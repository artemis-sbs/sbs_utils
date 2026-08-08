"""Naming a PLACE so a job can say where its work is (PRM-10, PRM-12).

"I have no idea what asteroids this refers to, or where the shipping lane is." The
description could not say: targets are scattered at runtime, so prose written at
authoring time can only name coordinates that go stale, and there is no
position-to-sector-name helper anywhere. Doug's call was to put a real object in the
world instead - a navarea or navpoint, or a selectable marker built like the nebula
cluster marker when the crew has to click it.

    python -m unittest tests.test_markers
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural.roles import has_role
from sbs_utils.procedural.markers import (
    marker_point, marker_area, marker_object, marker_delete, marker_delete_role)


class MarkerTests(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        SpaceObject.clear()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())

    def test_a_point_is_a_navpoint(self):
        nid = marker_point(100, 0, 200, "Rendezvous")
        self.assertTrue(sbs.sim.navpoint_exists(nid))

    def test_an_area_covers_the_box_a_job_scatters_into(self):
        """size_x/size_z are FULL width and depth, so a job passes the same numbers it
        gave scatter.box and the marker covers exactly what was placed inside it."""
        nid = marker_area(1000, 0, 2000, 4000, 6000, "Shipping Lane")
        area = sbs.sim.get_navpoint_by_id(nid)
        xs = [p[0] for p in area._points]
        zs = [p[1] for p in area._points]
        self.assertEqual((-1000, 3000), (min(xs), max(xs)))
        self.assertEqual((-1000, 5000), (min(zs), max(zs)))

    def test_a_square_area_needs_only_one_size(self):
        nid = marker_area(0, 0, 0, 4000, text="Field")
        area = sbs.sim.get_navpoint_by_id(nid)
        self.assertEqual({-2000, 2000}, {p[0] for p in area._points})
        self.assertEqual({-2000, 2000}, {p[1] for p in area._points})

    def test_a_marker_object_is_selectable_and_off_the_main_screen(self):
        """The nebula-marker recipe: it must be clickable, and it must not hang in space
        in front of the crew on the main view."""
        sd = marker_object(500, 0, 500, "Hazard Rock Field", roles="pr_job_marker")
        self.assertTrue(has_role(sd.id, "marker"))
        self.assertTrue(has_role(sd.id, "pr_job_marker"))
        self.assertEqual(1, sd.data_set.get("elite_main_scn_invis", 0))

    def test_delete_takes_either_kind(self):
        nid = marker_point(0, 0, 0, "Spot")
        sd = marker_object(0, 0, 0, "Thing", roles="tmp")
        marker_delete(nid)
        marker_delete(sd)
        self.assertFalse(sbs.sim.navpoint_exists(nid))

    def test_delete_is_safe_twice(self):
        nid = marker_point(0, 0, 0, "Spot")
        marker_delete(nid)
        marker_delete(nid)
        marker_delete(None)

    def test_a_job_can_clear_its_own_markers_by_role(self):
        marker_object(0, 0, 0, "A", roles="job_marker")
        marker_object(1, 0, 1, "B", roles="job_marker")
        marker_object(2, 0, 2, "C", roles="other_marker")
        self.assertEqual(2, marker_delete_role("job_marker"))
        self.assertEqual(0, marker_delete_role("job_marker"))


if __name__ == "__main__":
    unittest.main()
