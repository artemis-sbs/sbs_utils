from cosmos_dev.mock import sbs as sbs
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.agent import Agent, get_story_id
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.fs import test_set_exe_dir
from sbs_utils.procedural.quest import (
    quest_add, quest_get, quest_remove, quest_transfer,
    quest_get_state, quest_get_key, quest_set_key,
    quest_activate, quest_complete,
    quest_console_enable, quest_is_console_enabled,
    quest_add_yaml, quest_add_object, quest_agent_quests,
    document_get_amd_file,
    QuestState,
)
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


if __name__ == '__main__':
    unittest.main()
