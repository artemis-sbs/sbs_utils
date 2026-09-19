"""Tests for the quest offer provider and the `quest_offered` signal.

The provider goes through quest_log_build_items on purpose, so the Offers board inherits
the quest log's visibility rules rather than reimplementing them. These pin that: a quest
the LOG hides must never reach the board, however it came to be hidden (SECRET, or a
`Show:` value).

    python -m unittest tests.test_offer_quest_provider
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs as sbs
from tests.reset_helper import reset_mock

from sbs_utils.agent import Agent
from sbs_utils.procedural.quest import (
    quest_add, quest_set_key, QuestState, quest_add_object)
from sbs_utils.procedural.a2x.spawn import create_enemy
from sbs_utils.procedural.query import to_id
from sbs_utils.procedural.offer import offers, offer_count, offer_clear
from sbs_utils.procedural import quest_driver as QD


class QuestOfferProviderTests(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        offer_clear()
        self.ship = to_id(create_enemy(0, 0, 0, "kralien_cruiser", name="P"))

    def tearDown(self):
        offer_clear()

    def _titles(self):
        return sorted(r.get("title") for r in offers(client_id=0, ship_id=self.ship))

    # --- which states are offers ---------------------------------------------
    def test_idle_is_an_offer(self):
        quest_add(self.ship, "patrol", "Patrol Sector 7", "")
        self.assertEqual(self._titles(), ["Patrol Sector 7"])

    def test_active_is_not_an_offer(self):
        quest_add(self.ship, "taken", "Already Mine", "", state=QuestState.ACTIVE)
        self.assertEqual(self._titles(), [])

    def test_complete_and_failed_are_not_offers(self):
        quest_add(self.ship, "c", "Done", "", state=QuestState.COMPLETE)
        quest_add(self.ship, "f", "Blown", "", state=QuestState.FAILED)
        self.assertEqual(self._titles(), [])

    def test_secret_is_not_an_offer(self):
        quest_add(self.ship, "s", "Hidden", "", state=QuestState.SECRET)
        self.assertEqual(self._titles(), [])

    def test_posting_is_listed_but_pending_and_uncounted(self):
        """POSTING means a board you take by ANSWERING a call - visible, not takeable."""
        quest_add(self.ship, "p", "Board Job", "", state=QuestState.POSTING)
        rows = offers(client_id=0, ship_id=self.ship)
        self.assertEqual([r.get("title") for r in rows], ["Board Job"])
        self.assertTrue(rows[0].get("pending"))
        self.assertEqual(offer_count(client_id=0, ship_id=self.ship), 0)

    def test_a_revealed_quest_becomes_an_offer(self):
        quest_add(self.ship, "s", "Hidden", "", state=QuestState.SECRET)
        self.assertEqual(self._titles(), [])
        quest_set_key(self.ship, "s", "state", QuestState.IDLE)
        self.assertEqual(self._titles(), ["Hidden"])

    # --- the log's visibility rules must carry over ---------------------------
    def test_show_never_is_not_an_offer(self):
        quest_add(self.ship, "n", "Invisible", "", data={"show": "never"})
        self.assertEqual(self._titles(), [])

    def test_show_when_done_is_not_an_offer_while_idle(self):
        quest_add(self.ship, "w", "Later", "", data={"show": "when done"})
        self.assertEqual(self._titles(), [])

    # --- scope ----------------------------------------------------------------
    def test_shared_and_ship_sources_both_appear(self):
        quest_add(Agent.SHARED_ID, "game", "Game Job", "")
        quest_add(self.ship, "mine", "Ship Job", "")
        self.assertEqual(self._titles(), ["Game Job", "Ship Job"])

    def test_source_names_the_section(self):
        quest_add(Agent.SHARED_ID, "game", "Game Job", "")
        row = offers(client_id=0, ship_id=self.ship)[0]
        self.assertEqual(row.get("source"), "Game")

    def test_a_ship_quest_attributes_to_the_ship(self):
        """agent_id is the comms/scan hook, so it must be a real space object or None."""
        quest_add(self.ship, "mine", "Ship Job", "")
        row = offers(client_id=0, ship_id=self.ship)[0]
        self.assertEqual(row.get("agent_id"), self.ship)

    def test_a_shared_quest_is_unattributed(self):
        """The SHARED story agent is not a thing you can select or scan."""
        quest_add(Agent.SHARED_ID, "game", "Game Job", "")
        row = offers(client_id=0, ship_id=self.ship)[0]
        self.assertIsNone(row.get("agent_id"))

    def test_a_per_object_question_has_no_quest_answer(self):
        """Quests are held by a crew, not by the thing you clicked on."""
        quest_add(self.ship, "mine", "Ship Job", "")
        self.assertEqual(offers(client_id=0, ship_id=self.ship, object_id=self.ship), [])

    # --- the record -----------------------------------------------------------
    def test_key_is_stable_and_identifies_the_quest(self):
        quest_add(self.ship, "patrol", "Patrol", "")
        row = offers(client_id=0, ship_id=self.ship)[0]
        self.assertEqual(row.get("key"), f"quest:{self.ship}:patrol")
        self.assertEqual(row.get("data").get("quest_id"), "patrol")

    def test_a_step_is_not_an_offer(self):
        """An arc's step is its sequencer's to reveal, not the crew's to take - offering
        it would let a crew start step three of something they never began."""
        quest_add(self.ship, "arc", "The Arc", "")
        quest_add(self.ship, "arc/step1", "Step One", "")
        keys = [r.get("data").get("quest_id")
                for r in offers(client_id=0, ship_id=self.ship)]
        self.assertIn("arc", keys)
        self.assertNotIn("arc/step1", keys)

    def test_it_opens_the_quests_app(self):
        quest_add(self.ship, "j", "J", "")
        self.assertEqual(offers(client_id=0, ship_id=self.ship)[0].get("app"), "quest")

    def test_reward_becomes_the_detail_line(self):
        quest_add(self.ship, "j", "J", "", data={"reward": "120 credits"})
        row = offers(client_id=0, ship_id=self.ship)[0]
        self.assertIn("120", row.get("detail"))

    def test_per_quest_accept_console_override_is_carried(self):
        quest_add(self.ship, "j", "J", "", data={"accept_consoles": "science"})
        row = offers(client_id=0, ship_id=self.ship)[0]
        self.assertIn("Science", row.get("where"))

    def test_where_is_ascii(self):
        quest_add(self.ship, "j", "J", "")
        row = offers(client_id=0, ship_id=self.ship)[0]
        row.get("where").encode("ascii")     # raises if not

    # --- accepted on the board ------------------------------------------------
    def test_a_quest_offer_can_be_taken(self):
        quest_add(self.ship, "j", "J", "")
        row = offers(client_id=0, ship_id=self.ship)[0]
        self.assertTrue(callable(row.get("take")))
        self.assertTrue(row.get("take")(0, row))
        from sbs_utils.procedural.quest import quest_get_state
        self.assertEqual(int(quest_get_state(self.ship, "j")), int(QuestState.ACTIVE))
        self.assertEqual(self._titles(), [], "a taken job is no longer on offer")

    def test_taking_does_not_restart_a_job_no_longer_idle(self):
        quest_add(self.ship, "j", "J", "")
        row = offers(client_id=0, ship_id=self.ship)[0]
        quest_set_key(self.ship, "j", "state", QuestState.FAILED)
        self.assertFalse(row.get("take")(0, row))
        from sbs_utils.procedural.quest import quest_get_state
        self.assertEqual(int(quest_get_state(self.ship, "j")), int(QuestState.FAILED))

    def test_the_description_rides_along_for_the_reading_pane(self):
        quest_add(self.ship, "j", "J", "Clear the lane of hazard rocks.")
        row = offers(client_id=0, ship_id=self.ship)[0]
        self.assertIn("hazard rocks", row.get("description"))

    # --- a multi-step job -----------------------------------------------------
    def test_a_parent_job_with_steps_is_still_an_offer(self):
        """_quest_log_rows emits a parent with visible children as a collapsible HEADER
        carrying the quest's row data. The Quests tab treats every header as a
        non-quest; the board unwraps it, or a multi-step job would be invisible."""
        quest_add_object(self.ship, {
            "display_text": "The Arc", "description": "", "state": "IDLE",
            "children": {"step1": {"display_text": "Step One", "description": "",
                                   "state": "IDLE"}},
        }, "arc")
        self.assertIn("The Arc", self._titles())


class QuestTabListsOnlyTakenWorkTests(unittest.TestCase):
    """Untaken jobs are on the Offers board; the Quests tab is work in hand."""

    def setUp(self):
        reset_mock(sbs)
        offer_clear()
        self.ship = to_id(create_enemy(0, 0, 0, "kralien_cruiser", name="P"))

    def _tab_titles(self):
        out = []
        for item in QD.quest_tab_items(0, self.ship):
            row = QD._quest_offer_row(item)
            if row is not None:
                out.append(row.get("title"))
        return out

    def test_an_idle_job_is_not_on_the_tab(self):
        quest_add(self.ship, "idle", "Waiting", "")
        quest_add(self.ship, "live", "Running", "", state=QuestState.ACTIVE)
        self.assertEqual(self._tab_titles(), ["Running"])

    def test_a_section_with_only_idle_jobs_is_dropped(self):
        quest_add(self.ship, "idle", "Waiting", "")
        self.assertEqual(QD.quest_tab_items(0, self.ship), [])

    def test_the_shared_builder_still_lists_idle(self):
        """The Offers provider and the results log read the builder - it must not filter."""
        from sbs_utils.procedural.quest import quest_log_build_items
        quest_add(self.ship, "idle", "Waiting", "")
        items = quest_log_build_items([("Ship", self.ship)])
        self.assertTrue(any(QD._quest_offer_row(i) is not None for i in items))


class OffersTabIsTheQuestScreenTests(unittest.TestCase):
    """Available Quests lists untaken work in the quest log's own row shape, so the Quests
    tab's template, description pane and Accept gate serve it unchanged."""

    def setUp(self):
        reset_mock(sbs)
        offer_clear()
        self.ship = to_id(create_enemy(0, 0, 0, "kralien_cruiser", name="P"))

    def tearDown(self):
        offer_clear()

    def _rows(self, console="comms"):
        return [i for i in QD.quest_offers_tab_items(0, self.ship, console)
                if QD._quest_offer_row(i) is not None]

    def test_idle_jobs_are_listed_and_taken_ones_are_not(self):
        quest_add(self.ship, "idle", "Waiting", "Clear the lane.")
        quest_add(self.ship, "live", "Running", "", state=QuestState.ACTIVE)
        rows = self._rows()
        self.assertEqual([r.get("title") for r in rows], ["Waiting"])
        self.assertEqual(rows[0].get("desc"), "Clear the lane.")

    def test_a_step_is_not_listed(self):
        quest_add(self.ship, "arc", "The Arc", "")
        quest_add(self.ship, "arc/step1", "Step One", "")
        self.assertEqual([r.get("title") for r in self._rows()], ["The Arc"])

    def test_accepting_a_listed_job_uses_the_quest_tabs_own_accept(self):
        quest_add(self.ship, "idle", "Waiting", "")
        row = self._rows()[0]
        gate = QD.quest_tab_controls_gate("comms", row, "comms,admiral", False, "helm")
        self.assertTrue(gate.get("show_accept"))
        QD.quest_tab_accept(row, 0)
        from sbs_utils.procedural.quest import quest_get_state
        self.assertEqual(int(quest_get_state(self.ship, "idle")), int(QuestState.ACTIVE))
        self.assertEqual(self._rows(), [])

    def test_a_non_quest_offer_is_a_row_with_its_record(self):
        from sbs_utils.procedural.offer import offer_register, offer_record
        taken = []
        offer_register("t", lambda ctx: [offer_record(
            "sortie:1", "Strike Run", detail="200 cr", kind="sortie", source="Flight Deck",
            description="Hit the depot.", consoles="hangar",
            take=lambda cid, rec: taken.append(cid))])
        rows = self._rows("hangar")
        self.assertEqual([r.get("title") for r in rows], ["Strike Run"])
        row = rows[0]
        self.assertEqual(row.get("desc"), "Hit the depot.")
        self.assertEqual(row.get("group"), "Flight Deck")
        self.assertTrue(QD.quest_tab_controls_gate("hangar", row, "", False, "").get("show_accept"))
        self.assertFalse(QD.quest_tab_controls_gate("comms", row, "", False, "").get("show_accept"))
        QD.quest_tab_accept(row, 42)
        self.assertEqual(taken, [42])

    def test_an_offer_taken_by_hailing_shows_where_instead(self):
        from sbs_utils.procedural.offer import offer_register, offer_record
        offer_register("t", lambda ctx: [offer_record(
            "ou:1", "Cargo Run", source="DS 4", where="Comms - hail DS 4", route="//comms")])
        row = self._rows()[0]
        gate = QD.quest_tab_controls_gate("comms", row, "", False, "")
        self.assertFalse(gate.get("show_accept"))
        self.assertIn("hail DS 4", gate.get("hint"))


class QuestOfferedSignalTests(unittest.TestCase):
    """`quest_offered` is the sibling that was missing: until it existed, a job
    appearing on the board emitted nothing at all."""

    def setUp(self):
        reset_mock(sbs)
        self.ship = to_id(create_enemy(0, 0, 0, "kralien_cruiser", name="P"))
        self.seen = []
        import sbs_utils.procedural.quest as Q
        self._real = Q.signal_emit

        def spy(name, data=None):
            if name == "quest_offered":
                self.seen.append((data or {}).get("QUEST_ID"))
            return self._real(name, data)

        Q.signal_emit = spy
        self._Q = Q

    def tearDown(self):
        self._Q.signal_emit = self._real

    def test_an_idle_grant_emits(self):
        quest_add(self.ship, "patrol", "P", "")
        self.assertEqual(self.seen, ["patrol"])

    def test_an_active_grant_is_silent(self):
        """OU side jobs and the hangar board grant ACTIVE at the moment of acceptance -
        announcing those would announce work the crew just took."""
        quest_add(self.ship, "taken", "T", "", state=QuestState.ACTIVE)
        self.assertEqual(self.seen, [])

    def test_a_secret_grant_is_silent(self):
        quest_add(self.ship, "s", "S", "", state=QuestState.SECRET)
        self.assertEqual(self.seen, [])

    def test_a_reveal_to_idle_emits(self):
        quest_add(self.ship, "s", "S", "", state=QuestState.SECRET)
        self.assertEqual(self.seen, [])
        quest_set_key(self.ship, "s", "state", QuestState.IDLE)
        self.assertEqual(self.seen, ["s"])

    def test_going_active_does_not_emit_offered(self):
        quest_add(self.ship, "p", "P", "")
        self.seen.clear()
        quest_set_key(self.ship, "p", "state", QuestState.ACTIVE)
        self.assertEqual(self.seen, [])

    def test_reasserting_idle_does_not_re_emit(self):
        quest_add(self.ship, "p", "P", "")
        self.seen.clear()
        quest_set_key(self.ship, "p", "state", QuestState.IDLE)
        self.assertEqual(self.seen, [])

    def test_a_non_state_key_never_emits(self):
        quest_add(self.ship, "p", "P", "", state=QuestState.ACTIVE)
        self.seen.clear()
        quest_set_key(self.ship, "p", "difficulty", "hard")
        self.assertEqual(self.seen, [])


if __name__ == "__main__":
    unittest.main()
