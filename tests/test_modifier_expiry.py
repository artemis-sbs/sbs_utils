# Unit test: the modifier AUTO-EXPIRY sweep - modifiers.py ModifierHandler.remove_expired_modifiers,
# driven the way production does it, through objective.py objectives_run_everything (state-0 slice).
#
# This is the one modifier path the LM_TestRange test_modifiers map could NOT drive deterministically
# (it depends on the periodic objective sweep tick); as pure sbs_utils library behavior it belongs
# here as a fast, isolated unit test rather than a conformance map.
#
# Run:  python -m unittest tests.test_modifier_expiry
from cosmos_dev.mock import sbs as sbs
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.agent import Agent, get_story_id
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.fs import test_set_exe_dir
from sbs_utils.procedural.modifiers import (
    modifier_add, modifiers_get_for_object, modifier_is_expired, ModifierHandler,
)
from sbs_utils.procedural.inventory import get_inventory_value
from sbs_utils.procedural.timers import TICK_PER_SECONDS
from sbs_utils.procedural.objective import objectives_run_everything
import unittest

test_set_exe_dir()


def advance_sim(seconds):
    """Advance the mock sim clock so a duration timer can elapse (now > target)."""
    sbs.sim._time_tick_counter += int(seconds * TICK_PER_SECONDS)


def make_agent():
    a = Agent()
    a.id = get_story_id()
    a.add()
    return a


class _FakeTick:
    """objectives_run_everything reads .state (%3 == 0 runs the modifier sweep) and bumps it."""
    def __init__(self, state=0):
        self.state = state


def sweep():
    """Run the state-0 slice of the production per-tick task = the modifier sweep."""
    objectives_run_everything(_FakeTick(0))


# An inventory-key modifier (not a live data_set/blob field) fully exercises the sweep's
# expire -> modifier_remove -> recalculate path without needing a mock space-object blob;
# the data_set/coeff variant is already covered by LM_TestRange test_modifiers. Base of an
# unset key defaults to 1.0, so an additive 2.0 modifier -> 1*(1+2.0) = 3.0.
_K = "buff_coeff"


class TestModifierExpiry(unittest.TestCase):
    def setUp(self):
        SpaceObject.clear()
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        # all_modifiers is a class-global list; clear it so a leaked modifier from an
        # earlier test can't be swept into this one.
        ModifierHandler.all_modifiers = []

    def test_expired_modifier_is_swept_and_value_restored(self):
        a = make_agent()
        m = modifier_add(a.id, _K, 2.0, "srcA", duration=1)
        self.assertEqual(get_inventory_value(a.id, _K, 0), 3.0)
        self.assertEqual(len(modifiers_get_for_object(a.id, _K)), 1)
        self.assertFalse(modifier_is_expired(m))

        advance_sim(3)  # past the 1s duration; is_timer_finished needs now > target
        self.assertTrue(modifier_is_expired(m))

        sweep()

        self.assertEqual(len(modifiers_get_for_object(a.id, _K)), 0,
                         "expired modifier must be removed by the sweep")
        self.assertEqual(get_inventory_value(a.id, _K, 0), 1.0,
                         "value must return to baseline after the modifier is swept")

    def test_sweep_before_expiry_keeps_active_modifier(self):
        a = make_agent()
        modifier_add(a.id, _K, 2.0, "srcA", duration=100)
        sweep()  # sweep while still active
        self.assertEqual(len(modifiers_get_for_object(a.id, _K)), 1,
                         "an unexpired modifier must survive the sweep")
        self.assertEqual(get_inventory_value(a.id, _K, 0), 3.0)

    def test_permanent_modifier_never_swept(self):
        a = make_agent()
        modifier_add(a.id, _K, 2.0, "perm")  # no duration -> timer None -> never expires
        advance_sim(100000)
        sweep()
        self.assertEqual(len(modifiers_get_for_object(a.id, _K)), 1,
                         "a no-duration modifier has no timer and must never be swept")
        self.assertEqual(get_inventory_value(a.id, _K, 0), 3.0)

    def test_only_expired_source_removed_others_recalc(self):
        # Two sources on the same key; only the expired one is swept, the other stays and the
        # value recalculates to reflect just the survivor.
        a = make_agent()
        modifier_add(a.id, _K, 2.0, "shortsrc", duration=1)   # expires
        modifier_add(a.id, _K, 1.0, "longsrc", duration=100)  # survives
        self.assertEqual(get_inventory_value(a.id, _K, 0), 4.0)   # 1*(1+2.0+1.0)
        self.assertEqual(len(modifiers_get_for_object(a.id, _K)), 2)

        advance_sim(3)
        sweep()

        self.assertEqual(len(modifiers_get_for_object(a.id, _K)), 1,
                         "only the expired source should be swept")
        self.assertEqual(get_inventory_value(a.id, _K, 0), 2.0,
                         "value recalculates to the surviving source (1*(1+1.0))")

    def test_direct_remove_expired_modifiers_call(self):
        # Same behavior straight through ModifierHandler.remove_expired_modifiers (the function
        # objectives_run_everything delegates to), independent of the tick-state rotation.
        a = make_agent()
        modifier_add(a.id, _K, 2.0, "srcA", duration=1)
        advance_sim(3)
        ModifierHandler.remove_expired_modifiers()
        self.assertEqual(len(modifiers_get_for_object(a.id, _K)), 0)
        self.assertEqual(get_inventory_value(a.id, _K, 0), 1.0)


if __name__ == "__main__":
    unittest.main()
