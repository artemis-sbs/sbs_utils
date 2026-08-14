"""A property panel must populate on the build that creates it.

The regression: gui_properties_set bailed whenever the frame's event was tagged
`gui_present`. Building a MAST GUI label IS a gui_present, so the canonical

    gui_property_list_box("Options")
    gui_properties_set(p)

pair left the panel EMPTY. It only filled once something re-entered the label
under a different event -- clicking next/prev, loading a preset. Measured on
LM's server mission picker with the headless layout audit: 0 item sections
before, 13 after.

The bail is narrowed, not removed. It was standing in for "this frame does not
own the panel", and the half that is genuinely that -- a follow_route_select_comms
running a comms route on the SERVER's frame, where writing would overwrite the
panel a console is already showing -- still bails. What separates the two is
whether the panel has ever been presented: a listbox whose client_id is still
None can only be one this build just created. Both halves are pinned below.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.agent import Agent
from sbs_utils.vec import Vec3

import sbs_utils.procedural.gui  # noqa: F401  (circular-import order)
from sbs_utils.procedural.gui.property_listbox import gui_properties_set
from sbs_utils.pages.widgets.layout_listbox import LayoutListbox

PROPS = """
Difficulty: 'gui_int_slider("low:1;high:11;", var="DIFFICULTY")'
Player Ships: 'gui_int_slider("low:1;high:8;", var="PLAYER_COUNT")'
"""

CID = 7


class FakeGuiTask:
    """The slice of a GUI task that gui_properties_set touches."""
    def __init__(self):
        self.vars = {}
        self.inventory = {}
        self.on_change_items = []

    def get_variable(self, k, d=None):
        return self.vars.get(k, d)

    def set_variable(self, k, v):
        self.vars[k] = v

    def get_inventory_value(self, k, d=None):
        return self.inventory.get(k, d)

    def set_inventory_value(self, k, v):
        self.inventory[k] = v


class FakePage:
    def __init__(self, task):
        self.gui_task = task
        self.client_id = CID


class FakeGuiAgent:
    """What Agent.get(client_id) resolves to for a connected console."""
    def __init__(self, page):
        self.page = page


class TestPropertiesFirstBuild(unittest.TestCase):
    def setUp(self):
        from cosmos_dev.mock import sbs as mock_sbs
        mock_sbs.create_new_sim()
        FrameContext.aspect_ratios[CID] = Vec3(1024, 768, 0)
        # The frame a console paints under -- the tag the old gate rejected.
        FrameContext.context = Context(mock_sbs.sim, mock_sbs,
                                       FakeEvent(client_id=CID, tag="gui_present"))
        self.task = FakeGuiTask()
        Agent.all[CID] = FakeGuiAgent(FakePage(self.task))

    def tearDown(self):
        Agent.all.pop(CID, None)
        FrameContext.context = None
        FrameContext.task = None
        FrameContext.page = None

    def _panel(self, tag="__PROPS_LB__"):
        lb = LayoutListbox(0, 0, "lb", [], item_template=lambda item: None)
        lb.tag = "lb"
        self.task.set_inventory_value(tag, lb)
        return lb

    def test_a_panel_built_this_frame_gets_its_rows(self):
        lb = self._panel()
        gui_properties_set(PROPS)
        self.assertEqual(2, len(lb.items),
                         "the panel that was just built must not paint blank")
        self.assertEqual(["Difficulty", "Player Ships"],
                         [i.label for i in lb.items])

    def test_a_client_with_no_panel_is_left_alone(self):
        # What the removed gate was really protecting: a frame that does not own
        # the panel writes nothing. Here the task has no __PROPS_LB__ at all.
        gui_properties_set(PROPS)          # must not raise, must not invent one
        self.assertIsNone(self.task.get_inventory_value("__PROPS_LB__"))

    def test_a_frame_with_no_gui_client_writes_nothing(self):
        lb = self._panel()
        Agent.all.pop(CID)                 # client_task resolves to None
        # A dev build makes this loud rather than silent (the is_dev_build
        # branch); a shipped one just returns. Either way nothing is written.
        with self.assertRaises(Exception):
            gui_properties_set(PROPS)
        self.assertEqual([], lb.items)

    def test_the_build_that_creates_a_panel_does_not_re_present_it(self):
        """gui_represent on a never-presented listbox emits sub_region + clear +
        a full present + complete, at the widget's CONSTRUCTOR bounds (no layout
        pass has run), nested inside the enclosing page's own build. The mock
        tolerates that; a real engine session did not -- the server console came
        up but player ships were never created.

        It is redundant besides: a panel built this frame is presented anyway as
        part of the build we are inside."""
        from sbs_utils.procedural.gui import property_listbox as pl
        calls = []
        orig, pl.gui_represent = pl.gui_represent, lambda w: calls.append(w)
        try:
            lb = self._panel()
            gui_properties_set(PROPS)
            self.assertEqual(2, len(lb.items), "still populated")
            self.assertEqual([], calls, "must not re-present a panel mid-build")

            # An already-drawn panel is a genuine update and still re-presents.
            lb.client_id = CID
            FrameContext.context.event = FakeEvent(client_id=CID, tag="gui_message")
            gui_properties_set(PROPS)
            self.assertEqual([lb], calls)
        finally:
            pl.gui_represent = orig

    def test_an_already_drawn_panel_keeps_the_old_protection(self):
        """The half the guard exists for, and the reason it is narrowed rather
        than removed: a follow_route_select_comms can run a comms route on the
        SERVER's frame, where client_task resolves to the server's own GUI task.
        Writing there would overwrite the panel that console is showing.

        "Never presented" is what separates the two: a panel with client_id
        still None can only be one this build just created."""
        lb = self._panel()
        lb.client_id = CID                 # it has been drawn at least once
        gui_properties_set(PROPS)
        self.assertEqual([], lb.items,
                         "an already-drawn panel must not be written during a "
                         "present -- that is the clobber the guard prevents")

    def test_a_named_panel_is_addressed_by_its_own_tag(self):
        other = self._panel("__FAB_PROPS__")
        default = self._panel()
        gui_properties_set(PROPS, tag="__FAB_PROPS__")
        self.assertEqual(2, len(other.items))
        self.assertEqual([], default.items, "only the named panel is written")


if __name__ == "__main__":
    unittest.main()
