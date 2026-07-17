"""Multi-axis faction reputation (sbs_utils.procedural.reputation), promoted from OU.

Run: python -m unittest tests.test_reputation
"""
import unittest
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural.spawn import npc_spawn
from sbs_utils.procedural.query import to_id
from sbs_utils.procedural import reputation as R


class FakeEvent:
    client_id = 0; tag = ""; sub_tag = ""; origin_id = 0; selected_id = 0
    parent_id = 0; value_tag = ""; extra_tag = ""; extra_extra_tag = ""
    sub_float = 0.0; source_point = None; event_time = 0


class ReputationTests(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        SpaceObject.clear()
        R.reputation_configure(None)   # reset to defaults
        self.ship = to_id(npc_spawn(0, 0, 0, "P", "tsn", "tsn_light_cruiser", "behav_npcship"))

    def test_pole_orientation(self):
        R.reputation_adjust(self.ship, "ashfang", "honest", 10)
        self.assertEqual(R.reputation_get(self.ship, "ashfang", "honest"), 10)
        self.assertEqual(R.reputation_get(self.ship, "ashfang", "liar"), -10)   # same axis, negated

    def test_clamp(self):
        R.reputation_adjust(self.ship, "c", "fearsome", 500)
        self.assertEqual(R.reputation_get(self.ship, "c", "fearsome"), 100)

    def test_apply_block(self):
        R.reputation_apply(self.ship, {"ashfang": {"selfish": 5, "cruel": 3}})
        self.assertEqual(R.reputation_get(self.ship, "ashfang", "selfish"), 5)
        self.assertEqual(R.reputation_get(self.ship, "ashfang", "generous"), -5)

    def test_standing_weighted_by_leans(self):
        R.reputation_adjust(self.ship, "ashfang", "fearsome", 40)
        R.reputation_adjust(self.ship, "ashfang", "honest", 0)
        clan = {"key": "ashfang", "leans": {"fearsome": 2, "honest": 1}}
        # (2*40 + 1*0) / 3 = 26
        self.assertEqual(R.reputation_standing(self.ship, clan), 26)

    def test_tiers_and_reward(self):
        self.assertEqual(R.reputation_offer_tier(0), 1)
        self.assertEqual(R.reputation_offer_tier(25), 2)
        self.assertEqual(R.reputation_offer_tier(60), 3)
        self.assertEqual(R.reputation_reward_mult(0), 1.0)
        self.assertEqual(R.reputation_reward_mult(100), 2.0)

    def test_configure_replaces_axes_and_tuning(self):
        R.reputation_configure({"axes": [{"axis": "trust", "pos": "trusted", "neg": "shady"}],
                                "tiers": {"t2": 5, "t3": 10}})
        R.reputation_adjust(self.ship, "c", "trusted", 8)
        self.assertEqual(R.reputation_get(self.ship, "c", "shady"), -8)
        self.assertEqual(R.reputation_offer_tier(6), 2)          # new tuning
        self.assertEqual(R.reputation_get(self.ship, "c", "honest"), 0)  # old axis gone

    def test_ceasefire_and_ransom_pricing(self):
        R.reputation_configure(None)
        self.assertEqual(R.reputation_ceasefire_cost(30), 0)     # free at/above free line
        self.assertEqual(R.reputation_ceasefire_cost(0), 600)    # (30-0)*20
        self.assertEqual(R.reputation_ransom_cost(30), 400)      # base at/above line
        self.assertEqual(R.reputation_ransom_cost(0), 850)       # 400 + (30*15)


if __name__ == "__main__":
    unittest.main()
