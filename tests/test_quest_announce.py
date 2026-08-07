"""Quest completion/failure announcements, and Abandon routing (PRM-16, PRM-16b, PRM-18).

Three behaviours that all live on the announce path:

* **Noun by depth** - "Mission" is reserved for a quest that ENDS THE GAME
  (`end_win`/`end_lose`); every other quest is a "Quest", which is the word already on
  the tab the player clicks. Before this, the last step of every arc announced itself as
  a Mission.
* **The library defers to the author** - a quest carrying its own `on_complete` /
  `on_fail` overlay directive is already telling the crew, so the library does not add a
  second line. Every job on the Peacetime board announced twice, in two vocabularies.
* **Abandon is a real failure** - `quest_tab_abandon` used to write `state = FAILED`
  directly, skipping the penalty, the overlay, the announcement, `quest_failed_done` and
  `_quest_maybe_end_game`. Abandoning was cheaper than failing, and an `end_lose` quest
  could be neutralised by abandoning it.

    python -m unittest tests.test_quest_announce
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs as sbs
from tests.reset_helper import reset_mock
from sbs_utils.procedural import quest_driver as QD
from sbs_utils.procedural.quest import quest_add, quest_set_key, QuestState
from sbs_utils.procedural.a2x.spawn import create_enemy
from sbs_utils.procedural.query import to_id
from sbs_utils.mast.mast_node import MastDataObject


class _Capture:
    """Record what the driver broadcasts and signals, without a live comms layer."""

    def __init__(self):
        self.lines = []
        self.signals = []

    def __enter__(self):
        self._bc = QD.comms_broadcast
        self._se = QD.signal_emit
        QD.comms_broadcast = lambda to, msg, color=None, *a, **k: self.lines.append(str(msg))
        QD.signal_emit = lambda name, data=None, *a, **k: self.signals.append((name, data))
        return self

    def __exit__(self, *exc):
        QD.comms_broadcast = self._bc
        QD.signal_emit = self._se
        return False


class QuestAnnounceTests(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        self.player = to_id(create_enemy(0, 0, 0, "kralien_cruiser", name="P"))

    def _grant(self, key, display, data, state=QuestState.ACTIVE):
        quest_add(self.player, key, display, "", state=state, data=data)

    # --- PRM-16: the noun ----------------------------------------------------
    def test_ordinary_quest_says_Quest(self):
        self._grant("job_gunnery", "Gunnery Qualification", {})
        with _Capture() as cap:
            QD.quest_mark_complete(self.player, "job_gunnery")
        self.assertIn("Quest complete: Gunnery Qualification", cap.lines)
        self.assertFalse([l for l in cap.lines if l.startswith("Mission complete")])

    def test_game_ending_quest_still_says_Mission(self):
        self._grant("defend", "Defend the Station", {"end_win": True})
        with _Capture() as cap:
            QD.quest_mark_complete(self.player, "defend")
        self.assertIn("Mission complete: Defend the Station", cap.lines)

    def test_failure_uses_the_same_rule(self):
        self._grant("job_mercy", "Mercy Run", {})
        with _Capture() as cap:
            QD.quest_mark_failed(self.player, "job_mercy")
        self.assertIn("Quest failed: Mercy Run", cap.lines)

    def test_game_ending_failure_says_Mission(self):
        self._grant("hold", "Hold the Line", {"end_lose": True})
        with _Capture() as cap:
            QD.quest_mark_failed(self.player, "hold")
        self.assertIn("Mission failed: Hold the Line", cap.lines)

    # --- PRM-16b: defer to the author ---------------------------------------
    def test_authored_on_complete_suppresses_the_library_line(self):
        """The Peacetime board case: the job already toasts its own completion."""
        self._grant("job_rocks", "Rock Breakers",
                    {"on_complete": "toast Job complete: Rock Breakers"})
        with _Capture() as cap:
            QD.quest_mark_complete(self.player, "job_rocks")
        self.assertEqual([], [l for l in cap.lines if "complete" in l.lower()],
                         f"library announced on top of the authored toast: {cap.lines}")

    def test_authored_on_fail_suppresses_the_library_line(self):
        self._grant("job_poacher", "Board the Poacher",
                    {"on_fail": "banner Poacher destroyed"})
        with _Capture() as cap:
            QD.quest_mark_failed(self.player, "job_poacher")
        self.assertEqual([], [l for l in cap.lines if "failed" in l.lower()])

    def test_space_authored_key_is_honored_too(self):
        """`_quest_fire_overlays` accepts `on complete`; the suppression must match."""
        self._grant("job_x", "X", {"on complete": "toast done"})
        with _Capture() as cap:
            QD.quest_mark_complete(self.player, "job_x")
        self.assertEqual([], [l for l in cap.lines if "complete" in l.lower()])

    def test_unauthored_quest_still_announces(self):
        self._grant("plain", "Plain", {})
        with _Capture() as cap:
            QD.quest_mark_complete(self.player, "plain")
        self.assertIn("Quest complete: Plain", cap.lines)


class QuestDisplayNameTests(unittest.TestCase):
    """PRM-15: the waterfall printed raw quest ids, for EVERY quest.

    `quest_add` stores `display_text`; `quest_get_display_name` read `display_name` -
    a key nothing in the codebase ever writes. So it returned None every time and each
    caller fell back to the quest id (`job_ghost/hail`, `brief`, ...). Not "some quests
    are missing a name": a key mismatch affecting all of them.
    """

    def setUp(self):
        reset_mock(sbs)
        self.player = to_id(create_enemy(0, 0, 0, "kralien_cruiser", name="P"))

    def _nested(self):
        """A path-keyed child, the shape the multi-step arcs use. The parent must
        exist first - quest_add requires every level above the leaf."""
        quest_add(self.player, "job_ghost", "Ghost Freighter", "", data={})
        quest_add(self.player, "job_ghost/hail", "Hail the Derelict", "",
                  state=QuestState.ACTIVE, data={})

    def test_display_text_is_what_gets_read(self):
        self._nested()
        self.assertEqual("Hail the Derelict",
                         QD.quest_get_display_name(self.player, "job_ghost/hail"))

    def test_the_raw_key_no_longer_reaches_the_waterfall(self):
        self._nested()
        with _Capture() as cap:
            QD.quest_mark_complete(self.player, "job_ghost/hail")
        self.assertIn("Quest complete: Hail the Derelict", cap.lines)
        self.assertFalse([l for l in cap.lines if "job_ghost/hail" in l],
                         f"the internal key leaked to the crew: {cap.lines}")

    def test_an_explicit_display_name_still_overrides(self):
        quest_add(self.player, "j", "From display_text", "",
                  state=QuestState.ACTIVE, data={})
        quest_set_key(self.player, "j", "display_name", "Explicit Override")
        self.assertEqual("Explicit Override",
                         QD.quest_get_display_name(self.player, "j"))


class QuestAbandonTests(unittest.TestCase):
    """Abandon must be a real failure, not a state poke."""

    def setUp(self):
        reset_mock(sbs)
        self.player = to_id(create_enemy(0, 0, 0, "kralien_cruiser", name="P"))

    def _row(self, key, display, data):
        quest_add(self.player, key, display, "", state=QuestState.ACTIVE, data=data)
        return MastDataObject({"agent_id": self.player, "key": key,
                               "state": int(QuestState.ACTIVE)})

    def test_abandon_still_fails_the_quest(self):
        row = self._row("job_mercy", "Mercy Run", {})
        with _Capture():
            QD.quest_tab_abandon(row)
        self.assertEqual(QuestState.FAILED,
                         QD.quest_get_state(self.player, "job_mercy"))

    def test_abandon_announces(self):
        row = self._row("job_mercy", "Mercy Run", {})
        with _Capture() as cap:
            QD.quest_tab_abandon(row)
        self.assertIn("Quest failed: Mercy Run", cap.lines)

    def test_abandon_emits_quest_failed_done(self):
        row = self._row("job_mercy", "Mercy Run", {})
        with _Capture() as cap:
            QD.quest_tab_abandon(row)
        self.assertIn("quest_failed_done", [n for n, _ in cap.signals])

    def test_abandon_cannot_neutralise_an_end_lose_quest(self):
        """The serious one: abandoning must still lose the game."""
        row = self._row("hold", "Hold the Line", {"end_lose": True})
        with _Capture() as cap:
            QD.quest_tab_abandon(row)
        overs = [d for n, d in cap.signals if n == "game_over"]
        self.assertTrue(overs, "abandoning an end_lose quest did not end the game")
        self.assertFalse(overs[0]["WIN"])

    def test_abandon_is_a_noop_on_a_non_active_quest(self):
        quest_add(self.player, "idle_job", "Idle", "", state=QuestState.IDLE, data={})
        row = MastDataObject({"agent_id": self.player, "key": "idle_job",
                              "state": int(QuestState.IDLE)})
        with _Capture() as cap:
            QD.quest_tab_abandon(row)
        self.assertEqual(QuestState.IDLE, QD.quest_get_state(self.player, "idle_job"))
        self.assertEqual([], cap.lines)


if __name__ == "__main__":
    unittest.main()
