from cosmos_dev.mock import sbs as sbs
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.agent import Agent, get_story_id
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.fs import test_set_exe_dir
from sbs_utils.procedural.quest import (
    quest_add, quest_get, quest_remove, quest_transfer,
    quest_get_state, quest_get_key, quest_set_key,
    quest_activate, quest_complete,
    quest_log_build_items,
    quest_console_enable, quest_is_console_enabled,
    quest_add_yaml, quest_add_object, quest_agent_quests,
    document_get_amd_file,
    QuestState,
)
from sbs_utils.procedural.quest_driver import quest_mark_complete, quest_mark_failed
import unittest

test_set_exe_dir()

_ALL_CONSOLES = "helm,comms,weapons,science,engineering,main_screen"


def make_agent():
    a = Agent()
    a.id = get_story_id()
    a.add()
    return a


class TestQuestCRUD(unittest.TestCase):

    def setUp(self):
        SpaceObject.clear()
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        # reset the module-level console set between tests
        quest_console_enable(_ALL_CONSOLES, False)

    def tearDown(self):
        quest_console_enable(_ALL_CONSOLES, False)

    # ------------------------------------------------------------------
    # quest_add / quest_get
    # ------------------------------------------------------------------

    def test_quest_add_and_get(self):
        agent = make_agent()
        quest_add(agent.id, "find_artifact", "Find the Artifact", "Locate the lost relic")
        q = quest_get(agent.id, "find_artifact")
        self.assertIsNotNone(q)
        self.assertEqual(q.get("display_text"), "Find the Artifact")
        self.assertEqual(q.get("description"), "Locate the lost relic")

    def test_quest_get_state_defaults_idle(self):
        agent = make_agent()
        quest_add(agent.id, "patrol", "Patrol Sector", "Patrol sector 7")
        self.assertEqual(quest_get_state(agent.id, "patrol"), QuestState.IDLE)

    def test_quest_add_with_explicit_state(self):
        agent = make_agent()
        quest_add(agent.id, "rescue", "Rescue Mission", "Save the crew", state=QuestState.ACTIVE)
        self.assertEqual(quest_get_state(agent.id, "rescue"), QuestState.ACTIVE)

    def test_quest_get_returns_none_for_unknown(self):
        agent = make_agent()
        self.assertIsNone(quest_get(agent.id, "no_such_quest"))

    def test_quest_get_state_returns_idle_for_unknown(self):
        agent = make_agent()
        self.assertEqual(quest_get_state(agent.id, "missing"), QuestState.IDLE)

    def test_quest_agent_quests_none_before_any_quest(self):
        agent = make_agent()
        self.assertIsNone(quest_agent_quests(agent.id))

    def test_quest_agent_quests_not_none_after_add(self):
        agent = make_agent()
        quest_add(agent.id, "find", "Find", "Find something")
        self.assertIsNotNone(quest_agent_quests(agent.id))

    # ------------------------------------------------------------------
    # quest_get_key / quest_set_key
    # ------------------------------------------------------------------

    def test_quest_get_key(self):
        agent = make_agent()
        quest_add(agent.id, "patrol", "Patrol Sector", "Patrol sector 7")
        self.assertEqual(quest_get_key(agent.id, "patrol", "display_text"), "Patrol Sector")

    def test_quest_set_key(self):
        agent = make_agent()
        quest_add(agent.id, "patrol", "Patrol Sector", "Patrol sector 7")
        quest_set_key(agent.id, "patrol", "state", QuestState.ACTIVE)
        self.assertEqual(quest_get_state(agent.id, "patrol"), QuestState.ACTIVE)

    def test_quest_set_key_custom(self):
        agent = make_agent()
        quest_add(agent.id, "recon", "Recon Mission", "Scout enemy territory")
        quest_set_key(agent.id, "recon", "priority", 5)
        self.assertEqual(quest_get_key(agent.id, "recon", "priority"), 5)

    def test_quest_set_key_on_unknown_is_noop(self):
        agent = make_agent()
        quest_set_key(agent.id, "ghost", "state", QuestState.ACTIVE)
        # No exception, no effect
        self.assertIsNone(quest_get(agent.id, "ghost"))

    # ------------------------------------------------------------------
    # quest_remove
    # ------------------------------------------------------------------

    def test_quest_remove(self):
        agent = make_agent()
        quest_add(agent.id, "find_artifact", "Find Artifact", "Locate it")
        removed = quest_remove(agent.id, "find_artifact")
        self.assertIsNotNone(removed)
        self.assertIsNone(quest_get(agent.id, "find_artifact"))

    def test_quest_remove_returns_quest_data(self):
        agent = make_agent()
        quest_add(agent.id, "patrol", "Patrol", "Patrol sector")
        removed = quest_remove(agent.id, "patrol")
        self.assertEqual(removed.get("display_text"), "Patrol")

    def test_quest_remove_nonexistent_returns_none(self):
        agent = make_agent()
        result = quest_remove(agent.id, "ghost")
        self.assertIsNone(result)

    # ------------------------------------------------------------------
    # quest_transfer
    # ------------------------------------------------------------------

    def test_quest_transfer(self):
        src = make_agent()
        dst = make_agent()
        quest_add(src.id, "courier", "Courier Run", "Deliver supplies")
        result = quest_transfer(src.id, dst.id, "courier")
        self.assertTrue(result)
        self.assertIsNone(quest_get(src.id, "courier"))
        self.assertIsNotNone(quest_get(dst.id, "courier"))

    def test_quest_transfer_nonexistent_returns_false(self):
        src = make_agent()
        dst = make_agent()
        result = quest_transfer(src.id, dst.id, "ghost")
        self.assertFalse(result)

    # ------------------------------------------------------------------
    # quest_set_state — documents that signals fire but state is NOT stored
    # NOTE: quest_set_state calls signal_emit but never writes quest["state"];
    # state must be set explicitly via quest_set_key to take effect.
    # ------------------------------------------------------------------

    def test_quest_activate_does_not_change_state(self):
        agent = make_agent()
        quest_add(agent.id, "patrol", "Patrol", "Patrol sector")
        quest_activate(agent.id, "patrol")
        # signal_emit fires but quest["state"] is never written, so IDLE remains
        self.assertEqual(quest_get_state(agent.id, "patrol"), QuestState.IDLE)

    def test_quest_state_changes_via_set_key(self):
        agent = make_agent()
        quest_add(agent.id, "patrol", "Patrol", "Patrol sector")
        quest_set_key(agent.id, "patrol", "state", QuestState.ACTIVE)
        self.assertEqual(quest_get_state(agent.id, "patrol"), QuestState.ACTIVE)

    # ------------------------------------------------------------------
    # quest_console_enable / quest_is_console_enabled
    # ------------------------------------------------------------------

    def test_console_disabled_by_default(self):
        self.assertFalse(quest_is_console_enabled("helm"))

    def test_console_enabled_after_enable(self):
        quest_console_enable("helm")
        self.assertTrue(quest_is_console_enabled("helm"))

    def test_console_disabled_after_disable(self):
        quest_console_enable("comms")
        quest_console_enable("comms", False)
        self.assertFalse(quest_is_console_enabled("comms"))

    def test_console_enable_multiple(self):
        quest_console_enable("helm,comms,science")
        self.assertTrue(quest_is_console_enabled("helm"))
        self.assertTrue(quest_is_console_enabled("comms"))
        self.assertTrue(quest_is_console_enabled("science"))
        self.assertFalse(quest_is_console_enabled("weapons"))

    def test_console_enable_case_insensitive(self):
        quest_console_enable("Helm")
        self.assertTrue(quest_is_console_enabled("helm"))
        self.assertTrue(quest_is_console_enabled("HELM"))

    # ------------------------------------------------------------------
    # quest_add_yaml
    # ------------------------------------------------------------------

    def test_quest_add_yaml(self):
        agent = make_agent()
        yaml_text = """
find_artifact:
    display_text: Find the Artifact
    description: Locate the lost relic
patrol_sector:
    display_text: Patrol Sector 7
    description: Keep the peace
"""
        quest_add_yaml(agent.id, yaml_text)
        q1 = quest_get(agent.id, "find_artifact")
        q2 = quest_get(agent.id, "patrol_sector")
        self.assertIsNotNone(q1)
        self.assertEqual(q1.get("display_text"), "Find the Artifact")
        self.assertIsNotNone(q2)
        self.assertEqual(q2.get("display_text"), "Patrol Sector 7")

    def test_quest_add_yaml_state_string(self):
        agent = make_agent()
        yaml_text = """
active_quest:
    display_text: Active Quest
    description: Already started
    state: ACTIVE
"""
        quest_add_yaml(agent.id, yaml_text)
        self.assertEqual(quest_get_state(agent.id, "active_quest"), QuestState.ACTIVE)

    def test_quest_add_yaml_invalid_state_defaults_idle(self):
        agent = make_agent()
        yaml_text = """
bad_quest:
    display_text: Bad State Quest
    description: Has invalid state
    state: NOTASTATE
"""
        quest_add_yaml(agent.id, yaml_text)
        self.assertEqual(quest_get_state(agent.id, "bad_quest"), QuestState.IDLE)

    # ------------------------------------------------------------------
    # document_get_amd_file (AMD parser)
    # ------------------------------------------------------------------

    def test_amd_parse_single_header(self):
        content = "# [Find the Artifact](quest/find)\nLocate the lost relic.\n"
        result = document_get_amd_file(None, content=content)
        children = result.get("children")
        self.assertEqual(len(children), 1)
        self.assertEqual(children[0]["key"], "quest/find")
        self.assertEqual(children[0]["display_text"], "Find the Artifact")

    def test_amd_parse_nested_headers(self):
        content = (
            "# [Main Quest](quest/main)\nMain description.\n"
            "## [Sub Quest](quest/main/sub)\nSub description.\n"
        )
        result = document_get_amd_file(None, content=content)
        children = result.get("children")
        self.assertEqual(len(children), 1)
        sub = children[0].get("children")
        self.assertEqual(len(sub), 1)
        self.assertEqual(sub[0]["key"], "quest/main/sub")

    def test_amd_parse_multiple_top_level(self):
        content = (
            "# [Quest A](a)\n"
            "# [Quest B](b)\n"
            "# [Quest C](c)\n"
        )
        result = document_get_amd_file(None, content=content)
        keys = [c["key"] for c in result.get("children")]
        self.assertEqual(keys, ["a", "b", "c"])

    def test_amd_parse_description_text(self):
        content = "# [Quest](q/1)\nLine one.\nLine two.\n"
        result = document_get_amd_file(None, content=content)
        desc = result["children"][0]["description"]
        self.assertIn("Line one.", desc)
        self.assertIn("Line two.", desc)

    def test_amd_parse_query_string(self):
        content = "# [Quest](q/1?priority=high)\n"
        result = document_get_amd_file(None, content=content)
        child = result["children"][0]
        self.assertEqual(child["key"], "q/1")
        self.assertEqual(child["priority"], "high")

    def test_amd_parse_returns_root_on_error(self):
        # Invalid URN should be caught and return a fallback dict
        content = "# [Bad](q/1?broken)\n"
        result = document_get_amd_file(None, content=content)
        self.assertIsNotNone(result)
        self.assertIn("key", result)

    def test_amd_parse_strips_comments(self):
        content = "// this is a comment\n# [Quest](q/1)\n"
        result = document_get_amd_file(None, content=content)
        self.assertEqual(len(result["children"]), 1)

    def test_amd_parse_empty_content(self):
        result = document_get_amd_file(None, content="")
        self.assertEqual(result["children"], [])

    def test_amd_parse_missing_file_returns_root(self):
        result = document_get_amd_file("/nonexistent/path.amd")
        self.assertEqual(result["children"], [])

    def test_amd_parse_data_section(self):
        # YAML between 3+ dash lines attaches to the current heading as "data"
        content = ("# [Quest](q/1)\n"
                   "---\n"
                   "cockpit: fighter\n"
                   "on_kill: { role: raider, count: 5 }\n"
                   "---\n"
                   "The briefing prose.\n")
        result = document_get_amd_file(None, content=content)
        child = result["children"][0]
        self.assertEqual(child["data"]["cockpit"], "fighter")
        self.assertEqual(child["data"]["on_kill"]["count"], 5)
        # Fenced lines are not added to the description; prose still is.
        self.assertIn("The briefing prose.", child["description"])
        self.assertNotIn("cockpit", child["description"])

    def test_a_fence_opens_only_after_a_heading(self):
        # The `---` fence NO LONGER TOGGLES. It used to, so a single stray rule in
        # prose inverted data-and-body for the rest of the file. Now a fence opens
        # only right after a heading and closes only while open; anywhere else it is
        # prose. Re-opening a second data block after prose therefore no longer
        # merges - no file in the corpus (65 files, 1652 fences) did that.
        content = ("# [Quest](q/1)\n"
                   "---\n"
                   "a: 1\n"
                   "---\n"
                   "prose\n"
                   "---\n"
                   "b: 2\n"
                   "---\n")
        result = document_get_amd_file(None, content=content)
        child = result["children"][0]
        self.assertEqual(child["data"]["a"], 1)
        self.assertNotIn("b", child["data"])
        self.assertIn("b: 2", child["description"])

    def test_a_stray_rule_in_prose_cannot_swallow_the_file(self):
        content = ("# [One](q/1)\n---\na: 1\n---\n"
                   "prose\n---\nmore prose\n"
                   "# [Two](q/2)\n---\nb: 2\n---\n")
        result = document_get_amd_file(None, content=content)
        self.assertEqual(result["children"][0]["data"]["a"], 1)
        # the second heading and ITS fence still parse - under the old toggle the
        # stray rule inverted everything after it
        self.assertEqual(result["children"][1]["key"], "q/2")
        self.assertEqual(result["children"][1]["data"]["b"], 2)

    def test_amd_parse_no_data_section(self):
        # Headings without a data section have no "data" key
        content = "# [Quest](q/1)\nplain prose\n"
        result = document_get_amd_file(None, content=content)
        self.assertNotIn("data", result["children"][0])


class TestQuestLogShow(unittest.TestCase):
    """`Show:` decides WHEN a quest is listed, separately from whether it runs."""

    def setUp(self):
        SpaceObject.clear()
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        self.aid = make_agent().id

    def _add(self, key, title, show=None, state=QuestState.ACTIVE, **data):
        if show:
            data["show"] = show
        quest_add(self.aid, key, title, "", state=state, data=data)

    def _titles(self):
        rows = quest_log_build_items([("Mission", self.aid)])
        # a leaf row IS a MastDataObject; a group/section is a list-box header
        # carrying its row (a MastDataObject too, for a group) in `.data`
        out = []
        for r in rows:
            d = getattr(r, "data", None)
            t = (d.get("title") if d is not None else None) or getattr(r, "title", None)
            if t:
                out.append(t)
        return out

    def test_always_is_the_default(self):
        self._add("a", "Plain")
        self.assertIn("Plain", self._titles())

    def test_never_is_not_listed_in_any_state(self):
        self._add("a", "Machinery", show="never")
        self.assertNotIn("Machinery", self._titles())
        quest_mark_complete(self.aid, "a")
        self.assertNotIn("Machinery", self._titles())

    def test_when_done_appears_only_once_it_resolves(self):
        self._add("a", "Beat", show="when done")
        self.assertNotIn("Beat", self._titles(), "a running beat is not a to-do")
        quest_mark_complete(self.aid, "a")
        self.assertIn("Beat", self._titles(), "a resolved beat is history")

    def test_when_done_counts_FAILED_as_resolved(self):
        self._add("a", "Beat", show="when done")
        quest_mark_failed(self.aid, "a")
        self.assertIn("Beat", self._titles())

    def test_underscores_and_case_are_accepted(self):
        self._add("a", "Beat", show="When_Done")
        self.assertNotIn("Beat", self._titles())

    # -- `with children`: a grouping heading, not a quest ---------------------

    def test_with_children_hides_a_group_until_something_under_it_shows(self):
        self._add("grp", "Ramscoop", show="with children")
        self._add("grp/one", "Ramscoop Begin", show="when done")
        self.assertNotIn("Ramscoop", self._titles(),
                         "a group must not name a thread that has not happened")
        quest_mark_complete(self.aid, "grp/one")
        titles = self._titles()
        self.assertIn("Ramscoop", titles)
        self.assertIn("Ramscoop Begin", titles)

    # -- the KIND NOUN implies the same thing, in screenplay words ------------

    def test_Beat_implies_when_done(self):
        self._add("a", "Ramscoop Begin", __kind__="beat")
        self.assertNotIn("Ramscoop Begin", self._titles())
        quest_mark_complete(self.aid, "a")
        self.assertIn("Ramscoop Begin", self._titles())

    def test_Arc_implies_with_children(self):
        self._add("grp", "Ramscoop", __kind__="arc")
        self._add("grp/one", "Ramscoop Begin", __kind__="beat")
        self.assertNotIn("Ramscoop", self._titles())
        quest_mark_complete(self.aid, "grp/one")
        self.assertIn("Ramscoop", self._titles())

    def test_plural_noun_reads_the_same(self):
        self._add("a", "Beat", __kind__="Beats")
        self.assertNotIn("Beat", self._titles())

    def test_an_explicit_Show_beats_the_noun(self):
        self._add("a", "Loud Beat", show="always", __kind__="beat")
        self.assertIn("Loud Beat", self._titles(),
                      "the field is the override; the noun only fills the blank")

    def test_a_noun_with_no_display_meaning_is_just_a_quest(self):
        self._add("a", "Plain Job", __kind__="job")
        self.assertIn("Plain Job", self._titles())

    def test_Cue_is_never_listed(self):
        self._add("a", "Play SPFX", __kind__="cue")
        self.assertNotIn("Play SPFX", self._titles())
        quest_mark_complete(self.aid, "a")
        self.assertNotIn("Play SPFX", self._titles())

    def test_a_multi_step_JOB_stays_visible_with_secret_steps(self):
        """The regression that makes this a DECLARED value instead of a renderer
        heuristic: an available job also has children, and every step is secret
        until it is accepted. Hiding it would make the job unacceptable."""
        self._add("job", "The Ghost Freighter", state=QuestState.IDLE, reward="400 credits")
        self._add("job/hail", "Hail the Meridian", state=QuestState.SECRET)
        self.assertIn("The Ghost Freighter", self._titles())


if __name__ == '__main__':
    unittest.main()
