"""Reputation as a quest consequence (DESIGN_RECORD.md s4).

`Pays:` / `Penalty:` can now shift standing, not just credits and items - but only where
standing MEANS something. A world-held quest (a station, a side) carries no reputation:
`reputation_adjust` shifts *that agent's* view of a faction, so a rep penalty on DS1's
resupply quest would move DS1's own opinion of TSN, which no player can perceive.

Run:
    python -m unittest tests.test_quest_reputation
"""
import unittest

from cosmos_dev.mock import sbs as sbs
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.agent import Agent, get_story_id
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.fs import test_set_exe_dir

test_set_exe_dir()

from sbs_utils.procedural.amd_quest import amd_reward
from sbs_utils.procedural.quest_driver import (
    quest_grant_reward, quest_grant_penalty, _quest_rep_holder)
from sbs_utils.procedural.reputation import reputation_get


def make_agent(*roles):
    a = Agent()
    a.id = get_story_id()
    a.add()
    for r in roles:
        a.add_role(r)
    return a


class QuestReputationTests(unittest.TestCase):
    def setUp(self):
        SpaceObject.clear()
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())

    # -- who may carry a reputation line ------------------------------------
    def test_player_is_a_rep_holder(self):
        player = make_agent("__player__")
        self.assertTrue(_quest_rep_holder(player.id))

    def test_shared_is_a_rep_holder(self):
        self.assertTrue(_quest_rep_holder(Agent.SHARED_ID))

    def test_station_is_not_a_rep_holder(self):
        station = make_agent("station")
        self.assertFalse(_quest_rep_holder(station.id))

    # -- granting ------------------------------------------------------------
    def test_reward_applies_reputation_to_a_player(self):
        player = make_agent("__player__")
        quest_grant_reward(player.id, amd_reward("300 credits, earns tsn honest +10"))
        self.assertEqual(reputation_get(player.id, "tsn", "honest"), 10)

    def test_penalty_applies_the_authored_sign(self):
        # A Penalty: block does NOT flip the sign for you - -15 stays -15.
        player = make_agent("__player__")
        quest_grant_penalty(player.id, amd_reward("earns tsn honest -15"))
        self.assertEqual(reputation_get(player.id, "tsn", "honest"), -15)

    def test_world_holder_gets_no_reputation(self):
        station = make_agent("station")
        quest_grant_penalty(station.id, amd_reward("earns tsn honest -15"))
        self.assertEqual(reputation_get(station.id, "tsn", "honest"), 0)

    def test_world_holder_still_gets_items(self):
        # Only the reputation half is gated; a station-held quest keeps its other stakes.
        station = make_agent("station")
        station.set_inventory_value("ore", 5)
        quest_grant_penalty(station.id, amd_reward("2 ore, earns tsn honest -15"))
        self.assertEqual(station.get_inventory_value("ore", 0), 3)
        self.assertEqual(reputation_get(station.id, "tsn", "honest"), 0)

    def test_items_now_reach_the_agent(self):
        # The parser could not produce `items` before, so this path was dead code.
        player = make_agent("__player__")
        quest_grant_reward(player.id, amd_reward("300 credits, 2 torpedoes"))
        self.assertEqual(player.get_inventory_value("torpedoes", 0), 2)

    def test_two_factions_both_land(self):
        player = make_agent("__player__")
        quest_grant_reward(player.id,
                           amd_reward("earns tsn honest +5, earns skaraan fearsome +3"))
        self.assertEqual(reputation_get(player.id, "tsn", "honest"), 5)
        self.assertEqual(reputation_get(player.id, "skaraan", "fearsome"), 3)

    def test_no_reputation_block_is_a_no_op(self):
        player = make_agent("__player__")
        quest_grant_reward(player.id, amd_reward("300 credits"))
        self.assertEqual(reputation_get(player.id, "tsn", "honest"), 0)


class QuestRewardTextTests(unittest.TestCase):
    """The quest log renders a reward back to the author. The new keys are nested, so
    the generic dict walk this used to do would emit braces - and a display string
    containing `{` is a runtime SyntaxError the moment MAST assigns it."""

    def _text(self, authored):
        from sbs_utils.procedural.quest import _quest_reward_text
        from sbs_utils.mast.mast_node import MastDataObject
        return _quest_reward_text(MastDataObject({"data": {"reward": amd_reward(authored)}}))

    def test_credits_unchanged(self):
        self.assertEqual(self._text("300 credits"), "300 credits")

    def test_items_read_back(self):
        self.assertEqual(self._text("300 credits, 2 torpedoes"), "300 credits, 2 torpedoes")

    def test_reputation_reads_back_with_a_sign(self):
        self.assertEqual(self._text("earns tsn honest +10"), "+10 honest with tsn")

    def test_flavor_reward_has_no_text(self):
        self.assertIsNone(self._text("a favor"))

    def test_no_braces_ever_reach_a_display_string(self):
        for authored in ("300 credits", "300 credits, 2 torpedoes",
                         "earns tsn honest +10", "200 credits, earns tsn diplomatic -15",
                         "300 credits, 2 torpedoes, earns tsn honest +10"):
            out = self._text(authored)
            self.assertNotIn("{", out or "", f"brace leaked from {authored!r}")


if __name__ == "__main__":
    unittest.main()
