"""The shipped crew console WALKS you when you click the map.

The crew console drew the interior and nothing listened to it: no shipped route called
`boarding_click` (only a scratch probe mission did), so a boarder in a real mission could
only watch. This compiles the `//point/grid` route out of the REAL
`LegendaryMissions/boarding/boarding_crew_console.mast` - so an edit to that file is what is
tested, not a copy of it - fires a click through the grid dispatcher the way the engine
does, and checks the right figure was sent.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import os
import sys
import tempfile
import unittest

import cosmos_dev.mock.sbs as mock_sbs
sys.modules.setdefault("sbs", mock_sbs)

from sbs_utils.agent import Agent, clear_shared
from sbs_utils.gui import Gui, GuiClient
from sbs_utils.griddispatcher import GridDispatcher
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.mast.maststory import MastStory
from sbs_utils.mast.mastscheduler import MastScheduler
from sbs_utils.mast_sbs import story_nodes  # noqa: F401  (registers route nodes)
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.procedural import boarding_site as B
from sbs_utils.procedural.lifeform import lifeform_spawn
from sbs_utils.procedural.query import to_object
from sbs_utils.procedural.routes import follow_route_point_grid
from sbs_utils.procedural.spawn import npc_spawn
from sbs_utils.spaceobject import SpaceObject

CID = 41

_LM = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..",
                                    "LegendaryMissions", "boarding",
                                    "boarding_crew_console.mast"))


def _route_block():
    """The `//point/grid` route, exactly as the addon ships it."""
    with open(_LM, encoding="utf-8") as f:
        lines = f.read().splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith("//point/grid"))
    out = [lines[start]]
    for ln in lines[start + 1:]:
        if ln and not ln[0].isspace():
            break
        out.append(ln)
    return "\n".join(out) + "\n"


HARNESS_STORY = '''import crew_route.mast
gui_text("$text:harness;")
await gui()
'''


class RoutePage(StoryPage):
    story = None


@unittest.skipUnless(os.path.exists(_LM), "LegendaryMissions is not checked out beside sbs_utils")
class ThePointGridRouteWalks(unittest.TestCase):
    def setUp(self):
        from sbs_utils.handlerhooks import reset_mission_state
        reset_mission_state()
        mock_sbs.create_new_sim()
        mock_sbs.resume_sim()
        clear_shared()
        SpaceObject.clear()
        GridDispatcher.clear()
        B.boarding_site_clear()
        Gui.clients = {}
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent(0, "test"))
        Agent.SHARED.set_inventory_value("sim", mock_sbs.sim)

        self.rte = []
        self._orig_rte = MastScheduler.on_runtime_error
        MastScheduler.on_runtime_error = self.rte.append

        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        with open(os.path.join(self.tmp.name, "crew_route.mast"), "w", encoding="utf-8") as f:
            f.write(_route_block())
        story = MastStory()
        story.basedir = self.tmp.name
        errors = story.compile(HARNESS_STORY, "crewroute", story)
        self.assertEqual(errors, [], f"compile errors: {errors}")
        RoutePage.story = story
        FrameContext.mast = story

        self.site = to_object(npc_spawn(3000, 0, 3000, "Outpost", "tsn",
                                        "starbase_civil", "behav_station"))
        B.boarding_site_build(self.site)
        GuiClient(CID)
        who = lifeform_spawn("Kovac", "", "boarding,engineering")
        self.fig = B.boarding_figure_spawn(self.site, who, 20, 36)
        B.boarding_take(CID, self.fig, self.site)

        self.server = RoutePage()
        Gui.push(0, self.server)
        self.present()

    def tearDown(self):
        MastScheduler.on_runtime_error = self._orig_rte
        GridDispatcher.clear()
        Gui.clients = {}
        RoutePage.story = None
        FrameContext.task = None
        FrameContext.page = None
        FrameContext.mast = None
        FrameContext.context = None
        SpaceObject.clear()

    def present(self, n=2):
        for _ in range(n):
            mock_sbs.sim._time_tick_counter += 30
            FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent(0, "gui_present"))
            self.server.gui_state = "repaint"
            self.server.present(FakeEvent(0, "gui_present"))
        self.assertEqual(self.rte, [], f"MAST runtime errors: {self.rte}")

    def test_the_route_is_in_the_addon(self):
        self.assertIn("boarding_click", _route_block())

    def test_a_click_on_the_site_walks_this_consoles_figure(self):
        calls = []
        orig = B.boarding_walk
        B.boarding_walk = lambda cid, x, y, *a, **k: calls.append((cid, x, y)) or True
        self.addCleanup(setattr, B, "boarding_walk", orig)
        follow_route_point_grid(CID, self.site, 22, 30)
        self.present()
        self.assertEqual(calls, [(CID, 22, 30)])

    def test_a_click_on_another_interior_does_nothing(self):
        """The route is gated on the site role; Engineering on the console's own ship
        must never walk the boarder."""
        calls = []
        orig = B.boarding_walk
        B.boarding_walk = lambda cid, x, y, *a, **k: calls.append((cid, x, y)) or True
        self.addCleanup(setattr, B, "boarding_walk", orig)
        ship = to_object(npc_spawn(0, 0, 0, "Own ship", "tsn", "tsn_light_cruiser",
                                   "behav_npcship"))
        follow_route_point_grid(CID, ship, 3, 3)
        self.present()
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
