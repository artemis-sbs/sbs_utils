"""`to_set` must say what it was handed, not just that Python could not hash it.

`to_id` and `Agent.resolve_id` are pass-throughs with no `else` branch: an Agent /
CloseData / SpawnData is unwrapped to its `.id` and everything else is returned
untouched. So a dict, a Vec3 or a nested list reaches the set literal in `to_set`
unchanged and Python raises `unhashable type: 'dict'` against query.py - a message that
names neither the resolver nor the argument, reported against the least useful frame in
the stack.

That is the shape of the report this pins: a mission scheduled
`default_player_friendly_eyes` (LegendaryMissions/fleets/map_common.mast) with a list of
{"name","hull"} loadout dicts where the label's contract is player ids or agents. The
crash surfaced four frames down inside `link()`, as `to_set line 148`.

Raising, not dropping, is the point. Every `to_set` caller is a WRITE - link, add_role,
target, brain_add, modifier_add - so swallowing a bad argument makes the write a no-op
with nothing logged, which is strictly harder to find than a crash.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from cosmos_dev.mock import sbs
from sbs_utils.agent import Agent, CloseData, SpawnData
from sbs_utils.helpers import FrameContext, Context
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural.query import to_set
from sbs_utils.procedural.spawn import npc_spawn
from sbs_utils.vec import Vec3


class FakeEvent:
    def __init__(self):
        self.client_id = 0
        self.tag = ""
        self.sub_tag = ""
        self.parent_id = 0
        self.origin_id = 0
        self.selected_id = 0
        self.value_tag = ""
        self.extra_tag = ""
        self.extra_extra_tag = ""
        self.sub_float = 0.0
        self.source_point = None
        self.event_time = 0


class TestToSetRejectsUnresolvable(unittest.TestCase):
    def setUp(self):
        SpaceObject.clear()
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())

    def tearDown(self):
        SpaceObject.clear()

    # --- the shapes that must keep working, unchanged -------------------------------

    def test_none_is_an_empty_set(self):
        self.assertEqual(to_set(None), set())

    def test_bare_id(self):
        self.assertEqual(to_set(7), {7})

    def test_server_id_zero_is_kept(self):
        # to_set is in the to_id_list row of the resolver table: no liveness check and
        # id 0 (the server console) is NOT dropped.
        self.assertEqual(to_set(0), {0})

    def test_agent_unwraps_to_its_id(self):
        ship = npc_spawn(0, 0, 0, "Probe", "tsn", "tsn_battle_cruiser", "behav_npcship")
        obj = ship.py_object
        self.assertEqual(to_set(obj), {obj.id})

    def test_close_data_and_spawn_data_unwrap(self):
        ship = npc_spawn(0, 0, 0, "Probe", "tsn", "tsn_battle_cruiser", "behav_npcship")
        self.assertEqual(to_set(ship), {ship.id})
        self.assertEqual(to_set(CloseData(ship.id, ship.py_object, 0.0)), {ship.id})

    def test_list_becomes_a_set_of_ids(self):
        ship = npc_spawn(0, 0, 0, "Probe", "tsn", "tsn_battle_cruiser", "behav_npcship")
        self.assertEqual(to_set([1, 2, ship]), {1, 2, ship.id})

    def test_set_passes_through(self):
        self.assertEqual(to_set({3, 4}), {3, 4})

    # --- the shapes that must now name themselves -----------------------------------

    def _assert_named(self, bad, type_name):
        with self.assertRaises(TypeError) as cm:
            to_set(bad)
        msg = str(cm.exception)
        # The three things the old `unhashable type: 'dict'` did not carry: which
        # resolver, what was passed, and what it should have been.
        self.assertIn("to_set", msg)
        self.assertIn(type_name, msg)
        self.assertIn("agent id", msg)
        return msg

    def test_dict_names_itself(self):
        # The reported case: a loadout slot where an agent id belongs.
        msg = self._assert_named({"name": "Harbinger", "hull": "tsn_battle_cruiser"}, "dict")
        # The value is echoed so the author recognizes their own data.
        self.assertIn("Harbinger", msg)

    def test_vec3_names_itself(self):
        # Vec3 is deliberately unhashable (__eq__, no __hash__), so a point passed
        # into an id parameter lands here too.
        self._assert_named(Vec3(1, 2, 3), "Vec3")

    def test_dict_inside_a_list_names_itself(self):
        # The list branch builds its set separately; it must guard too. This is the
        # exact reported shape - a LIST of loadout dicts.
        self._assert_named([{"name": "Harbinger"}, 2], "dict")

    def test_nested_list_names_itself(self):
        self._assert_named([[1, 2], 3], "list")

    def test_error_is_not_chained_to_the_hash_failure(self):
        # `raise ... from None` - the useful message must not be printed under a
        # "During handling of the above exception" banner with the raw
        # "unhashable type" the reader has to scroll past to reach it.
        with self.assertRaises(TypeError) as cm:
            to_set({"a": 1})
        self.assertIsNone(cm.exception.__cause__)
        self.assertTrue(cm.exception.__suppress_context__)


if __name__ == "__main__":
    unittest.main()
