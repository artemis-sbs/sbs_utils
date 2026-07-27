# Unit test: modifier_add(..., replace_if_exists=True) - updating an already-applied
# modifier's value in place instead of leaving the original untouched.
#
# The in-place path writes Modifier.value, which is a LIST (one entry per blob index) that
# calculate_modified_value subscripts - so the regression guarded here is a scalar landing
# in .value and TypeError-ing on the next recalculate.
#
# Run:  python -m unittest tests.test_modifier_replace
from cosmos_dev.mock import sbs as sbs
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.agent import Agent, get_story_id
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.fs import test_set_exe_dir
from sbs_utils.procedural.modifiers import modifier_add, modifiers_get_for_object, ModifierHandler
from sbs_utils.procedural.inventory import get_inventory_value
from sbs_utils.procedural.query import get_data_set_value, to_object
from sbs_utils.procedural.spawn import npc_spawn
import unittest

test_set_exe_dir()


def make_agent():
    a = Agent()
    a.id = get_story_id()
    a.add()
    return a


# Base of an unset inventory key defaults to 1.0, so an additive 2.0 modifier -> 1*(1+2.0) = 3.0.
_K = "buff_coeff"


class TestModifierReplace(unittest.TestCase):
    def setUp(self):
        SpaceObject.clear()
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        ModifierHandler.all_modifiers = []

    def test_default_leaves_existing_modifier_untouched(self):
        a = make_agent()
        modifier_add(a.id, _K, 2.0, "src")
        modifier_add(a.id, _K, 4.0, "src")   # replace_if_exists defaults to False
        self.assertEqual(len(modifiers_get_for_object(a.id, _K)), 1,
                         "re-adding the same source must not stack a second modifier")
        self.assertEqual(get_inventory_value(a.id, _K, 0), 3.0,
                         "without replace_if_exists the original value must stand")

    def test_replace_updates_value_in_place(self):
        a = make_agent()
        modifier_add(a.id, _K, 2.0, "src")
        self.assertEqual(get_inventory_value(a.id, _K, 0), 3.0)

        modifier_add(a.id, _K, 4.0, "src", replace_if_exists=True)

        self.assertEqual(len(modifiers_get_for_object(a.id, _K)), 1,
                         "replacing must update the existing modifier, not add another")
        self.assertEqual(get_inventory_value(a.id, _K, 0), 5.0,
                         "value must recalculate from the new amount (1*(1+4.0))")

    def test_replace_on_a_blob_key_keeps_value_a_list(self):
        # The blob path builds one value per index; the in-place update must keep .value a
        # list or the recalculate here raises TypeError ('float' object is not subscriptable).
        o = to_object(npc_spawn(0, 0, 0, "Subject", "tsn", "tsn_scout", "behav_npcship"))
        _B = "shield_max_val"
        base = get_data_set_value(o.id, _B)

        modifier_add(o.id, _B, 1.0, "buff")
        self.assertAlmostEqual(get_data_set_value(o.id, _B), base * 2.0)

        modifier_add(o.id, _B, 3.0, "buff", replace_if_exists=True)

        mod = modifiers_get_for_object(o.id, _B)[0]
        self.assertIsInstance(mod.value, list, "Modifier.value must stay a list of per-index values")
        self.assertAlmostEqual(get_data_set_value(o.id, _B), base * 4.0,
                               msg="blob value must recalculate from the replaced amount")

    def test_replace_only_touches_the_matching_source(self):
        # Durations give each source its own timer, which is what makes two modifiers on one
        # key distinct (Modifier.__eq__ compares target/key/mod_type/timer/index).
        a = make_agent()
        modifier_add(a.id, _K, 2.0, "srcA", duration=100)
        modifier_add(a.id, _K, 1.0, "srcB", duration=100)
        self.assertEqual(get_inventory_value(a.id, _K, 0), 4.0)   # 1*(1+2.0+1.0)

        modifier_add(a.id, _K, 5.0, "srcA", duration=100, replace_if_exists=True)

        self.assertEqual(len(modifiers_get_for_object(a.id, _K)), 2)
        self.assertEqual(get_inventory_value(a.id, _K, 0), 7.0,
                         "only srcA changes: 1*(1+5.0+1.0)")

    def test_replace_adds_where_missing_across_a_set(self):
        # A set can mix objects that already carry the modifier with ones that don't - the
        # exists branch must not short-circuit the rest of the loop.
        a = make_agent()
        b = make_agent()
        modifier_add(a.id, _K, 2.0, "src")
        modifier_add({a.id, b.id}, _K, 4.0, "src", replace_if_exists=True)
        self.assertEqual(get_inventory_value(a.id, _K, 0), 5.0, "existing one updated")
        self.assertEqual(get_inventory_value(b.id, _K, 0), 5.0, "missing one added")


if __name__ == "__main__":
    unittest.main()
