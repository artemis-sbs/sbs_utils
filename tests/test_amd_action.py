"""`Action:` - the stage-direction block that fires when a beat starts."""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.agent import clear_shared
from sbs_utils.delete_queue import DeleteQueue
from sbs_utils.procedural.roles import role, has_role, add_role
from sbs_utils.procedural.query import to_id_list, to_object
from sbs_utils.procedural.spawn import npc_spawn
from sbs_utils.procedural.amd_action import (
    amd_action_parse, amd_action_run, amd_action_run_record, amd_action_verbs,
    amd_action_register, amd_action_actors)
from sbs_utils.procedural import amd_landmarks
from sbs_utils.procedural.amd_landmarks import (
    landmark_key_role, landmark_object, landmarks_registry_clear)
from sbs_utils.procedural.amd_schema import field_schema, amd_read_field


class FakeEvent:
    client_id = 0
    tag = ""
    sub_tag = ""
    parent_id = 0
    origin_id = 0
    selected_id = 0
    value_tag = ""
    extra_tag = ""
    source_point = None
    event_time = 0


class TestActionParse(unittest.TestCase):
    """Parsing is pure - no engine, no live objects."""

    def test_actor_verb_operand(self):
        acts = amd_action_parse(["Kidnapper becomes a pirate"])
        self.assertEqual(len(acts), 1)
        self.assertEqual(acts[0]["actor"], "Kidnapper")
        self.assertEqual(acts[0]["verb"], "becomes")
        self.assertEqual(acts[0]["operand"], "pirate")
        self.assertIsNone(acts[0]["error"])

    def test_leading_dash_and_blank_lines_ignored(self):
        acts = amd_action_parse(["- Xorn joins tsn", "", "  ", "// a comment"])
        self.assertEqual([a["verb"] for a in acts], ["joins"])

    def test_a_single_string_is_a_block_of_one(self):
        acts = amd_action_parse("Xorn joins tsn")
        self.assertEqual(len(acts), 1)

    def test_multiline_string_splits(self):
        acts = amd_action_parse("Xorn joins tsn\nKidnapper becomes a pirate")
        self.assertEqual([a["verb"] for a in acts], ["joins", "becomes"])

    def test_longest_verb_wins(self):
        """`is no longer` must not be read as some shorter verb."""
        act = amd_action_parse(["Kidnapper is no longer a suspect"])[0]
        self.assertEqual(act["verb"], "is no longer")
        self.assertEqual(act["actor"], "Kidnapper")
        self.assertEqual(act["operand"], "suspect")

    def test_multi_word_actor(self):
        """The verb sits BETWEEN the names, which is what makes this recoverable."""
        act = amd_action_parse(["The Iron Duke joins tsn"])[0]
        self.assertEqual(act["actor"], "The Iron Duke")
        self.assertEqual(act["operand"], "tsn")

    def test_articles_stripped_from_operand(self):
        for text, want in (("X becomes a pirate", "pirate"),
                           ("X becomes an outlaw", "outlaw"),
                           ("X becomes the villain", "villain")):
            self.assertEqual(amd_action_parse([text])[0]["operand"], want)

    def test_trailing_period_dropped(self):
        self.assertEqual(amd_action_parse(["Xorn joins tsn."])[0]["operand"], "tsn")

    def test_operandless_verb(self):
        act = amd_action_parse(["Kessel Station arrives"])[0]
        self.assertEqual(act["verb"], "arrives")
        self.assertEqual(act["actor"], "Kessel Station")
        self.assertIsNone(act["error"])

    def test_unknown_verb_reports_rather_than_vanishing(self):
        act = amd_action_parse(["Ragnarok frobnicates DS1"])[0]
        self.assertIsNone(act["verb"])
        self.assertIn("no action verb", act["error"])
        self.assertIn("becomes", act["error"])   # offers what it does know

    def test_missing_operand_is_an_error(self):
        act = amd_action_parse(["Kidnapper becomes"])[0]
        self.assertIsNotNone(act["error"])

    def test_missing_actor_is_an_error(self):
        act = amd_action_parse(["becomes a pirate"])[0]
        self.assertIsNotNone(act["error"])

    def test_operand_on_an_operandless_verb_is_an_error(self):
        act = amd_action_parse(["Kessel Station arrives loudly"])[0]
        self.assertIsNotNone(act["error"])

    def test_verbs_are_longest_first(self):
        verbs = amd_action_verbs()
        self.assertEqual(verbs[0], "is no longer")


class TestActionRun(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        SpaceObject.clear()
        landmarks_registry_clear()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())

    def tearDown(self):
        landmarks_registry_clear()
        SpaceObject.clear()
        # `departs` deletes, and delete_object() is DEFERRED. Ids are recycled, so an
        # undrained queue reaches into the NEXT test and deletes whatever inherited
        # that id (it was breaking TestArrives, which passed alone).
        DeleteQueue.clear()
        FrameContext.context = None

    def _spawn(self, key, roles=""):
        """Spawn an actor the way AMD names one: its KEY is a role.

        Actor resolution is declared-key then role - the same order `amd_cutscene`
        resolves a Subject, and deliberately NOT by display name, which nothing
        indexes."""
        csv = "raider, " + key + (", " + roles if roles else "")
        return npc_spawn(0, 0, 0, key, csv, "raider", "behav_npcship")

    def test_becomes_adds_a_role(self):
        so = self._spawn("kidnapper", "civilian, suspect")
        n = amd_action_run(["kidnapper becomes a pirate"])
        self.assertEqual(n, 1)
        self.assertTrue(has_role(so.id, "pirate"))

    def test_is_no_longer_removes_a_role(self):
        so = self._spawn("kidnapper", "civilian, suspect")
        amd_action_run(["kidnapper is no longer a suspect"])
        self.assertFalse(has_role(so.id, "suspect"))
        self.assertTrue(has_role(so.id, "civilian"))

    def test_the_corpus_case_end_to_end(self):
        """LM's `kidnapper_discovered`, verbatim, as an Action block."""
        so = self._spawn("kidnapper", "civilian, suspect")
        n = amd_action_run([
            "kidnapper is no longer a suspect",
            "kidnapper is no longer a civilian",
            "kidnapper becomes a pirate",
            "kidnapper becomes discovered",
        ])
        self.assertEqual(n, 4)
        self.assertFalse(has_role(so.id, "suspect"))
        self.assertFalse(has_role(so.id, "civilian"))
        self.assertTrue(has_role(so.id, "pirate"))
        self.assertTrue(has_role(so.id, "discovered"))

    def test_becomes_acts_on_every_member_of_a_role(self):
        """'Raiders become hostile' is a group direction, not a first-match."""
        a = self._spawn("one", "hostile_group")
        b = self._spawn("two", "hostile_group")
        amd_action_run(["hostile_group becomes hostile"])
        self.assertTrue(has_role(a.id, "hostile"))
        self.assertTrue(has_role(b.id, "hostile"))

    def test_joins_sets_side_and_display(self):
        """Goes through side_set_object_side, so `side_display` moves too - assigning
        `.side` direct leaves the GUI showing the faction the ship just left."""
        from sbs_utils.procedural.sides import side_ensure
        side_ensure("tsn")
        so = self._spawn("xorn")
        amd_action_run(["xorn joins tsn"])
        self.assertEqual(to_object(so.id).side, "tsn")
        self.assertIsNotNone(getattr(to_object(so.id), "side_display", None))

    def test_joins_an_unknown_side_reports(self):
        so = self._spawn("xorn")
        self.assertEqual(amd_action_run(["xorn joins nowhere_at_all"]), 0)

    def test_departs_removes_the_object(self):
        so = self._spawn("scout")
        amd_action_run(["scout departs"])
        self.assertEqual(len(to_id_list(role("scout"))), 0)

    def test_spaces_in_an_actor_name_resolve(self):
        """An author writes the display name; roles are slugs."""
        so = self._spawn("iron_duke")
        amd_action_run(["Iron Duke becomes hostile"])
        self.assertTrue(has_role(so.id, "hostile"))

    def test_one_bad_line_does_not_stop_the_others(self):
        so = self._spawn("kidnapper", "suspect")
        n = amd_action_run([
            "nobody_at_all becomes a pirate",     # unresolvable actor
            "kidnapper becomes a pirate",         # must still run
        ])
        self.assertEqual(n, 1)
        self.assertTrue(has_role(so.id, "pirate"))

    def test_unresolvable_actor_reports_false_not_crash(self):
        self.assertEqual(amd_action_run(["ghost becomes a pirate"]), 0)

    def test_run_record_reads_the_action_field(self):
        so = self._spawn("kidnapper", "suspect")
        rec = {"key": "reveal", "data": {"action": ["kidnapper becomes a pirate"]}}
        self.assertEqual(amd_action_run_record(rec), 1)
        self.assertTrue(has_role(so.id, "pirate"))

    def test_run_record_with_no_action_is_zero(self):
        self.assertEqual(amd_action_run_record({"key": "x", "data": {}}), 0)
        self.assertEqual(amd_action_run_record(None), 0)


class TestArrives(unittest.TestCase):
    """`arrives` places a DECLARED landmark, and its identity is the landmark key -
    which is why an event verb needs no `once` flag."""

    def setUp(self):
        sbs.create_new_sim()
        SpaceObject.clear()
        landmarks_registry_clear()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        amd_landmarks._RECORDS["kessel_station"] = {
            "key": "kessel_station", "name": "Kessel Station", "kind": "station",
            "art": "starbase", "side": "tsn", "roles": "station", "loc": [100, 0, 200],
        }

    def tearDown(self):
        landmarks_registry_clear()
        SpaceObject.clear()

    def test_arrives_spawns_the_declared_landmark(self):
        n = amd_action_run(["Kessel Station arrives"])
        self.assertEqual(n, 1)
        self.assertIsNotNone(landmark_object("kessel_station"))

    def test_arriving_twice_does_not_duplicate(self):
        """A beat can be entered more than once - re-reveal, reload, a repeatable
        thread. The identity is the landmark key, checked against the LIVE world."""
        amd_action_run(["Kessel Station arrives"])
        amd_action_run(["Kessel Station arrives"])
        self.assertEqual(len(to_id_list(role(landmark_key_role("kessel_station")))), 1)

    def test_undeclared_landmark_reports_rather_than_spawning_nothing_quietly(self):
        self.assertEqual(amd_action_run(["Nowhere Station arrives"]), 0)

    def test_an_arrived_landmark_is_an_actor_for_later_lines(self):
        amd_action_run(["Kessel Station arrives"])
        self.assertTrue(amd_action_actors("Kessel Station"))


class TestActionSchema(unittest.TestCase):
    def test_action_is_declared_on_a_quest(self):
        d = field_schema("action", "quest")
        self.assertEqual(d.get("type"), "lines")

    def test_a_single_line_coerces_to_a_list(self):
        key, value = amd_read_field("Action", "Kidnapper becomes a pirate", "quest")
        self.assertEqual(key, "action")
        self.assertEqual(value, ["Kidnapper becomes a pirate"])

    def test_commas_are_not_split(self):
        """A direction contains commas - `csv` would have shredded it."""
        _key, value = amd_read_field("Action", "X becomes a pirate, discovered", "quest")
        self.assertEqual(value, ["X becomes a pirate, discovered"])


class TestActionRegistry(unittest.TestCase):
    def test_a_mission_can_add_a_verb(self):
        seen = []

        def _fn(actor, operand, line):
            seen.append((actor, operand))
            return True

        amd_action_register("salutes", _fn, domain="test")
        try:
            self.assertEqual(amd_action_run(["Xorn salutes the admiral"]), 1)
            self.assertEqual(seen, [("Xorn", "admiral")])
        finally:
            from sbs_utils.procedural import amd_action
            amd_action._VERBS.pop("salutes", None)

    def test_colliding_verb_raises(self):
        from sbs_utils.procedural.amd_action import _becomes
        with self.assertRaises(ValueError):
            amd_action_register("becomes", lambda a, o, l: True, domain="test")
        # the real one survives the attempt
        from sbs_utils.procedural import amd_action
        self.assertIs(amd_action._VERBS["becomes"]["fn"], _becomes)

    def test_reregistering_the_same_fn_is_a_no_op(self):
        from sbs_utils.procedural.amd_action import _becomes
        amd_action_register("becomes", _becomes, domain="test")


if __name__ == "__main__":
    unittest.main()


class TestActionFiresOnQuestStart(unittest.TestCase):
    """The whole point of the slot: `Action:` runs the moment a beat goes ACTIVE."""

    def setUp(self):
        sbs.create_new_sim()
        SpaceObject.clear()
        clear_shared()   # SpaceObject.clear() drops the SHARED agent; quests need it back
        landmarks_registry_clear()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())

    def tearDown(self):
        landmarks_registry_clear()
        SpaceObject.clear()
        DeleteQueue.clear()
        FrameContext.context = None

    def _spawn(self, key, roles=""):
        csv = "raider, " + key + (", " + roles if roles else "")
        return npc_spawn(0, 0, 0, key, csv, "raider", "behav_npcship")

    def test_activating_a_quest_runs_its_action_block(self):
        from sbs_utils.procedural.quest import quest_add, quest_activate
        from sbs_utils.agent import Agent
        so = self._spawn("kidnapper", "suspect")
        quest_add(Agent.SHARED_ID, "reveal", "Reveal", "",
                  data={"action": ["kidnapper becomes a pirate"]})
        self.assertFalse(has_role(so.id, "pirate"))
        quest_activate(Agent.SHARED_ID, "reveal")
        self.assertTrue(has_role(so.id, "pirate"))

    def test_a_quest_with_no_action_is_harmless(self):
        from sbs_utils.procedural.quest import quest_add, quest_activate, quest_run_action
        from sbs_utils.agent import Agent
        quest_add(Agent.SHARED_ID, "plain", "Plain", "", data={"reward": {"credits": 10}})
        quest_activate(Agent.SHARED_ID, "plain")
        self.assertEqual(quest_run_action(Agent.SHARED_ID, "plain"), 0)
        self.assertEqual(quest_run_action(Agent.SHARED_ID, "no_such_quest"), 0)

    def test_running_twice_is_idempotent(self):
        """A quest activated on several agents runs the block once EACH - so every
        built-in verb has to survive being applied twice."""
        from sbs_utils.procedural.quest import quest_add, quest_run_action
        from sbs_utils.procedural.sides import side_ensure
        from sbs_utils.agent import Agent
        side_ensure("tsn")     # `joins` now refuses a side that does not exist
        so = self._spawn("kidnapper", "civilian, suspect")
        quest_add(Agent.SHARED_ID, "reveal", "Reveal", "", data={"action": [
            "kidnapper is no longer a suspect",
            "kidnapper becomes a pirate",
            "kidnapper joins tsn",
        ]})
        first = quest_run_action(Agent.SHARED_ID, "reveal")
        second = quest_run_action(Agent.SHARED_ID, "reveal")
        self.assertEqual(first, second)
        self.assertTrue(has_role(so.id, "pirate"))
        self.assertFalse(has_role(so.id, "suspect"))
        self.assertEqual(to_object(so.id).side, "tsn")


class TestActionLint(unittest.TestCase):
    """A typo'd direction silently does nothing at runtime, so lint has to catch it
    first. The check IS the runtime parser, so the two cannot disagree."""

    def _lint(self, body):
        from sbs_utils.procedural.amd_lint import amd_lint
        amd = ("# [Test](test)\n\n## [Beats](beats)\n\n### [A beat](beat)\n---\n"
               + body + "\n---\nProse.\n")
        return [f for f in amd_lint(content=amd, cross_file=False)
                if f.code in ("unknown-action-verb", "bad-action")]

    def test_valid_block_is_silent(self):
        found = self._lint("Action:\n"
                           "  - Kidnapper becomes a pirate\n"
                           "  - Kidnapper is no longer a suspect\n"
                           "  - Kessel Station arrives\n")
        self.assertEqual(found, [])

    def test_inline_form_is_silent(self):
        self.assertEqual(self._lint("Action: Xorn joins tsn"), [])

    def test_unknown_verb_is_flagged(self):
        found = self._lint("Action:\n  - Ragnarok frobnicates DS1\n")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].code, "unknown-action-verb")
        self.assertIn("becomes", found[0].message)      # offers what it knows

    def test_missing_actor_is_flagged(self):
        found = self._lint("Action:\n  - becomes a pirate\n")
        self.assertEqual([f.code for f in found], ["bad-action"])

    def test_operand_on_an_operandless_verb_is_flagged(self):
        found = self._lint("Action:\n  - Kessel Station arrives loudly\n")
        self.assertEqual([f.code for f in found], ["bad-action"])

    def test_the_finding_points_at_the_right_line(self):
        found = self._lint("Starts when: signal alarm\n"
                           "Action:\n"
                           "  - Kidnapper becomes a pirate\n"
                           "  - Ragnarok frobnicates DS1\n")
        self.assertEqual(len(found), 1)
        # heading(5) + fence(6) + Starts when(7) + Action(8) + good(9) + bad(10)
        self.assertEqual(found[0].line, 10)

    def test_a_following_field_closes_the_block(self):
        """Prose or another field after the list must not be read as directions."""
        found = self._lint("Action:\n"
                           "  - Kidnapper becomes a pirate\n"
                           "Objective: Find the ambassador\n")
        self.assertEqual(found, [])

    def test_a_record_with_no_action_is_silent(self):
        self.assertEqual(self._lint("Objective: Find the ambassador"), [])
