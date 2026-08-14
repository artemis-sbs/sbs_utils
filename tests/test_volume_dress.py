"""`volume_dress` - the props, their size, and which way they face.

The three claims the look rests on, each of which was wrong before and silently so:

* a prop is sized to the SPACING it has, not to the room it is in (rocks bigger than the
  gaps between them are what made a station read as a gravel field);
* an oriented prop's local +Z lands on the surface normal, so a flat mesh lies ON the
  wall rather than floating near it;
* a part can wear a different look from its relic, which is the field that parsed, passed
  lint, and then did nothing at all.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import math
import unittest

import sbs_utils.mast_sbs.story_nodes  # noqa: F401 - import first, circular import

from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural.query import to_object
from sbs_utils.procedural.roles import role
from sbs_utils.procedural.volume import (volume_define, volume_box, volume_chamber,
                                         volume_solid, volume_align_quat,
                                         volume_surface_points)
from sbs_utils.procedural.volume_dress import volume_dress, volume_style_names, STYLES


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


def _rotate_z(q):
    """Where a quaternion `(w, x, y, z)` sends local +Z."""
    w, x, y, z = q
    return (2.0 * (x * z + w * y), 2.0 * (y * z - w * x), 1.0 - 2.0 * (x * x + y * y))


class TestAlignQuat(unittest.TestCase):
    def test_local_z_lands_on_the_direction(self):
        for d in ((0, 1, 0), (0, -1, 0), (1, 0, 0), (0, 0, 1), (0.3, -0.5, 0.81)):
            length = math.sqrt(sum(c * c for c in d))
            unit = tuple(c / length for c in d)
            got = _rotate_z(volume_align_quat(d))
            for a, b in zip(got, unit):
                self.assertAlmostEqual(a, b, places=5, msg=f"aligning to {d}")

    def test_straight_up_does_not_collapse(self):
        # The frame's degenerate case: a vertical shaft is exactly where the naive
        # cross product is zero, and a collapsed frame dresses a shaft as a flat disc.
        got = _rotate_z(volume_align_quat((0.0, 1.0, 0.0)))
        self.assertAlmostEqual(got[1], 1.0, places=5)

    def test_roll_spins_about_the_axis_it_was_given(self):
        # A roll must not move the face - only what is drawn on it.
        for roll in (0.0, 1.0, 2.5):
            got = _rotate_z(volume_align_quat((0, 0, 1), roll))
            self.assertAlmostEqual(got[2], 1.0, places=5)

    def test_a_zero_direction_is_no_rotation_rather_than_a_crash(self):
        self.assertEqual(volume_align_quat((0.0, 0.0, 0.0)), (1.0, 0.0, 0.0, 0.0))


class TestDressing(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        SpaceObject.clear()
        volume_define("t", {})
        volume_box("t", "hall", 0, 0, 0, 1400, 420, 420)

    def _props(self):
        return [to_object(i) for i in role("wall")]

    def _coeffs(self, so):
        ds = so.data_set
        return (ds.get("local_scale_x_coeff", 0), ds.get("local_scale_y_coeff", 0),
                ds.get("local_scale_z_coeff", 0))

    def test_scenery_is_not_a_contact(self):
        # A relic lays hundreds of pieces. Every one of them used to arrive in the science
        # list and under the weapons cursor, because nothing marked them. Visible, yes -
        # targetable, no. (Not `elite_main_scn_invis`: that would hide the wall.)
        from sbs_utils.procedural.volume import volume_solid
        volume_solid("t", "box", 0, 0, 0, 200, 200, 200)
        volume_dress("t", n=120, seed=3, style="plates", roles="wall", debris=10)
        props = self._props()
        self.assertGreater(len(props), 10)
        for so in props:
            self.assertEqual(so.data_set.get("unselectable", 0), 1,
                             "a wall, a mass or a rock is scenery, not a contact")
            self.assertNotEqual(so.data_set.get("elite_main_scn_invis", 0), 1,
                                "scenery must stay VISIBLE on the main screen")

    def test_it_makes_props_and_they_are_not_solid(self):
        made = volume_dress("t", n=60, seed=3, style="plates", roles="wall")
        self.assertGreater(made, 0)
        for so in self._props():
            self.assertEqual(so.engine_object.exclusion_radius, 0,
                             "a wall prop with a radius pushes the ship off the wall")

    def test_a_plate_is_a_slab_not_a_cube(self):
        volume_dress("t", n=60, seed=3, style="plates", roles="wall")
        sx, sy, sz = self._coeffs(self._props()[0])
        # rectangle is 100 x 100 x 1.25, so world thickness is sz * 1.25.
        across, through = sx * 100.0, sz * 1.25
        self.assertGreater(across, through * 4.0,
                           "a plate must be much wider than it is thick")

    def test_size_follows_the_spacing_on_a_curved_wall(self):
        # A chamber is TILED - a sphere cannot be panelled - so there the budget still
        # sets the size: more props means smaller props. (A box is panelled instead, and
        # its slabs are sized by the room; see the panel tests below.)
        volume_define("c", {"room": (0, 0, 0, 1200)})
        volume_dress("c", n=40, seed=3, style="plates", roles="wall")
        sparse = self._coeffs(self._props()[0])[0]
        SpaceObject.clear()
        volume_define("c", {"room": (0, 0, 0, 1200)})
        volume_dress("c", n=400, seed=3, style="plates", roles="wall")
        dense = self._coeffs(self._props()[0])[0]
        self.assertLess(dense, sparse,
                        "ten times the props must be smaller, or they overlap into mush")

    def test_one_plate_per_surface_when_a_plate_is_big_enough(self):
        # THE contract, at its simplest: block the space out, then lay wall primitives on
        # it. With a plate bigger than the room, that is one piece per wall, floor and
        # ceiling - six - each exactly its surface. The hall is 2800 x 840 x 840.
        volume_dress("t", n=600, seed=3, style="plates", roles="wall", plate=9000)
        self.assertEqual(len(self._props()), 6)
        got = sorted((round(self._coeffs(so)[0] * 100.0),
                      round(self._coeffs(so)[1] * 100.0)) for so in self._props())
        self.assertEqual(got, [(840, 840), (840, 840),
                               (2800, 840), (2800, 840), (2800, 840), (2800, 840)])

    def test_a_wall_is_laid_up_out_of_plates(self):
        # And in practice it is not one quad: the engine does not cope with big planes
        # overlapping, and a ruin should have pieces missing. So a surface is tiled with
        # plates of about `plate` across - regular, coplanar, edge to edge.
        volume_dress("t", n=600, seed=3, style="plates", roles="wall", plate=700)
        props = self._props()
        self.assertGreater(len(props), 6, "a wall of one huge quad is what this replaced")
        for so in props:
            wide = self._coeffs(so)[0] * 100.0
            tall = self._coeffs(so)[1] * 100.0
            self.assertLessEqual(max(wide, tall), 1000.0,
                                 "a plate must stay near the size asked for")

    def test_plates_tile_a_surface_rather_than_overlapping(self):
        # The distinction from the confetti this replaced: those were sized to overlap by
        # 24% and rolled at random. These tile - so the plate area on one face adds up to
        # that face's area, near enough, instead of half again.
        volume_dress("t", n=600, seed=3, style="plates", roles="wall", plate=700)
        area = 0.0
        for so in self._props():
            if abs(so.pos.y - 420.0) > 1.0:          # the +Y face only
                continue
            area += (self._coeffs(so)[0] * 100.0) * (self._coeffs(so)[1] * 100.0)
        self.assertAlmostEqual(area, 2800.0 * 840.0, delta=1.0)

    def test_gaps_leave_plates_out(self):
        # A wall with nothing missing from it is a wall, not a wreck.
        volume_dress("t", n=600, seed=3, style="plates", roles="wall", plate=700)
        whole = len(self._props())
        SpaceObject.clear()
        volume_define("t", {})
        volume_box("t", "hall", 0, 0, 0, 1400, 420, 420)
        volume_dress("t", n=600, seed=3, style="plates", roles="wall", plate=700,
                     gaps=0.35)
        self.assertLess(len(self._props()), whole)

    def test_the_budget_does_not_change_a_wall(self):
        # A wall is sized by its surface, so `n` - which drives the tiled path - must not
        # touch it. Ten times the budget, same six pieces, same size.
        volume_dress("t", n=600, seed=3, style="plates", roles="wall")
        first = sorted(round(self._coeffs(so)[0], 6) for so in self._props())
        SpaceObject.clear()
        volume_define("t", {})
        volume_box("t", "hall", 0, 0, 0, 1400, 420, 420)
        volume_dress("t", n=60, seed=3, style="plates", roles="wall")
        self.assertEqual(sorted(round(self._coeffs(so)[0], 6)
                                for so in self._props()), first)

    def test_a_wall_piece_lies_on_its_surface(self):
        # ON the plane, not floating outside it: the piece IS the wall. It used to be
        # pushed half its own thickness clear and to overrun the face by a wall
        # thickness at every edge, which is what made every corner sprout a fin.
        volume_dress("t", n=600, seed=3, style="plates", roles="wall")
        half = (1400.0, 420.0, 420.0)
        for so in self._props():
            p = (so.pos.x, so.pos.y, so.pos.z)
            axis = max(range(3), key=lambda i: abs(p[i]) / half[i])
            self.assertAlmostEqual(abs(p[axis]), half[axis], places=3)

    def test_a_panel_is_never_rolled(self):
        # A quarter turn swaps a non-square slab's width and height, and the scale is
        # applied after the rotation - so a rolled panel comes out the wrong shape.
        volume_dress("t", n=60, seed=3, style="plates", roles="wall")
        for so in self._props():
            q = so.engine_object.rot_quat
            face = _rotate_z((q.w, q.x, q.y, q.z))
            self.assertGreater(max(abs(c) for c in face), 0.99)

    def test_a_swallowed_wall_is_simply_not_built(self):
        # Two rooms overlapping means no wall between them at all - the boolean union of
        # a blockout. The hall's far cap is inside the second room, so that surface has
        # no piece, and the corridor is open into the hall it runs into.
        volume_box("t", "annex", 2400, 0, 0, 1300, 500, 1300)
        volume_dress("t", n=60, seed=3, style="plates", roles="wall")
        # No piece may sit at x = +1400: that cap is the doorway.
        caps = [so for so in self._props() if abs(so.pos.x - 1400.0) < 1.0]
        self.assertEqual(caps, [], "a wall across the doorway seals the rooms apart")
        self.assertGreater(len(self._props()), 6, "the annex still has walls of its own")

    def test_a_corner_bite_leaves_a_wall_with_a_hole(self):
        # The other case, and the reason the face is tested cell by cell rather than as a
        # whole: a room that overlaps only a CORNER of this one takes a bite out of the
        # wall, and what is left is the pieces around the hole - what a door primitive
        # leaves behind. All of them must still be wall, not doorway.
        from sbs_utils.procedural.volume import volume_depth
        volume_box("t", "bite", 1300, 0, 800, 500, 200, 500)
        volume_dress("t", n=60, seed=3, style="plates", roles="wall")
        for so in self._props():
            self.assertGreaterEqual(
                volume_depth("t", (so.pos.x, so.pos.y, so.pos.z)), -1.0,
                "a piece standing in the opening is the bug this replaced")

    def test_a_subtracted_box_is_one_cube(self):
        # A pillar is looked AT, not flown inside, so it is the shape at its size - not
        # fifty little plates wrapped around a crate.
        from sbs_utils.procedural.volume import volume_solid
        volume_solid("t", "box", 0, 0, 0, 200, 200, 200)
        volume_dress("t", n=60, seed=3, style="plates", roles="wall")
        cubes = [so for so in self._props()
                 if so.engine_object._data_tag == "generic-cube"]
        self.assertEqual(len(cubes), 1)
        sx, sy, sz = self._coeffs(cubes[0])
        self.assertAlmostEqual(sx * 40.0, 400.0, places=3)   # cube is 40 a side at 1
        self.assertAlmostEqual(sz * 40.0, 400.0, places=3)

    def test_debris_lands_inside_the_rooms(self):
        volume_dress("t", n=60, seed=3, style="plates", roles="wall", debris=20)
        from sbs_utils.procedural.volume import volume_depth
        inside = [so for so in self._props()
                  if volume_depth("t", (so.pos.x, so.pos.y, so.pos.z)) < -100]
        self.assertGreater(len(inside), 5, "a clean empty box does not read as a ruin")

    def test_neighbours_overlap_rather_than_leaving_gaps(self):
        # A wall of exactly-touching tiles shows a seam at every joint the moment one
        # jitters; every style is deliberately over 1.0 across.
        for name, spec in STYLES.items():
            if spec is None:
                continue
            self.assertGreaterEqual(spec.across, 1.0, f"{name} would leave gaps")

    def test_every_wall_piece_faces_into_the_room(self):
        # Six surfaces, six pieces, each lying flat on its own wall and turned to face
        # the crew. Anything else and you are looking at the back of a wall.
        volume_dress("t", n=120, seed=5, style="plates", roles="wall")
        half = (1400.0, 420.0, 420.0)
        seen = set()
        for so in self._props():
            q = so.engine_object.rot_quat
            face = _rotate_z((q.w, q.x, q.y, q.z))
            p = (so.pos.x, so.pos.y, so.pos.z)
            axis = max(range(3), key=lambda i: abs(face[i]))
            self.assertAlmostEqual(abs(face[axis]), 1.0, places=3,
                                   msg="a piece on an axis-aligned box must be aligned")
            self.assertAlmostEqual(abs(p[axis]), half[axis], places=3,
                                   msg="a wall piece lies on its wall")
            self.assertLess(p[axis] * face[axis], 0.0,
                            "a wall piece must face into the room, not out of it")
            seen.add((axis, 1 if p[axis] > 0 else -1))
        self.assertEqual(len(seen), 6, "all six surfaces must be built, once each")

    def test_a_wall_is_at_least_as_deep_as_the_tolerance_it_covers(self):
        # Containment lets a ship push a whole scrape band past the boundary. A wall
        # thinner than that is a skin: the ship crosses it and comes out the far side,
        # which is what "I flew through the wall" actually was.
        volume_dress("t", n=60, seed=3, style="plates", roles="wall", wall_depth=220)
        sz = self._coeffs(self._props()[0])[2]
        self.assertGreaterEqual(sz * 1.25, 220.0 - 1.0)

    def test_nothing_juts_into_the_space_you_fly_through(self):
        from sbs_utils.procedural.volume import volume_depth
        volume_dress("t", n=120, seed=3, style="plates", roles="wall", wall_depth=220)
        for so in self._props():
            self.assertGreaterEqual(
                volume_depth("t", (so.pos.x, so.pos.y, so.pos.z)), -1.0,
                "a wall prop standing inside the room is an obstacle you cannot see")

    def test_rock_is_left_unoriented(self):
        volume_dress("t", n=60, seed=3, style="rock", roles="wall")
        turned = 0
        for so in self._props():
            q = so.engine_object.rot_quat
            if abs(q.w - 1.0) > 1e-9 or abs(q.x) + abs(q.y) + abs(q.z) > 1e-9:
                turned += 1
        self.assertEqual(turned, 0, "a boulder has no face to point at anything")

    def test_a_part_may_wear_a_different_look(self):
        volume_box("t", "shaft", 6000, 0, 0, 380, 1400, 380)
        volume_dress("t", n=200, seed=9, style="plates", roles="wall",
                     part_styles={"shaft": "ribs"})
        arts = {so.engine_object._data_tag for so in self._props()}
        self.assertIn("generic-rectangle", arts)
        self.assertIn("generic-cylinder", arts, "the per-part style did nothing")

    def test_explicit_art_beats_the_style(self):
        volume_dress("t", n=40, seed=3, style="plates", art="plain_asteroid_6",
                     roles="wall")
        arts = {so.engine_object._data_tag for so in self._props()}
        self.assertEqual(arts, {"plain_asteroid_6"},
                         "naming a mesh is deliberate and must win")

    def test_style_none_builds_nothing(self):
        self.assertEqual(volume_dress("t", n=60, seed=3, style="none", roles="wall"), 0)

    def test_an_unknown_style_falls_back_rather_than_failing(self):
        # A typo should be a plain wall, not a mission that will not start.
        self.assertGreater(volume_dress("t", n=40, seed=3, style="wibble", roles="wall"), 0)

    def test_a_subtracted_mass_is_dressed_too(self):
        # An undressed pillar is an invisible obstacle: containment stops the ship at
        # something with nothing there to see.
        volume_define("s", {})
        volume_chamber("s", "room", 0, 0, 0, 1200)
        volume_solid("s", "sphere", 0, 0, 0, 300)
        before = volume_dress("s", n=60, seed=4, style="rock", roles="wall", solids=False)
        SpaceObject.clear()
        after = volume_dress("s", n=60, seed=4, style="rock", roles="wall", solids=True)
        self.assertGreater(after, before)

    def test_it_is_deterministic(self):
        volume_dress("t", n=80, seed=11, style="plates", roles="wall")
        first = sorted((round(o.pos.x, 3), round(o.pos.y, 3)) for o in self._props())
        SpaceObject.clear()
        volume_define("t", {})
        volume_box("t", "hall", 0, 0, 0, 1400, 420, 420)
        volume_dress("t", n=80, seed=11, style="plates", roles="wall")
        second = sorted((round(o.pos.x, 3), round(o.pos.y, 3)) for o in self._props())
        self.assertEqual(first, second, "a relic must look the same every run")

    def test_every_style_names_itself(self):
        for name in volume_style_names():
            self.assertIn(name, STYLES)


class TestEvenBoxFaces(unittest.TestCase):
    """A flat face is where clumping shows worst - the eye reads a plane and finds the
    holes. Spheres have been sampled evenly since the beginning; boxes were uniform
    random until the dressing work."""

    def test_a_face_is_covered_more_evenly_than_chance(self):
        volume_define("b", {})
        volume_box("b", "wall", 0, 0, 0, 1000, 100, 1000)
        pts = [p for p in volume_surface_points("b", 240, seed=2)
               if p[4] > 0.5]            # the +Y face only
        self.assertGreater(len(pts), 20)
        # Quarter the face and count. An even sampler fills all four; the old uniform
        # draw could leave one nearly empty.
        quads = [0, 0, 0, 0]
        for (x, _y, z, _nx, _ny, _nz) in pts:
            quads[(0 if x < 0 else 1) + (0 if z < 0 else 2)] += 1
        self.assertGreater(min(quads), 0.5 * (len(pts) / 4.0),
                           f"a quarter of the wall is nearly bare: {quads}")


if __name__ == "__main__":
    unittest.main()
