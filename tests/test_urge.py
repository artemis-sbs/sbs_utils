"""Urges: an actor's recurring want (URGE_PLAN.md phase 3).

Covers the condition vocabulary, selection (cooldown / Until / Weight), the AMD reader,
and the ticker's lifecycle guards.

Run:
    python -m unittest tests.test_urge
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs as sbs
from tests.reset_helper import reset_mock
from sbs_utils.agent import Agent, get_story_id
from sbs_utils.procedural.quest import quest_add, QuestState
from sbs_utils.procedural import urge as U
from sbs_utils.procedural.urge import (
    urge_record, urge_add, urge_clear, urge_pick, urge_run_one, urge_actors,
    urge_condition_eval, urge_register_condition, urges_run_all)
from sbs_utils.procedural.amd_urge import urges_from_section, urges_install

SH = Agent.SHARED_ID


def make_agent(*roles):
    a = Agent()
    a.id = get_story_id()
    a.add()
    for r in roles:
        a.add_role(r)
    return a


class UrgeBase(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        self.said = []
        self._real_speak = U.urge_speak
        U.urge_speak = lambda actor_id, line: (self.said.append((actor_id, line)), True)[1]

    def tearDown(self):
        U.urge_speak = self._real_speak


class ConditionTests(UrgeBase):
    def test_always(self):
        a = make_agent()
        self.assertTrue(urge_condition_eval(a.id, "always"))

    def test_not_negates(self):
        a = make_agent()
        self.assertFalse(urge_condition_eval(a.id, "not always"))

    def test_has_role(self):
        a = make_agent("waiting")
        self.assertTrue(urge_condition_eval(a.id, "has role waiting"))
        self.assertFalse(urge_condition_eval(a.id, "has role departed"))

    def test_quest_state_on_any_holder(self):
        a = make_agent()
        station = make_agent("ds1")
        quest_add(station.id, "resupply", "Resupply", "", state=QuestState.ACTIVE)
        # The urge belongs to the ACTOR; the quest is held by someone else entirely.
        self.assertTrue(urge_condition_eval(a.id, "quest resupply active"))
        self.assertFalse(urge_condition_eval(a.id, "quest resupply failed"))

    def test_unknown_phrasing_is_false_not_true(self):
        """An urge nobody can trigger is a bug; a silently-TRUE one talks forever."""
        a = make_agent()
        self.assertFalse(urge_condition_eval(a.id, "frobnicate the widget"))

    def test_registry_rejects_a_conflicting_rebind(self):
        urge_register_condition("test only", lambda aid, op: True, operand="none")
        with self.assertRaises(ValueError):
            urge_register_condition("test only", lambda aid, op: False, operand="none")
        # identical re-register is a no-op, so reloading is safe
        fn = U._CONDITIONS["test only"]["fn"]
        urge_register_condition("test only", fn, operand="none")
        del U._CONDITIONS["test only"]


class SelectionTests(UrgeBase):
    def test_picks_nothing_without_urges(self):
        self.assertIsNone(urge_pick(make_agent().id))

    def test_highest_weight_wins(self):
        a = make_agent()
        urge_add(a.id, urge_record(key="low", weight=10, pool=["low"]))
        urge_add(a.id, urge_record(key="high", weight=90, pool=["high"]))
        self.assertEqual(urge_pick(a.id, now=0)["rec"]["key"], "high")

    def test_cooldown_blocks_a_repeat(self):
        a = make_agent()
        urge_add(a.id, urge_record(key="nag", every=300, pool=["nag"]))
        first = urge_run_one(a.id, now=0)
        self.assertIsNotNone(first)
        self.assertIsNone(urge_pick(a.id, now=100), "still cooling")
        self.assertIsNotNone(urge_pick(a.id, now=400), "cooldown elapsed")

    def test_until_retires_permanently(self):
        a = make_agent("waiting")
        urge_add(a.id, urge_record(key="nag", every=0, until="not has role waiting",
                                   pool=["nag"]))
        self.assertIsNotNone(urge_pick(a.id, now=0))
        a.remove_role("waiting")
        self.assertIsNone(urge_pick(a.id, now=1))
        a.add_role("waiting")       # even if the world comes back...
        self.assertIsNone(urge_pick(a.id, now=2), "Until: retires, it does not cool")

    def test_whenever_gates(self):
        a = make_agent()
        urge_add(a.id, urge_record(key="nag", whenever="has role waiting", pool=["nag"]))
        self.assertIsNone(urge_pick(a.id, now=0))
        a.add_role("waiting")
        self.assertIsNotNone(urge_pick(a.id, now=0))

    def test_a_refused_urge_keeps_its_turn(self):
        """A budget refusal must NOT stamp the cooldown - it retries next pass."""
        a = make_agent()
        urge_add(a.id, urge_record(key="nag", every=300, pool=["nag"]))
        real = U.urge_budget_allows
        U.urge_budget_allows = lambda actor_id, state, now=None: False
        try:
            self.assertIsNone(urge_run_one(a.id, now=0))
        finally:
            U.urge_budget_allows = real
        self.assertEqual(self.said, [])
        self.assertIsNotNone(urge_pick(a.id, now=1), "refusal must not burn the cooldown")


class SpeakingTests(UrgeBase):
    def test_running_speaks_a_pool_line(self):
        a = make_agent()
        urge_add(a.id, urge_record(key="nag", pool=["only line"]))
        urge_run_one(a.id, now=0)
        self.assertEqual([line for _, line in self.said], ["only line"])

    def test_action_runs_even_with_no_lines(self):
        a = make_agent("here")
        urge_add(a.id, urge_record(key="leave", pool=[],
                                   action="Nobody is no longer here"))
        # The action's actor resolves by role; give something that name.
        target = make_agent("nobody")
        target.add_role("here")
        urge_run_one(a.id, now=0)
        self.assertFalse(target.has_role("here"), "the Action: should have run")


class TickerTests(UrgeBase):
    def test_actors_lists_only_agents_with_urges(self):
        a = make_agent()
        make_agent()        # no urges
        urge_add(a.id, urge_record(key="nag", pool=["x"]))
        self.assertEqual(urge_actors(), [a.id])

    def test_actors_is_a_list_not_the_live_registry(self):
        a = make_agent()
        urge_add(a.id, urge_record(key="nag", pool=["x"]))
        self.assertIsInstance(urge_actors(), list)

    def test_a_pass_lets_exactly_one_actor_speak(self):
        """Everyone is VISITED; the global floor means only one of them speaks. Three
        actors all piping up the instant they become eligible is the behavior the
        budget exists to prevent."""
        U.urge_budget_reset()
        from sbs_utils.procedural.announce import announce_traffic_reset
        announce_traffic_reset()
        agents = [make_agent() for _ in range(3)]
        for i, a in enumerate(agents):
            urge_add(a.id, urge_record(key=f"nag{i}", every=0, pool=[f"line{i}"]))
        urges_run_all()
        self.assertEqual(len(self.said), 1, f"one voice per pass, got {self.said}")

    def test_the_others_speak_on_later_passes(self):
        U.urge_budget_reset()
        from sbs_utils.procedural.announce import announce_traffic_reset
        announce_traffic_reset()
        agents = [make_agent() for _ in range(3)]
        for i, a in enumerate(agents):
            urge_add(a.id, urge_record(key=f"nag{i}", every=0, pool=[f"line{i}"]))
        from sbs_utils.procedural.timers import TICK_PER_SECONDS
        for _ in range(3):
            urges_run_all()
            sbs.sim._time_tick_counter += int((U.URGE_GLOBAL_FLOOR + 1) * TICK_PER_SECONDS)
        self.assertEqual(sorted(line for _, line in self.said),
                         ["line0", "line1", "line2"])

    def test_removing_an_agent_purges_its_urge_registry_entry(self):
        """Agent._remove purges the inventory registries, so a clean removal needs no
        help from us. Pinned because the guard below only makes sense given this."""
        a = make_agent()
        urge_add(a.id, urge_record(key="nag", pool=["x"]))
        dead_id = a.id
        Agent.remove_id(dead_id)
        self.assertIsNone(Agent.get(dead_id))
        self.assertNotIn(dead_id, urge_actors())

    def test_a_stale_registry_id_is_unscheduled_not_crashed_on(self):
        """The case the purge does NOT cover: an id that reaches the loop with no live
        agent behind it. It must unschedule and carry on - the shape that once made
        every brain in the game stop thinking, permanently, with no error."""
        real = U.urge_actors
        U.urge_actors = lambda: [123456789]
        try:
            urges_run_all()         # must not raise
        finally:
            U.urge_actors = real
        self.assertEqual(self.said, [], "a dead actor must not speak")

    def test_one_bad_actor_does_not_stop_the_others(self):
        """A pass must not be abandoned halfway because one actor threw."""
        good = make_agent()
        urge_add(good.id, urge_record(key="nag", pool=["heard"]))
        real = U.urge_actors
        U.urge_actors = lambda: [123456789, good.id]
        try:
            urges_run_all()
        finally:
            U.urge_actors = real
        self.assertEqual([line for _, line in self.said], ["heard"])

    def test_urge_clear_stops_visits(self):
        a = make_agent()
        urge_add(a.id, urge_record(key="nag", pool=["x"]))
        urge_clear(a.id)
        self.assertEqual(urge_actors(), [])

    def test_reset_clears_the_scheduled_latch(self):
        U.urge_schedule()
        U.urge_reset()
        self.assertIsNone(U._urge_slicer._sig)


class BudgetTests(UrgeBase):
    """The speech budget (URGE_PLAN.md s5.2). Not an optimization - it is what decides
    whether autonomous speech is pleasant or unbearable."""

    def setUp(self):
        super().setUp()
        U.urge_budget_reset()
        from sbs_utils.procedural.announce import announce_traffic_reset
        announce_traffic_reset()

    def _actor_with(self, key="nag", **kw):
        a = make_agent()
        kw.setdefault("every", 0)
        kw.setdefault("pool", ["line"])
        urge_add(a.id, urge_record(key=key, **kw))
        return a

    def test_an_actor_does_not_monologue(self):
        a = self._actor_with()
        self.assertIsNotNone(urge_run_one(a.id, now=0))
        self.assertIsNone(urge_run_one(a.id, now=10), "inside the per-actor floor")
        self.assertIsNotNone(urge_run_one(a.id, now=U.URGE_ACTOR_FLOOR + 1))

    def test_actors_do_not_pile_up(self):
        a, b = self._actor_with("a"), self._actor_with("b")
        self.assertIsNotNone(urge_run_one(a.id, now=0))
        self.assertIsNone(urge_run_one(b.id, now=5), "inside the global floor")
        self.assertIsNotNone(urge_run_one(b.id, now=U.URGE_GLOBAL_FLOOR + 1))

    def test_urgent_bypasses_the_global_floor(self):
        a = self._actor_with("a")
        b = self._actor_with("b", weight=U.URGE_URGENT_WEIGHT)
        self.assertIsNotNone(urge_run_one(a.id, now=0))
        self.assertIsNotNone(urge_run_one(b.id, now=1),
                             "leaving forever outranks politeness")

    def test_urgent_does_NOT_bypass_its_own_floor(self):
        """Back-to-back lines from one mouth read as a bug however urgent they are."""
        a = make_agent()
        urge_add(a.id, urge_record(key="nag", every=0, pool=["line"]))
        urge_add(a.id, urge_record(key="bye", every=0, weight=U.URGE_URGENT_WEIGHT,
                                   pool=["goodbye"]))
        self.assertIsNotNone(urge_run_one(a.id, now=0))
        self.assertIsNone(urge_run_one(a.id, now=1))

    def test_an_actor_does_not_talk_over_mission_dispatch(self):
        from sbs_utils.procedural.announce import announce_note_traffic
        a = self._actor_with()
        announce_note_traffic(0)        # the mission just said something
        self.assertIsNone(urge_run_one(a.id, now=5))
        self.assertIsNotNone(urge_run_one(a.id, now=U.URGE_GLOBAL_FLOOR + 1))

    def test_a_refusal_does_not_burn_the_cooldown(self):
        a = self._actor_with(every=300)
        self.assertIsNotNone(urge_run_one(a.id, now=0))
        b = self._actor_with("other", every=300)
        self.assertIsNone(urge_run_one(b.id, now=1), "refused by the global floor")
        # ...and it still has its turn once the floor clears
        self.assertIsNotNone(urge_run_one(b.id, now=U.URGE_GLOBAL_FLOOR + 1))

    def test_a_line_that_failed_does_not_register_traffic(self):
        """Only speech that actually happened should hold the floor against others."""
        from sbs_utils.procedural.announce import announce_last_traffic
        a = self._actor_with()
        real = U.urge_speak
        U.urge_speak = lambda actor_id, line: False
        try:
            urge_run_one(a.id, now=0)
        finally:
            U.urge_speak = real
        self.assertIsNone(announce_last_traffic(), "a silent failure is not traffic")

    def test_reset_drops_the_clocks(self):
        from sbs_utils.handlerhooks import reset_mission_state
        from sbs_utils.procedural.announce import announce_last_traffic
        a = self._actor_with()
        urge_run_one(a.id, now=0)
        self.assertTrue(U._last_actor_spoke)
        self.assertIsNotNone(announce_last_traffic())
        # Through the real entry point, so this cannot pass while reset_mission_state
        # forgets one of the two clocks - which is the way it would actually break.
        reset_mission_state()
        self.assertFalse(U._last_actor_spoke)
        self.assertIsNone(announce_last_traffic(),
                          "a carried-over clock mutes the next mission's first minute")


class EscalationTests(UrgeBase):
    """`%` / `%%` / `%%%` are stages, and `Escalates: with deadline` takes the stage from
    the bound quest's remaining clock - so the drama curve IS the countdown that already
    exists (URGE_PLAN.md s4.1)."""

    def _staged(self, escalates, whenever="always"):
        a = make_agent()
        urge_add(a.id, urge_record(
            key="nag", every=0, whenever=whenever, escalates=escalates,
            pool=["calm", "firmer", "final"],
            stages={1: ["calm"], 2: ["firmer"], 3: ["final"]}))
        return a

    def _state(self, agent):
        from sbs_utils.procedural.inventory import get_inventory_value
        return get_inventory_value(agent.id, "__URGES__")[0]

    def test_no_escalation_uses_the_flat_pool(self):
        a = self._staged(None)
        self.assertEqual(U.urge_stage(self._state(a)), 1)
        self.assertIn(U.urge_line(self._state(a)), ["calm", "firmer", "final"])

    def test_per_firing_advances_a_stage_each_time(self):
        a = self._staged("firing")
        st = self._state(a)
        self.assertEqual(U.urge_line(st), "calm")
        st["stage"] = 1
        self.assertEqual(U.urge_line(st), "firmer")
        st["stage"] = 2
        self.assertEqual(U.urge_line(st), "final")

    def test_per_firing_sticks_at_the_last_stage(self):
        a = self._staged("firing")
        st = self._state(a)
        st["stage"] = 99
        self.assertEqual(U.urge_line(st), "final")

    def test_a_missing_stage_falls_back_to_the_nearest_lower(self):
        """Three stage-1 lines and one stage-3 line must not go quiet in the middle."""
        a = make_agent()
        urge_add(a.id, urge_record(key="nag", every=0, escalates="firing",
                                   pool=["calm", "final"],
                                   stages={1: ["calm"], 3: ["final"]}))
        st = self._state(a)
        st["stage"] = 1         # wants stage 2, which has no lines
        self.assertEqual(U.urge_line(st), "calm")


class DeadlineEscalationTests(UrgeBase):
    def setUp(self):
        super().setUp()
        self._real_emit = __import__(
            "sbs_utils.procedural.quest_driver", fromlist=["x"]).signal_emit

    def _advance(self, seconds):
        from sbs_utils.procedural.timers import TICK_PER_SECONDS
        sbs.sim._time_tick_counter += int(seconds * TICK_PER_SECONDS)

    def _setup(self, minutes=30):
        from sbs_utils.procedural import quest_driver as QD
        station = make_agent("ds1")
        quest_add(station.id, "resupply", "Resupply", "", state=QuestState.ACTIVE,
                  data={"fail_after": {"minutes": minutes}})
        actor = make_agent()
        urge_add(actor.id, urge_record(
            key="call", every=0, whenever="quest resupply active",
            escalates="deadline", pool=["calm", "firmer", "final"],
            stages={1: ["calm"], 2: ["firmer"], 3: ["final"]}))
        QD.quest_tick_fail_after()      # anchor the clock
        return station, actor

    def _state(self, agent):
        from sbs_utils.procedural.inventory import get_inventory_value
        return get_inventory_value(agent.id, "__URGES__")[0]

    def test_bound_quest_is_read_from_whenever(self):
        rec = urge_record(whenever="quest deliver_vell active")
        self.assertEqual(U.urge_bound_quest(rec), "deliver_vell")

    def test_no_quest_condition_has_no_bound_quest(self):
        self.assertIsNone(U.urge_bound_quest(urge_record(whenever="always")))

    def test_stage_follows_the_countdown(self):
        _, actor = self._setup(minutes=30)
        st = self._state(actor)
        self.assertEqual(U.urge_line(st), "calm", "start of the clock")
        self._advance(60 * 12)                      # 40% gone
        self.assertEqual(U.urge_line(st), "firmer")
        self._advance(60 * 12)                      # 80% gone
        self.assertEqual(U.urge_line(st), "final")

    def test_stage_is_one_before_the_watcher_anchors(self):
        from sbs_utils.procedural import quest_driver as QD
        station = make_agent("ds1")
        quest_add(station.id, "resupply", "Resupply", "", state=QuestState.ACTIVE,
                  data={"fail_after": {"minutes": 30}})
        actor = make_agent()
        urge_add(actor.id, urge_record(
            key="call", every=0, whenever="quest resupply active",
            escalates="deadline", pool=["calm"], stages={1: ["calm"], 2: ["firmer"]}))
        self.assertEqual(U.urge_stage(self._state(actor)), 1,
                         "nothing has elapsed until the watcher anchors the timer")

    def test_deadlineless_quest_falls_back_to_per_firing_and_warns_once(self):
        station = make_agent("ds1")
        quest_add(station.id, "resupply", "Resupply", "", state=QuestState.ACTIVE)
        actor = make_agent()
        urge_add(actor.id, urge_record(
            key="call", every=0, whenever="quest resupply active",
            escalates="deadline", pool=["calm", "firmer"],
            stages={1: ["calm"], 2: ["firmer"]}))
        st = self._state(actor)
        self.assertEqual(U.urge_line(st), "calm")
        self.assertTrue(st.get("_warned_no_deadline"), "must say so, once")
        st["stage"] = 1
        self.assertEqual(U.urge_line(st), "firmer", "falls back to per-firing")


class AmdEscalationTests(UrgeBase):
    def _recs(self, data, desc):
        return urges_from_section({"children": [
            {"key": "nag", "display_text": "nag", "description": desc, "data": data}]})

    def test_markers_become_stages(self):
        r = self._recs({"Actor": "ds1", "Escalates": "yes"},
                       "% calm\n%% firmer\n%%% final\n")[0]
        self.assertEqual(r["stages"], {1: ["calm"], 2: ["firmer"], 3: ["final"]})
        self.assertEqual(r["pool"], ["calm", "firmer", "final"])
        self.assertEqual(r["escalates"], "firing")

    def test_with_deadline_parses(self):
        r = self._recs({"Actor": "ds1", "Escalates": "with deadline"}, "% a\n%% b")[0]
        self.assertEqual(r["escalates"], "deadline")

    def test_a_flat_pool_has_no_stages(self):
        r = self._recs({"Actor": "ds1"}, "% one\n% two\n")[0]
        self.assertIsNone(r["stages"], "one stage is not an escalation")
        self.assertEqual(r["pool"], ["one", "two"])

    def test_unmarked_lines_sit_at_stage_one(self):
        r = self._recs({"Actor": "ds1", "Escalates": "yes"}, "plain\n%% firmer\n")[0]
        self.assertEqual(r["stages"], {1: ["plain"], 2: ["firmer"]})

    def test_staged_lines_without_escalates_warn_rather_than_guess(self):
        r = self._recs({"Actor": "ds1"}, "% a\n%% b")[0]
        self.assertIsNone(r["escalates"], "never default it on")
        self.assertEqual(U.urge_line({"rec": r, "stage": 0}) in ["a", "b"], True)


class RealSpeechTests(unittest.TestCase):
    """The REAL urge_speak, unmocked. URGE_PLAN.md s10.1: every phase here widens
    something a display path already touches, and the unit tests happily pass with a
    formatting bug sitting in it - so exercise the path, not just the parse."""

    def setUp(self):
        reset_mock(sbs)

    def test_unhosted_actor_speaks(self):
        from sbs_utils.procedural.lifeform import lifeform_spawn
        lf = lifeform_spawn("Ambassador Vell", None, "diplomat")
        self.assertTrue(U.urge_speak(lf.id, "I am still waiting."))

    def test_empty_line_says_nothing(self):
        from sbs_utils.procedural.lifeform import lifeform_spawn
        lf = lifeform_spawn("Ambassador Vell", None, "diplomat")
        self.assertFalse(U.urge_speak(lf.id, ""))

    def test_a_dead_actor_says_nothing(self):
        self.assertFalse(U.urge_speak(123456789, "hello?"))

    def test_a_failing_send_is_caught_not_propagated(self):
        """One unspeakable line must not stop the ticker for every other actor."""
        from sbs_utils.procedural.lifeform import lifeform_spawn
        from sbs_utils.procedural import comms as C
        lf = lifeform_spawn("Ambassador Vell", None, "diplomat")
        real = C.comms_message
        C.comms_message = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
        try:
            self.assertFalse(U.urge_speak(lf.id, "this cannot be sent"))
        finally:
            C.comms_message = real

    def test_a_failing_line_still_stamps_its_cooldown(self):
        """Otherwise a permanently-broken line retries - and logs - every pass, forever."""
        from sbs_utils.procedural.lifeform import lifeform_spawn
        lf = lifeform_spawn("Ambassador Vell", None, "diplomat")
        urge_add(lf.id, urge_record(key="nag", every=300, pool=["unspeakable"]))
        real = U.urge_speak
        U.urge_speak = lambda actor_id, line: False
        try:
            urge_run_one(lf.id, now=0)
        finally:
            U.urge_speak = real
        self.assertIsNone(urge_pick(lf.id, now=10), "a failed line must back off")


class AmdUrgeTests(UrgeBase):
    def _section(self, children):
        return {"children": children}

    def _node(self, key, data, desc):
        return {"key": key, "display_text": key, "description": desc, "data": data}

    def test_body_is_the_pool(self):
        recs = urges_from_section(self._section([
            self._node("nag", {"Actor": "ds1"}, "% first line\n% second line\n")]))
        self.assertEqual(recs[0]["pool"], ["first line", "second line"])

    def test_comments_are_ignored(self):
        recs = urges_from_section(self._section([
            self._node("nag", {"Actor": "ds1"}, "// a note\n% real line\n")]))
        self.assertEqual(recs[0]["pool"], ["real line"])

    def test_every_accepts_the_compact_duration(self):
        recs = urges_from_section(self._section([
            self._node("nag", {"Actor": "ds1", "Every": "5m"}, "% line")]))
        self.assertEqual(recs[0]["every"], 300)

    def test_defaults(self):
        recs = urges_from_section(self._section([
            self._node("nag", {"Actor": "ds1"}, "% line")]))
        self.assertEqual(recs[0]["whenever"], "always")
        self.assertEqual(recs[0]["weight"], 0)

    def test_an_urge_with_nothing_to_say_is_dropped(self):
        recs = urges_from_section(self._section([
            self._node("nag", {"Actor": "ds1"}, "")]))
        self.assertEqual(recs, [])

    def test_install_binds_to_the_named_actor(self):
        station = make_agent("ds1")
        n = urges_install(self._section([
            self._node("nag", {"Actor": "ds1", "Every": "5m"}, "% resupply us")]))
        self.assertEqual(n, 1)
        self.assertEqual(urge_actors(), [station.id])

    def test_install_skips_an_unknown_actor(self):
        n = urges_install(self._section([
            self._node("nag", {"Actor": "no_such_place"}, "% hello")]))
        self.assertEqual(n, 0)
        self.assertEqual(urge_actors(), [])

    def test_install_is_idempotent(self):
        make_agent("ds1")
        section = self._section([self._node("nag", {"Actor": "ds1"}, "% resupply us")])
        urges_install(section)
        urges_install(section)
        states = urge_actors()
        from sbs_utils.procedural.inventory import get_inventory_value
        self.assertEqual(len(get_inventory_value(states[0], "__URGES__")), 1)


if __name__ == "__main__":
    unittest.main()
