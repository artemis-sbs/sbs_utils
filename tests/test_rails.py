"""The rail web: seeding, density, edges, barriers, and the thing that must not regress.

The volume fixtures here are deliberately the two shapes the shipped relics are actually
built from - a chain of boxes (the Torgoth ruins) and chambers joined by passages (the
Kralien ones) - because a solver that only works on one of them flies about half of
Storm's Beacon.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir

test_set_exe_dir()

from sbs_utils.procedural.rails import (KIND_PLACE, KIND_SPINE, RAIL_MAX_NODES,
                                        rail_attach, rail_barrier, rail_barrier_approach,
                                        rail_barrier_is_open, rail_barrier_open,
                                        rail_barrier_shut, rail_barriers, rail_build,
                                        rail_clear, rail_count, rail_detach, rail_dump,
                                        rail_get, rail_hide, rail_is_hidden, rail_leg,
                                        rail_names, rail_node, rail_node_pos, rail_nodes,
                                        rail_reachable, rail_remove, rail_reveal,
                                        rail_route, rail_stats)
from sbs_utils.procedural.volume import (volume_clear, volume_define, volume_depth,
                                         volume_get)


def corridor(name="corridor"):
    """Two long halls meeting end to end, plus a side room off the join.

    Deliberately box-built: four of the seven shipped relics have no chamber or passage
    in them at all.
    """
    return volume_define(
        name,
        boxes={
            "west": (-1500, 0, 0, 1500, 200, 200),
            "east": (1500, 0, 0, 1500, 200, 200),
            "side": (0, 0, 900, 200, 200, 900),
        })


def beads(name="beads"):
    """Three chambers on a string - the Kralien shape."""
    return volume_define(
        name,
        chambers={"a": (-2000, 0, 0, 600), "b": (0, 0, 0, 600), "c": (2000, 0, 0, 600)},
        passages=[("a", "b", 160), ("b", "c", 160)])


class TestRailBuild(unittest.TestCase):
    def setUp(self):
        volume_clear()
        rail_clear()

    def tearDown(self):
        volume_clear()
        rail_clear()

    def test_a_room_is_more_than_one_node(self):
        """The whole point of the density pass: a 3000-unit hall is not a dot.

        Before this, a room contributed its centre and nothing else, so every route across
        it was the same route and there was never an alternative to offer.
        """
        corridor()
        rail_build("corridor", margin=20.0)
        spine = rail_nodes("corridor", kind=KIND_SPINE)
        self.assertGreater(len(spine), 10, "a 6000-unit corridor should be many stations")
        xs = sorted(round(rec["pos"][0]) for _k, rec in spine)
        self.assertLess(xs[0], -1500, "nothing seeded in the west half")
        self.assertGreater(xs[-1], 1500, "nothing seeded in the east half")

    def test_every_node_is_inside_the_volume(self):
        """A node outside the volume can see nothing and contributes no edges, so it is
        worse than absent - it is a destination that silently never routes."""
        corridor()
        rail_build("corridor", margin=20.0)
        for key, rec in rail_nodes("corridor"):
            self.assertLessEqual(volume_depth("corridor", rec["pos"]), -20.0 + 1e-6,
                                 "%s is not inside by the margin" % key)

    def test_the_web_is_joined_up(self):
        """One component, on both fixture shapes. A denser web that is not connected is
        worse than the coarse one it replaces."""
        corridor()
        beads()
        for name in ("corridor", "beads"):
            st = rail_build(name, margin=20.0)
            self.assertEqual(st["components"], 1, "%s came out in pieces" % name)

    def test_the_step_grows_to_fit_the_node_budget(self):
        """A large ruin gets a coarser web rather than an unaffordable one."""
        volume_define("huge", boxes={"hall": (0, 0, 0, 20000, 20000, 20000)})
        st = rail_build("huge", margin=20.0)
        self.assertLessEqual(st["nodes"], RAIL_MAX_NODES * 2)
        self.assertGreater(st["step"], 450.0, "the step should have grown")

    def test_places_keep_their_own_keys(self):
        """A route has to be able to end somewhere a person named, so an authored place
        is never merged into a derived node that happened to land on it."""
        corridor()
        rail_build("corridor", places={"the far end": (2800, 0, 0)}, margin=20.0)
        self.assertIsNotNone(rail_node("corridor", "the far end"))
        self.assertEqual(rail_node("corridor", "the far end")["kind"], KIND_PLACE)

    def test_a_place_outside_the_hull_is_pulled_in(self):
        """Every relic's `entrance` marker sits outside the hull by design - it is the
        sensor contact. Unprojected it sees nothing and the graph collapses."""
        corridor()
        rail_build("corridor", places={"mouth": (-3400, 0, 0)}, margin=20.0)
        pos = rail_node_pos("corridor", "mouth")
        self.assertIsNotNone(pos)
        self.assertLessEqual(volume_depth("corridor", pos), -20.0 + 1e-6)

    def test_stray_derived_nodes_are_dropped(self):
        """A seed that projects into a pocket nothing can see is a dud, not a piece of the
        ruin - and left in, it makes the component count lie."""
        corridor()
        rail_build("corridor", margin=20.0)
        web = rail_get("corridor")
        for key in web.order:
            if key.startswith("@"):
                self.assertTrue(web.edges.get(key), "%s survived with no edges" % key)

    def test_stats_report_the_shape(self):
        corridor()
        st = rail_build("corridor", margin=20.0)
        for field in ("nodes", "edges", "components", "step", "build_ms", "pruned"):
            self.assertIn(field, st)
        self.assertEqual(rail_stats("corridor")["nodes"], st["nodes"])
        self.assertIsNone(rail_stats("nope"))


class TestRailRoute(unittest.TestCase):
    def setUp(self):
        volume_clear()
        rail_clear()
        corridor()
        rail_build("corridor",
                   places={"west end": (-2800, 0, 0), "east end": (2800, 0, 0),
                           "the alcove": (0, 0, 1600)},
                   margin=20.0)

    def tearDown(self):
        volume_clear()
        rail_clear()

    def test_it_routes_end_to_end(self):
        r = rail_route("corridor", (-2800, 0, 0), "east end")
        self.assertTrue(r)
        self.assertAlmostEqual(r[-1][0], rail_node_pos("corridor", "east end")[0], 3)

    def test_every_leg_stays_inside(self):
        """The assertion the whole layer exists for. A relic has no engine collision, so a
        leg through the rock is not caught by anything downstream."""
        r = rail_route("corridor", (-2800, 0, 0), "the alcove")
        self.assertTrue(r)
        prev = (-2800.0, 0.0, 0.0)
        for leg in r:
            for i in range(1, 21):
                t = i / 20.0
                p = (prev[0] + (leg[0] - prev[0]) * t,
                     prev[1] + (leg[1] - prev[1]) * t,
                     prev[2] + (leg[2] - prev[2]) * t)
                self.assertLess(volume_depth("corridor", p), 0.0,
                                "a leg left the volume at %r" % (p,))
            prev = leg

    def test_a_clear_shot_is_one_leg(self):
        """Somebody already in the room should not be walked round the houses."""
        r = rail_route("corridor", (-2800, 0, 0), "west end")
        self.assertEqual(len(r), 1)

    def test_an_unknown_destination_is_no_route_not_a_guess(self):
        self.assertEqual(rail_route("corridor", (0, 0, 0), "nowhere"), [])
        self.assertEqual(rail_route("nosuchweb", (0, 0, 0), "west end"), [])

    def test_it_never_answers_with_the_straight_line(self):
        """`volume_route` used to answer with `[goal]` for all four of its failure cases,
        so a caller could not tell one clean leg from no way at all - and the suit flew
        the straight line through the rock. There is no such fallback here."""
        volume_define("split", boxes={"a": (-3000, 0, 0, 400, 400, 400),
                                      "b": (3000, 0, 0, 400, 400, 400)})
        rail_build("split", places={"far": (3000, 0, 0)}, margin=20.0)
        self.assertEqual(rail_route("split", (-3000, 0, 0), "far"), [])

    def test_a_position_goal_works_too(self):
        r = rail_route("corridor", (-2800, 0, 0), (2800, 0, 0))
        self.assertTrue(r)
        self.assertAlmostEqual(r[-1][0], 2800.0, 3)


class TestRailBarriers(unittest.TestCase):
    def setUp(self):
        volume_clear()
        rail_clear()
        # A ring with a SHORT way and a LONG way. Deliberately asymmetric: a symmetric
        # ring makes every barrier test vacuous, because the router was already taking
        # the other side and shutting one gate changes nothing measurable.
        #
        #      west column                east column
        #   (-2000, z -1000..2500)     (2000, z -1000..2500)
        #        |----- north corridor (z = -800) -----|      <- the short way
        #        |----- south corridor (z = 2300) -----|      <- the long way round
        volume_define("ring", boxes={
            "wcol": (-2000, 0, 750, 200, 200, 1750),
            "ecol": (2000, 0, 750, 200, 200, 1750),
            "north": (0, 0, -800, 2000, 200, 200),
            "south": (0, 0, 2300, 2000, 200, 200),
        })
        rail_build("ring",
                   places={"west end": (-2000, 0, -800), "east end": (2000, 0, -800)},
                   margin=20.0)

    def tearDown(self):
        volume_clear()
        rail_clear()

    HERE = (-2000, 0, -800)

    def test_the_short_way_is_the_default(self):
        """Guard on the fixture itself. Every barrier test below is only worth anything
        if the router takes the NORTH corridor when nothing is in the way."""
        r = rail_route("ring", self.HERE, "east end")
        self.assertTrue(r)
        self.assertLess(max(p[2] for p in r), 500, "it was not using the short way")

    def test_a_shut_barrier_forces_the_long_way_round(self):
        """The dungeon property: two ways there, and shutting one changes the route rather
        than ending it."""
        self.assertTrue(rail_barrier("ring", "hatch", (0, 0, -800), 500))
        after = rail_route("ring", self.HERE, "east end")
        self.assertTrue(after, "shutting ONE way should not strand the far side")
        self.assertGreater(max(p[2] for p in after), 1500,
                           "the route did not go round the south")

    def test_opening_a_barrier_gives_the_short_way_back(self):
        rail_barrier("ring", "hatch", (0, 0, -800), 500)
        self.assertGreater(max(p[2] for p in rail_route("ring", self.HERE, "east end")),
                           1500)
        self.assertTrue(rail_barrier_open("ring", "hatch"))
        self.assertTrue(rail_barrier_is_open("ring", "hatch"))
        self.assertLess(max(p[2] for p in rail_route("ring", self.HERE, "east end")), 500)

    def test_shutting_both_ways_is_no_route(self):
        rail_barrier("ring", "north gate", (0, 0, -800), 500)
        rail_barrier("ring", "south gate", (0, 0, 2300), 500)
        self.assertEqual(rail_route("ring", self.HERE, "east end"), [])

    def test_open_only_false_asks_what_if(self):
        """What the lint needs: would there BE a way, if this opened?"""
        rail_barrier("ring", "north gate", (0, 0, -800), 500)
        rail_barrier("ring", "south gate", (0, 0, 2300), 500)
        self.assertEqual(rail_route("ring", self.HERE, "east end"), [])
        self.assertTrue(rail_route("ring", self.HERE, "east end", open_only=False))

    def test_a_direct_leg_cannot_slip_through_a_shut_barrier(self):
        """The one-clean-leg shortcut is tested BEFORE the graph, so it has to respect the
        barriers too or a short hop walks straight through a locked door."""
        volume_define("hall", boxes={"h": (0, 0, 0, 2000, 200, 200)})
        rail_build("hall", places={"far": (1800, 0, 0)}, margin=20.0)
        rail_barrier("hall", "plug", (0, 0, 0), 300)
        self.assertEqual(rail_route("hall", (-1800, 0, 0), "far"), [])

    def test_the_approach_is_a_node_beside_it(self):
        """A barrier sits IN the way, so it is not a place - you fly to the node next to
        it and work from there."""
        rail_barrier("ring", "hatch", (0, 0, -800), 500)
        approach = rail_barrier_approach("ring", "hatch", self.HERE)
        self.assertIsNotNone(approach)
        pos = rail_node_pos("ring", approach)
        self.assertLess(abs(pos[2] - (-800)), 600, "the approach is not beside the hatch")
        self.assertTrue(rail_route("ring", self.HERE, approach),
                        "the approach has to be somewhere you can actually get to")

    def test_barriers_list_and_shut_again(self):
        rail_barrier("ring", "hatch", (0, 0, -800), 500)
        self.assertEqual([k for k, _b in rail_barriers("ring")], ["hatch"])
        self.assertEqual([k for k, _b in rail_barriers("ring", shut_only=True)], ["hatch"])
        rail_barrier_open("ring", "hatch")
        self.assertEqual(rail_barriers("ring", shut_only=True), [])
        rail_barrier_shut("ring", "hatch")
        self.assertFalse(rail_barrier_is_open("ring", "hatch"))

    def test_an_unknown_barrier_is_answered_not_raised(self):
        self.assertFalse(rail_barrier_open("ring", "nope"))
        self.assertFalse(rail_barrier_is_open("ring", "nope"))
        self.assertIsNone(rail_barrier_approach("ring", "nope"))
        self.assertFalse(rail_barrier("nosuchweb", "x", (0, 0, 0), 100))


class TestRailHidden(unittest.TestCase):
    def setUp(self):
        volume_clear()
        rail_clear()
        corridor()
        rail_build("corridor",
                   places={"west end": (-2800, 0, 0),
                           "the cache": {"pos": (2800, 0, 0), "hidden": True,
                                         "roles": ("treasure",),
                                         "display": "a sealed locker"}},
                   margin=20.0)

    def tearDown(self):
        volume_clear()
        rail_clear()

    def test_hidden_is_left_off_the_list(self):
        listed = [k for k, _r in rail_nodes("corridor", listed=True)]
        self.assertIn("west end", listed)
        self.assertNotIn("the cache", listed)

    def test_hidden_still_routes_through_and_to(self):
        """Stumbling into a secret on the way somewhere else is the point of having one,
        so hiding is a property of the LIST, never of the graph."""
        self.assertTrue(rail_is_hidden("corridor", "the cache"))
        self.assertTrue(rail_route("corridor", (-2800, 0, 0), "the cache"))

    def test_revealing_puts_it_on_the_list(self):
        self.assertTrue(rail_reveal("corridor", "the cache"))
        self.assertIn("the cache", [k for k, _r in rail_nodes("corridor", listed=True)])
        self.assertTrue(rail_hide("corridor", "the cache"))
        self.assertNotIn("the cache",
                         [k for k, _r in rail_nodes("corridor", listed=True)])

    def test_derived_waypoints_are_never_listed(self):
        """A spine node is how you get somewhere, not somewhere to go."""
        for key, _rec in rail_nodes("corridor", listed=True):
            self.assertFalse(key.startswith("@"))

    def test_roles_and_display_survive(self):
        rec = rail_node("corridor", "the cache")
        self.assertEqual(rec["roles"], ("treasure",))
        self.assertEqual(rec["display"], "a sealed locker")
        self.assertEqual([k for k, _r in rail_nodes("corridor", role="treasure")],
                         ["the cache"])

    def test_hiding_something_that_is_not_there(self):
        self.assertFalse(rail_hide("corridor", "nope"))
        self.assertFalse(rail_reveal("corridor", "nope"))
        self.assertFalse(rail_is_hidden("corridor", "nope"))


class TestRailAttach(unittest.TestCase):
    def setUp(self):
        volume_clear()
        rail_clear()
        corridor()
        rail_build("corridor", places={"west end": (-2800, 0, 0)}, margin=20.0)

    def tearDown(self):
        volume_clear()
        rail_clear()

    def test_a_late_cache_becomes_a_destination(self):
        """A relic's contents do not all exist when it is built - `Starts when: reach ...`
        places one the first time somebody gets near the room."""
        self.assertTrue(rail_attach("corridor", "the manifest", (2600, 0, 0),
                                    roles=("clue",), display="a cargo manifest"))
        self.assertIn("the manifest", [k for k, _r in rail_nodes("corridor", listed=True)])
        self.assertTrue(rail_route("corridor", (-2800, 0, 0), "the manifest"))

    def test_attaching_twice_replaces_rather_than_doubles(self):
        rail_attach("corridor", "thing", (2600, 0, 0))
        rail_attach("corridor", "thing", (-2600, 0, 0))
        self.assertEqual(sum(1 for k, _r in rail_nodes("corridor") if k == "thing"), 1)
        self.assertAlmostEqual(rail_node_pos("corridor", "thing")[0], -2600.0, 0)

    def test_detaching_takes_its_edges_with_it(self):
        rail_attach("corridor", "thing", (2600, 0, 0))
        web = rail_get("corridor")
        neighbours = list(web.edges["thing"])
        self.assertTrue(neighbours)
        self.assertTrue(rail_detach("corridor", "thing"))
        for other in neighbours:
            self.assertNotIn("thing", web.edges[other])
        self.assertIsNone(rail_node("corridor", "thing"))

    def test_attach_refuses_what_it_cannot_place(self):
        self.assertFalse(rail_attach("nosuchweb", "x", (0, 0, 0)))
        self.assertFalse(rail_detach("corridor", "never existed"))


class TestRailRegistry(unittest.TestCase):
    def setUp(self):
        volume_clear()
        rail_clear()

    def tearDown(self):
        volume_clear()
        rail_clear()

    def test_count_does_not_conjure_state_by_asking(self):
        """A reset-ledger probe that creates what it measures reports state surviving a
        reset with nothing running."""
        self.assertEqual(rail_count(), 0)
        self.assertEqual(rail_count(), 0)
        self.assertEqual(rail_names(), [])

    def test_clear_and_remove(self):
        corridor()
        beads()
        rail_build("corridor", margin=20.0)
        rail_build("beads", margin=20.0)
        self.assertEqual(rail_count(), 2)
        self.assertTrue(rail_remove("beads"))
        self.assertFalse(rail_remove("beads"))
        self.assertEqual(rail_count(), 1)
        rail_clear()
        self.assertEqual(rail_count(), 0)

    def test_building_an_unknown_volume_answers_none(self):
        self.assertIsNone(rail_build("nosuchvolume"))

    def test_it_takes_a_volume_object_as_well_as_a_name(self):
        corridor()
        st = rail_build(volume_get("corridor"), margin=20.0)
        self.assertEqual(st["name"], "corridor")

    def test_leg_and_dump(self):
        corridor()
        rail_build("corridor", places={"west end": (-2800, 0, 0)}, margin=20.0)
        web = rail_get("corridor")
        a = "west end"
        b = next(iter(web.edges[a]))
        self.assertEqual(rail_leg("corridor", a, b),
                         (web.nodes[a]["pos"], web.nodes[b]["pos"]))
        self.assertIsNone(rail_leg("corridor", a, "not a node"))
        dump = rail_dump("corridor")
        self.assertEqual(len(dump["nodes"]), len(web.order))
        self.assertEqual(len(dump["edges"]),
                         sum(len(v) for v in web.edges.values()) // 2)
        self.assertIsNone(rail_dump("nope"))

    def test_reachable_counts_what_lint_needs(self):
        corridor()
        rail_build("corridor", places={"west end": (-2800, 0, 0)}, margin=20.0)
        reach = rail_reachable("corridor", "west end")
        self.assertEqual(len(reach), len(rail_get("corridor").order))
        self.assertEqual(rail_reachable("corridor", "nope"), set())


if __name__ == "__main__":
    unittest.main()
