"""Incoming hails, AMD layer: the DIALOGUE schema fields, the `amd_lint_hails` pass and
the LSP help for both. Phase 1 - pure, no engine, no GUI.

    python -m unittest tests.test_hail_amd

AMD sources here are PYTHON STRINGS rather than checked-in .amd files, for the reason
tests/amd_corpus.py gives: core.autocrlf rewrites a checked-in text file's line endings,
so a fixture's bytes would be decided by the developer's git config.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural import amd_lsp as L
from sbs_utils.procedural import amd_dialogue as D
from sbs_utils.procedural.amd_core import parse
from sbs_utils.procedural.amd_lint import (
    amd_lint_hails, amd_lint_field_values, ERROR, WARNING)
from sbs_utils.procedural.amd_schema import field_schema, enum_values

NL = chr(10)


def _scene(fence_lines, body_lines=()):
    """One dialogue scene.

    `Speaker:` is ALWAYS present, and that is load-bearing: kind is inferred by field
    scoring, and QUEST declares `When:` too - a fence of `When: hail` alone scores as a
    quest, and the hail pass then correctly ignores it. Every real scene names a speaker.
    """
    return NL.join(["# [S](s)", "---", "Speaker: ashfang"]
                   + list(fence_lines) + ["---"] + list(body_lines) + [""])


def _codes(src):
    return [f.code for f in amd_lint_hails(parse(src))]


class HailSchemaTests(unittest.TestCase):
    def test_presentation_is_a_closed_enum_of_the_three_forms(self):
        self.assertEqual(enum_values("Presentation", "dialogue"),
                         ["portrait", "still", "orbit"])

    def test_when_is_OPEN_so_the_shipped_corpus_gains_no_finding(self):
        # This is the whole backward-compatibility mechanism: enum_values() returns
        # None for an open enum, so amd_lint_field_values skips it exactly as it
        # skipped text(). If this ever closes, every `When:` in the corpus lights up.
        self.assertIsNone(enum_values("When", "dialogue"))
        self.assertTrue(field_schema("When", "dialogue").get("open"))

    def test_authored_aliases_resolve(self):
        for alias in ("Presentation", "Shot", "Form"):
            self.assertEqual(field_schema(alias, "dialogue").get("type"), "enum", alias)
        for alias in ("Backdrop", "Still"):
            self.assertEqual(field_schema(alias, "dialogue").get("type"), "text", alias)

    def test_subject_is_late_resolved_text_not_a_reference(self):
        # An orbit films a ship that is usually spawned at runtime, so it does not
        # exist when the .amd loads. ref("node") would make lint dangle on every
        # legitimate role-based subject. Same call CUTSCENE already makes.
        self.assertEqual(field_schema("Subject", "dialogue").get("type"), "text")
        self.assertEqual(field_schema("Subject", "cutscene").get("type"), "text")

    def test_enum_honors_its_hint(self):
        # enum() accepted `hint=` and silently discarded it, so `When:` and `Align:`
        # had no hover text at all. Regression guard for that fix.
        self.assertIn("hail", field_schema("When", "dialogue").get("hint", ""))
        self.assertTrue(field_schema("Align", "cutscene").get("hint"))


class HailLintTests(unittest.TestCase):
    def test_orbit_without_a_subject_is_an_error(self):
        src = _scene(["When: hail", "Presentation: orbit"], ["% hi", "- [a](x)"])
        self.assertIn("hail-missing-subject", _codes(src))
        self.assertEqual(amd_lint_hails(parse(src))[0].severity, ERROR)

    def test_orbit_with_a_subject_is_clean(self):
        self.assertEqual(_codes(_scene(
            ["When: hail", "Presentation: orbit", "Subject: raider_lead"],
            ["% hi", "- [a](x)"])), [])

    def test_still_without_a_backdrop_is_an_error(self):
        src = _scene(["When: hail", "Presentation: still"], ["% hi", "- [a](x)"])
        self.assertIn("hail-missing-backdrop", _codes(src))
        self.assertEqual(amd_lint_hails(parse(src))[0].severity, ERROR)

    def test_the_aliases_satisfy_the_same_checks(self):
        self.assertEqual(_codes(_scene(
            ["When: hail", "Shot: still", "Still: nebula_wide"], ["% hi"])), [])

    def test_a_fifth_UNGUARDED_choice_can_never_be_pressed(self):
        body = ["% hi"] + ["- [c%d](x)" % i for i in range(5)]
        src = _scene(["When: hail"], body)
        found = amd_lint_hails(parse(src))
        self.assertEqual([f.code for f in found], ["hail-too-many-choices"])
        self.assertEqual(found[0].severity, WARNING)
        # It points at the choice that is unreachable, not at the heading.
        self.assertEqual(src.split(NL)[found[0].line - 1].strip(), "- [c4](x)")

    def test_guarded_choices_are_the_authors_own_business(self):
        body = ["% hi", "- [a](x)", "- [b](x)", "- [c](x)",
                "- [d](x) if fearsome > 10", "- [e](x) if credits >= 5"]
        self.assertEqual(_codes(_scene(["When: hail"], body)), [])

    def test_a_hail_with_no_lines_and_no_choices_opens_and_closes(self):
        self.assertEqual(_codes(_scene(["When: hail"])), ["hail-empty"])

    def test_lines_without_choices_is_a_deliberate_one_way_message(self):
        # HereThereBeMonsters briefings are exactly this shape; it must never warn.
        self.assertEqual(_codes(_scene(
            ["When: hail", "Presentation: portrait"],
            ["% A briefing that closes on its own."])), [])

    def test_cues_and_directions_are_not_mistaken_for_silence(self):
        self.assertEqual(_codes(_scene(
            ["When: hail", "Presentation: orbit", "Subject: raider_lead"],
            ["@Ashfang (over)", "(cold)", "% You are a long way from friends.",
             "- [a](x)"])), [])

    def test_a_comms_scene_is_not_hail_checked(self):
        # `When: comms` is the shipped corpus. The choice cap and the empty check are
        # hail-only; a comms menu may have more buttons than an answer strip shows.
        body = ["% hi"] + ["- [c%d](x)" % i for i in range(6)]
        self.assertEqual(_codes(_scene(["When: comms"], body)), [])


class ShippedCorpusStaysQuietTests(unittest.TestCase):
    """The backward-compatibility gate. Every compat claim reduces to these."""

    def test_the_repo_dialogue_corpus_gains_no_hail_finding(self):
        from tests.amd_corpus import DIALOGUE
        self.assertEqual(amd_lint_hails(parse(DIALOGUE)), [])

    def test_when_comms_is_not_flagged_as_a_bad_enum_value(self):
        src = _scene(["When: comms"], ["% hi"])
        codes = [f.code for f in amd_lint_field_values(parse(src))]
        self.assertNotIn("unknown-enum-value", codes)

    def test_an_unlisted_when_value_still_parses(self):
        # `When:` is open on purpose - a mission may already use a word we never saw.
        src = _scene(["When: whenever_the_moon_is_full"], ["% hi"])
        self.assertNotIn("unknown-enum-value",
                         [f.code for f in amd_lint_field_values(parse(src))])

    def test_presentation_being_CLOSED_still_catches_a_typo(self):
        src = _scene(["When: hail", "Presentation: orbt"], ["% hi"])
        self.assertIn("unknown-enum-value",
                      [f.code for f in amd_lint_field_values(parse(src))])


class DialogueEntryTests(unittest.TestCase):
    """`When:` is what tells a hail entry from a selectable contact."""

    SCENES = {
        "ashfang_hail": {"data": {"speaker": "ashfang", "when": "hail"}},
        "ashfang_menu": {"data": {"speaker": "ashfang", "when": "comms"}},
        "ashfang_mid": {"data": {"speaker": "ashfang"}},
    }

    def test_hail_and_comms_entries_do_not_collide(self):
        self.assertEqual(D.dialogue_entry_for(self.SCENES, "ashfang", when="hail"),
                         "ashfang_hail")
        # The default is still comms, so every existing caller is unchanged.
        self.assertEqual(D.dialogue_entry_for(self.SCENES, "ashfang"), "ashfang_menu")

    def test_a_speaker_with_no_hail_entry_returns_none(self):
        self.assertIsNone(D.dialogue_entry_for(self.SCENES, "verdant", when="hail"))


class HailLspTests(unittest.TestCase):
    SRC = NL.join(["# [Ashfang Hails You](ashfang_hail)", "---", "Speaker: ashfang",
                   "When: ", "Presentation: ", "---", "% hi", ""])
    INDEX = {"known": {"ashfang", "ashfang_hail"}}

    def _complete(self, line, char):
        doc = parse(self.SRC, "x.amd")
        return L._completion(self.INDEX, doc, {"line": line, "character": char}, self.SRC)

    def _hover(self, line):
        doc = parse(self.SRC, "x.amd")
        h = L._hover(self.INDEX, doc, {"line": line, "character": 3}, self.SRC)
        return (h or {}).get("contents", {}).get("value", "")

    def test_an_open_enum_suggests_without_closing_the_list(self):
        r = self._complete(3, len("When: "))
        self.assertEqual([i["label"] for i in r["items"]], ["comms", "hail"])
        # isIncomplete keeps the client asking as a value outside the set is typed.
        self.assertTrue(r["isIncomplete"])

    def test_a_closed_enum_completes_and_stays_closed(self):
        r = self._complete(4, len("Presentation: "))
        self.assertEqual([i["label"] for i in r["items"]],
                         ["portrait", "still", "orbit"])
        self.assertFalse(r["isIncomplete"])

    def test_hover_tells_open_and_closed_enums_apart(self):
        self.assertIn("usually:", self._hover(3))
        self.assertIn("open", self._hover(3))
        self.assertIn("one of:", self._hover(4))


DOC_HAILS = """# [Mission](m)

## [Voices](voices)

### [DS 1 Briefing](ds1_brief)
---
Speaker: ds1
When: hail
---
The ambassador was taken.

- [Take the case]()

### [DS 1 Market](ds1_market)
---
Speaker: ds1
When: comms
---
What can we sell you?

## [Beats](beats)

### [Take the Case](brief)
---
Job
Action: {action}
---
"""


# Only what these tests are about. The fixture declares no cast section, so every
# scene also raises `dangling-speaker` - a true finding about the fixture and noise here.
HAIL_CODES = {"dangling-action-ref", "hail-unknown-scene", "hail-no-entry",
              "hail-speaker-mismatch", "hail-not-a-hail", "unknown-action-verb",
              "bad-action"}


def _hail_findings(action, codes=HAIL_CODES):
    from sbs_utils.procedural.amd_lint import amd_lint
    found = amd_lint(content=DOC_HAILS.replace("{action}", action), cross_file=False)
    return [f for f in found if f.code in codes]


class HailsVerbLintTests(unittest.TestCase):
    """`Action: X hails Y` is checkable before the mission ever runs, which is the
    whole reason the verb declares `operand_ref="node"`."""

    def test_a_correct_line_is_quiet(self):
        self.assertEqual(_hail_findings("DS1 hails ds1_brief"), [])

    def test_a_mistyped_scene_is_a_dangling_reference(self):
        codes = [f.code for f in _hail_findings("DS1 hails ds1_breif")]
        self.assertIn("dangling-action-ref", codes)

    def test_naming_a_record_that_is_not_a_scene(self):
        codes = [f.code for f in _hail_findings("DS1 hails brief")]
        self.assertIn("hail-unknown-scene", codes)

    def test_the_bare_form_needs_a_hail_entry(self):
        codes = [f.code for f in _hail_findings("nobody hails")]
        self.assertIn("hail-no-entry", codes)

    def test_the_bare_form_is_quiet_when_one_exists(self):
        self.assertEqual(_hail_findings("DS1 hails"), [])

    def test_a_speaker_mismatch_is_a_warning_not_an_error(self):
        found = _hail_findings("someone_else hails ds1_brief",
                               codes={"hail-speaker-mismatch"})
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].severity, "warning")

    def test_pushing_a_comms_scene_at_the_crew_is_flagged(self):
        codes = [f.code for f in _hail_findings("ds1 hails ds1_market")]
        self.assertIn("hail-not-a-hail", codes)


THEN_DOC = """# [Mission](m)

## [Beats](beats)

### [Step](step)
---
Job
Then: {then}
---
"""


class ThenVerbLintTests(unittest.TestCase):
    """`Then:` silently means `reveal <the whole line>` for anything it does not know,
    so an unrecognized verb is not ignored - it is misread."""

    @staticmethod
    def _lint(then):
        from sbs_utils.procedural.amd_lint import amd_lint
        doc = THEN_DOC.replace("{then}", then)
        return [f.code for f in amd_lint(content=doc, cross_file=False)]

    def test_reveal_and_signal_are_quiet(self):
        self.assertNotIn("unknown-then-verb", self._lint("reveal step_two"))
        self.assertNotIn("unknown-then-verb", self._lint("signal case_opened"))

    def test_an_unknown_verb_is_flagged(self):
        self.assertIn("unknown-then-verb", self._lint("hail ds1_brief"))

    def test_a_bare_single_token_is_still_a_reveal_target(self):
        # `Then: step_two` has always meant "reveal step_two" and must stay quiet.
        self.assertNotIn("unknown-then-verb", self._lint("step_two"))


OUTCOME_DOC = """# [Mission](m)

## [Voices](voices)

### [A Deal](deal)
---
Speaker: ds1
When: hail
---
Two hundred and it never happened.

- [Pay up]() ; {outcome}
- [Walk away]()
"""


class OutcomeVerbLintTests(unittest.TestCase):
    """An unregistered outcome verb is applied by nobody: `dialogue_apply` walks past
    it and the choice does everything except the thing written after the semicolon.

    The known set is the RUNTIME registry, so a mission's own word counts as soon as
    its module is loaded - which is the only reason this pass can exist without
    flagging every correct Open Universe file.
    """

    @staticmethod
    def _codes(outcome):
        from sbs_utils.procedural.amd_lint import amd_lint
        found = amd_lint(content=OUTCOME_DOC.replace("{outcome}", outcome),
                         cross_file=False)
        return [f.code for f in found]

    def setUp(self):
        # quest_driver registers accepts/completes/fails at import; without something
        # beyond the built-in `signal` the pass declines to judge at all.
        import sbs_utils.procedural.quest_driver  # noqa: F401

    def test_a_library_verb_is_quiet(self):
        self.assertNotIn("unknown-outcome-verb", self._codes("completes florbin/brief"))

    def test_the_built_in_signal_is_quiet(self):
        self.assertNotIn("unknown-outcome-verb", self._codes("signal case_opened"))

    def test_a_typo_is_flagged(self):
        self.assertIn("unknown-outcome-verb", self._codes("completez florbin/brief"))

    def test_a_registered_mission_verb_is_quiet(self):
        from sbs_utils.procedural.amd_dialogue import (dialogue_register_outcome,
                                                       _OUTCOME_HANDLERS)
        prev = dict(_OUTCOME_HANDLERS)
        dialogue_register_outcome("costs", lambda a, s, t: True)
        try:
            self.assertNotIn("unknown-outcome-verb", self._codes("costs 200 credits"))
        finally:
            _OUTCOME_HANDLERS.clear()
            _OUTCOME_HANDLERS.update(prev)

    def test_it_declines_to_judge_with_nothing_but_the_builtin(self):
        # A bare-file lint that has not loaded a mission cannot tell a typo from a word
        # it simply has not met, and a linter that flags correct files gets ignored.
        from sbs_utils.procedural.amd_dialogue import _OUTCOME_HANDLERS
        prev = dict(_OUTCOME_HANDLERS)
        _OUTCOME_HANDLERS.clear()
        try:
            self.assertNotIn("unknown-outcome-verb", self._codes("costs 200 credits"))
        finally:
            _OUTCOME_HANDLERS.update(prev)


if __name__ == "__main__":
    unittest.main()
