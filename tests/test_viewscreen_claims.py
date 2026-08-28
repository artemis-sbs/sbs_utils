"""Who holds a ship's main screen.

Bookkeeping only - no consoles, no camera, no engine. The half that makes the
engine agree is tested in test_viewscreen.py.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.mock import sbs as mock_sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural.query import to_id
from sbs_utils.procedural.spawn import player_spawn
from sbs_utils.procedural.gui.viewscreen_claims import (
    OWNER_ANON, TIER_CONSOLE, TIER_STORY, VIEWSCREEN_TIERS,
    viewscreen_baseline, viewscreen_baseline_drop, viewscreen_bump,
    viewscreen_claim, viewscreen_claim_drop, viewscreen_claimed, viewscreen_held,
    viewscreen_hold, viewscreen_hold_drop, viewscreen_hold_take, viewscreen_owner,
    viewscreen_owner_token, viewscreen_owns, viewscreen_roster,
    viewscreen_roster_add, viewscreen_seq, viewscreen_tier)


CREW = ("3d_view", "front", "chase")
STORY_VIEW = ("tactical", "left", "long")


class ClaimBase(unittest.TestCase):
    def setUp(self):
        mock_sbs.create_new_sim()
        SpaceObject.clear()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())
        self.artemis = to_id(player_spawn(0, 0, 0, "Artemis", "tsn", "battle"))
        self.intrepid = to_id(player_spawn(9000, 0, 0, "Intrepid", "tsn", "battle"))

    def tearDown(self):
        FrameContext.context = None


class TestTheClaim(ClaimBase):

    def test_a_fresh_ship_is_unclaimed(self):
        self.assertFalse(viewscreen_claimed(self.artemis))
        self.assertEqual(viewscreen_owner(self.artemis), "")
        self.assertEqual(viewscreen_tier(self.artemis), "")
        self.assertIsNone(viewscreen_baseline(self.artemis))

    def test_a_claim_records_its_owner_and_tier(self):
        self.assertTrue(viewscreen_claim(self.artemis, TIER_CONSOLE, "science:7"))
        self.assertTrue(viewscreen_claimed(self.artemis))
        self.assertEqual(viewscreen_owner(self.artemis), "science:7")
        self.assertEqual(viewscreen_tier(self.artemis), TIER_CONSOLE)

    def test_an_unnamed_claim_is_still_a_claim(self):
        self.assertTrue(viewscreen_claim(self.artemis))
        self.assertEqual(viewscreen_owner(self.artemis), OWNER_ANON)
        self.assertTrue(viewscreen_claimed(self.artemis))

    def test_an_unknown_tier_is_refused_and_changes_nothing(self):
        self.assertFalse(viewscreen_claim(self.artemis, "urgent", "science:7"))
        self.assertFalse(viewscreen_claimed(self.artemis))

    def test_every_tier_is_claimable(self):
        for tier in VIEWSCREEN_TIERS:
            viewscreen_claim_drop(self.artemis)
            self.assertTrue(viewscreen_claim(self.artemis, tier, "x"), tier)
            self.assertEqual(viewscreen_tier(self.artemis), tier)

    def test_the_owner_token_names_the_console(self):
        self.assertEqual(viewscreen_owner_token("science", 1001), "science:1001")
        self.assertEqual(viewscreen_owner_token("hail"), "hail")

    def test_two_science_consoles_are_two_claimants(self):
        a = viewscreen_owner_token("science", 1001)
        b = viewscreen_owner_token("science", 1002)
        viewscreen_claim(self.artemis, TIER_CONSOLE, a)
        self.assertTrue(viewscreen_owns(self.artemis, a))
        self.assertFalse(viewscreen_owns(self.artemis, b))


class TestTheBaseline(ClaimBase):

    def test_the_first_claim_captures_it(self):
        viewscreen_claim(self.artemis, TIER_CONSOLE, "science:7", baseline=CREW)
        self.assertEqual(viewscreen_baseline(self.artemis), CREW)

    def test_a_second_claim_does_not_recapture_it(self):
        """A shot replacing a shot must not overwrite what the crew had with the
        previous shot's own framing, or standing down restores a state the crew
        never chose."""
        viewscreen_claim(self.artemis, TIER_CONSOLE, "science:7", baseline=CREW)
        viewscreen_claim(self.artemis, TIER_CONSOLE, "weapons:8", baseline=STORY_VIEW)
        self.assertEqual(viewscreen_baseline(self.artemis), CREW)

    def test_a_story_claim_over_a_console_one_keeps_the_crews_baseline(self):
        """The sentinel is the baseline being unset, NOT viewscreen_is_live - a
        story claim sets no viewer mode, so an is_live test would let a second
        capture through here."""
        viewscreen_claim(self.artemis, TIER_CONSOLE, "science:7", baseline=CREW)
        viewscreen_claim(self.artemis, TIER_STORY, "hail", baseline=STORY_VIEW)
        self.assertEqual(viewscreen_baseline(self.artemis), CREW)

    def test_releasing_forgets_it(self):
        viewscreen_claim(self.artemis, TIER_CONSOLE, "science:7", baseline=CREW)
        viewscreen_claim_drop(self.artemis)
        self.assertIsNone(viewscreen_baseline(self.artemis))

    def test_a_release_mid_apply_can_keep_it(self):
        viewscreen_claim(self.artemis, TIER_CONSOLE, "science:7", baseline=CREW)
        viewscreen_claim_drop(self.artemis, keep_baseline=True)
        self.assertFalse(viewscreen_claimed(self.artemis))
        self.assertEqual(viewscreen_baseline(self.artemis), CREW)

    def test_dropping_it_outright_leaves_nothing_to_restore(self):
        """What a helm takeover does. A stale baseline left recorded would let a
        later, unrelated release put the screen back somewhere the crew left."""
        viewscreen_claim(self.artemis, TIER_CONSOLE, "science:7", baseline=CREW)
        viewscreen_baseline_drop(self.artemis)
        self.assertIsNone(viewscreen_baseline(self.artemis))

    def test_the_roster_records_the_consoles_with_a_home(self):
        viewscreen_claim(self.artemis, TIER_CONSOLE, "science:7", baseline=CREW,
                         cids=[1001, 1002])
        self.assertEqual(sorted(viewscreen_roster(self.artemis)), [1001, 1002])

    def test_a_late_console_joins_the_roster(self):
        viewscreen_claim(self.artemis, TIER_CONSOLE, "science:7", baseline=CREW,
                         cids=[1001])
        self.assertTrue(viewscreen_roster_add(self.artemis, 1003))
        self.assertFalse(viewscreen_roster_add(self.artemis, 1003), "added twice")
        self.assertEqual(sorted(viewscreen_roster(self.artemis)), [1001, 1003])


class TestTiers(ClaimBase):

    def test_a_console_claim_replaces_a_console_claim(self):
        viewscreen_claim(self.artemis, TIER_CONSOLE, "science:7", baseline=CREW)
        self.assertTrue(viewscreen_claim(self.artemis, TIER_CONSOLE, "weapons:8"))
        self.assertEqual(viewscreen_owner(self.artemis), "weapons:8")

    def test_a_story_claim_replaces_a_console_claim(self):
        viewscreen_claim(self.artemis, TIER_CONSOLE, "science:7", baseline=CREW)
        self.assertTrue(viewscreen_claim(self.artemis, TIER_STORY, "hail"))
        self.assertEqual(viewscreen_tier(self.artemis), TIER_STORY)

    def test_a_story_claim_replaces_a_story_claim(self):
        viewscreen_claim(self.artemis, TIER_STORY, "hail", baseline=CREW)
        self.assertTrue(viewscreen_claim(self.artemis, TIER_STORY, "cutscene:3"))
        self.assertEqual(viewscreen_owner(self.artemis), "cutscene:3")

    def test_a_console_claim_is_refused_under_a_story_one(self):
        viewscreen_claim(self.artemis, TIER_STORY, "hail", baseline=CREW)
        self.assertFalse(viewscreen_claim(self.artemis, TIER_CONSOLE, "science:7"))
        self.assertEqual(viewscreen_owner(self.artemis), "hail")

    def test_a_refused_claim_does_not_bump_the_seq(self):
        viewscreen_claim(self.artemis, TIER_STORY, "hail", baseline=CREW)
        seq = viewscreen_seq(self.artemis)
        viewscreen_claim(self.artemis, TIER_CONSOLE, "science:7")
        self.assertEqual(viewscreen_seq(self.artemis), seq,
                         "a refused claim moved the sequence, so every console "
                         "would repaint for nothing")


class TestTheParkedRequest(ClaimBase):

    def test_it_survives_until_taken(self):
        viewscreen_hold(self.artemis, {"mode": "orbit"})
        self.assertEqual(viewscreen_held(self.artemis), {"mode": "orbit"})
        self.assertEqual(viewscreen_hold_take(self.artemis), {"mode": "orbit"})
        self.assertIsNone(viewscreen_held(self.artemis))

    def test_only_the_last_one_survives(self):
        """The crew pressing three things during a cutscene want the last one;
        replaying all three would walk the screen through states nobody asked
        to see."""
        viewscreen_hold(self.artemis, {"mode": "orbit"})
        viewscreen_hold(self.artemis, {"mode": "tactical"})
        self.assertEqual(viewscreen_hold_take(self.artemis), {"mode": "tactical"})

    def test_taking_from_an_empty_park_is_none(self):
        self.assertIsNone(viewscreen_hold_take(self.artemis))

    def test_it_can_be_thrown_away(self):
        viewscreen_hold(self.artemis, {"mode": "orbit"})
        viewscreen_hold_drop(self.artemis)
        self.assertIsNone(viewscreen_held(self.artemis))


class TestRelease(ClaimBase):

    def test_the_owner_may_release(self):
        viewscreen_claim(self.artemis, TIER_CONSOLE, "science:7", baseline=CREW)
        self.assertTrue(viewscreen_claim_drop(self.artemis, "science:7"))
        self.assertFalse(viewscreen_claimed(self.artemis))

    def test_a_stale_owner_may_not(self):
        """A releaser whose claim has been replaced must not take the screen off
        the console that replaced it."""
        viewscreen_claim(self.artemis, TIER_CONSOLE, "science:7", baseline=CREW)
        viewscreen_claim(self.artemis, TIER_CONSOLE, "weapons:8")
        self.assertFalse(viewscreen_claim_drop(self.artemis, "science:7"))
        self.assertEqual(viewscreen_owner(self.artemis), "weapons:8")

    def test_no_owner_forces(self):
        viewscreen_claim(self.artemis, TIER_STORY, "hail", baseline=CREW)
        self.assertTrue(viewscreen_claim_drop(self.artemis))

    def test_releasing_an_unclaimed_screen_is_a_no_op(self):
        self.assertFalse(viewscreen_claim_drop(self.artemis))


class TestTheSequence(ClaimBase):

    def test_it_bumps_on_claim_and_on_release(self):
        start = viewscreen_seq(self.artemis)
        viewscreen_claim(self.artemis, TIER_CONSOLE, "science:7", baseline=CREW)
        self.assertEqual(viewscreen_seq(self.artemis), start + 1)
        viewscreen_claim_drop(self.artemis)
        self.assertEqual(viewscreen_seq(self.artemis), start + 2)

    def test_it_is_already_bumped_when_the_outcome_runs(self):
        """hail.py's rule, copied deliberately: the bump happens BEFORE the outcome,
        so a second actor in the same frame is already carrying a stale token by the
        time it arrives."""
        seen = {}

        def outcome(ship):
            seen["seq"] = viewscreen_seq(ship)

        start = viewscreen_seq(self.artemis)
        viewscreen_bump(self.artemis)
        outcome(self.artemis)
        self.assertEqual(seen["seq"], start + 1)

    def test_it_never_goes_backwards_across_a_release(self):
        viewscreen_claim(self.artemis, TIER_CONSOLE, "a", baseline=CREW)
        viewscreen_claim_drop(self.artemis)
        viewscreen_claim(self.artemis, TIER_CONSOLE, "b", baseline=CREW)
        self.assertEqual(viewscreen_seq(self.artemis), 3)


class TestTwoShips(ClaimBase):

    def test_they_hold_independent_claims(self):
        viewscreen_claim(self.artemis, TIER_CONSOLE, "science:7", baseline=CREW)
        viewscreen_claim(self.intrepid, TIER_STORY, "hail", baseline=STORY_VIEW)
        self.assertEqual(viewscreen_owner(self.artemis), "science:7")
        self.assertEqual(viewscreen_owner(self.intrepid), "hail")
        self.assertEqual(viewscreen_baseline(self.artemis), CREW)
        self.assertEqual(viewscreen_baseline(self.intrepid), STORY_VIEW)

    def test_a_story_on_one_does_not_park_the_others_crew_request(self):
        viewscreen_claim(self.intrepid, TIER_STORY, "hail", baseline=STORY_VIEW)
        self.assertTrue(viewscreen_claim(self.artemis, TIER_CONSOLE, "science:7",
                                         baseline=CREW),
                        "one bridge's cutscene refused the other bridge's console")

    def test_releasing_one_leaves_the_other_claimed(self):
        viewscreen_claim(self.artemis, TIER_CONSOLE, "science:7", baseline=CREW)
        viewscreen_claim(self.intrepid, TIER_CONSOLE, "science:9", baseline=CREW)
        viewscreen_claim_drop(self.artemis)
        self.assertFalse(viewscreen_claimed(self.artemis))
        self.assertTrue(viewscreen_claimed(self.intrepid))

    def test_the_sequences_are_independent(self):
        viewscreen_claim(self.artemis, TIER_CONSOLE, "a", baseline=CREW)
        viewscreen_claim(self.artemis, TIER_CONSOLE, "b")
        self.assertEqual(viewscreen_seq(self.intrepid), 0)


class TestReset(ClaimBase):

    def test_the_claim_goes_away_with_the_agents(self):
        """No module-level container, so the restart-reset ledger needs no new
        registration - Agent.clear() is the whole story."""
        viewscreen_claim(self.artemis, TIER_STORY, "hail", baseline=CREW)
        viewscreen_hold(self.artemis, {"mode": "orbit"})
        ship_id = self.artemis
        SpaceObject.clear()
        self.assertFalse(viewscreen_claimed(ship_id))
        self.assertIsNone(viewscreen_baseline(ship_id))
        self.assertIsNone(viewscreen_held(ship_id))
        self.assertEqual(viewscreen_seq(ship_id), 0)


if __name__ == "__main__":
    unittest.main()
