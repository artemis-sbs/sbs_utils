"""`comms_drag_event` -> DragDispatcher -> `//drag/comms`.

The engine sends `comms_drag_event` when an object is dragged onto another on the
comms console: origin = the dragged object, selected = the drop target, parent = the
console's player ship. The mock has no drag gesture, so these tests are the only
headless proof the event reaches a route at all.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  registers the route label node
from cosmos_dev.mock import sbs as mock_sbs
from sbs_utils.gui import Gui, GuiClient
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.dragdispatcher import DragDispatcher
from sbs_utils.procedural.routes import route_drag_comms
from sbs_utils.procedural.spawn import player_spawn, npc_spawn
from sbs_utils.procedural.query import to_id

CLIENT = 0x8000000000000001


def _drag_event(source, target, ship, client_id=CLIENT):
    return FakeEvent(client_id=client_id, tag="comms_drag_event",
                     origin_id=source, selected_id=target, parent_id=ship)


class _RecordingTask:
    """Stands in for the server GUI task: records what the route would start."""
    def __init__(self):
        self.started = []

    def start_task(self, label, data):
        self.started.append((label, data))
        return self

    def tick_in_context(self):
        pass


class _Page:
    def __init__(self, task):
        self.gui_task = task


class DragBase(unittest.TestCase):
    def setUp(self):
        mock_sbs.create_new_sim()
        SpaceObject.clear()
        DragDispatcher.clear()
        self.addCleanup(DragDispatcher.clear)
        self._clients, self._sent = Gui.clients, Gui.widget_list_sent
        Gui.clients, Gui.widget_list_sent = {}, {}
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())
        self.ship = to_id(player_spawn(0, 0, 0, "Artemis", "tsn", "tsn_light_cruiser"))
        self.cargo = to_id(npc_spawn(500, 0, 0, "Pod", "tsn", "container_1a", "behav_npcship"))
        self.station = to_id(npc_spawn(900, 0, 0, "DS1", "tsn", "starbase_command", "behav_station"))

    def tearDown(self):
        Gui.clients, Gui.widget_list_sent = self._clients, self._sent
        FrameContext.context = None


class TestDispatch(DragBase):

    def test_the_handler_routes_comms_drag_event(self):
        """Before this the tag fell into `case _:` and printed 'Unhandled event'."""
        from sbs_utils.handlerhooks import cosmos_event_handler
        seen = []
        DragDispatcher.add_comms(seen.append)
        cosmos_event_handler(mock_sbs.sim, _drag_event(self.cargo, self.station, self.ship))
        self.assertEqual(1, len(seen))
        ev = seen[0]
        self.assertEqual((self.cargo, self.station, self.ship, CLIENT),
                         (ev.origin_id, ev.selected_id, ev.parent_id, ev.client_id))

    def test_reset_empties_the_dispatcher(self):
        from sbs_utils.handlerhooks import reset_mission_state, reset_mission_audit
        DragDispatcher.add_comms(lambda e: None)
        reset_mission_state()
        self.assertNotIn("DragDispatcher", reset_mission_audit())
        self.assertEqual(0, len(DragDispatcher._dispatch_comms))


class TestRouteData(DragBase):

    def setUp(self):
        super().setUp()
        self.task = _RecordingTask()
        server = GuiClient(0)
        server.page_stack.append(_Page(self.task))

    def test_the_route_gets_source_target_and_ship(self):
        label = object()
        route_drag_comms(label)
        DragDispatcher.dispatch_comms(_drag_event(self.cargo, self.station, self.ship))
        self.assertEqual(1, len(self.task.started))
        got_label, data = self.task.started[0]
        self.assertIs(label, got_label)
        self.assertEqual(self.cargo, data["DRAG_SOURCE_ID"])
        self.assertEqual(self.station, data["DRAG_TARGET_ID"])
        self.assertEqual(self.ship, data["DRAG_SHIP_ID"])
        self.assertEqual(self.cargo, data["DRAG_SOURCE"].id)
        self.assertEqual(self.station, data["DRAG_TARGET"].id)
        self.assertEqual(self.ship, data["DRAG_SHIP"].id)
        self.assertEqual(CLIENT, data["DRAG_CLIENT_ID"])
        self.assertEqual("comms", data["DRAG_CONSOLE"])

    def test_origin_is_not_passed_as_comms_origin(self):
        """In comms routes COMMS_ORIGIN_ID is the player ship; here origin is the
        dragged object, so reusing the name would mislead."""
        route_drag_comms(object())
        DragDispatcher.dispatch_comms(_drag_event(self.cargo, self.station, self.ship))
        self.assertNotIn("COMMS_ORIGIN_ID", self.task.started[0][1])

    def test_a_label_registered_twice_runs_once(self):
        """Every client compiles the route; it must not fire once per client."""
        label = object()
        route_drag_comms(label)
        route_drag_comms(label)
        DragDispatcher.dispatch_comms(_drag_event(self.cargo, self.station, self.ship))
        self.assertEqual(1, len(self.task.started))

    def test_a_drop_on_nothing_carries_zero_and_none(self):
        route_drag_comms(object())
        DragDispatcher.dispatch_comms(_drag_event(self.cargo, 0, self.ship))
        data = self.task.started[0][1]
        self.assertEqual(0, data["DRAG_TARGET_ID"])
        self.assertIsNone(data["DRAG_TARGET"])


if __name__ == "__main__":
    unittest.main()
