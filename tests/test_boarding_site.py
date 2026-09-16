"""Several consoles walking ONE interior at once, each driving its own body.

This is the claim the whole boarding design rests on, and until `follow_route_point_grid`
existed there was no way to test it at all - the mock emits no `grid_point_selection`, so
a `//point/grid` route was unreachable off a real bridge.

The thing under test is not "can a figure walk". It is that six consoles clicking one
interior in the same frame move six DIFFERENT figures. The prototype could not: it kept
the driven figure on the SITE, so a site had exactly one, and the second console to click
simply stole the first one's body. `test_the_per_site_shape_really_does_break` reproduces
that older shape and asserts it fails, so these tests are pinned against the bug rather
than merely passing.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir

test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.agent import Agent
from sbs_utils.griddispatcher import GridDispatcher
from sbs_utils.procedural import boarding_site as B
from sbs_utils.procedural.grid import grid_pos_data, grid_objects
from sbs_utils.procedural.inventory import get_inventory_value, set_inventory_value
from sbs_utils.procedural.lifeform import lifeform_spawn
from sbs_utils.procedural.query import to_id, to_object
from sbs_utils.procedural.roles import has_role, role
from sbs_utils.procedural.routes import follow_route_point_grid
from sbs_utils.procedural.spawn import npc_spawn

CONSOLES = [41, 42, 43, 44, 45, 46]


class _SiteBase(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        SpaceObject.clear()
        GridDispatcher.clear()
        B.boarding_site_clear()
        # The MAST route body, in Python, so these tests exercise the real dispatch path
        # rather than calling the policy function directly. In a mission this is:
        #
        #     //point/grid
        #         ->END if not has_role(EVENT.client_id, "crew")
        #         boarding_click(EVENT.client_id, GRID_PARENT_ID,
        #                        int(EVENT.source_point.x), int(EVENT.source_point.y))
        #
        # EVENT.client_id, never the MAST global `client_id` - the route runs on the
        # SERVER task, so the global is 0 for every console.
        GridDispatcher.add_any_point(
            lambda e: B.boarding_click(e.client_id, e.parent_id,
                                       e.source_point.x, e.source_point.y))
        # An NPC on purpose. Engine-measured 2026-09-16: a plain NPC returns a real hull
        # map, builds an authored layout to exact counts, and pathfinds a figure across it.
        self.site = to_object(npc_spawn(3000, 0, 3000, "Derelict Kepler", "tsn",
                                        "starbase_civil", "behav_station"))
        B.boarding_site_build(self.site)
        # A console has to be a real agent before anything can be stored ON it:
        # `set_inventory_value` resolves through `to_agent_list`, so a bare int that is
        # nobody silently writes nothing and every read answers None. That failure reads
        # exactly like "all six consoles share one figure", which is the bug under test -
        # so getting this wrong would have looked like a finding.
        from sbs_utils.gui import GuiClient
        for cid in CONSOLES:
            GuiClient(cid)
        self.people = [lifeform_spawn("Boarder %d" % i, "terran_male", "boarding,science")
                       for i in range(len(CONSOLES))]
        self.figs = []
        for i, (cid, who) in enumerate(zip(CONSOLES, self.people)):
            fig = B.boarding_figure_spawn(self.site, who, 19 + i, 36)
            self.figs.append(fig)
            B.boarding_take(cid, fig, self.site)

    def tearDown(self):
        GridDispatcher.clear()
        B.boarding_site_clear()

    def _target_of(self, fig):
        """Where the engine has been told to send this figure, as (pathx, pathy)."""
        blob = to_object(fig).data_set
        return blob.get("pathx", 0), blob.get("pathy", 0)


class TheSiteItself(_SiteBase):
    def test_an_npc_carries_a_built_interior(self):
        self.assertGreater(len(grid_objects(self.site.id)), 0)

    def test_it_is_marked_so_engineerings_routes_can_stand_down(self):
        """LegendaryMissions gates //point/grid and //focus/grid off exactly this role."""
        self.assertTrue(B.boarding_site_is(self.site))
        self.assertTrue(has_role(self.site.id, "boarding_site"))

    def test_a_figure_is_two_agents_pointing_at_each_other(self):
        who, fig = self.people[0], self.figs[0]
        self.assertEqual(to_id(fig), B.boarding_figure_of(who))
        self.assertEqual(to_id(who), B.boarding_lifeform_of(fig))

    def test_the_lifeform_keeps_no_host_so_the_ship_can_still_hail_it(self):
        """A hosted lifeform loses `ultra_beam`, which is the party's channel home."""
        self.assertTrue(has_role(to_id(self.people[0]), "ultra_beam"))


class SixConsolesOneInterior(_SiteBase):
    def test_each_console_holds_its_own_body(self):
        held = [B.boarding_my_figure(cid) for cid in CONSOLES]
        self.assertEqual(len(set(held)), len(CONSOLES), "two consoles share a figure")

    def test_a_click_walks_only_the_clicker(self):
        B.boarding_click(CONSOLES[0], self.site, 4, 18)
        self.assertEqual((4, 18), self._target_of(self.figs[0]))
        for fig in self.figs[1:]:
            self.assertNotEqual((4, 18), self._target_of(fig),
                                "somebody else's figure moved")

    def test_six_clicks_in_one_frame_move_six_different_figures(self):
        """THE CLAIM. Through the real route, not the policy function."""
        cells = [(3, 3), (5, 5), (7, 7), (9, 9), (11, 11), (13, 13)]
        for cid, (x, y) in zip(CONSOLES, cells):
            follow_route_point_grid(cid, self.site, x, y)
        got = [self._target_of(f) for f in self.figs]
        self.assertEqual(cells, got)

    def test_the_route_reads_the_event_not_the_page(self):
        """A //point/grid route runs on the SERVER task. If anything in this path fell
        back to FrameContext.page for the console, every click would move the same body."""
        FrameContext.page = None
        follow_route_point_grid(CONSOLES[2], self.site, 8, 8)
        self.assertEqual((8, 8), self._target_of(self.figs[2]))
        self.assertNotEqual((8, 8), self._target_of(self.figs[0]))

    def test_a_console_that_is_not_boarded_walks_nobody(self):
        self.assertFalse(B.boarding_click(999, self.site, 4, 18))

    def test_a_click_on_a_DIFFERENT_interior_is_ignored(self):
        """//point/grid fires for every interior, including the console's own ship when
        somebody opens Engineering. Without the host check a boarder at Engineering would
        walk their surface body by clicking their own engine room."""
        other = to_object(npc_spawn(-3000, 0, 0, "Kestrel", "tsn", "starbase_civil",
                                    "behav_station"))
        before = self._target_of(self.figs[0])
        self.assertFalse(B.boarding_click(CONSOLES[0], other, 4, 18))
        self.assertEqual(before, self._target_of(self.figs[0]))

    def test_the_per_site_shape_really_does_break(self):
        """The prototype's storage, reproduced, and asserted to fail.

        A test that only passes proves the code runs. This one pins it against the bug it
        replaces: with the driven figure on the SITE, the last console to be given one
        owns it, and every click moves that single body.
        """
        for cid, fig in zip(CONSOLES, self.figs):
            set_inventory_value(self.site.id, "DRIVING", to_id(fig))   # the old shape
        driven = get_inventory_value(self.site.id, "DRIVING", None)
        self.assertEqual(to_id(self.figs[-1]), driven,
                         "per-site storage keeps only the last console's figure")
        held = {B.boarding_my_figure(cid) for cid in CONSOLES}
        self.assertEqual(len(CONSOLES), len(held),
                         "per-client storage keeps all of them - that is the fix")


class WhereAnybodyIs(_SiteBase):
    def test_it_answers_the_cell_without_reading_any_selection(self):
        self.assertEqual((19, 36), B.boarding_where(CONSOLES[0]))

    def test_a_console_with_no_body_has_no_cell(self):
        self.assertIsNone(B.boarding_where(999))

    def test_the_room_under_a_cell_never_answers_a_person(self):
        """`boarding_room_at` is what a panel prints as "where you are". A figure standing
        on the same cell is not a room, and six of them are not six rooms."""
        found = B.boarding_room_at(self.site, 19, 36)
        self.assertNotIn(found, [to_object(f) for f in self.figs])


class ResetAndCleanup(_SiteBase):
    def test_clearing_takes_the_bodies_and_leaves_the_people(self):
        B.boarding_site_clear()
        self.assertEqual(0, B.boarding_figure_count())
        self.assertEqual(0, B.boarding_site_count())
        # The cast is boarding.py's and must survive - they are still on the mission.
        self.assertIsNotNone(to_object(self.people[0]))

    def test_clearing_lets_every_console_go(self):
        B.boarding_site_clear()
        for cid in CONSOLES:
            self.assertIsNone(B.boarding_my_figure(cid))
            self.assertIsNone(B.boarding_my_host(cid))

    def test_clearing_drops_the_stale_link_on_the_surviving_lifeform(self):
        """The figure is deleted but the lifeform is not, so a "figure" link left behind
        would hand the next screen a dead grid-object id."""
        B.boarding_site_clear()
        self.assertIsNone(B.boarding_figure_of(self.people[0]))

    def test_the_probes_report_what_is_live(self):
        self.assertEqual(len(CONSOLES), B.boarding_figure_count())
        self.assertEqual(1, B.boarding_site_count())


if __name__ == "__main__":
    unittest.main()
