"""A synthetic console selection must run on a frame that DESCRIBES it.

`follow_route_select_comms` and friends exist to fire a console route "as if the
player made a selection". A real engine selection arrives AS the frame's event,
which is what everything reading FrameContext resolves through -- client_id,
client_task, client_page, EVENT.

These used to build a FakeEvent, hand it to the dispatcher, and leave
FrameContext.context.event pointing at whatever was ambient. So the dispatched
route described itself as the OUTER event -- typically the `gui_present` of
whichever console happened to be painting -- and anything downstream that asked
"what is happening right now?" got the wrong answer.

That is not cosmetic. gui_properties_set could not tell a synthetic route from a
console building its own panel, so it was given an `event.tag == "gui_present"`
bail. That bail ALSO blocked the legitimate first build: LM's server mission
picker painted its Options panel with zero rows until something re-entered the
menu under a different event (measured: 0 rows before, 13 after).
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.consoledispatcher import ConsoleDispatcher
from sbs_utils.procedural.routes import follow_route_select_comms

COMMS = "comms_target_UID"
# Not 0: a 0 origin collides with the comms module's own default-select
# registration, and we want this test to exercise the frame, not comms.
SHIP = 12345


class PresentEvent(FakeEvent):
    """The ambient frame a console is painting under."""
    def __init__(self, client_id=7):
        super().__init__(client_id=client_id, tag="gui_present")


class TestSyntheticRouteFrame(unittest.TestCase):
    def setUp(self):
        from cosmos_dev.mock import sbs as mock_sbs
        mock_sbs.create_new_sim()
        self.ambient = PresentEvent()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, self.ambient)
        self.seen = []
        ConsoleDispatcher.add_select(None, COMMS, self._record)

    def tearDown(self):
        ConsoleDispatcher._dispatch_select.pop((None, COMMS), None)
        FrameContext.context = None

    def _record(self, event):
        # What the ROUTE would see if it asked the frame what is going on.
        ev = FrameContext.context.event
        self.seen.append({
            "tag": ev.tag,
            "sub_tag": ev.sub_tag,
            "client_id": ev.client_id,
            "origin_id": ev.origin_id,
            "selected_id": ev.selected_id,
            "is_frame_event": ev is event,
        })

    def test_the_frame_describes_the_selection_not_the_ambient_present(self):
        follow_route_select_comms(SHIP, 999)

        self.assertEqual(1, len(self.seen), "the select route should have run")
        got = self.seen[0]
        self.assertTrue(got["is_frame_event"],
                        "the dispatched event must BE the frame's event")
        self.assertNotEqual("gui_present", got["tag"],
                            "a synthetic selection must not describe itself as "
                            "the ambient present -- that is what forced the "
                            "gui_properties_set tag bail")
        self.assertEqual(COMMS, got["sub_tag"])
        self.assertEqual(SHIP, got["origin_id"])
        self.assertEqual(999, got["selected_id"])

    def test_the_callers_console_is_carried_into_the_route(self):
        # Every caller inside an @console label or a gui handler is already on
        # the console it means; the route has to land there, not on client 0.
        follow_route_select_comms(SHIP, 999)
        self.assertEqual(7, self.seen[0]["client_id"])

    def test_a_server_caller_stays_on_the_server(self):
        # autoplay's background comms AI has no console. It must not be
        # silently re-pointed at some other client.
        FrameContext.context.event = PresentEvent(client_id=0)
        follow_route_select_comms(SHIP, 999)
        self.assertEqual(0, self.seen[0]["client_id"])

    def test_the_frame_is_restored_afterwards(self):
        follow_route_select_comms(SHIP, 999)
        self.assertIs(self.ambient, FrameContext.context.event,
                      "the override must not leak past the dispatch")

    def test_the_frame_is_restored_even_if_a_route_raises(self):
        def boom(event):
            raise RuntimeError("route blew up")
        ConsoleDispatcher.add_select(None, COMMS, boom)
        try:
            with self.assertRaises(RuntimeError):
                follow_route_select_comms(SHIP, 999)
            self.assertIs(self.ambient, FrameContext.context.event)
        finally:
            ConsoleDispatcher._dispatch_select.pop((None, COMMS), None)


if __name__ == "__main__":
    unittest.main()
