"""A dispatched event is READ-ONLY, in the mock as in the engine.

The engine hands the handler a Pybind11 object whose attributes cannot be
assigned. `FakeEvent` is a plain Python object and took an assignment happily, so
the mock was kinder than the thing it stands in for - and that hid a real defect:
code that carried an arbitrated value onward by re-stamping `event.sub_tag`
passed the entire suite and raised on a live bridge.

So the mock refuses it too. Construction stays mutable (a builder has to fill one
in); `cosmos_event_handler` freezes on the way in, which is the one place every
event passes through.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.mock import sbs as mock_sbs
from sbs_utils.helpers import FakeEvent, FrameContext, Context
from sbs_utils.spaceobject import SpaceObject


class TestFakeEventFreeze(unittest.TestCase):

    def test_a_builder_can_still_fill_one_in(self):
        """The mock runner builds an event across several statements - a slider's
        value, a click's world point - so construction cannot be frozen."""
        ev = FakeEvent(client_id=1, tag="main_screen_change")
        ev.sub_tag = "lrs"
        ev.value_tag = "front"
        ev.sub_float = 0.5
        self.assertEqual((ev.sub_tag, ev.value_tag, ev.sub_float), ("lrs", "front", 0.5))

    def test_freezing_makes_a_write_raise(self):
        ev = FakeEvent(tag="main_screen_change", sub_tag="lrs")
        ev.freeze()
        with self.assertRaises(AttributeError):
            ev.sub_tag = "tactical"

    def test_the_message_says_what_to_do_instead(self):
        """The error is the only warning a future author gets, so it has to name the
        cause and the alternative rather than just refusing."""
        ev = FakeEvent().freeze()
        with self.assertRaises(AttributeError) as cm:
            ev.value_tag = "x"
        msg = str(cm.exception)
        self.assertIn("Pybind11", msg)
        self.assertIn("read-only", msg)

    def test_reads_still_work_and_freeze_is_idempotent(self):
        ev = FakeEvent(tag="t", sub_tag="s").freeze().freeze()
        self.assertEqual((ev.tag, ev.sub_tag), ("t", "s"))

    def test_an_unfrozen_event_is_unaffected(self):
        """Events the library builds for itself - overlay repaints, gui pushes -
        never go through dispatch and must stay writable."""
        ev = FakeEvent(tag="overlay")
        ev.sub_tag = "fine"
        self.assertEqual(ev.sub_tag, "fine")

    def test_no_stray_attributes(self):
        """__slots__ as well: the engine's event has a fixed set of fields, so code
        that stashes something extra on it is writing somewhere the engine has not
        got."""
        ev = FakeEvent()
        with self.assertRaises(AttributeError):
            ev.my_own_field = 1


class TestDispatchFreezes(unittest.TestCase):
    """The choke point. Freezing at each call site would miss the next one added."""

    def setUp(self):
        from sbs_utils.gui import Gui
        mock_sbs.create_new_sim()
        SpaceObject.clear()
        # The handler presents the GUI as its last phase, so leftover client state
        # from another module turns this into a test of that instead.
        self._clients, self._sent = Gui.clients, Gui.widget_list_sent
        Gui.clients, Gui.widget_list_sent = {}, {}
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())

    def tearDown(self):
        from sbs_utils.gui import Gui
        Gui.clients, Gui.widget_list_sent = self._clients, self._sent
        FrameContext.context = None

    # The freeze is the first thing cosmos_event_handler does, before any dispatch.
    # What the handler goes on to do needs a whole mission behind it - a story, a
    # start page - so these assert the POST-CONDITION and let the rest fail if it
    # wants to. Driving the full handler here would be a test of the fixture.

    def test_cosmos_event_handler_freezes_the_event(self):
        from sbs_utils.handlerhooks import cosmos_event_handler
        ev = FakeEvent(client_id=0, tag="mission_tick", sub_tag="sim_running")
        ev.value_tag = "writable before dispatch"
        try:
            cosmos_event_handler(mock_sbs.sim, ev)
        except Exception:                                    # noqa: BLE001
            pass
        with self.assertRaises(AttributeError,
                               msg="the event was still writable after dispatch"):
            ev.value_tag = "after"

    def test_a_real_engine_event_without_freeze_is_left_alone(self):
        """A Pybind11 event has no `freeze`, so the hook has to be a guarded getattr.
        An unguarded call would raise on the ENGINE's own object - turning a
        mock-fidelity measure into a crash on the only thing that matters."""
        from sbs_utils.handlerhooks import cosmos_event_handler

        class EngineLikeEvent:
            tag = "mission_tick"
            sub_tag = "sim_running"
            client_id = 0
            origin_id = 0
            selected_id = 0
            parent_id = 0
            value_tag = ""
            extra_tag = ""
            extra_extra_tag = ""
            sub_float = 0.0
            event_time = 0
            source_point = None

        ev = EngineLikeEvent()
        self.assertFalse(hasattr(ev, "freeze"), "precondition: no freeze to call")
        try:
            cosmos_event_handler(mock_sbs.sim, ev)
        except Exception as e:                               # noqa: BLE001
            self.assertNotIn("freeze", str(e),
                             "the freeze hook tripped over an engine event")


if __name__ == "__main__":
    unittest.main()
