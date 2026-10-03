"""A boarding room is checked like any other scene, and a guard nobody can read is reported.

Found by writing the third boarding lesson - "everyone gets a menu" - and then making the
mistakes a new author makes. Thirteen of them; twelve linted clean.

The reason for most of the twelve was one gap. A room is a line and its ways out:

    ### [The Airlock](airlock)
    % The outer door was never sealed.

    - [Read the name tags](suits) if medical ; learn suits

It has no `---` fence, the kind of a record was resolved where its fence CLOSES, and so a
room had no kind at all. Every dialogue check asks "is this dialogue" first, and walked
past it: `; lern suits` in a room was clean while the same typo in a hail was reported.

The rest were conditions the game cannot read. A guard that is neither a name nor
`name op number` is answered False every time, so the choice is never offered and nothing
says why.

    python -m unittest tests.test_amd_lint_boarding_rooms
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural import boarding  # noqa: F401 - registers the `learn` verb
from sbs_utils.procedural.amd_core import parse
from sbs_utils.procedural.amd_lint import amd_lint

MISSION = """# [Sample Mission](sample_mission)

## [Scenes](boarding)

### [The Airlock](airlock)
% The outer door was never sealed.

- [Read the name tags on the suits](suits) if medical ; learn suits
- [Go forward, to the bridge](bridge)
- [Return to the ship]()

### [Six Suits](suits)
% Six suits, six names.

- [Step back](airlock)

### [The Bridge](bridge)
%{learned < 1} The log is locked.
%{learned >= 1} The log is open.

- [Answer the log](airlock) if learned >= 1
- [Return to the ship]()
"""


def _codes(text):
    return [f.code for f in amd_lint(content=text, cross_file=False)]


def _swap(old, new):
    assert MISSION.count(old) == 1, old
    return MISSION.replace(old, new)


class ARoomHasAKindTests(unittest.TestCase):
    def kinds(self, text):
        return {n.key: n.kind for n in parse(text).nodes}

    def test_a_room_with_no_fence_is_dialogue(self):
        kinds = self.kinds(MISSION)
        for room in ("airlock", "suits", "bridge"):
            self.assertEqual(kinds[room], "dialogue", room)

    def test_the_section_can_be_keyed_scenes(self):
        kinds = self.kinds(MISSION.replace("](boarding)", "](scenes)"))
        self.assertEqual(kinds["airlock"], "dialogue")

    def test_a_record_with_no_fence_takes_its_sections_kind(self):
        kinds = self.kinds("# [M](m)\n\n## [Quests](quests)\n\n### [Find it](find)\nGo and look.\n")
        self.assertEqual(kinds["find"], "quest")

    def test_an_unnamed_section_still_types_nothing(self):
        kinds = self.kinds("# [M](m)\n\n## [Notes](notes)\n\n### [A thought](thought)\nProse.\n")
        self.assertIsNone(kinds["thought"])

    def test_a_fence_still_decides(self):
        text = MISSION.replace("### [Six Suits](suits)\n", "### [Six Suits](suits)\n---\nItem\n---\n")
        self.assertEqual(self.kinds(text)["suits"], "item")


class TheLessonsFileIsCleanTests(unittest.TestCase):
    def test_nothing_is_reported(self):
        self.assertEqual(_codes(MISSION), [])

    def test_guards_that_take_an_argument_are_readable(self):
        # What shipped missions write: a word and an argument, with or without a number.
        text = _swap("if medical ; learn suits",
                     "if skill comms >= 3 ; learn suits")
        text = text.replace("if learned >= 1\n", "if holding coil\n")
        self.assertNotIn("unreadable-guard", _codes(text))

    def test_every_operator_is_readable(self):
        for op in (">=", "<=", "==", "!=", ">", "<"):
            text = _swap("if learned >= 1\n", "if learned %s 1\n" % op)
            self.assertNotIn("unreadable-guard", _codes(text), op)

    def test_a_gate_with_no_percent_is_readable(self):
        self.assertEqual(_codes(_swap("%{learned < 1}", "{learned < 1}")), [])


class MistakesInARoomAreReportedTests(unittest.TestCase):
    def test_a_misspelled_verb(self):
        self.assertIn("unknown-outcome-verb", _codes(_swap("; learn suits", "; lern suits")))

    def test_learn_with_no_fact(self):
        self.assertIn("learn-nothing", _codes(_swap("; learn suits", "; learn")))

    def test_the_operator_backwards(self):
        self.assertIn("unreadable-guard",
                      _codes(_swap("if learned >= 1\n", "if learned => 1\n")))

    def test_a_comma_where_the_semicolon_goes(self):
        codes = _codes(_swap("if medical ; learn suits", "if medical, learn suits"))
        self.assertIn("unreadable-guard", codes)

    def test_the_condition_after_the_outcome(self):
        codes = _codes(_swap("if medical ; learn suits", "; learn suits if medical"))
        self.assertIn("guard-after-outcome", codes)

    def test_a_gate_the_game_cannot_read(self):
        self.assertIn("unreadable-guard", _codes(_swap("%{learned < 1}", "%{learned =< 1}")))

    def test_the_finding_is_on_the_line_that_is_wrong(self):
        text = _swap("if learned >= 1\n", "if learned => 1\n")
        found = [f for f in amd_lint(content=text, cross_file=False)
                 if f.code == "unreadable-guard"]
        self.assertEqual(len(found), 1)
        want = text.splitlines().index("- [Answer the log](airlock) if learned => 1") + 1
        self.assertEqual(found[0].line, want)


if __name__ == "__main__":
    unittest.main()
