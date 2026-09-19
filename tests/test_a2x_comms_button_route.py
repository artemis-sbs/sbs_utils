"""2.8 comms buttons, driven through a real //comms route.

arme2cosmos emits a 2.8 comms button as

    + "Request Bounty" if a2x_comms_button_visible("Request Bounty", COMMS_ORIGIN_ID):
        if (paid != 1):
            ...
            a2x_clear_comms_button("Request Bounty", 2)

with a2x_set_comms_button / a2x_clear_comms_button where 2.8 had set/clear. This
compiles that shape, opens comms from a player ship, reads the buttons the engine would
be sent, and presses them: the button appears only once set, only for its side, shows up
in a menu that is ALREADY open (comms_refresh_open), and is gone after a one-shot press.
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
from sbs_utils.consoledispatcher import ConsoleDispatcher
from sbs_utils.delete_queue import DeleteQueue
from sbs_utils.gui import Gui
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.mast.maststory import MastStory
from sbs_utils.mast.mastscheduler import MastScheduler
from sbs_utils.mast_sbs import story_nodes  # noqa: F401  (registers route nodes)
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.procedural.a2x.comms import set_comms_button
from sbs_utils.procedural.a2x.sides import declare_sides
from sbs_utils.procedural.query import to_object
from sbs_utils.procedural.routes import follow_route_select_comms
from sbs_utils.procedural.science import science_set_scan_data
from sbs_utils.procedural.spawn import npc_spawn, player_spawn
from sbs_utils.spaceobject import SpaceObject

CID = 1

# The comms console opens only if some //enable/comms answers - LM's comms addon supplies
# those in a real mission; the harness supplies its own.
ROUTE_MAST = '''//enable/comms

//comms
    + "Request Bounty" if a2x_comms_button_visible("Request Bounty", COMMS_ORIGIN_ID):
        if (paid != 1):
            shared paid = 1
            a2x_clear_comms_button("Request Bounty", 2)
    + "Always":
        ~~ pass ~~
'''

HARNESS_STORY = '''shared paid = 0
import a2x_buttons.mast
gui_text("$text:harness;")
await gui()
'''


class ButtonPage(StoryPage):
    story = None


def _library_defaults(table):
    return {k: [cb for cb in v if not hasattr(cb, "__self__")]
            for k, v in table.items() if k[0] == 0 and isinstance(v, list)}


import sbs_utils.procedural.comms, sbs_utils.procedural.science  # noqa: E401,F401
_SELECT_DEFAULTS = _library_defaults(ConsoleDispatcher._dispatch_select)
_MESSAGE_DEFAULTS = _library_defaults(ConsoleDispatcher._dispatch_messages)


class A2xCommsButtonRouteTests(unittest.TestCase):
    def setUp(self):
        from sbs_utils.handlerhooks import reset_mission_state
        reset_mission_state()
        for k, v in _SELECT_DEFAULTS.items():
            ConsoleDispatcher._dispatch_select[k] = list(v)
        for k, v in _MESSAGE_DEFAULTS.items():
            ConsoleDispatcher._dispatch_messages[k] = list(v)
        mock_sbs.create_new_sim()
        mock_sbs.resume_sim()
        DeleteQueue.clear()
        clear_shared()
        SpaceObject.clear()
        Gui.clients = {}
        Gui.widget_list_sent = {}
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent(0, "test"))
        Agent.SHARED.set_inventory_value("sim", mock_sbs.sim)
        declare_sides([1, 2])

        self.buttons = []
        orig_btn, orig_sel = mock_sbs.send_comms_button_info, mock_sbs.send_comms_selection_info
        mock_sbs.send_comms_button_info = lambda ship, color, text, tag: self.buttons.append((text, tag))
        mock_sbs.send_comms_selection_info = lambda ship, face, color, title: self.buttons.clear()

        def restore():
            mock_sbs.send_comms_button_info = orig_btn
            mock_sbs.send_comms_selection_info = orig_sel
        self.addCleanup(restore)

        self.rte = []
        self._orig_rte = MastScheduler.on_runtime_error
        MastScheduler.on_runtime_error = self.rte.append

        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        with open(os.path.join(self.tmp.name, "a2x_buttons.mast"), "w", encoding="utf-8") as f:
            f.write(ROUTE_MAST)
        story = MastStory()
        story.basedir = self.tmp.name
        errors = story.compile(HARNESS_STORY, "a2xbuttons", story)
        self.assertEqual(errors, [], f"compile errors: {errors}")
        ButtonPage.story = story
        FrameContext.mast = story

        self.ship = to_object(player_spawn(0, 0, 0, "Hero", "friendly", "tsn_light_cruiser"))
        self.foe_ship = to_object(player_spawn(0, 0, 500, "Rival", "enemy", "tsn_light_cruiser"))
        self.station = to_object(npc_spawn(1000, 0, 0, "DS1", "friendly", "starbase_command", "behav_station"))
        mock_sbs.assign_client_to_ship(CID, self.ship.id)
        science_set_scan_data(self.ship, self.station, "identified")
        science_set_scan_data(self.foe_ship, self.station, "identified")

        self.server = ButtonPage()
        Gui.push(0, self.server)
        self.page = ButtonPage()
        Gui.push(CID, self.page)
        self.present()

    def tearDown(self):
        MastScheduler.on_runtime_error = self._orig_rte
        Gui.clients = {}
        Gui.widget_list_sent = {}
        ButtonPage.story = None
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
            self.page.gui_state = "repaint"
            self.page.present(FakeEvent(CID, "gui_present"))
        self.assertEqual(self.rte, [], f"MAST runtime errors: {self.rte}")

    def open_comms(self, ship):
        mock_sbs.assign_client_to_ship(CID, ship.id)
        FrameContext.context = Context(mock_sbs.sim, mock_sbs,
                                       FakeEvent(CID, "select_space_object"))
        follow_route_select_comms(ship.id, self.station.id)
        self.present()

    def texts(self):
        return [t for t, _tag in self.buttons]

    def press(self, text):
        tag = next(tag for t, tag in self.buttons if t == text)
        ev = FakeEvent(client_id=CID, tag="press_comms_button", sub_tag=tag,
                       origin_id=self.ship.id, selected_id=self.station.id)
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, ev)
        ConsoleDispatcher.dispatch_message(ev, "comms_target_UID")
        self.present()

    def test_hidden_until_the_mission_sets_it(self):
        self.open_comms(self.ship)
        self.assertIn("Always", self.texts())
        self.assertNotIn("Request Bounty", self.texts())

    def test_setting_it_shows_it_in_the_menu_already_open(self):
        self.open_comms(self.ship)
        self.assertNotIn("Request Bounty", self.texts())
        set_comms_button("Request Bounty", 2)
        self.present()
        self.assertIn("Request Bounty", self.texts())

    def test_a_side_scoped_button_is_not_offered_to_the_other_side(self):
        set_comms_button("Request Bounty", 2)
        self.open_comms(self.foe_ship)
        self.assertIn("Always", self.texts())
        self.assertNotIn("Request Bounty", self.texts())

    def test_a_one_shot_press_runs_once_and_takes_the_button_away(self):
        set_comms_button("Request Bounty", 2)
        self.open_comms(self.ship)
        self.press("Request Bounty")
        self.assertEqual(1, self.server.story_scheduler.get_variable("paid"))
        self.assertNotIn("Request Bounty", self.texts())
        self.assertIn("Always", self.texts())


if __name__ == "__main__":
    unittest.main()
