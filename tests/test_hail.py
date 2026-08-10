"""Incoming hails, runtime layer (sbs_utils.procedural.hail) - Phase 2.

State, the queue, server-side arbitration, the placement dial, and the replay archive.
No GUI: what is under test is who may answer a hail, what happens when two consoles
answer at once, and that none of it outlives a mission reset.

    python -m unittest tests.test_hail
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from cosmos_dev.mock import sbs as mock_sbs
from sbs_utils.agent import Agent
from sbs_utils.helpers import FrameContext, Context
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural import amd_dialogue as D
from sbs_utils.procedural import hail as H
from sbs_utils.procedural.inventory import set_inventory_value
from sbs_utils.procedural.links import link
from sbs_utils.procedural.query import to_id
from sbs_utils.procedural.roles import add_role
from sbs_utils.procedural.space_objects import delete_object
from sbs_utils.procedural.spawn import player_spawn, npc_spawn

NL = chr(10)

# Real-shaped console ids - the client bit is what makes the audience resolver treat
# these as consoles rather than as space objects.
C_COMMS = 0x8000000000000001
C_COMMS2 = 0x8000000000000002
C_MAIN = 0x8000000000000003
C_HELM = 0x8000000000000004


class FakeEvent:
    client_id = 0
    tag = ""
    sub_tag = ""
    origin_id = 0
    selected_id = 0
    parent_id = 0
    value_tag = ""
    extra_tag = ""
    extra_extra_tag = ""
    sub_float = 0.0
    source_point = None
    event_time = 0


# A two-beat scene that branches, so beat advancement and scene navigation are both
# reachable. `%` variants collapse into ONE beat by design (they are alternatives);
# a second BEAT needs a second `@cue`.
SCENES = {
    "open": {
        "data": {"speaker": "ashfang", "when": "hail", "presentation": "portrait"},
        "description": NL.join([
            "@Ashfang",
            "% You are a long way from friends.",
            "",
            "@Vell",
            "Captain, their weapons are hot.",
            "",
            "- [Stand down](backoff)",
            "- [Pay them off](deal) ; costs 200 credits",
            "- [Say nothing](nowhere)",
        ]),
    },
    "backoff": {
        "data": {"speaker": "ashfang"},
        "description": "@Ashfang" + NL + "% Wise." + NL,
    },
    "deal": {
        "data": {"speaker": "ashfang"},
        "description": "@Ashfang" + NL + "% A pleasure." + NL,
    },
}


def _console(cid, ship_id, *roles):
    agent = Agent()
    agent.id = cid
    agent.add()
    for r in roles:
        add_role(cid, r)
    link(ship_id, "consoles", cid)
    # What "this console's own ship" means. Set directly rather than through the engine
    # so the test does not depend on client-to-ship assignment.
    set_inventory_value(cid, "VIEWER_HOME_SHIP", ship_id)
    return cid


class HailTestCase(unittest.TestCase):
    def setUp(self):
        mock_sbs.create_new_sim()
        SpaceObject.clear()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())
        H.hail_reset()
        self.ship = to_id(player_spawn(0, 0, 0, "Artemis", "tsn", "battle"))
        self.comms = _console(C_COMMS, self.ship, "console", "comms")

    def tearDown(self):
        FrameContext.context = None
        H.hail_reset()
        D._OUTCOME_HANDLERS.clear()

    def _offer(self, **kw):
        kw.setdefault("scenes", SCENES)
        kw.setdefault("scene", "open")
        kw.setdefault("speaker", "ashfang")
        return H.hail_offer(self.ship, **kw)

    def _open(self):
        """Offer, accept, and talk through the beats so the choices are live."""
        self._offer()
        H.hail_accept(self.ship)
        while H.hail_advance(self.ship):
            pass
        return H.hail_choices(self.ship)


class QueueTests(HailTestCase):
    def test_an_offered_hail_waits_to_be_answered(self):
        self.assertEqual(H.hail_pending_count(self.ship), 0)
        self.assertIsNotNone(self._offer())
        self.assertEqual(H.hail_pending_count(self.ship), 1)
        self.assertFalse(H.hail_is_active(self.ship))

    def test_the_same_key_twice_is_a_no_op(self):
        # A re-emitted setup signal must not queue the same hail again. This is the
        # whole reason hail_offer takes a key.
        self.assertIsNotNone(self._offer(key="ashfang@1"))
        self.assertIsNone(self._offer(key="ashfang@1"))
        self.assertEqual(H.hail_pending_count(self.ship), 1)

    def test_a_key_is_still_claimed_while_the_hail_is_OPEN(self):
        self._offer(key="ashfang@1")
        H.hail_accept(self.ship)
        self.assertIsNone(self._offer(key="ashfang@1"))

    def test_priority_wins_and_arrival_order_breaks_the_tie(self):
        a = self._offer(name="first")
        b = self._offer(name="second")
        c = self._offer(name="urgent", priority=10)
        self.assertEqual([r.id for r in H.hail_pending(self.ship)], [c, a, b])

    def test_an_expired_hail_is_pruned_without_a_ticker(self):
        self._offer(expires=-1)          # already past, whatever the sim clock says
        self.assertEqual(H.hail_pending_count(self.ship), 0)

    def test_a_destroyed_subject_takes_its_hail_with_it(self):
        raider = to_id(npc_spawn(500, 0, 0, "Raider", "raider", "battle", "behav_npcship"))
        self._offer(subject=raider)
        self.assertEqual(H.hail_pending_count(self.ship), 1)
        delete_object(raider)
        self.assertEqual(H.hail_pending_count(self.ship), 0)

    def test_a_STRING_subject_is_never_pruned(self):
        # `Subject:` is late-resolved - a role, or a ship not spawned yet. Treating it
        # as a dead id would silently drop every role-based hail.
        self._offer(subject="raider_lead")
        self.assertEqual(H.hail_pending_count(self.ship), 1)

    def test_cancel_withdraws_it(self):
        hid = self._offer()
        self.assertTrue(H.hail_cancel(self.ship, hid))
        self.assertEqual(H.hail_pending_count(self.ship), 0)
        self.assertFalse(H.hail_cancel(self.ship, hid))

    def test_an_unknown_presentation_is_refused_not_raised(self):
        # Reachable from authored data; it must not end the caller's task.
        hid = self._offer(presentation="hologram")
        self.assertIsNotNone(hid)
        H.hail_accept(self.ship)
        self.assertEqual(H.hail_form(self.ship), "portrait")


class ConversationTests(HailTestCase):
    def test_accept_caches_the_beats_and_moves_the_token(self):
        self._offer()
        before = H.hail_seq(self.ship)
        rec = H.hail_accept(self.ship)
        self.assertIsNotNone(rec)
        self.assertGreater(H.hail_seq(self.ship), before)
        self.assertTrue(H.hail_is_active(self.ship))
        self.assertEqual(H.hail_pending_count(self.ship), 0)

    def test_only_one_conversation_is_open_at_a_time(self):
        self._offer()
        self._offer()
        self.assertIsNotNone(H.hail_accept(self.ship))
        self.assertIsNone(H.hail_accept(self.ship))
        self.assertEqual(H.hail_pending_count(self.ship), 1)

    def test_the_beats_are_spoken_in_script_order(self):
        self._offer()
        H.hail_accept(self.ship)
        self.assertEqual(H.hail_beat(self.ship).speaker, "ashfang")
        self.assertTrue(H.hail_advance(self.ship))
        self.assertEqual(H.hail_beat(self.ship).speaker, "vell")
        self.assertFalse(H.hail_advance(self.ship))
        self.assertIsNone(H.hail_beat(self.ship))

    def test_choices_stay_empty_until_the_talking_stops(self):
        self._offer()
        H.hail_accept(self.ship)
        self.assertEqual(H.hail_choices(self.ship), [])
        while H.hail_advance(self.ship):
            pass
        self.assertEqual([c.label for c in H.hail_choices(self.ship)],
                         ["Stand down", "Pay them off", "Say nothing"])

    def test_a_beat_carries_a_resolved_card(self):
        H.hail_set_speaker_resolver(
            lambda key, ship: {"name": key.title(), "face": "terran", "color": "#e33"})
        self._offer()
        H.hail_accept(self.ship)
        beat = H.hail_beat(self.ship)
        self.assertEqual(beat.name, "Ashfang")
        self.assertEqual(beat.face, "terran")

    def test_answering_navigates_to_the_target_scene(self):
        self._open()
        self.assertTrue(H.hail_answer(self.ship, 0))
        self.assertTrue(H.hail_is_active(self.ship))
        self.assertEqual(H.hail_active(self.ship).scene, "backoff")
        self.assertEqual(H.hail_beat(self.ship).text, "Wise.")

    def test_a_choice_with_no_scene_behind_it_ends_the_conversation(self):
        self._open()
        self.assertTrue(H.hail_answer(self.ship, 2))     # "Say nothing" -> nowhere
        self.assertFalse(H.hail_is_active(self.ship))

    def test_the_branch_that_was_walked_is_recorded(self):
        self._open()
        H.hail_answer(self.ship, 0)
        while H.hail_advance(self.ship):
            pass
        H.hail_close(self.ship)
        self.assertEqual([t["label"] for t in H.hail_log(self.ship)[0].taken],
                         ["Stand down"])

    def test_a_ONE_beat_hail_is_answerable_the_moment_it_opens(self):
        # The last beat is shown WITH its choices - a line and the replies to it on
        # screen at once. Gating the choices until after the last beat made a one-beat
        # hail a dead end: nothing more to read, and nothing answerable.
        H.hail_offer(self.ship, speaker="a", lines="Respond.", choices=["Aye"])
        H.hail_accept(self.ship)
        self.assertFalse(H.hail_more(self.ship))
        self.assertEqual([c.label for c in H.hail_choices(self.ship)], ["Aye"])
        self.assertTrue(H.hail_answer(self.ship, 0))

    def test_a_multi_beat_hail_has_more_to_read_until_the_last_one(self):
        self._offer()                       # two beats
        H.hail_accept(self.ship)
        self.assertTrue(H.hail_more(self.ship))
        self.assertEqual(H.hail_choices(self.ship), [])
        H.hail_advance(self.ship)
        self.assertFalse(H.hail_more(self.ship))
        self.assertTrue(H.hail_choices(self.ship))

    def test_an_answer_is_refused_while_the_beats_are_still_running(self):
        self._offer()
        H.hail_accept(self.ship)
        self.assertFalse(H.hail_answer(self.ship, 0))

    def test_an_out_of_range_choice_is_refused(self):
        self._open()
        self.assertFalse(H.hail_answer(self.ship, 9))
        self.assertFalse(H.hail_answer(self.ship, -1))


class ArbitrationTests(HailTestCase):
    """Two comms officers, one hail. Nothing here may need a lock."""

    def test_a_stale_token_is_refused_and_changes_nothing(self):
        choices = self._open()
        seq = choices[0].seq
        self.assertTrue(H.hail_answer(self.ship, 0, self.comms, seq=seq))
        # The second console rendered its buttons before the first press landed.
        self.assertFalse(H.hail_answer(self.ship, 1, C_COMMS2, seq=seq))
        self.assertEqual(H.hail_active(self.ship).scene, "backoff")

    def test_the_token_moves_before_an_outcome_runs(self):
        seen = []
        D.dialogue_register_outcome(
            "costs", lambda a, s, t: seen.append(H.hail_seq(self.ship)))
        choices = self._open()
        seq = choices[0].seq
        H.hail_answer(self.ship, 1, self.comms, seq=seq)
        # If the bump came after, a second press in the same frame would still match.
        self.assertEqual(seen, [seq + 1])

    def test_only_a_comms_console_may_answer(self):
        _console(C_MAIN, self.ship, "console", "mainscreen")
        _console(C_HELM, self.ship, "console", "helm")
        self._open()
        self.assertFalse(H.hail_answer(self.ship, 0, C_MAIN))
        self.assertFalse(H.hail_answer(self.ship, 0, C_HELM))
        self.assertTrue(H.hail_answer(self.ship, 0, self.comms))

    def test_a_scripted_answer_passes_no_console_and_skips_the_check(self):
        self._open()
        self.assertTrue(H.hail_answer(self.ship, 0))

    def test_an_unaffordable_outcome_refuses_the_pick_and_leaves_the_scene(self):
        D.dialogue_register_outcome("costs", lambda a, s, t: False)
        self._open()
        self.assertFalse(H.hail_answer(self.ship, 1, self.comms))
        self.assertEqual(H.hail_active(self.ship).scene, "open")
        self.assertEqual(H.hail_active(self.ship).taken, [])

    def test_accept_is_arbitrated_the_same_way_as_answer(self):
        _console(C_MAIN, self.ship, "console", "mainscreen")
        self._offer()
        self.assertIsNone(H.hail_accept(self.ship, client_id=C_MAIN))
        self.assertIsNotNone(H.hail_accept(self.ship, client_id=self.comms))


class PlacementDialTests(HailTestCase):
    def test_labels_round_trip(self):
        for label, value in H.HAIL_WHERE_LABELS:
            self.assertEqual(H.hail_where_for(label), value)
            self.assertEqual(H.hail_where_label_for(value), label)

    def test_an_unknown_label_reads_as_off(self):
        self.assertEqual(H.hail_where_for("Somewhere Else"), "off")

    def test_the_property_string_uses_list_not_items(self):
        # A dropdown built with `items:` has no options and the engine dies allocating
        # for it, which does not look like a typo from the outside.
        props = H.hail_where_props("Both")
        self.assertIn("list:", props)
        self.assertNotIn("items:", props)
        self.assertTrue(props.startswith("text:Both;"))

    def test_the_dial_starts_off_and_is_a_standing_preference(self):
        self.assertEqual(H.hail_where(self.comms), "off")
        self.assertTrue(H.hail_where_set(self.comms, "console"))
        self.assertEqual(H.hail_where(self.comms), "console")
        # Settable before any hail exists.
        self.assertFalse(H.hail_shows_here(self.comms))

    def test_setting_the_same_value_twice_is_not_a_change(self):
        H.hail_where_set(self.comms, "console")
        self.assertFalse(H.hail_where_set(self.comms, "console"))

    def test_an_unknown_placement_is_refused(self):
        self.assertFalse(H.hail_where_set(self.comms, "wherever"))
        self.assertEqual(H.hail_where(self.comms), "off")

    def test_this_console_shows_it_without_touching_the_main_screen(self):
        main = _console(C_MAIN, self.ship, "console", "mainscreen")
        H.hail_where_set(self.comms, "console")
        self._offer()
        H.hail_accept(self.ship)
        self.assertTrue(H.hail_shows_here(self.comms))
        self.assertFalse(H.hail_shows_here(main))

    def test_main_screen_is_ship_wide_so_the_mainscreen_console_follows(self):
        main = _console(C_MAIN, self.ship, "console", "mainscreen")
        H.hail_where_set(self.comms, "main")
        self._offer()
        H.hail_accept(self.ship)
        self.assertTrue(H.hail_shows_here(main))
        # "main" alone does not put it on the comms console itself.
        self.assertFalse(H.hail_shows_here(self.comms))

    def test_both_shows_it_in_both_places(self):
        main = _console(C_MAIN, self.ship, "console", "mainscreen")
        H.hail_where_set(self.comms, "both")
        self._offer()
        H.hail_accept(self.ship)
        self.assertTrue(H.hail_shows_here(self.comms))
        self.assertTrue(H.hail_shows_here(main))

    def test_a_second_officer_can_pull_it_off_the_main_screen(self):
        # Last writer wins on the SHIP half - deliberately the same arbitration the
        # science On-Screen dropdown already has.
        main = _console(C_MAIN, self.ship, "console", "mainscreen")
        other = _console(C_COMMS2, self.ship, "console", "comms")
        H.hail_where_set(self.comms, "main")
        self._offer()
        H.hail_accept(self.ship)
        self.assertTrue(H.hail_shows_here(main))
        H.hail_where_set(other, "off")
        self.assertFalse(H.hail_shows_here(main))

    def test_a_second_officers_dial_reads_the_SHIP_not_its_own_last_click(self):
        # The dial is derived. If it only remembered its own clicks, this console would
        # read "Off" while the hail was plainly up on the main screen - and its "Off"
        # would then be a no-op, so nobody but the first officer could take it down.
        other = _console(C_COMMS2, self.ship, "console", "comms")
        H.hail_where_set(self.comms, "main")
        self.assertEqual(H.hail_where(other), "main")
        self.assertTrue(H.hail_where_set(other, "off"))

    def test_the_dial_combines_its_own_half_with_the_ships(self):
        other = _console(C_COMMS2, self.ship, "console", "comms")
        H.hail_where_set(self.comms, "console")
        H.hail_where_set(other, "main")
        # This console: its own centre AND the ship's screen. The other: only the ship's.
        self.assertEqual(H.hail_where(self.comms), "both")
        self.assertEqual(H.hail_where(other), "main")

    def test_nothing_shows_when_no_hail_is_open(self):
        H.hail_where_set(self.comms, "both")
        self.assertFalse(H.hail_shows_here(self.comms))


class ConsoleTextTests(HailTestCase):
    def test_the_answer_button_names_who_is_calling(self):
        self.assertEqual(H.hail_answer_label({"name": "Ashfang"}), "Answer Ashfang")
        self.assertEqual(H.hail_answer_label({"speaker": "vex"}), "Answer vex")
        self.assertEqual(H.hail_answer_label({}), "Answer Hail")

    def test_only_comms_and_mainscreen_consoles_repaint(self):
        helm = _console(C_HELM, self.ship, "console", "helm")
        main = _console(C_MAIN, self.ship, "console", "mainscreen")
        self._offer()
        self.assertTrue(H.hail_console_cares(self.comms))
        self.assertTrue(H.hail_console_cares(main))
        self.assertFalse(H.hail_console_cares(helm))

    def test_an_idle_ship_needs_no_repaint(self):
        self.assertFalse(H.hail_console_cares(self.comms))


class _FakeTask:
    """Stands in for the task an `on signal hail:` route runs on - the signal payload
    arrives as task variables, which is what hail_repaint_needed reads."""

    def __init__(self, **variables):
        self.vars = dict(variables)

    def set_variable(self, name, value):
        self.vars[name] = value

    def get_variable(self, name, default=None):
        return self.vars.get(name, default)


class RepaintGuardTests(HailTestCase):
    """One officer moving a dial must not rebuild every console on the bridge."""

    def tearDown(self):
        FrameContext.task = None
        super().tearDown()

    def _signal(self, **payload):
        FrameContext.task = _FakeTask(**payload)

    def test_a_signal_for_this_ship_repaints(self):
        self._offer()
        self._signal(HAIL_SHIP=self.ship, HAIL_CLIENT=None)
        self.assertTrue(H.hail_repaint_needed(self.comms))

    def test_a_signal_for_ANOTHER_ship_is_ignored(self):
        self._offer()
        other = to_id(player_spawn(9000, 0, 0, "Intrepid", "tsn", "battle"))
        self._signal(HAIL_SHIP=other, HAIL_CLIENT=None)
        self.assertFalse(H.hail_repaint_needed(self.comms))

    def test_a_dial_move_repaints_only_the_console_that_moved_it(self):
        other = _console(C_COMMS2, self.ship, "console", "comms")
        self._offer()
        self._signal(HAIL_SHIP=self.ship, HAIL_CLIENT=self.comms)
        self.assertTrue(H.hail_repaint_needed(self.comms))
        self.assertFalse(H.hail_repaint_needed(other))

    def test_a_ship_wide_change_repaints_every_console(self):
        other = _console(C_COMMS2, self.ship, "console", "comms")
        self._offer()
        self._signal(HAIL_SHIP=self.ship, HAIL_CLIENT=None)
        self.assertTrue(H.hail_repaint_needed(self.comms))
        self.assertTrue(H.hail_repaint_needed(other))

    def test_a_console_with_nothing_to_show_never_repaints(self):
        helm = _console(C_HELM, self.ship, "console", "helm")
        self._offer()
        self._signal(HAIL_SHIP=self.ship, HAIL_CLIENT=None)
        self.assertFalse(H.hail_repaint_needed(helm))


class HistoryAndReplayTests(HailTestCase):
    def test_a_closed_conversation_is_archived(self):
        self._open()
        H.hail_answer(self.ship, 2)          # ends it
        log = H.hail_log(self.ship)
        self.assertEqual(len(log), 1)
        self.assertEqual(log[0].speaker, "ashfang")
        self.assertTrue(log[0].lines)

    def test_the_archive_is_capped(self):
        for _ in range(H.HAIL_LOG_CAP + 5):
            self._offer()
            H.hail_accept(self.ship)
            H.hail_close(self.ship)
        self.assertEqual(len(H.hail_log(self.ship)), H.HAIL_LOG_CAP)

    def test_the_newest_conversation_is_first(self):
        self._offer(name="older")
        H.hail_accept(self.ship)
        H.hail_close(self.ship)
        self._offer(name="newer")
        H.hail_accept(self.ship)
        H.hail_close(self.ship)
        self.assertEqual(H.hail_log(self.ship)[0].name, "newer")

    def test_an_entry_can_be_fetched_by_id(self):
        hid = self._offer()
        H.hail_accept(self.ship)
        H.hail_close(self.ship)
        self.assertIsNotNone(H.hail_log_entry(self.ship, hid))
        self.assertIsNone(H.hail_log_entry(self.ship, 9999))

    def test_a_replay_can_never_answer(self):
        # Read-only is enforced HERE, not by leaving the buttons out - there must be no
        # code path at all from a replay to an outcome.
        self._open()
        H.hail_replay_start(self.comms, 1)
        self.assertEqual(H.hail_replaying(self.comms), 1)
        self.assertFalse(H.hail_answer(self.ship, 0, self.comms))
        self.assertTrue(H.hail_replay_stop(self.comms))
        self.assertTrue(H.hail_answer(self.ship, 0, self.comms))

    def test_closing_leaves_the_next_hail_PENDING(self):
        # The strip re-fills with an Answer entry; the screen does not cut to a stranger.
        self._offer(name="first")
        self._offer(name="second")
        H.hail_accept(self.ship)
        H.hail_close(self.ship)
        self.assertFalse(H.hail_is_active(self.ship))
        self.assertEqual(H.hail_pending_count(self.ship), 1)

    def test_decline_archives_it_as_declined(self):
        self._offer()
        H.hail_accept(self.ship)
        self.assertTrue(H.hail_decline(self.ship))
        self.assertTrue(H.hail_log(self.ship)[0].declined)


class AudioTests(HailTestCase):
    """`Audio:` on a scene plays once, server-side - five consoles must not start five
    copies of the same voice line."""

    def setUp(self):
        super().setUp()
        from sbs_utils.procedural import media
        self.media = media
        self.played = []
        self._real = media.media_play_audio
        media.media_play_audio = lambda f, *a, **k: self.played.append(f) or True

    def tearDown(self):
        self.media.media_play_audio = self._real
        super().tearDown()

    def test_an_amd_scene_plays_its_audio_when_the_hail_opens(self):
        scenes = {"open": {"data": {"speaker": "ashfang", "when": "hail",
                                    "audio": "audio/intercept"},
                           "description": "% Hello." + NL}}
        H.hail_offer_amd(self.ship, scenes, "ashfang")
        H.hail_accept(self.ship)
        self.assertEqual(self.played, ["audio/intercept"])

    def test_a_branch_plays_the_next_scenes_audio(self):
        H.hail_offer(self.ship, speaker="a", lines="One.",
                     choices=[("Go", "next")], scenes={
                         "next": {"data": {"speaker": "a", "audio": "audio/second"},
                                  "description": "% Two." + NL}}, scene="start")
        H.hail_accept(self.ship)
        H.hail_advance(self.ship)
        self.played.clear()
        H.hail_answer(self.ship, 0)
        self.assertEqual(self.played, ["audio/second"])

    def test_a_branch_can_change_how_the_hail_is_DRAWN(self):
        # The confrontation is an orbit shot; the reply is a portrait. A record that
        # kept the entry scene's fields forever could never do that.
        # No subject: a subject id that names nothing is pruned before accept, and
        # hail_form reports the form regardless.
        H.hail_offer(self.ship, speaker="a", presentation="orbit",
                     lines="One.", choices=[("Go", "next")], scene="start", scenes={
                         "next": {"data": {"speaker": "a", "presentation": "portrait"},
                                  "description": "% Two." + NL}})
        H.hail_accept(self.ship)
        H.hail_advance(self.ship)
        H.hail_answer(self.ship, 0)
        self.assertEqual(H.hail_form(self.ship), "portrait")

    def test_a_branch_that_says_nothing_keeps_what_was_running(self):
        H.hail_offer(self.ship, speaker="a", presentation="still", backdrop="neb",
                     lines="One.", choices=[("Go", "next")], scene="start", scenes={
                         "next": {"data": {"speaker": "a"},
                                  "description": "% Two." + NL}})
        H.hail_accept(self.ship)
        H.hail_advance(self.ship)
        H.hail_answer(self.ship, 0)
        self.assertEqual(H.hail_form(self.ship), "still")

    def test_audio_is_ON_by_default(self):
        # A scene that ships a sound file expects to be heard.
        self.assertTrue(H.hail_audio(self.ship))

    def test_turning_audio_off_silences_a_scene_that_has_one(self):
        H.hail_audio_set(self.ship, False)
        scenes = {"open": {"data": {"speaker": "a", "when": "hail",
                                    "audio": "audio/one"},
                           "description": "% Hi." + NL}}
        H.hail_offer_amd(self.ship, scenes, "a")
        H.hail_accept(self.ship)
        self.assertEqual(self.played, [])

    def test_turning_it_back_on_restores_the_sound(self):
        H.hail_audio_set(self.ship, False)
        H.hail_audio_set(self.ship, True)
        scenes = {"open": {"data": {"speaker": "a", "when": "hail",
                                    "audio": "audio/one"},
                           "description": "% Hi." + NL}}
        H.hail_offer_amd(self.ship, scenes, "a")
        H.hail_accept(self.ship)
        self.assertEqual(self.played, ["audio/one"])

    def test_setting_it_to_what_it_already_is_is_not_a_change(self):
        self.assertFalse(H.hail_audio_set(self.ship, True))
        self.assertTrue(H.hail_audio_set(self.ship, False))

    def test_a_hail_with_no_audio_plays_nothing(self):
        self._offer()
        H.hail_accept(self.ship)
        self.assertEqual(self.played, [])

    def test_audio_is_played_once_per_open_not_once_per_console(self):
        _console(C_COMMS2, self.ship, "console", "comms")
        _console(C_MAIN, self.ship, "console", "mainscreen")
        scenes = {"open": {"data": {"speaker": "a", "when": "hail",
                                    "audio": "audio/one"},
                           "description": "% Hi." + NL}}
        H.hail_offer_amd(self.ship, scenes, "a")
        H.hail_accept(self.ship)
        self.assertEqual(len(self.played), 1)


class SignalPayloadTests(HailTestCase):
    """A story reacts to WHICH answer was given, so the signal has to carry it."""

    def setUp(self):
        super().setUp()
        from sbs_utils.procedural import signal as SIG
        self.sig = SIG
        self.seen = []
        self._real = SIG.signal_emit
        # hail.py imported signal_emit by name, so patch it where it is USED.
        import sbs_utils.procedural.hail as HM
        self._real_hail = HM.signal_emit
        HM.signal_emit = lambda name, data=None: self.seen.append((name, data or {}))

    def tearDown(self):
        import sbs_utils.procedural.hail as HM
        HM.signal_emit = self._real_hail
        super().tearDown()

    def _last(self, state):
        for name, data in reversed(self.seen):
            if name == "hail" and data.get("HAIL_STATE") == state:
                return data
        return None

    def test_an_answer_names_the_choice_that_was_taken(self):
        self._open()
        H.hail_answer(self.ship, 0)
        payload = self._last("answered")
        self.assertEqual(payload["HAIL_CHOICE"], "Stand down")
        self.assertEqual(payload["HAIL_TARGET"], "backoff")

    def test_the_payload_identifies_WHICH_hail(self):
        self._offer(key="fb_brief")
        H.hail_accept(self.ship)
        payload = self._last("accepted")
        self.assertEqual(payload["HAIL_KEY"], "fb_brief")
        self.assertEqual(payload["HAIL_SCENE"], "open")

    def test_a_refusal_still_names_the_choice(self):
        D.dialogue_register_outcome("costs", lambda a, s, t: False)
        self._open()
        H.hail_answer(self.ship, 1)
        self.assertEqual(self._last("refused")["HAIL_CHOICE"], "Pay them off")


class AwaitableHailTests(HailTestCase):
    """`await hail_ask(...)` - the shape a LINEAR story needs.

    HereThereBeMonsters is the case: it offers a message and cannot go on until somebody
    takes it. Every ending settles, because a story blocked forever is worse than one
    that hears the wrong answer.
    """

    def test_it_resolves_with_the_chosen_label(self):
        prom = H.hail_ask(self.ship, scenes=SCENES, scene="open", speaker="ashfang")
        self.assertFalse(prom.done())
        H.hail_accept(self.ship)
        while H.hail_advance(self.ship):
            pass
        H.hail_answer(self.ship, 0)
        self.assertTrue(prom.done())
        self.assertEqual(prom.result().value, "Stand down")
        self.assertTrue(prom.result().answered)

    def test_a_branch_still_releases_the_story(self):
        # Answering navigated to another scene. The crew ANSWERED, so a linear story
        # moves on even though the conversation carries on.
        prom = H.hail_ask(self.ship, scenes=SCENES, scene="open", speaker="ashfang")
        H.hail_accept(self.ship)
        while H.hail_advance(self.ship):
            pass
        H.hail_answer(self.ship, 0)
        self.assertTrue(H.hail_is_active(self.ship))
        self.assertTrue(prom.done())

    def test_closing_without_answering_still_settles(self):
        prom = H.hail_ask(self.ship, scenes=SCENES, scene="open", speaker="ashfang")
        H.hail_accept(self.ship)
        H.hail_close(self.ship)
        self.assertTrue(prom.done())
        self.assertIsNone(prom.result().value)
        self.assertFalse(prom.result().answered)

    def test_declining_settles(self):
        prom = H.hail_ask(self.ship, scenes=SCENES, scene="open", speaker="ashfang")
        H.hail_accept(self.ship)
        H.hail_decline(self.ship)
        self.assertTrue(prom.done())

    def test_cancelling_before_anyone_saw_it_settles(self):
        prom = H.hail_ask(self.ship, scenes=SCENES, scene="open", speaker="ashfang")
        H.hail_cancel(self.ship)
        self.assertTrue(prom.done())
        self.assertIsNone(prom.result().value)

    def test_a_repeated_key_returns_no_promise_like_hail_offer(self):
        self.assertIsNotNone(H.hail_ask(self.ship, lines="hi", choices=["ok"], key="k"))
        self.assertIsNone(H.hail_ask(self.ship, lines="hi", choices=["ok"], key="k"))

    def test_the_replay_log_does_not_carry_the_promise(self):
        H.hail_ask(self.ship, scenes=SCENES, scene="open", speaker="ashfang")
        H.hail_accept(self.ship)
        H.hail_close(self.ship)
        self.assertNotIn("promise", dict(H.hail_log(self.ship)[0].__dict__))


class TranscriptTests(HailTestCase):
    """A replay is only worth having if it is the WHOLE conversation."""

    def test_the_transcript_spans_a_branch(self):
        # `lines` holds one scene at a time - each new scene overwrites it - so a
        # transcript built from it would show only the last thing said.
        self._open()
        H.hail_answer(self.ship, 0)          # -> backoff
        while H.hail_advance(self.ship):
            pass
        H.hail_close(self.ship)
        kinds = [t["kind"] for t in H.hail_log(self.ship)[0].transcript]
        texts = [t["text"] for t in H.hail_log(self.ship)[0].transcript]
        self.assertEqual(kinds, ["line", "line", "choice", "line"])
        self.assertIn("Stand down", texts)   # the answer, in the order it was given
        self.assertIn("Wise.", texts)        # and what the SECOND scene replied

    def test_lines_are_recorded_as_spoken_not_as_resolved(self):
        # Closing early must not archive words nobody heard.
        self._offer()
        H.hail_accept(self.ship)
        H.hail_close(self.ship)
        self.assertEqual(len(H.hail_log(self.ship)[0].transcript), 1)

    def test_the_speaker_is_resolved_into_the_transcript(self):
        H.hail_set_speaker_resolver(lambda key, ship: {"name": key.title()})
        self._offer()
        H.hail_accept(self.ship)
        H.hail_close(self.ship)
        self.assertEqual(H.hail_log(self.ship)[0].transcript[0]["name"], "Ashfang")


class OrbitBandTests(HailTestCase):
    """An orbit hail draws nothing inline, so the band IS the conversation on screen -
    it has to follow the beats and go when the hail does."""

    def setUp(self):
        super().setUp()
        from sbs_utils.procedural.gui import hail_gui
        self.gui = hail_gui
        self.shown, self.cleared = [], []
        self._show = hail_gui.hail_band_show
        self._clear = hail_gui.hail_band_clear
        self.screen_shown, self.screen_cleared = [], []
        self._sshow = hail_gui.hail_screen_show
        self._sclear = hail_gui.hail_screen_clear
        hail_gui.hail_band_show = lambda ship, **kw: self.shown.append(ship) or True
        hail_gui.hail_band_clear = lambda ship, **kw: self.cleared.append(ship) or True
        hail_gui.hail_screen_show = lambda ship, **kw: self.screen_shown.append(ship) or True
        hail_gui.hail_screen_clear = lambda ship, **kw: self.screen_cleared.append(ship) or True
        self.main = _console(C_MAIN, self.ship, "console", "mainscreen")

    def tearDown(self):
        self.gui.hail_band_show = self._show
        self.gui.hail_band_clear = self._clear
        self.gui.hail_screen_show = self._sshow
        self.gui.hail_screen_clear = self._sclear
        super().tearDown()

    def _orbit(self):
        raider = to_id(npc_spawn(500, 0, 0, "Raider", "raider", "battle", "behav_npcship"))
        H.hail_where_set(self.comms, "main")
        self._offer(presentation="orbit", subject=raider)
        return raider

    def test_an_orbit_hail_puts_the_band_up(self):
        self._orbit()
        H.hail_accept(self.ship)
        self.assertEqual(self.shown, [self.ship])

    def test_the_band_follows_each_beat(self):
        self._orbit()
        H.hail_accept(self.ship)
        self.shown.clear()
        H.hail_advance(self.ship)
        self.assertEqual(self.shown, [self.ship])

    def test_closing_takes_the_band_down(self):
        self._orbit()
        H.hail_accept(self.ship)
        H.hail_close(self.ship)
        self.assertIn(self.ship, self.cleared)

    def test_a_portrait_never_raises_a_band(self):
        H.hail_where_set(self.comms, "main")
        self._offer(presentation="portrait")
        H.hail_accept(self.ship)
        self.assertEqual(self.shown, [])

    def test_taking_it_off_the_main_screen_takes_the_band_with_it(self):
        self._orbit()
        H.hail_accept(self.ship)
        self.cleared.clear()
        H.hail_where_set(self.comms, "off")
        self.assertIn(self.ship, self.cleared)

    def test_turning_the_dial_OFF_takes_the_conversation_off_the_screen(self):
        # The dial cleared the orbit band by hand and left the full-screen overlay up,
        # so a portrait stayed on the main screen after it was switched off.
        H.hail_where_set(self.comms, "main")
        self._offer(presentation="portrait")
        H.hail_accept(self.ship)
        self.cleared.clear()
        H.hail_where_set(self.comms, "off")
        self.assertIn(self.ship, self.screen_cleared)

    def test_a_late_resolved_subject_starts_no_shot(self):
        # A role or a cast name cannot be filmed until something binds it; the renderer
        # does that, so the library must not guess an id here.
        H.hail_where_set(self.comms, "main")
        self._offer(presentation="orbit", subject="raider_lead")
        H.hail_accept(self.ship)
        self.assertEqual(self.shown, [])


class ResetTests(HailTestCase):
    def test_the_resolver_is_a_latch_the_ledger_can_see(self):
        from sbs_utils.handlerhooks import reset_mission_audit
        H.hail_set_speaker_resolver(lambda k, s: {"name": k})
        self.assertEqual(reset_mission_audit().get("hail speaker resolver"), 1)
        H.hail_reset()
        self.assertNotIn("hail speaker resolver", reset_mission_audit())

    def test_per_ship_state_goes_with_the_agents(self):
        # The queue, the open conversation and the replay log are ship inventory, so
        # SpaceObject.clear() takes them - there is no module container to leak.
        self._offer()
        H.hail_accept(self.ship)
        SpaceObject.clear()
        ship = to_id(player_spawn(0, 0, 0, "Artemis", "tsn", "battle"))
        self.assertFalse(H.hail_is_active(ship))
        self.assertEqual(H.hail_pending_count(ship), 0)
        self.assertEqual(H.hail_log(ship), [])


class UnknownShipTests(unittest.TestCase):
    """Every entry point takes an id from a caller and must survive a bad one."""

    def setUp(self):
        mock_sbs.create_new_sim()
        SpaceObject.clear()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())

    def tearDown(self):
        FrameContext.context = None

    def test_nothing_raises_on_an_unknown_ship(self):
        self.assertIsNone(H.hail_offer(None))
        self.assertEqual(H.hail_pending(None), [])
        self.assertEqual(H.hail_pending_count(None), 0)
        self.assertIsNone(H.hail_active(None))
        self.assertFalse(H.hail_is_active(None))
        self.assertIsNone(H.hail_accept(None))
        self.assertIsNone(H.hail_beat(None))
        self.assertFalse(H.hail_advance(None))
        self.assertEqual(H.hail_choices(None), [])
        self.assertFalse(H.hail_answer(None, 0))
        self.assertFalse(H.hail_close(None))
        self.assertFalse(H.hail_cancel(None))
        self.assertIsNone(H.hail_form(None))
        self.assertEqual(H.hail_log(None), [])


class AmdEntryTests(HailTestCase):
    def test_offer_amd_finds_the_hail_entry_and_reads_its_fence(self):
        hid = H.hail_offer_amd(self.ship, SCENES, "ashfang")
        self.assertIsNotNone(hid)
        rec = H.hail_pending(self.ship)[0]
        self.assertEqual(rec.scene, "open")
        self.assertEqual(rec.presentation, "portrait")

    def test_a_speaker_with_no_hail_entry_offers_nothing(self):
        self.assertIsNone(H.hail_offer_amd(self.ship, SCENES, "verdant"))

    def test_a_keyword_overrides_the_document(self):
        H.hail_offer_amd(self.ship, SCENES, "ashfang", presentation="still",
                         backdrop="nebula")
        rec = H.hail_pending(self.ship)[0]
        self.assertEqual(rec.presentation, "still")
        self.assertEqual(rec.backdrop, "nebula")


class NoAmdTests(HailTestCase):
    """A MAST-driven hail with no document behind it still has to work."""

    def test_lines_and_choices_can_be_passed_directly(self):
        H.hail_offer(self.ship, speaker="command", name="TSN Command",
                     lines="Report to the station.",
                     choices=[("Acknowledge", None), ("Refuse", None)])
        H.hail_accept(self.ship)
        self.assertEqual(H.hail_beat(self.ship).text, "Report to the station.")
        self.assertFalse(H.hail_advance(self.ship))
        self.assertEqual([c.label for c in H.hail_choices(self.ship)],
                         ["Acknowledge", "Refuse"])

    def test_more_than_four_choices_are_truncated(self):
        H.hail_offer(self.ship, speaker="command", lines="Pick.",
                     choices=["a", "b", "c", "d", "e", "f"])
        H.hail_accept(self.ship)
        H.hail_advance(self.ship)
        self.assertEqual(len(H.hail_choices(self.ship)), H.HAIL_MAX_CHOICES)


class TheNameOnTheListComesFromTheResolver(HailTestCase):
    """A hail authored entirely in AMD still has a NAME on the pending list.

    The list and the `Answer X` button render BEFORE any beat does, and only a beat
    builds a speaker card - so both read the record, which held nothing but the raw
    key. Every early call site passed `name=` and hid it; the moment a mission named
    its cast in the document instead, the list read `Answer tsn_command`.
    """

    def test_the_pending_record_carries_the_resolved_name(self):
        H.hail_set_speaker_resolver(lambda key, sid=None: {"name": "TSN Command"})
        hid = self._offer(speaker="tsn_command")
        rec = [r for r in H.hail_pending(self.ship) if r.get("id") == hid][0]
        self.assertEqual(rec.get("name"), "TSN Command")
        self.assertEqual(H.hail_answer_label(rec), "Answer TSN Command")

    def test_an_explicit_name_still_wins(self):
        H.hail_set_speaker_resolver(lambda key, sid=None: {"name": "TSN Command"})
        hid = self._offer(speaker="tsn_command", name="Fleet HQ")
        rec = [r for r in H.hail_pending(self.ship) if r.get("id") == hid][0]
        self.assertEqual(rec.get("name"), "Fleet HQ")

    def test_no_resolver_leaves_the_key_rather_than_inventing_a_name(self):
        hid = self._offer(speaker="tsn_command")
        rec = [r for r in H.hail_pending(self.ship) if r.get("id") == hid][0]
        self.assertEqual(H.hail_answer_label(rec), "Answer tsn_command")


if __name__ == "__main__":
    unittest.main()
