"""Away missions (sbs_utils.procedural.away) - one shared scene, one character per console.

The headline behavior, and the reason the module exists at all: the SAME authored scene must
hand a DIFFERENT set of choices to each character. Everything else here guards a specific way
that could quietly stop being true - the random line diverging per console, an answer racing
another answer, or the guard resolver clobbering whoever installed one first.

Run: python -m unittest tests.test_away
"""
import unittest
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural.lifeform import lifeform_spawn
from sbs_utils.procedural import amd_dialogue as D
from sbs_utils.procedural import away as A


# One scene, four choices: three role-gated, one open to anybody.
SCENE_BODY = (
    "% The body is cold.\n"
    "- [Examine the body](autopsy) if medical >= 1\n"
    "- [Force the panel](panel_open) if engineering >= 1\n"
    "- [Cover the doorway](cover) if security >= 1\n"
    "- [Back out](corridor)\n"
)


def _scenes():
    """The shape dialogue_scenes() produces: key -> node."""
    def node(key, body):
        return {"key": key, "display_text": key, "description": body,
                "data": {"speaker": "outpost"}}
    return {
        "lab": node("lab", SCENE_BODY),
        "autopsy": node("autopsy", "% Phaser burn, close range.\n- [Report it](corridor)\n"),
        "panel_open": node("panel_open", "% The relay is fused.\n- [Report it](corridor)\n"),
        "cover": node("cover", "% Nothing in the corridor.\n- [Report it](corridor)\n"),
        # A scene with no choices at all - the end of a branch.
        "corridor": node("corridor", "% You regroup.\n"),
    }


class _AwayBase(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        SpaceObject.clear()
        # Snapshot rather than clear, for the reason test_amd_dialogue records: the library
        # registers its own resolver, and wiping it leaves later tests running without one -
        # which passes alone and fails under discover.
        self._prev_metric = D._METRIC_RESOLVER
        A.away_clear()
        A.away_metric_install()
        self.scenes = _scenes()
        self.doc = lifeform_spawn("Dr Sorel", "terran_female", "away,medical")
        self.eng = lifeform_spawn("Chief Ruiz", "terran_male", "away,engineering")
        self.sec = lifeform_spawn("Ensign Vale", "terran_male", "away,security")

    def tearDown(self):
        A.away_clear()
        D.dialogue_set_metric_resolver(self._prev_metric)

    def _labels(self, client_id):
        return [c.label for c in A.away_choices(client_id)]


class AwayTeamTests(_AwayBase):
    def test_assign_and_lookup(self):
        A.away_assign(101, self.doc)
        A.away_assign(102, self.eng)
        self.assertEqual(A.away_me(101), self.doc.id)
        self.assertEqual(A.away_me(102), self.eng.id)
        self.assertIsNone(A.away_me(999))
        self.assertEqual(A.away_team(), {self.doc.id, self.eng.id})
        self.assertEqual(A.away_client_of(self.eng), 102)

    def test_assign_none_releases(self):
        A.away_assign(101, self.doc)
        self.assertIsNone(A.away_assign(101, None))
        self.assertIsNone(A.away_me(101))
        self.assertEqual(A.away_team(), set())

    def test_team_is_a_set_not_a_list(self):
        # Two clients watching one character must not make that character appear twice.
        A.away_assign(101, self.doc)
        A.away_assign(102, self.doc)
        self.assertEqual(A.away_team(), {self.doc.id})
        self.assertEqual(A.away_team_count(), 2)        # two CLIENTS, one character


class AwayJobTests(_AwayBase):
    """What a screen may print as a character's job."""

    def test_machinery_is_not_a_job(self):
        # `ultra_beam` is added the moment a lifeform has no host - i.e. to every away-team
        # member - and the AMD loader stamps `amd_lifeform:<key>`. Neither describes anyone.
        A.away_assign(101, self.doc)
        jobs = A.away_jobs(self.doc)
        self.assertIn("medical", jobs)
        self.assertNotIn("ultra_beam", jobs)
        self.assertNotIn("away", jobs)
        self.assertNotIn("lifeform", jobs)
        for j in jobs:
            self.assertNotIn(":", j, f"{j!r} is namespaced bookkeeping, not a job")

    def test_the_filter_has_something_to_remove(self):
        # The guard on the guard: if a lifeform ever stops carrying machinery, the test
        # above passes while measuring nothing.
        from sbs_utils.procedural.roles import get_role_list
        raw = get_role_list(self.doc.id)
        self.assertGreater(len(raw), len(A.away_jobs(self.doc)),
                           "nothing was filtered - the fixture no longer carries machinery")

    def test_order_is_stable(self):
        # Roles are a SET, so unsorted the same character reads differently per repaint.
        both = lifeform_spawn("Dr Kell", "terran_fluid", "away,surgery,xenobiology")
        self.assertEqual(A.away_jobs(both), ["surgery", "xenobiology"])
        self.assertEqual(A.away_jobs(both), A.away_jobs(both))

    def test_job_text_is_one_line(self):
        self.assertEqual(A.away_job_text(self.eng), "engineering")
        blank = lifeform_spawn("Nobody", "terran", "away")
        self.assertEqual(A.away_job_text(blank), "")
        self.assertEqual(A.away_job_text(blank, default="watching"), "watching")


class AwayChoiceFilteringTests(_AwayBase):
    """The whole feature: one scene, different menus."""

    def setUp(self):
        super().setUp()
        A.away_assign(101, self.doc)
        A.away_assign(102, self.eng)
        A.away_assign(103, self.sec)
        A.away_scene_begin(self.scenes, "lab", speaker="outpost")

    def test_each_character_gets_a_different_menu(self):
        self.assertEqual(self._labels(101), ["Examine the body", "Back out"])
        self.assertEqual(self._labels(102), ["Force the panel", "Back out"])
        self.assertEqual(self._labels(103), ["Cover the doorway", "Back out"])

    def test_the_menus_actually_differ(self):
        # Stated separately from the exact contents: if guard evaluation ever stopped seeing
        # the character, every list above would still be a list - just the same one.
        self.assertNotEqual(self._labels(101), self._labels(102))
        self.assertNotEqual(self._labels(102), self._labels(103))

    def test_a_client_with_no_character_gets_only_ungated_choices(self):
        self.assertEqual(self._labels(777), ["Back out"])

    def test_a_guard_is_case_and_space_insensitive(self):
        # Authors write guards in prose and will capitalize. has_role normalizes both
        # sides, so this holds - pinned here because a guard that silently never opens
        # looks like a writing mistake rather than a lookup one.
        body = "% Cold.\n- [Look](corridor) if  Medical  >= 1\n"
        scenes = {"lab": {"key": "lab", "display_text": "lab", "description": body,
                          "data": {"speaker": "outpost"}},
                  "corridor": self.scenes["corridor"]}
        A.away_scene_begin(scenes, "lab", speaker="outpost")
        self.assertEqual(self._labels(101), ["Look"])
        self.assertEqual(self._labels(102), [])

    def test_a_character_with_two_roles_gets_both(self):
        medic_eng = lifeform_spawn("Dr Kell", "terran_fluid", "away,medical,engineering")
        A.away_assign(104, medic_eng)
        self.assertEqual(self._labels(104),
                         ["Examine the body", "Force the panel", "Back out"])


class AwaySharedLineTests(_AwayBase):
    def test_every_console_is_told_the_same_line(self):
        # dialogue_pick_line is RANDOM. Picked per console it would tell each of them a
        # different story; picked once at the beat it cannot.
        scenes = dict(self._many_line_scene())
        A.away_assign(101, self.doc)
        A.away_assign(102, self.eng)
        seen = set()
        for _ in range(25):
            A.away_scene_begin(scenes, "noisy", speaker="outpost")
            line = A.away_line()
            self.assertEqual(line, A.away_line())     # same answer twice, same beat
            seen.add(line)
        self.assertGreater(len(seen), 1, "fixture should have several variants")

    def _many_line_scene(self):
        body = "".join(f"% Variant {i}.\n" for i in range(8)) + "- [Go](corridor)\n"
        return {"noisy": {"key": "noisy", "display_text": "noisy", "description": body,
                          "data": {"speaker": "outpost"}},
                "corridor": self.scenes["corridor"]}


class AwayArbitrationTests(_AwayBase):
    def setUp(self):
        super().setUp()
        A.away_assign(101, self.doc)
        A.away_assign(102, self.eng)
        A.away_scene_begin(self.scenes, "lab", speaker="outpost")

    def test_first_answer_wins_and_second_is_refused(self):
        seq = A.away_seq()
        self.assertTrue(A.away_answer(101, 0, seq))            # doctor examines the body
        self.assertEqual(A.away_scene(), "autopsy")
        # The engineer pressed in the same frame, carrying the seq they rendered with.
        self.assertFalse(A.away_answer(102, 0, seq))
        self.assertEqual(A.away_scene(), "autopsy")            # unmoved

    def test_seq_moves_on_every_beat(self):
        first = A.away_seq()
        A.away_answer(101, 0, first)
        self.assertNotEqual(A.away_seq(), first)

    def test_an_index_valid_for_someone_else_is_refused(self):
        # Index 0 is "Force the panel" for the engineer and "Examine the body" for the
        # doctor; the point is that each list is indexed against its OWN character.
        seq = A.away_seq()
        self.assertTrue(A.away_answer(102, 0, seq))
        self.assertEqual(A.away_scene(), "panel_open")

    def test_out_of_range_is_refused(self):
        seq = A.away_seq()
        self.assertFalse(A.away_answer(101, 5, seq))
        self.assertFalse(A.away_answer(101, -1, seq))
        self.assertEqual(A.away_scene(), "lab")

    def test_answering_without_a_seq_still_works(self):
        # A caller that does not render buttons (a test, a script) may omit the token.
        self.assertTrue(A.away_answer(101, 0))
        self.assertEqual(A.away_scene(), "autopsy")

    def test_a_choice_with_no_target_ends_the_scene(self):
        A.away_answer(101, 0)                                  # -> autopsy
        self.assertTrue(A.away_answer(101, 0))                 # -> corridor (no choices)
        self.assertEqual(A.away_scene(), "corridor")
        self.assertTrue(A.away_is_open())
        self.assertEqual(A.away_choices(101), [])

    def test_a_missing_target_closes_rather_than_hangs(self):
        scenes = {"start": {"key": "start", "display_text": "s",
                            "description": "% Hi.\n- [Onward](nowhere)\n",
                            "data": {"speaker": "outpost"}}}
        A.away_scene_begin(scenes, "start", speaker="outpost")
        self.assertTrue(A.away_answer(101, 0))
        self.assertIsNone(A.away_scene())
        self.assertFalse(A.away_is_open())

    def test_answering_a_closed_scene_is_refused(self):
        A.away_scene_end()
        self.assertFalse(A.away_answer(101, 0))


class AwayMetricCompositionTests(_AwayBase):
    """The resolver is ONE global and Open Universe already claims it at import time."""

    def test_unknown_names_fall_through_to_the_incumbent(self):
        A.away_metric_uninstall()
        D.dialogue_set_metric_resolver(lambda name, agent, spk: 42 if name == "credits" else 0)
        A.away_metric_install()
        # ours
        self.assertTrue(D.dialogue_guard_ok("medical >= 1", self.doc.id, None))
        # theirs, still reachable
        self.assertTrue(D.dialogue_guard_ok("credits >= 40", self.doc.id, None))

    def test_a_role_the_character_lacks_still_falls_through(self):
        A.away_metric_uninstall()
        D.dialogue_set_metric_resolver(lambda name, agent, spk: 7)
        A.away_metric_install()
        # "medical" is a role the ENGINEER lacks, so it must reach the incumbent rather
        # than short-circuit to 0 - a mission may mean something else by that word.
        self.assertEqual(D._METRIC_RESOLVER("medical", self.eng.id, None), 7)

    def test_install_is_idempotent_and_does_not_recurse(self):
        self.assertFalse(A.away_metric_install())      # already installed by setUp
        # If a second install had chained the resolver to itself, an unowned name would
        # recurse forever rather than answer.
        self.assertEqual(D._METRIC_RESOLVER("nothing_owns_this", self.doc.id, None), 0)

    def test_uninstall_restores_the_previous_resolver(self):
        A.away_metric_uninstall()
        sentinel = lambda name, agent, spk: 5
        D.dialogue_set_metric_resolver(sentinel)
        A.away_metric_install()
        self.assertIsNot(D._METRIC_RESOLVER, sentinel)
        A.away_metric_uninstall()
        self.assertIs(D._METRIC_RESOLVER, sentinel)


class AwayResetTests(_AwayBase):
    def test_clear_empties_the_ledger_probes(self):
        A.away_assign(101, self.doc)
        A.away_scene_begin(self.scenes, "lab", speaker="outpost")
        self.assertEqual(A.away_team_count(), 1)
        self.assertEqual(A.away_scene_count(), 1)
        A.away_clear()
        self.assertEqual(A.away_team_count(), 0)
        self.assertEqual(A.away_scene_count(), 0)

    def test_clear_hands_the_resolver_back(self):
        sentinel = self._prev_metric
        A.away_clear()
        self.assertIs(D._METRIC_RESOLVER, sentinel)

    def test_probes_are_registered_on_the_reset_ledger(self):
        # An unregistered container is invisible to the restart soak, which is how
        # "works on run 1, broken on run 2" gets shipped.
        from sbs_utils.handlerhooks import _RESET_PROBES
        self.assertIn("away team", _RESET_PROBES)
        self.assertIn("away scene", _RESET_PROBES)


class AwayMastRegistrationTests(unittest.TestCase):
    def test_away_is_callable_from_mast(self):
        # A procedural module is invisible to MAST until it is listed in
        # mast_sbs_procedural.py. Unit tests and headless both pass without it; the
        # engine dies with NameError. Same guard as test_fleet_tables.
        import sbs_utils.mast_sbs.mast_sbs_procedural  # noqa: F401
        from sbs_utils.mast.mast_globals import MastGlobals
        for name in ("away_assign", "away_me", "away_choices", "away_answer",
                     "away_scene_begin", "away_seq", "away_line"):
            self.assertIn(name, MastGlobals.globals, f"{name} is not reachable from MAST")


# One room, three readings, and a door that opens once the party has three of them.
LEARN_FIELD = (
    "% Swept, and too quiet.\n"
    "- [Read the people](field_med) if medical >= 1 ; learn thin\n"
    "- [Read the power spur](field_eng) if engineering >= 1 ; learn cold\n"
    "- [Count the doors](field_sec) if security >= 1 ; learn watched\n"
    "- [Open the shed](shed) if learned >= 3\n"
    "- [Walk on](field)\n"
)


def _learn_scenes():
    def node(key, body):
        return {"key": key, "display_text": key, "description": body,
                "data": {"speaker": "bel"}}
    return {
        "field": node("field", LEARN_FIELD),
        "field_med": node("field_med", "% A tremor in every hand.\n- [Say it](field)\n"),
        "field_eng": node("field_eng", "% Drawing for forty.\n- [Say it](field)\n"),
        "field_sec": node("field_sec", "% They lock from outside.\n- [Say it](field)\n"),
        "shed": node("shed", "% Thirty of them, asleep.\n- [Oh]()\n"),
    }


# Consoles are plain ints here, as everywhere else in this file.
LEARN_CID = 201


class AwayLearnTests(_AwayBase):
    """`; learn cold` on a choice, `if learned >= 3` on the one it unlocks.

    The mission's first instinct is a signal per fact, a route per signal, and a role
    granted at the threshold - four moving parts across three files to say "they worked
    something out". Worse, it CANNOT dedupe: a `signal` outcome carries nothing but its
    name, and by the time a route sees it the choice that fired it is gone, so a reading
    the party walks back into counts twice and the door opens early.
    """

    def setUp(self):
        super().setUp()
        self.scenes = _learn_scenes()

    def _answer(self, who, label):
        A.away_assign(LEARN_CID, who)
        labels = self._labels(LEARN_CID)
        self.assertIn(label, labels, f"{label} not offered: {labels}")
        return A.away_answer(LEARN_CID, labels.index(label), A.away_seq())

    def test_nothing_is_known_at_the_start(self):
        A.away_scene_begin(self.scenes, "field")
        self.assertEqual(A.away_learned(), 0)
        self.assertEqual(A.away_facts(), [])

    def test_a_reading_is_recorded_by_name(self):
        A.away_scene_begin(self.scenes, "field")
        self._answer(self.eng, "Read the power spur")
        self.assertEqual(A.away_facts(), ["cold"])
        self.assertEqual(A.away_learned("cold"), 1)
        self.assertEqual(A.away_learned("thin"), 0)

    def test_the_same_reading_twice_counts_once(self):
        # THE REASON THIS IS NOT A SIGNAL. Every reading returns the party to the room it
        # came from, so walking back into one is the normal way to play, not an abuse.
        for _ in range(3):
            A.away_scene_begin(self.scenes, "field")
            self._answer(self.eng, "Read the power spur")
        self.assertEqual(A.away_learned(), 1)

    def test_the_gate_is_shut_until_enough_is_known(self):
        A.away_scene_begin(self.scenes, "field")
        A.away_assign(LEARN_CID, self.eng)
        self.assertNotIn("Open the shed", self._labels(LEARN_CID))

    def test_three_readings_open_it(self):
        for who, label in ((self.doc, "Read the people"),
                           (self.eng, "Read the power spur"),
                           (self.sec, "Count the doors")):
            A.away_scene_begin(self.scenes, "field")
            self._answer(who, label)
        A.away_scene_begin(self.scenes, "field")
        A.away_assign(LEARN_CID, self.eng)
        self.assertEqual(A.away_learned(), 3)
        self.assertIn("Open the shed", self._labels(LEARN_CID))

    def test_the_gate_belongs_to_the_PARTY_not_the_character(self):
        # Four people each holding a piece is the whole design. Were `learned` per
        # character, nobody would ever reach three and the door would never open.
        for who, label in ((self.doc, "Read the people"),
                           (self.eng, "Read the power spur"),
                           (self.sec, "Count the doors")):
            A.away_scene_begin(self.scenes, "field")
            self._answer(who, label)
        # Asked as the MEDIC, who personally read exactly one thing.
        A.away_scene_begin(self.scenes, "field")
        A.away_assign(LEARN_CID, self.doc)
        self.assertIn("Open the shed", self._labels(LEARN_CID))

    def test_a_role_guard_still_works_beside_it(self):
        A.away_scene_begin(self.scenes, "field")
        A.away_assign(LEARN_CID, self.doc)
        labels = self._labels(LEARN_CID)
        self.assertIn("Read the people", labels)
        self.assertNotIn("Read the power spur", labels)

    def test_a_reset_forgets_what_the_party_knew(self):
        A.away_scene_begin(self.scenes, "field")
        self._answer(self.eng, "Read the power spur")
        A.away_clear()
        self.assertEqual(A.away_learned(), 0)

    def test_learn_with_no_token_records_nothing(self):
        # An authoring slip (`; learn`) must not bank an empty fact that still counts.
        A._away_learn_outcome(None, None, ())
        self.assertEqual(A.away_learned(), 0)

    def test_a_multi_word_fact_is_one_fact(self):
        A._away_learn_outcome(None, None, ("the", "power", "spur"))
        self.assertEqual(A.away_facts(), ["the power spur"])


if __name__ == "__main__":
    unittest.main()
