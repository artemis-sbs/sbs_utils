# Unit test: modifier_exists(id, source) - is a modifier from this source active on this object?
#
# It used `id in mod.id` where mod.id is the modifier's OWN integer id, so any call with a
# source name raised "TypeError: argument of type 'int' is not iterable" (found by the elite
# warp probe; LM's gamemaster upgrade handler calls it this way). It must compare the
# modifier's TARGET, which is an id or a set of ids.
#
# Run:  python -m unittest tests.test_modifier_exists
from cosmos_dev.mock import sbs as sbs
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.agent import Agent, get_story_id
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.fs import test_set_exe_dir
from sbs_utils.procedural.modifiers import (
    modifier_add, modifier_exists, modifier_remove, Modifier, ModifierHandler,
)
import unittest

test_set_exe_dir()

_K = "buff_coeff"


def make_agent():
    a = Agent()
    a.id = get_story_id()
    a.add()
    return a


class TestModifierExists(unittest.TestCase):
    def setUp(self):
        SpaceObject.clear()
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        ModifierHandler.all_modifiers = []

    def test_a_source_that_is_applied_exists(self):
        a = make_agent()
        modifier_add(a.id, _K, 2.0, "GM")
        self.assertTrue(modifier_exists(a.id, "GM"))

    def test_nothing_applied_does_not_raise(self):
        a = make_agent()
        self.assertFalse(modifier_exists(a.id, "GM"))

    def test_another_source_does_not_match(self):
        a = make_agent()
        modifier_add(a.id, _K, 2.0, "other")
        self.assertFalse(modifier_exists(a.id, "GM"))

    def test_another_object_does_not_match(self):
        a, b = make_agent(), make_agent()
        modifier_add(a.id, _K, 2.0, "GM")
        self.assertFalse(modifier_exists(b.id, "GM"))

    def test_an_object_is_accepted_as_well_as_an_id(self):
        a = make_agent()
        modifier_add(a.id, _K, 2.0, "GM")
        self.assertTrue(modifier_exists(a, "GM"))

    def test_a_set_target_matches_each_member(self):
        a, b = make_agent(), make_agent()
        ModifierHandler.all_modifiers.append(Modifier({a.id, b.id}, _K, [1.0], "GM"))
        self.assertTrue(modifier_exists(a.id, "GM"))
        self.assertTrue(modifier_exists(b.id, "GM"))

    def test_removed_modifier_no_longer_exists(self):
        a = make_agent()
        modifier_add(a.id, _K, 2.0, "GM")
        modifier_remove(a.id, _K, "GM")
        self.assertFalse(modifier_exists(a.id, "GM"))

    def test_a_modifier_object_still_matches_by_equality(self):
        a = make_agent()
        mod = modifier_add(a.id, _K, 2.0, "GM")
        self.assertTrue(modifier_exists(a.id, mod))


class TestObjectiveSectionAlias(unittest.TestCase):
    """`Objective` (singular) on a fence's first line is a kind, as `Objectives` is."""

    def test_singular_objective_is_a_quest_kind(self):
        from sbs_utils.procedural.amd_schema import _kind_to_archetype
        self.assertEqual(_kind_to_archetype("Objective"), "quest")
        self.assertEqual(_kind_to_archetype("objectives"), "quest")


if __name__ == "__main__":
    unittest.main()
