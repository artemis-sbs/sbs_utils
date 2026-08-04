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
        U.urge_budget_allows = lambda actor_id, state: False
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

    def test_run_all_visits_everyone(self):
        agents = [make_agent() for _ in range(3)]
        for i, a in enumerate(agents):
            urge_add(a.id, urge_record(key=f"nag{i}", pool=[f"line{i}"]))
        urges_run_all()
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
