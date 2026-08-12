"""Geometry tests for procedural.volume - the navigable-volume core.

Pure math: no sim, no FrameContext, no engine. That is deliberate - the containment
test is the one piece of the relic design that must be right before anything is
built on it, and it should be provable without launching anything.
"""

import math
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural.volume import (
    volume_define, volume_get, volume_chamber, volume_passage,
    volume_depth, volume_contains, volume_nearest_inside, volume_path,
    volume_names, volume_count, volume_clear, volume_load, volume_box, volume_solid,
    volume_tier, volume_watch, volume_unwatch, volume_watching,
    volume_watch_count, volume_containment_tick, volume_anchor, volume_anchor_count,
    TIER_INSIDE, TIER_SCRAPE, TIER_BREACH,
)


class TestChamberGeometry(unittest.TestCase):
    def setUp(self):
        volume_clear()
        volume_define("v", chambers={"hub": (0, 0, 0, 1000)})

    def test_center_is_deepest(self):
        # Depth is signed distance to the wall, so the center of a 1000u sphere is
        # 1000 units inside it.
        self.assertAlmostEqual(volume_depth("v", (0, 0, 0)), -1000.0)

    def test_sign_flips_exactly_at_the_wall(self):
        self.assertLess(volume_depth("v", (999, 0, 0)), 0.0)
        self.assertAlmostEqual(volume_depth("v", (1000, 0, 0)), 0.0)
        self.assertGreater(volume_depth("v", (1001, 0, 0)), 0.0)

    def test_depth_outside_is_the_gap(self):
        self.assertAlmostEqual(volume_depth("v", (1500, 0, 0)), 500.0)

    def test_contains(self):
        self.assertTrue(volume_contains("v", (0, 0, 500)))
        self.assertFalse(volume_contains("v", (0, 0, 1500)))

    def test_measured_in_three_dimensions(self):
        # A relic is not a floor plan; y must count exactly as x and z do.
        d = 1000 / math.sqrt(3.0)
        self.assertAlmostEqual(volume_depth("v", (d, d, d)), 0.0, places=6)
        self.assertLess(volume_depth("v", (0, 999, 0)), 0.0)


class TestPassageGeometry(unittest.TestCase):
    def setUp(self):
        volume_clear()
        # A bare corridor: one capsule, no chambers.
        volume_define("v", passages=[((0, 0, 0), (10000, 0, 0), 300)])

    def test_inside_along_its_length(self):
        for x in (0, 2500, 5000, 9999):
            self.assertTrue(volume_contains("v", (x, 0, 0)), f"x={x}")

    def test_radius_holds_across_the_corridor(self):
        self.assertLess(volume_depth("v", (5000, 0, 299)), 0.0)
        self.assertGreater(volume_depth("v", (5000, 0, 301)), 0.0)

    def test_clamped_at_the_ends_not_an_infinite_cylinder(self):
        # THE capsule property. An unclamped line test would call this contained,
        # and the corridor would silently extend forever past its mouth.
        self.assertGreater(volume_depth("v", (10400, 0, 0)), 0.0)
        self.assertGreater(volume_depth("v", (-400, 0, 0)), 0.0)
        # ...and the end cap is a hemisphere, so just past the end is still in.
        self.assertTrue(volume_contains("v", (10299, 0, 0)))

    def test_degenerate_passage_behaves_as_a_sphere(self):
        volume_define("d", passages=[((0, 0, 0), (0, 0, 0), 100)])
        self.assertTrue(volume_contains("d", (99, 0, 0)))
        self.assertFalse(volume_contains("d", (101, 0, 0)))


class TestUnion(unittest.TestCase):
    def setUp(self):
        volume_clear()
        volume_define(
            "v",
            chambers={"a": (0, 0, 0, 500), "b": (4000, 0, 0, 500)},
            passages=[("a", "b", 150)],
        )

    def test_nearest_primitive_wins(self):
        self.assertTrue(volume_contains("v", (0, 0, 0)))       # chamber a
        self.assertTrue(volume_contains("v", (4000, 0, 0)))    # chamber b
        self.assertTrue(volume_contains("v", (2000, 0, 0)))    # the passage between

    def test_the_gap_between_is_wall(self):
        # Off the corridor axis, between the two chambers: solid rock.
        self.assertFalse(volume_contains("v", (2000, 0, 400)))

    def test_empty_volume_contains_nothing(self):
        # All wall rather than all void - an empty volume must not read as
        # "everything is contained", which would silently disable containment.
        volume_define("empty")
        self.assertFalse(volume_contains("empty", (0, 0, 0)))
        self.assertEqual(volume_depth("empty", (0, 0, 0)), float("inf"))


class TestNearestInside(unittest.TestCase):
    def setUp(self):
        volume_clear()
        volume_define("v", chambers={"hub": (0, 0, 0, 1000)})

    def test_interior_point_is_returned_unchanged(self):
        p = (10, 20, 30)
        self.assertEqual(volume_nearest_inside("v", p), p)

    def test_outside_point_is_projected_onto_the_wall(self):
        got = volume_nearest_inside("v", (5000, 0, 0))
        self.assertAlmostEqual(got[0], 1000.0)
        self.assertAlmostEqual(got[1], 0.0)
        self.assertAlmostEqual(got[2], 0.0)

    def test_projection_preserves_direction(self):
        got = volume_nearest_inside("v", (3000, 3000, 0))
        self.assertAlmostEqual(math.sqrt(got[0] ** 2 + got[1] ** 2 + got[2] ** 2), 1000.0)
        self.assertAlmostEqual(got[0], got[1])

    def test_margin_pulls_further_in(self):
        got = volume_nearest_inside("v", (5000, 0, 0), margin=100)
        self.assertAlmostEqual(got[0], 900.0)

    def test_margin_also_moves_a_point_in_the_margin_band(self):
        # Inside the wall but not by `margin` - the clamp must still act, otherwise
        # the backstop never fires until the ship is already out.
        got = volume_nearest_inside("v", (950, 0, 0), margin=100)
        self.assertAlmostEqual(got[0], 900.0)

    def test_margin_equal_to_the_radius_yields_the_center(self):
        # "Inside by at least 1000" in a 1000u sphere describes exactly one point.
        # Returning the center is correct, not a degenerate case to guard against -
        # a chamber center is empty space, not an object at zero distance.
        got = volume_nearest_inside("v", (0, 0, 0), margin=1000)
        self.assertAlmostEqual(math.sqrt(got[0] ** 2 + got[1] ** 2 + got[2] ** 2), 0.0)

    def test_impossible_margin_still_lands_inside(self):
        # Asking for more clearance than the volume has must not return None, throw,
        # or hand back a point outside. This is also what exercises the zero-length
        # direction guard: from the exact center there is no direction to preserve.
        got = volume_nearest_inside("v", (0, 0, 0), margin=1500)
        self.assertIsNotNone(got)
        self.assertGreater(math.sqrt(got[0] ** 2 + got[1] ** 2 + got[2] ** 2), 0.0)
        self.assertLess(volume_depth("v", got), 0.0)

    def test_impossible_margin_from_outside_lands_inside(self):
        got = volume_nearest_inside("v", (9000, 0, 0), margin=1500)
        self.assertLess(volume_depth("v", got), 0.0)

    def test_projected_point_is_actually_inside(self):
        # The property that matters: whatever comes back must satisfy the test the
        # caller is about to re-run next tick.
        for p in ((5000, 0, 0), (0, -9000, 0), (700, 700, 700), (1001, 0, 0)):
            got = volume_nearest_inside("v", p, margin=10)
            self.assertLessEqual(volume_depth("v", got), 0.0, f"from {p}")


class TestPathfinding(unittest.TestCase):
    def setUp(self):
        volume_clear()
        # a - b - c, plus an island d joined to nothing.
        volume_define(
            "v",
            chambers={"a": (0, 0, 0, 400), "b": (2000, 0, 0, 400),
                      "c": (4000, 0, 0, 400), "d": (0, 0, 9000, 400)},
            passages=[("a", "b", 120), ("b", "c", 120)],
        )

    def test_direct(self):
        self.assertEqual(volume_path("v", "a", "b"), ["a", "b"])

    def test_transitive(self):
        self.assertEqual(volume_path("v", "a", "c"), ["a", "b", "c"])

    def test_same_chamber(self):
        self.assertEqual(volume_path("v", "a", "a"), ["a"])

    def test_unreachable_island(self):
        self.assertEqual(volume_path("v", "a", "d"), [])

    def test_unknown_chamber(self):
        self.assertEqual(volume_path("v", "a", "nope"), [])

    def test_shortest_route_wins(self):
        volume_passage("v", "a", "c", 120)     # a shortcut appears
        self.assertEqual(volume_path("v", "a", "c"), ["a", "c"])


class TestRegistry(unittest.TestCase):
    def setUp(self):
        volume_clear()

    def test_define_and_get(self):
        volume_define("v", chambers={"hub": (0, 0, 0, 100)})
        self.assertIsNotNone(volume_get("v"))
        self.assertIn("v", volume_names())
        self.assertEqual(volume_count(), 1)

    def test_redefine_replaces(self):
        volume_define("v", chambers={"hub": (0, 0, 0, 100)})
        volume_define("v", chambers={"hub": (0, 0, 0, 5000)})
        self.assertEqual(volume_count(), 1)
        self.assertAlmostEqual(volume_depth("v", (0, 0, 0)), -5000.0)

    def test_unknown_volume_is_all_wall(self):
        # Never silently contained - a typo in a volume name must fail closed.
        self.assertEqual(volume_depth("nope", (0, 0, 0)), float("inf"))
        self.assertFalse(volume_contains("nope", (0, 0, 0)))
        self.assertIsNone(volume_nearest_inside("nope", (0, 0, 0)))
        self.assertEqual(volume_path("nope", "a", "b"), [])

    def test_clear_empties_the_registry(self):
        # The reset-ledger contract: cosmos_dev reuses one interpreter across
        # missions, so a registry that survives is a run-2 bug.
        volume_define("v", chambers={"hub": (0, 0, 0, 100)})
        volume_clear()
        self.assertEqual(volume_count(), 0)

    def test_incremental_construction(self):
        volume_define("v")
        volume_chamber("v", "a", 0, 0, 0, 300)
        volume_chamber("v", "b", 3000, 0, 0, 300)
        volume_passage("v", "a", "b", 100)
        self.assertTrue(volume_contains("v", (1500, 0, 0)))
        self.assertEqual(volume_path("v", "a", "b"), ["a", "b"])

    def test_bound_encloses_every_primitive(self):
        volume_define("v", chambers={"a": (0, 0, 0, 400), "b": (8000, 0, 0, 600)})
        (c, r) = volume_get("v").bound()
        for x, rad in ((0, 400), (8000, 600)):
            d = math.sqrt((c[0] - x) ** 2 + c[1] ** 2 + c[2] ** 2)
            self.assertLessEqual(d + rad, r + 1e-6)


class TestVec3Interop(unittest.TestCase):
    def test_accepts_anything_with_xyz(self):
        from sbs_utils.vec import Vec3
        volume_clear()
        volume_define("v", chambers={"hub": (0, 0, 0, 1000)})
        self.assertTrue(volume_contains("v", Vec3(0, 0, 500)))
        self.assertFalse(volume_contains("v", Vec3(0, 0, 1500)))


class TestDeclarative(unittest.TestCase):
    """Authoring a relic from a yaml block rather than a wall of calls."""

    def setUp(self):
        volume_clear()

    def test_yaml_shaped_lists_are_accepted(self):
        # yaml parses to LISTS, not tuples. The whole declarative story depends on
        # that working without a conversion step at every call site.
        import yaml
        data = yaml.safe_load(
            "chambers:\n"
            "    hub:   [0, 0, 0, 1200]\n"
            "    spine: [4000, 0, 0, 900]\n"
            "passages:\n"
            "    - [hub, spine, 300]\n"
        )
        volume_load("relic", data)
        self.assertTrue(volume_contains("relic", (0, 0, 0)))
        self.assertTrue(volume_contains("relic", (2000, 0, 0)))     # down the passage
        self.assertFalse(volume_contains("relic", (2000, 0, 900)))  # off it: wall
        self.assertEqual(volume_path("relic", "hub", "spine"), ["hub", "spine"])

    def test_passages_may_name_chambers_declared_later(self):
        # A declarative block is a mapping, not a program - it must not have to be
        # written in dependency order.
        volume_load("relic", {"chambers": {"a": [0, 0, 0, 500], "b": [3000, 0, 0, 500]},
                              "passages": [["b", "a", 100]]})
        self.assertTrue(volume_contains("relic", (1500, 0, 0)))

    def test_empty_block_is_a_valid_empty_volume(self):
        volume_load("relic", {})
        self.assertEqual(volume_count(), 1)
        self.assertFalse(volume_contains("relic", (0, 0, 0)))

    def test_typo_in_a_passage_names_the_volume_and_the_chamber(self):
        # This used to be a bare KeyError from inside add_passage - no volume, no
        # hint that it was an endpoint, on a relic with a dozen chambers.
        with self.assertRaises(ValueError) as cm:
            volume_load("relic", {"chambers": {"hub": [0, 0, 0, 100]},
                                  "passages": [["hub", "spien", 50]]})
        msg = str(cm.exception)
        self.assertIn("relic", msg)
        self.assertIn("spien", msg)
        self.assertIn("hub", msg)          # lists what WAS available

    def test_zero_radius_chamber_is_rejected(self):
        with self.assertRaises(ValueError):
            volume_load("relic", {"chambers": {"hub": [0, 0, 0, 0]}})

    def test_zero_radius_passage_is_rejected(self):
        with self.assertRaises(ValueError):
            volume_load("relic", {"chambers": {"a": [0, 0, 0, 10], "b": [50, 0, 0, 10]},
                                  "passages": [["a", "b", 0]]})

    def test_short_chamber_tuple_is_rejected(self):
        with self.assertRaises(ValueError):
            volume_load("relic", {"chambers": {"hub": [0, 0, 0]}})

    def test_short_passage_tuple_is_rejected(self):
        with self.assertRaises(ValueError):
            volume_load("relic", {"chambers": {"hub": [0, 0, 0, 10]},
                                  "passages": [["hub", "hub"]]})

    def test_explicit_points_still_work_as_endpoints(self):
        volume_load("relic", {"passages": [[[0, 0, 0], [1000, 0, 0], 200]]})
        self.assertTrue(volume_contains("relic", (500, 0, 0)))


class TestBoxGeometry(unittest.TestCase):
    """Rectangular spaces - flat walls and real corners, which spheres cannot express."""

    def setUp(self):
        volume_clear()
        # 2000 x 800 x 2000 overall: half-extents are HALF the width.
        volume_define("v", boxes={"vault": (0, 0, 0, 1000, 400, 1000)})

    def test_inside(self):
        self.assertTrue(volume_contains("v", (0, 0, 0)))
        self.assertTrue(volume_contains("v", (999, 399, 999)))

    def test_outside_on_each_axis(self):
        self.assertFalse(volume_contains("v", (1001, 0, 0)))
        self.assertFalse(volume_contains("v", (0, 401, 0)))
        self.assertFalse(volume_contains("v", (0, 0, 1001)))

    def test_corners_are_reachable(self):
        # THE reason boxes exist. Any sphere covering this room would either exclude
        # the corners or bulge far past the flat walls.
        for sx in (-1, 1):
            for sy in (-1, 1):
                for sz in (-1, 1):
                    p = (sx * 995, sy * 395, sz * 995)
                    self.assertTrue(volume_contains("v", p), f"corner {p}")

    def test_depth_inside_is_distance_to_nearest_face(self):
        # At the centre the nearest face is the y one, 400 away - not the x one.
        self.assertAlmostEqual(volume_depth("v", (0, 0, 0)), -400.0)
        self.assertAlmostEqual(volume_depth("v", (0, 300, 0)), -100.0)

    def test_depth_outside_is_euclidean(self):
        self.assertAlmostEqual(volume_depth("v", (1300, 0, 0)), 300.0)
        # Diagonally off two faces: 300 and 400 out -> 500.
        self.assertAlmostEqual(volume_depth("v", (1300, 800, 0)), 500.0)

    def test_projection_clamps_per_axis(self):
        got = volume_nearest_inside("v", (5000, 0, 0))
        self.assertAlmostEqual(got[0], 1000.0)
        self.assertAlmostEqual(got[1], 0.0)

    def test_projection_keeps_a_corner_a_corner(self):
        # Projecting towards a centre would drag this to the middle of a face.
        got = volume_nearest_inside("v", (5000, 5000, 5000))
        self.assertAlmostEqual(got[0], 1000.0)
        self.assertAlmostEqual(got[1], 400.0)
        self.assertAlmostEqual(got[2], 1000.0)

    def test_projected_point_is_inside(self):
        for p in ((5000, 0, 0), (0, -900, 0), (2000, 2000, 2000), (-1100, 0, 500)):
            got = volume_nearest_inside("v", p, margin=10)
            self.assertLessEqual(volume_depth("v", got), 0.0, f"from {p}")

    def test_half_extents_must_be_positive(self):
        with self.assertRaises(ValueError) as cm:
            volume_define("bad", boxes={"flat": (0, 0, 0, 100, 0, 100)})
        self.assertIn("hy", str(cm.exception))

    def test_box_joins_the_union(self):
        volume_define("v", chambers={"hub": (0, 0, 0, 300)},
                      boxes={"hall": (2000, 0, 0, 800, 200, 200)})
        self.assertTrue(volume_contains("v", (0, 0, 0)))          # sphere
        self.assertTrue(volume_contains("v", (2700, 0, 0)))       # box
        self.assertFalse(volume_contains("v", (1000, 0, 0)))      # wall between


class TestSolids(unittest.TestCase):
    """Subtraction - the pillar in the middle of the room.

    Union alone can only ADD space, so without this a chamber with a column has to be
    faked by routing capsules around where the column goes.
    """

    def setUp(self):
        volume_clear()
        volume_define("v", chambers={"hub": (0, 0, 0, 1000)})

    def test_pillar_removes_its_own_space(self):
        self.assertTrue(volume_contains("v", (0, 0, 0)))
        volume_solid("v", "sphere", 0, 0, 0, 300)
        self.assertFalse(volume_contains("v", (0, 0, 0)))

    def test_room_around_the_pillar_survives(self):
        volume_solid("v", "sphere", 0, 0, 0, 300)
        self.assertTrue(volume_contains("v", (600, 0, 0)))
        self.assertTrue(volume_contains("v", (0, 0, -700)))

    def test_depth_near_a_pillar_measures_the_pillar(self):
        # Standing 400 from the centre of a 300 pillar in a 1000 room: the nearest wall
        # is the PILLAR at 100, not the shell at 600.
        volume_solid("v", "sphere", 0, 0, 0, 300)
        self.assertAlmostEqual(volume_depth("v", (400, 0, 0)), -100.0)

    def test_projection_leaves_the_pillar_not_the_room(self):
        # Buried in the column, the way out is AWAY from the column. Projecting onto
        # the enclosing room would leave the ship still inside the pillar.
        volume_solid("v", "sphere", 0, 0, 0, 300)
        got = volume_nearest_inside("v", (100, 0, 0), margin=10)
        self.assertGreaterEqual(math.sqrt(sum(c * c for c in got)), 310.0 - 1e-6)
        self.assertLessEqual(volume_depth("v", got), 0.0)

    def test_a_solid_makes_its_interior_breach(self):
        volume_solid("v", "sphere", 0, 0, 0, 300)
        self.assertEqual(volume_tier("v", (0, 0, 0)), TIER_BREACH)

    def test_solid_box(self):
        volume_solid("v", "box", 0, 0, 0, 200, 900, 200)   # a square column, floor to roof
        self.assertFalse(volume_contains("v", (0, 0, 0)))
        self.assertTrue(volume_contains("v", (500, 0, 0)))

    def test_solid_box_projection_leaves_by_the_nearest_face(self):
        volume_solid("v", "box", 0, 0, 0, 200, 900, 200)
        got = volume_nearest_inside("v", (150, 0, 50), margin=5)
        self.assertGreaterEqual(abs(got[0]), 205.0 - 1e-6)   # left by the x face
        self.assertLessEqual(volume_depth("v", got), 0.0)

    def test_solid_capsule_as_a_spine(self):
        volume_solid("v", "capsule", (0, -800, 0), (0, 800, 0), 150)
        self.assertFalse(volume_contains("v", (0, 0, 0)))
        self.assertFalse(volume_contains("v", (100, 400, 0)))
        self.assertTrue(volume_contains("v", (500, 0, 0)))

    def test_torus_with_a_solid_hub(self):
        # A ring of passages around a subtracted centre - expressible now, and the hub
        # is genuinely solid rather than merely unvisited.
        volume_define("t", chambers={
            "n": (0, 0, 1200, 300), "e": (1200, 0, 0, 300),
            "s": (0, 0, -1200, 300), "w": (-1200, 0, 0, 300)},
            passages=[("n", "e", 200), ("e", "s", 200),
                      ("s", "w", 200), ("w", "n", 200)])
        volume_solid("t", "sphere", 0, 0, 0, 600)
        self.assertTrue(volume_contains("t", (0, 0, 1200)))     # on the ring
        self.assertFalse(volume_contains("t", (0, 0, 0)))       # solid hub
        self.assertEqual(volume_path("t", "n", "s"), ["n", "e", "s"])

    def test_solids_are_declarative_too(self):
        volume_load("d", {"chambers": {"hub": [0, 0, 0, 1000]},
                          "boxes": {"hall": [2500, 0, 0, 600, 300, 300]},
                          "solids": [["sphere", 0, 0, 0, 250],
                                     ["box", 2500, 0, 0, 100, 100, 100]]})
        self.assertFalse(volume_contains("d", (0, 0, 0)))       # pillar
        self.assertFalse(volume_contains("d", (2500, 0, 0)))    # block in the hall
        self.assertTrue(volume_contains("d", (600, 0, 0)))
        self.assertTrue(volume_contains("d", (2900, 0, 0)))

    def test_unknown_solid_kind_is_rejected(self):
        with self.assertRaises(ValueError) as cm:
            volume_solid("v", "pyramid", 0, 0, 0, 100)
        self.assertIn("pyramid", str(cm.exception))

    def test_zero_size_solid_is_rejected(self):
        with self.assertRaises(ValueError):
            volume_solid("v", "sphere", 0, 0, 0, 0)

    def test_bound_still_encloses_everything_with_boxes(self):
        volume_define("v", chambers={"a": (0, 0, 0, 400)},
                      boxes={"b": (6000, 0, 0, 500, 500, 500)})
        (c, r) = volume_get("v").bound()
        self.assertGreaterEqual(r, 0.0)
        for p in ((400, 0, 0), (6500, 0, 0)):
            self.assertLessEqual(math.sqrt(sum((c[i] - p[i]) ** 2 for i in range(3))),
                                 r + 1e-6)


class TestTiers(unittest.TestCase):
    """The graded response, tested as pure geometry - no sim, no ticker."""

    def setUp(self):
        volume_clear()
        volume_define("v", chambers={"hub": (0, 0, 0, 1000)})

    def test_inside(self):
        self.assertEqual(volume_tier("v", (0, 0, 0)), TIER_INSIDE)
        self.assertEqual(volume_tier("v", (999, 0, 0)), TIER_INSIDE)

    def test_scrape_starts_at_the_wall(self):
        self.assertEqual(volume_tier("v", (1000.5, 0, 0)), TIER_SCRAPE)
        self.assertEqual(volume_tier("v", (1119, 0, 0)), TIER_SCRAPE)

    def test_breach_past_the_band(self):
        self.assertEqual(volume_tier("v", (1121, 0, 0)), TIER_BREACH)
        self.assertEqual(volume_tier("v", (9000, 0, 0)), TIER_BREACH)

    def test_band_is_tunable(self):
        self.assertEqual(volume_tier("v", (1050, 0, 0), scrape_band=10), TIER_BREACH)
        self.assertEqual(volume_tier("v", (1050, 0, 0), scrape_band=500), TIER_SCRAPE)

    def test_default_band_exceeds_one_tick_of_warp(self):
        # Engine-measured: 60 u per MAST tick at full warp. A scrape band narrower
        # than that would let a warping ship skip the scrape tier entirely and land
        # straight in breach, which is the wall-slam the grading exists to avoid.
        self.assertEqual(volume_tier("v", (1000 + 61, 0, 0)), TIER_SCRAPE)

    def test_unknown_volume_is_breach_not_inside(self):
        # Fail CLOSED. A typo must not read as "everywhere is safe".
        self.assertEqual(volume_tier("nope", (0, 0, 0)), TIER_BREACH)


class TestWatcherLifecycle(unittest.TestCase):
    """The only tests here that need a sim - TickDispatcher reads the tick counter
    off FrameContext. Everything above stays context-free on purpose."""

    def setUp(self):
        from cosmos_dev.mock import sbs
        from tests.reset_helper import reset_mock
        reset_mock(sbs)                 # also runs volume_clear() via reset_mission_state
        volume_define("v", chambers={"hub": (0, 0, 0, 1000)})

    def tearDown(self):
        volume_clear()

    def test_watch_registers(self):
        self.assertEqual(volume_watch_count(), 0)
        volume_watch("v")
        self.assertTrue(volume_watching("v"))
        self.assertEqual(volume_watch_count(), 1)

    def test_watch_replaces_rather_than_stacking(self):
        volume_watch("v")
        volume_watch("v")
        self.assertEqual(volume_watch_count(), 1)

    def test_unwatch(self):
        volume_watch("v")
        self.assertTrue(volume_unwatch("v"))
        self.assertEqual(volume_watch_count(), 0)
        self.assertFalse(volume_unwatch("v"))

    def test_watching_an_unknown_volume_is_a_no_op(self):
        self.assertIsNone(volume_watch("nope"))
        self.assertEqual(volume_watch_count(), 0)

    def test_clear_stops_watchers_too(self):
        # Otherwise a reset leaves a live tick task enforcing a volume that no
        # longer exists - the reused-interpreter trap, one layer down.
        volume_watch("v")
        volume_clear()
        self.assertEqual(volume_watch_count(), 0)

    def test_tick_with_no_watchers_is_harmless(self):
        volume_containment_tick()

    def test_tick_survives_the_volume_disappearing(self):
        # A mission can redefine or drop a volume while a watch is live; the ticker
        # must retire the orphan instead of raising every tick forever.
        volume_watch("v")
        from sbs_utils.procedural.volume import _VOLUMES
        _VOLUMES.pop("v")
        volume_containment_tick()
        self.assertEqual(volume_watch_count(), 0)


class TestEnforcement(unittest.TestCase):
    """End to end against a mock sim: a real ship, really clamped.

    The tiers above are pure geometry. This covers the half that actually touches
    the sim - the clamp, the throttle governor, and transition-only signalling.
    Engine evidence that the clamp is a legitimate mechanism at all is in
    `data/missions/relic_spike/relic_spike_report.engine.txt`: writes stick, and a
    3000u sphere held a warping ship at 3058.6 max.
    """

    def setUp(self):
        from cosmos_dev.mock import sbs
        from tests.reset_helper import reset_mock
        self.sim = reset_mock(sbs)
        from sbs_utils.procedural.spawn import player_spawn
        from sbs_utils.procedural.query import to_object
        self.ship = to_object(player_spawn(0, 0, 0, "Probe", "tsn", "tsn_light_cruiser"))
        volume_define("v", chambers={"hub": (0, 0, 0, 1000)})

    def tearDown(self):
        volume_clear()

    def _set_pos(self, x, y, z):
        from sbs_utils.procedural.space_objects import set_pos
        set_pos(self.ship.id, x, y, z)

    def _pos(self):
        from sbs_utils.procedural.space_objects import get_pos
        p = get_pos(self.ship.id)
        return (p.x, p.y, p.z)

    def test_inside_is_left_alone(self):
        volume_watch("v")
        self._set_pos(500, 0, 0)
        volume_containment_tick()
        self.assertEqual(self._pos(), (500, 0, 0))

    def test_scrape_is_not_clamped(self):
        # The soft tier: you are in the wall and it should hurt, but you keep flying.
        # Clamping here would make the wall feel like a hard stop everywhere.
        volume_watch("v")
        self._set_pos(1050, 0, 0)
        volume_containment_tick()
        self.assertAlmostEqual(self._pos()[0], 1050)

    def test_breach_is_clamped_back_inside(self):
        volume_watch("v", hold="clamp")
        self._set_pos(5000, 0, 0)
        volume_containment_tick()
        self.assertLessEqual(volume_depth("v", self._pos()), 0.0)

    def test_clamp_respects_margin(self):
        volume_watch("v", margin=200, hold="clamp")
        self._set_pos(5000, 0, 0)
        volume_containment_tick()
        self.assertAlmostEqual(self._pos()[0], 800.0, places=3)

    def test_clamp_can_be_disabled(self):
        volume_watch("v", clamp=False, hold="clamp")
        self._set_pos(5000, 0, 0)
        volume_containment_tick()
        self.assertAlmostEqual(self._pos()[0], 5000)

    def test_governor_caps_warp_on_breach(self):
        volume_watch("v")
        self.ship.data_set.set("playerThrottle", 3.0, 0)
        self._set_pos(5000, 0, 0)
        volume_containment_tick()
        self.assertAlmostEqual(self.ship.data_set.get("playerThrottle", 0), 1.0)

    def test_governor_leaves_impulse_alone(self):
        # Cap, never raise, and never touch a ship that is already sub-warp.
        volume_watch("v")
        self.ship.data_set.set("playerThrottle", 0.5, 0)
        self._set_pos(5000, 0, 0)
        volume_containment_tick()
        self.assertAlmostEqual(self.ship.data_set.get("playerThrottle", 0), 0.5)

    def test_governor_does_not_fire_inside(self):
        volume_watch("v")
        self.ship.data_set.set("playerThrottle", 3.0, 0)
        self._set_pos(0, 0, 0)
        volume_containment_tick()
        self.assertAlmostEqual(self.ship.data_set.get("playerThrottle", 0), 3.0)

    def test_repeated_ticks_hold_the_ship(self):
        # The property the whole design rests on: a ship under continuous outward
        # thrust stays contained tick after tick.
        volume_watch("v", hold="clamp")
        for _ in range(20):
            p = self._pos()
            self._set_pos(p[0] + 60, p[1], p[2])   # one tick of warp travel, measured
            volume_containment_tick()
            self.assertLess(volume_depth("v", self._pos()), 120.0)

    def test_signals_fire_on_transition_only(self):
        seen = []
        # The ticker imports signal_emit lazily, so patch the SOURCE module - patching
        # a name on volume itself would not be seen.
        import sbs_utils.procedural.signal as sig_mod
        original = sig_mod.signal_emit
        sig_mod.signal_emit = lambda name, data=None: seen.append(name)
        try:
            volume_watch("v", clamp=False, hold="none")
            self._set_pos(0, 0, 0)
            volume_containment_tick()
            self.assertEqual(seen, [])                    # inside is the default tier
            self._set_pos(1050, 0, 0)
            volume_containment_tick()
            self.assertEqual(seen, ["volume_scrape"])
            volume_containment_tick()
            self.assertEqual(seen, ["volume_scrape"])     # no repeat while unchanged
            self._set_pos(5000, 0, 0)
            volume_containment_tick()
            self.assertEqual(seen, ["volume_scrape", "volume_breach"])
            self._set_pos(0, 0, 0)
            volume_containment_tick()
            self.assertEqual(seen, ["volume_scrape", "volume_breach", "volume_recovered"])
        finally:
            sig_mod.signal_emit = original

    def test_explicit_agent_set_is_honored(self):
        volume_watch("v", agents=set())      # watch nobody
        self._set_pos(5000, 0, 0)
        volume_containment_tick()
        self.assertAlmostEqual(self._pos()[0], 5000)

    def test_callable_agent_set_is_re_evaluated(self):
        # A callable is the point: ships arriving mid-mission need no wiring.
        holder = {"ids": set()}
        volume_watch("v", agents=lambda: holder["ids"], hold="clamp")
        self._set_pos(5000, 0, 0)
        volume_containment_tick()
        self.assertAlmostEqual(self._pos()[0], 5000)      # not watched yet
        holder["ids"] = {self.ship.id}
        volume_containment_tick()
        self.assertLessEqual(volume_depth("v", self._pos()), 0.0)


class TestTractorHold(unittest.TestCase):
    """The default hold: an engine-side tractor rather than a teleport clamp.

    WHY it is the default: measured from the helm seat in engine 1.3.5, a per-tick
    `set_pos` clamp is correct on the server and looks WRONG on the client - the client
    predicts its own position, so a ship driven past the boundary visibly leaves the
    volume and snaps back. A tractor moves the ship inside the engine's own physics, so
    client prediction follows it.

    LIMIT OF THESE TESTS: the mock STORES tractor connections and never applies the pull
    (`cosmos_dev/mock/sbs.py:2128`). So this covers the WIRING - anchor created, rope
    attached, released on recovery, cleaned up on reset - and says nothing about whether
    the hold feels right. Only the engine answers that.
    """

    def setUp(self):
        from cosmos_dev.mock import sbs
        from tests.reset_helper import reset_mock
        self.sim = reset_mock(sbs)
        from sbs_utils.procedural.spawn import player_spawn
        from sbs_utils.procedural.query import to_object
        self.ship = to_object(player_spawn(0, 0, 0, "Probe", "tsn", "tsn_light_cruiser"))
        volume_define("v", chambers={"hub": (0, 0, 0, 1000)})

    def tearDown(self):
        volume_clear()

    def _set_pos(self, x, y, z):
        from sbs_utils.procedural.space_objects import set_pos
        set_pos(self.ship.id, x, y, z)

    def _connections(self):
        return dict(self.sim.tractor_connections)

    def test_no_anchor_until_a_breach(self):
        volume_watch("v")
        self._set_pos(500, 0, 0)
        volume_containment_tick()
        self.assertEqual(volume_anchor_count(), 0)
        self.assertEqual(self._connections(), {})

    def test_breach_creates_an_anchor_and_a_tether(self):
        volume_watch("v")
        self._set_pos(5000, 0, 0)
        volume_containment_tick()
        self.assertEqual(volume_anchor_count(), 1)
        self.assertEqual(len(self._connections()), 1)

    def test_anchor_sits_on_the_medial_axis(self):
        # For a chamber that is its center, so a rope of the chamber radius about it IS
        # the containment constraint. This is why `nearest` returns the anchor at all.
        volume_watch("v")
        self._set_pos(5000, 0, 0)
        volume_containment_tick()
        from sbs_utils.procedural.query import to_object
        from sbs_utils.procedural.space_objects import get_pos
        from sbs_utils.procedural.roles import role
        anchor = to_object(list(role("volume_anchor"))[0])
        p = get_pos(anchor.id)
        self.assertAlmostEqual(p.x, 0.0)
        self.assertAlmostEqual(p.y, 0.0)
        self.assertAlmostEqual(p.z, 0.0)

    def test_anchor_is_reused_not_respawned(self):
        volume_watch("v")
        self._set_pos(5000, 0, 0)
        for _ in range(5):
            volume_containment_tick()
        self.assertEqual(volume_anchor_count(), 1)

    def test_returning_inside_releases_the_tether(self):
        # Otherwise the ship flies around still roped to an anchor.
        volume_watch("v")
        self._set_pos(5000, 0, 0)
        volume_containment_tick()
        self.assertEqual(len(self._connections()), 1)
        self._set_pos(0, 0, 0)
        volume_containment_tick()
        self.assertEqual(len(self._connections()), 0)

    def test_anchors_are_cleared_on_reset(self):
        # Anchors are spawned OBJECTS, so a leak is worse than a stale dict entry.
        volume_watch("v")
        self._set_pos(5000, 0, 0)
        volume_containment_tick()
        self.assertEqual(volume_anchor_count(), 1)
        volume_clear()
        self.assertEqual(volume_anchor_count(), 0)

    def test_hold_none_does_nothing_positional(self):
        volume_watch("v", hold="none", govern=False)
        self._set_pos(5000, 0, 0)
        volume_containment_tick()
        self.assertEqual(volume_anchor_count(), 0)
        from sbs_utils.procedural.space_objects import get_pos
        self.assertAlmostEqual(get_pos(self.ship.id).x, 5000)

    def test_governor_still_applies_under_the_tractor(self):
        # The two are independent: the tractor holds position, the governor stops the
        # ship fighting it at warp.
        volume_watch("v")
        self.ship.data_set.set("playerThrottle", 3.0, 0)
        self._set_pos(5000, 0, 0)
        volume_containment_tick()
        self.assertAlmostEqual(self.ship.data_set.get("playerThrottle", 0), 1.0)


class TestFlightEnvelope(unittest.TestCase):
    """A speed limit for the whole volume, not just a punishment for leaving it.

    A relic interior should fly like a tight space. It also makes containment easier:
    a capped ship has a smaller per-tick tunneling budget to defeat the hold with.
    """

    def setUp(self):
        from cosmos_dev.mock import sbs
        from tests.reset_helper import reset_mock
        reset_mock(sbs)
        from sbs_utils.procedural.spawn import player_spawn
        from sbs_utils.procedural.query import to_object
        self.ship = to_object(player_spawn(0, 0, 0, "Probe", "tsn", "tsn_light_cruiser"))
        volume_define("v", chambers={"hub": (0, 0, 0, 1000)})

    def tearDown(self):
        volume_clear()

    def _thr(self):
        return self.ship.data_set.get("playerThrottle", 0)

    def test_no_limit_by_default(self):
        # Backward compatible: an existing caller's ships are not silently slowed.
        volume_watch("v")
        self.ship.data_set.set("playerThrottle", 3.0, 0)
        volume_containment_tick()
        self.assertAlmostEqual(self._thr(), 3.0)

    def test_limit_applies_while_merely_inside(self):
        volume_watch("v", speed_limit=0.5)
        self.ship.data_set.set("playerThrottle", 3.0, 0)
        volume_containment_tick()
        self.assertAlmostEqual(self._thr(), 0.5)

    def test_limit_of_one_forbids_warp_for_free(self):
        # Warp IS playerThrottle > 1.0, so no separate warp switch is needed.
        volume_watch("v", speed_limit=1.0)
        self.ship.data_set.set("playerThrottle", 3.0, 0)
        volume_containment_tick()
        self.assertAlmostEqual(self._thr(), 1.0)

    def test_limit_only_lowers(self):
        volume_watch("v", speed_limit=0.5)
        self.ship.data_set.set("playerThrottle", 0.2, 0)
        volume_containment_tick()
        self.assertAlmostEqual(self._thr(), 0.2)

    def test_block_jump_writes_the_drive_keys(self):
        # Wiring only - whether this actually stops a helm engaging the drive is
        # UNVERIFIED in the engine and needs a seat test.
        volume_watch("v", block_jump=True)
        self.ship.data_set.set("jump_drive_active", 1, 0)
        self.ship.data_set.set("warp_drive_active", 1, 0)
        volume_containment_tick()
        self.assertEqual(self.ship.data_set.get("jump_drive_active", 1), 0)
        self.assertEqual(self.ship.data_set.get("warp_drive_active", 1), 0)

    def test_block_jump_is_off_by_default(self):
        volume_watch("v")
        self.ship.data_set.set("jump_drive_active", 1, 0)
        volume_containment_tick()
        self.assertEqual(self.ship.data_set.get("jump_drive_active", 0), 1)


if __name__ == "__main__":
    unittest.main()
