"""A world of several areas, each on its own host - and walking around what is in the way.

The properties under test:

* **An area is a host.** Two zones are two objects; a console is in whichever one its
  body stands on, and moving between them points the console at the new interior.
* **A blocker is never walked through.** The engine cannot close a cell, so the library
  routes around rocks and shut doors and hands the engine one straight leg at a time.
* **An exit moves you.** Stopping on an exit cell takes the console to the zone it names,
  and it arrives BESIDE the way back, not on it.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  (import first: circular import)
import cosmos_dev.mock.sbs as sbs
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.agent import clear_shared
from sbs_utils.gui import GuiClient
from sbs_utils.griddispatcher import GridDispatcher
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural import boarding as A
from sbs_utils.procedural import boarding_site as B
from sbs_utils.procedural import boarding_world as W
from sbs_utils.procedural.gui import boarding_gui as G
from sbs_utils.procedural.lifeform import lifeform_spawn
from sbs_utils.procedural.query import to_object
from sbs_utils.procedural.signal import signal_observe, signal_unobserve

# A real console id: the client bit set, as the engine hands them out. A plain small int
# is not a client, and the library refuses to assign one to a ship.
CID = 0x8000000000000029
W_, H_ = 41, 40


def plan(layout, marks, legend):
    """A starbase_civil floor plan: all hallway, with `marks` {(x, y): char}."""
    rows = [["."] * W_ for _ in range(H_)]
    for (x, y), ch in marks.items():
        rows[y][x] = ch
    head = ["ship: starbase_civil", f"layout: {layout}", f"size: {W_}x{H_}", "legend:"]
    head += [f"  {ch}: {text}" for ch, text in legend.items()]
    return "\n".join(head + ["---"] + ["".join(r) for r in rows]) + "\n"


# A wall across row 10, from x=5 to x=35, with the gap at x=36. An exit on the ridge at
# (20, 0) to the colony; the colony has its way back at (20, 39).
RIDGE = plan("lp_test_ridge",
             {**{(x, 10): "x" for x in range(5, 36)}, (20, 0): "c", (20, 30): "a"},
             {"x": "rock / blocker", "c": "to_colony / room,exit", "a": "landing / room,access"})
COLONY = plan("lp_test_colony", {(20, 39): "r", (5, 5): "a"},
              {"r": "to_ridge / room,exit", "a": "square / room,access"})


class WorldBase(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        # Registered FIRST so it runs LAST: the resets below need a context.
        self.addCleanup(setattr, FrameContext, "context", None)
        # AN OPEN FLOOR. Every stock hull's interior is its silhouette (starbase_civil is
        # a ring and spokes), so an outdoor area needs a hull whose sprite is a solid
        # square. Stood in for here by a permissive mask, which is what such a hull gives.
        from cosmos_dev.mock import hull_mask
        orig = hull_mask.open_cells
        hull_mask.open_cells = lambda *a, **k: None
        self.addCleanup(setattr, hull_mask, "open_cells", orig)
        SpaceObject.clear()
        GridDispatcher.clear()
        clear_shared()
        A.boarding_clear()
        B.boarding_site_clear()
        W.boarding_world_clear()
        self.addCleanup(W.boarding_world_clear)
        self.addCleanup(B.boarding_site_clear)
        self.addCleanup(A.boarding_clear)
        self.ridge = W.boarding_zone_build("ridge", RIDGE, title="Landing Ridge")
        self.colony = W.boarding_zone_build("colony", COLONY, title="Stillwater")
        GuiClient(CID)
        self.who = lifeform_spawn("Kovac", "", "boarding,engineering")
        A.boarding_assign(CID, self.who.id)
        G.boarding_go_down(CID, self.ridge, at=(20, 30))
        self.seen = []
        signal_observe(self._obs)
        self.addCleanup(signal_unobserve, self._obs)

    def _obs(self, name, data):
        if name in ("boarding_moved", "boarding_blocked"):
            self.seen.append((name, data))

    def tearDown(self):
        GridDispatcher.clear()

    def run_world(self, ticks=3000):
        """Physics and the world tick, until the figure stops walking."""
        for _ in range(ticks):
            sbs._physics_grid_movers(1 / 30)
            W.boarding_world_tick()
            if not W.boarding_walking(CID) and not self._moving():
                W.boarding_world_tick()
                return

    def _moving(self):
        from sbs_utils.procedural.grid import grid_valid_blob
        fig = B.boarding_my_figure(CID)
        blob = grid_valid_blob(fig) if fig else None
        return bool(blob is not None and (blob.get("move_speed", 0) or 0) > 0)


class TestZonesAreHosts(WorldBase):
    def test_two_zones_are_two_objects(self):
        self.assertNotEqual(self.ridge.id, self.colony.id)
        self.assertEqual(W.boarding_zone_host("ridge"), self.ridge.id)
        self.assertEqual(W.boarding_zones(), ["ridge", "colony"])

    def test_the_console_is_in_the_zone_its_body_is_on(self):
        self.assertEqual(W.boarding_zone_of(CID), "ridge")
        self.assertEqual(W.boarding_zone_clients("ridge"), {CID})

    def test_the_legend_marks_blockers_and_exits(self):
        self.assertIn((20, 10), W.boarding_blocked_cells(self.ridge))
        self.assertNotIn((36, 10), W.boarding_blocked_cells(self.ridge))
        self.assertEqual(W.boarding_exit_at(self.ridge, 20, 0), "to_colony")

    def test_an_exit_named_to_zone_needs_no_table(self):
        self.assertEqual(W.boarding_exit_target(self.ridge, "to_colony"), ("colony", None))

    def test_a_hidden_host_is_parked_out_of_play(self):
        self.assertLess(self.ridge.pos.y, -10000)


class TestPathing(WorldBase):
    def test_a_path_goes_round_the_wall(self):
        path = W.boarding_path(self.ridge, (20, 30), (20, 2))
        self.assertEqual(path[-1], (20, 2))
        self.assertFalse(set(path) & W.boarding_blocked_cells(self.ridge))
        self.assertIn((36, 10), path)             # through the gap

    def test_an_unreachable_goal_gets_as_close_as_it_can(self):
        W.boarding_block(self.ridge, [(x, 10) for x in range(W_)])  # seal the row
        path = W.boarding_path(self.ridge, (20, 30), (20, 2))
        self.assertNotEqual(path[-1], (20, 2))
        self.assertEqual(path[-1][1], 11)         # stopped against the wall

    def test_legs_are_the_corners(self):
        path = [(1, 0), (2, 0), (2, 1), (2, 2)]
        self.assertEqual(W.boarding_legs(path, (0, 0)), [(2, 0), (2, 2)])


class TestWalking(WorldBase):
    def test_THE_FIGURE_NEVER_STANDS_ON_A_BLOCKER(self):
        blocked = W.boarding_blocked_cells(self.ridge)
        B.boarding_click(CID, self.ridge.id, 20, 5)
        visited = set()
        for _ in range(4000):
            sbs._physics_grid_movers(1 / 30)
            W.boarding_world_tick()
            visited.add(B.boarding_where(CID))
            if B.boarding_where(CID) == (20, 5):
                break
        self.assertEqual(B.boarding_where(CID), (20, 5))
        self.assertFalse(visited & blocked)

    def test_a_blocked_goal_says_so(self):
        B.boarding_click(CID, self.ridge.id, 20, 10)    # a rock
        self.assertTrue(any(n == "boarding_blocked" for n, _ in self.seen))

    def test_an_arrival_intent_runs_when_the_walk_ends(self):
        got = []
        B.boarding_click(CID, self.ridge.id, 22, 30)
        W.boarding_on_arrive(CID, got.append)
        self.run_world()
        self.assertEqual(got, [CID])


class TestMovingBetweenZones(WorldBase):
    def test_stopping_on_an_exit_moves_you(self):
        B.boarding_click(CID, self.ridge.id, 20, 0)
        self.run_world()
        self.assertEqual(W.boarding_zone_of(CID), "colony")
        moved = [d for n, d in self.seen if n == "boarding_moved"]
        self.assertEqual(moved[-1]["BOARDING_ZONE"], "colony")
        self.assertEqual(moved[-1]["BOARDING_FROM_ZONE"], "ridge")

    def test_you_arrive_BESIDE_the_way_back(self):
        """Arriving ON the exit would send you straight back out."""
        W.boarding_exit_follow(CID, "to_colony")
        at = B.boarding_where(CID)
        self.assertNotEqual(at, (20, 39))
        self.assertEqual(abs(at[0] - 20) + abs(at[1] - 39), 1)
        W.boarding_world_tick()
        self.assertEqual(W.boarding_zone_of(CID), "colony")

    def test_only_one_body(self):
        W.boarding_site_move(CID, "colony")
        self.assertEqual(len(B.boarding_figures()), 1)
        self.assertEqual(B.boarding_figures(self.ridge), set())

    def test_the_console_looks_at_the_new_interior(self):
        W.boarding_site_move(CID, "colony")
        self.assertEqual(sbs.get_ship_of_client(CID), self.colony.id)
        self.assertEqual(B.boarding_my_host(CID), self.colony.id)

    def test_its_home_ship_is_still_its_own(self):
        """Going down twice must not record the area it left as home."""
        home = G.boarding_home_ship(CID)
        W.boarding_site_move(CID, "colony")
        self.assertEqual(G.boarding_home_ship(CID), home)

    def test_leaving_an_area_leaves_its_conversation(self):
        scenes = {"deputy": {"key": "deputy", "display_text": "d",
                             "description": "% Hm.\n- [Go]()\n", "data": {}}}
        A.boarding_encounter(scenes, "deputy", CID)
        W.boarding_site_move(CID, "colony")
        self.assertEqual(A.boarding_channel_of(CID), A.boarding_party_channel())

    def test_a_zone_can_be_revealed(self):
        W.boarding_zone_build("caves", None, host=self.colony, known=False)
        self.assertNotIn("caves", W.boarding_zones(known_only=True))
        W.boarding_zone_reveal("caves")
        self.assertIn("caves", W.boarding_zones(known_only=True))


class TestZonesFromAmd(unittest.TestCase):
    def test_exits_are_read_with_their_coordinates(self):
        section = {"children": [{
            "key": "ridge", "display_text": "Landing Ridge", "description": "",
            "data": {"grid": "surface/ridge.grid", "entry": "20, 36",
                     "exits": "to_colony -> colony 20,2, to_flats -> flats",
                     "beam": "yes", "known": "no"}}]}
        rec = W.boarding_zone_records(section)[0]
        self.assertEqual(rec["exits"], {"to_colony": "colony 20,2", "to_flats": "flats"})
        self.assertFalse(rec["known"])
        self.assertTrue(rec["beam"])
        self.assertEqual(W._exit_spec(rec["exits"]["to_colony"]), ("colony", (20, 2)))


if __name__ == "__main__":
    unittest.main()
