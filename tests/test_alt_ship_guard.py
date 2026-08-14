"""A console may only be pointed at a SPACE OBJECT.

`sbs.assign_client_to_alt_ship` is how science, comms and the main screen say "look at
that". Hand it an id the engine never created - a task, a fleet, a side, a grid cell -
and the CLIENT dies: measured in engine 5 runs out of 5, as either a modal
`vertexIndex < numVerts` assert out of DX11PAXVertList.cpp or an access violation reading
off the end of a vertex list. The engine takes the id as a ship and indexes a mesh that
was never there.

Two things make that expensive to diagnose, which is why it is worth a test:

  * The crash names a VERTEX INDEX. Nothing in the message points back at the selection,
    so it reads as bad art - a whole investigation went into re-checking meshes that were
    all fine.
  * The id is easy to produce by accident. `prefab_spawn` returns a MastAsyncTask, not an
    object id, so an unawaited call yields something with an `.id` that looks usable and
    is not. That is exactly how it was found.

A dead-but-well-formed space id is deliberately still ALLOWED through: the engine handles
a deleted ship cleanly (measured), and rejecting it would drop legitimate focus changes on
a target that is merely mid-teardown. This guards the class the engine cannot survive.
"""

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.mock import sbs
from sbs_utils.helpers import Context, FrameContext, FakeEvent
from sbs_utils.procedural.query import is_alt_ship_target, is_space_object_id
from sbs_utils.procedural.science import science_set_2dview_focus
from sbs_utils.procedural.gui.viewscreen import _alt_ship
from sbs_utils.procedural.inventory import get_inventory_value, set_inventory_value
from sbs_utils.procedural.spawn import npc_spawn
from sbs_utils.agent import Agent
from sbs_utils.spaceobject import SpaceObject

# Ids the engine did not create. The task id is the real one this was found with -
# `prefab_spawn` handed it back and it went straight to the engine.
TASK_ID = 36028797018964400
FLEET_ID = 0x1000000000000007


class TestAltShipGuard(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        SpaceObject.clear()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        # A console is an Agent like anything else, and inventory writes to an id with
        # no Agent behind it are silently dropped - which quietly disabled the `2d_follow`
        # gate below and made an earlier version of this test pass without ever reaching
        # the guard.
        self.client_id = 1
        console = Agent()
        console.id = self.client_id
        Agent.all[self.client_id] = console
        set_inventory_value(self.client_id, "2d_follow", True)
        self.assertTrue(get_inventory_value(self.client_id, "2d_follow"),
                        "the follow gate is off, so science would send 0 regardless")

    def _capture(self, fn, *args):
        """Run `fn` with the engine call captured, and return what reached the engine."""
        sent = []
        original = sbs.assign_client_to_alt_ship
        sbs.assign_client_to_alt_ship = lambda cid, oid: sent.append((cid, oid))
        try:
            fn(*args)
        finally:
            sbs.assign_client_to_alt_ship = original
        return sent

    def test_zero_is_allowed_because_it_means_clear(self):
        """0 is not an object, it is "stop looking at anything" - it must pass."""
        self.assertTrue(is_alt_ship_target(0))

    def test_a_real_space_object_is_allowed(self):
        oid = npc_spawn(0, 0, 0, "Guarded", "raider", "tsn_light_cruiser", "behav_npcship")
        self.assertTrue(is_space_object_id(oid.id), "test fixture is not a space id")
        self.assertTrue(is_alt_ship_target(oid.id))

    def test_a_task_id_is_refused(self):
        """The id `prefab_spawn` actually returns when nobody awaits it."""
        self.assertFalse(is_alt_ship_target(TASK_ID))

    def test_a_fleet_or_side_id_is_refused(self):
        self.assertFalse(is_alt_ship_target(FLEET_ID))

    def test_none_is_refused(self):
        self.assertFalse(is_alt_ship_target(None))

    def test_science_focus_does_not_hand_a_task_id_to_the_engine(self):
        """The guard has to be in the CALLER, not merely available to it."""
        sent = self._capture(science_set_2dview_focus, self.client_id, TASK_ID)
        self.assertEqual(sent, [], f"a task id reached the engine: {sent}")

    def test_science_focus_still_passes_a_real_object(self):
        """The guard must not cost the ordinary case - this is what science does."""
        target = npc_spawn(0, 0, 2000, "Selected", "raider", "tsn_light_cruiser", "behav_npcship")
        sent = self._capture(science_set_2dview_focus, self.client_id, target.id)
        self.assertEqual(sent, [(self.client_id, target.id)])

    def test_viewscreen_does_not_hand_a_task_id_to_the_engine(self):
        """The main screen reaches the same engine call by a different route."""
        sent = self._capture(_alt_ship, self.client_id, TASK_ID)
        self.assertEqual(sent, [], f"a task id reached the engine: {sent}")

    def test_viewscreen_still_passes_a_real_object(self):
        target = npc_spawn(0, 0, 3000, "OnScreen", "raider", "tsn_light_cruiser", "behav_npcship")
        sent = self._capture(_alt_ship, self.client_id, target.id)
        self.assertEqual(sent, [(self.client_id, target.id)])


if __name__ == "__main__":
    unittest.main()
