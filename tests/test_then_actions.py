"""`Then:` takes several actions (procedural/amd_quest.py, quest_driver.py, amd_lint.py).

Both ways: a comma list (`Then: reveal next, learn the ledger page`) and repeated `Then:`
lines. All of them run, in the order written. A one-action line is read EXACTLY as it
always was - the same keys, the same values - including a bare value, which is a reveal.

Driven through the real readers (`amd_quest_data`, `amd_document` + `amd_mission_data`),
`quest_grant_amd` and `quest_mark_complete`, and `amd_lint`.

    python -m unittest tests.test_then_actions
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401
from cosmos_dev.mock import sbs as mock_sbs
from tests.reset_helper import reset_mock

from sbs_utils.agent import Agent
from sbs_utils.procedural import boarding as B
from sbs_utils.procedural.amd_doc import amd_document, amd_section
from sbs_utils.procedural.amd_lint import amd_lint
from sbs_utils.procedural.amd_mission import amd_mission_data
from sbs_utils.procedural.amd_quest import amd_quest_data, amd_then_actions
from sbs_utils.procedural.quest import QuestState, quest_get_data, quest_get_state
from sbs_utils.procedural.quest_driver import quest_grant_amd, quest_mark_complete
from sbs_utils.procedural.signal import signal_observe, signal_unobserve

THEN_MISSION = """# [Mission](mission)

## [Quests](quests)

### [Find the Ledger](find_ledger)
---
Beat
Done when: signal ledger_found
{then}
---
The page is in the purser's safe.

### [Report Home](next)
---
Beat
Starts when: revealed
Done when: signal home
---

### [The Long Way](first_contact)
---
Arc
Starts when: at once
---

#### [Study It](study)
---
Beat
Starts when: revealed
Done when: signal studied
---

### [Wait For It](waits)
---
Beat
Starts when: at once
Done when: signal page_read
---
"""


def _then_codes(text):
    return [f.code for f in amd_lint(content=text, cross_file=False)]


class ThenReadTests(unittest.TestCase):
    """What the game's reader makes of a `Then:` line."""

    def test_ONE_ACTION_is_read_exactly_as_it_always_was(self):
        for line, want in (
                ("Then: reveal next_step", {"reveal": "next_step"}),
                ("Then: signal alarm", {"signal": "alarm"}),
                ("Then: learn ledger page", {"learn": "ledger page"}),
                # A bare value is a reveal of that key.
                ("Then: step_two", {"reveal": "step_two"}),
                # An unknown verb falls through whole (and lint says so).
                ("Then: hail brief", {"reveal": "hail brief"}),
                # A path, with spaces round the slash and a slash in front.
                ("Then: reveal first_contact / study", {"reveal": "first_contact/study"}),
                ("Then: reveal /salvage/home", {"reveal": "salvage/home"}),
                ("Then: Reveal next_step", {"Reveal".lower(): "next_step"}),
        ):
            with self.subTest(line=line):
                self.assertEqual(amd_quest_data(line), want)

    def test_a_comma_list_is_every_action_in_order(self):
        data = amd_quest_data("Then: reveal next, learn the ledger page")
        self.assertEqual(data["then"], [["reveal", "next"], ["learn", "the ledger page"]])
        # The old keys still say the first of each, for anything that reads them.
        self.assertEqual(data["reveal"], "next")
        self.assertEqual(data["learn"], "the ledger page")

    def test_repeated_lines_are_every_action_in_order(self):
        data = amd_quest_data("Then: learn the ledger page\nThen: reveal next\n"
                              "Then: signal page_read")
        self.assertEqual(data["then"], [["learn", "the ledger page"], ["reveal", "next"],
                                        ["signal", "page_read"]])

    def test_both_ways_at_once_and_two_of_one_verb(self):
        data = amd_quest_data("Then: reveal next, reveal first_contact / study\n"
                              "Then: signal a, signal b")
        self.assertEqual(data["then"], [["reveal", "next"], ["reveal", "first_contact/study"],
                                        ["signal", "a"], ["signal", "b"]])
        self.assertEqual(data["reveal"], "next")
        self.assertEqual(data["signal"], "a")

    def test_a_comma_is_the_only_separator(self):
        self.assertEqual(amd_then_actions("learn the ledger page"),
                         [("learn", "the ledger page")])
        self.assertEqual(amd_then_actions("reveal first_contact/study , signal x,"),
                         [("reveal", "first_contact/study"), ("signal", "x")])
        # A bare key in a list is a reveal of it, as it is alone.
        self.assertEqual(amd_then_actions("step_two, learn it"),
                         [("reveal", "step_two"), ("learn", "it")])
        self.assertEqual(amd_then_actions(""), [])

    def test_a_second_then_does_not_touch_any_other_repeated_field(self):
        # Every other field: the last line is still the one that counts.
        data = amd_quest_data("Tier: 1\nTier: 2\nThen: reveal a\nThen: reveal b")
        self.assertEqual(data["tier"], 2)


class ThenRunsTests(unittest.TestCase):
    def setUp(self):
        reset_mock(mock_sbs)
        mock_sbs.resume_sim()
        self.heard = []
        signal_observe(self._obs)
        self.addCleanup(signal_unobserve, self._obs)

    def _obs(self, name, data):
        self.heard.append((name, dict(data) if isinstance(data, dict) else data))

    def grant(self, then):
        doc = amd_document(THEN_MISSION.replace("{then}", then),
                           data_parser=amd_mission_data)
        quest_grant_amd(Agent.SHARED_ID, amd_section(doc, "quests"))

    def state(self, key):
        return quest_get_state(Agent.SHARED_ID, key)

    def test_reveal_and_learn_on_one_line_both_happen(self):
        """`agent_c56_report.md` D31: a spine step can teach a fact."""
        self.grant("Then: reveal next, learn the ledger page")
        self.assertEqual(self.state("next"), QuestState.SECRET)
        quest_mark_complete(Agent.SHARED_ID, "find_ledger")
        self.assertNotEqual(self.state("next"), QuestState.SECRET)
        self.assertEqual(B.boarding_facts(""), ["the ledger page"])

    def test_two_then_lines_both_happen(self):
        """D31, the other half: two lines - the first was lost."""
        self.grant("Then: reveal next\nThen: learn the ledger page")
        quest_mark_complete(Agent.SHARED_ID, "find_ledger")
        self.assertNotEqual(self.state("next"), QuestState.SECRET)
        self.assertEqual(B.boarding_facts(""), ["the ledger page"])

    def test_three_verbs_two_reveals_and_a_path_in_the_order_written(self):
        self.grant("Then: signal page_read, reveal next\n"
                   "Then: reveal first_contact / study, learn the ledger page")
        self.assertEqual(self.state("first_contact/study"), QuestState.SECRET)
        quest_mark_complete(Agent.SHARED_ID, "find_ledger")
        self.assertNotEqual(self.state("next"), QuestState.SECRET)
        self.assertNotEqual(self.state("first_contact/study"), QuestState.SECRET)
        self.assertEqual(B.boarding_facts(""), ["the ledger page"])
        # The signal went out raw AND as a quest milestone, which is what another step's
        # `Done when: signal page_read` hears.
        self.assertIn("page_read", [n for n, _ in self.heard])
        self.assertIn("page_read", [d.get("SIGNAL_NAME") for n, d in self.heard
                                    if n == "quest_signal"])
        # ... before the step was announced as done, as a lone `Then: signal` is.
        names = [n for n, d in self.heard
                 if n == "page_read" or (n == "quest_succeeded"
                                         and d.get("QUEST_ID") == "find_ledger")]
        self.assertEqual(names[:1], ["page_read"])

    def test_one_action_still_runs_as_it_did(self):
        self.grant("Then: reveal next")
        self.assertNotIn("then", quest_get_data(Agent.SHARED_ID, "find_ledger"))
        quest_mark_complete(Agent.SHARED_ID, "find_ledger")
        self.assertNotEqual(self.state("next"), QuestState.SECRET)
        self.assertEqual(B.boarding_facts(""), [])


class ThenLintTests(unittest.TestCase):
    def lint(self, then):
        return amd_lint(content=THEN_MISSION.replace("{then}", then), cross_file=False)

    def codes(self, then):
        return [f.code for f in self.lint(then)]

    def test_repeated_then_is_no_longer_a_finding(self):
        codes = self.codes("Then: reveal next\nThen: learn the ledger page")
        self.assertNotIn("repeated-then", codes)
        self.assertNotIn("dangling-reveal", codes)
        self.assertNotIn("unknown-then-verb", codes)

    def test_a_comma_list_is_clean(self):
        codes = self.codes("Then: reveal next, learn the ledger page, signal page_read")
        for code in ("dangling-reveal", "unknown-then-verb", "repeated-then",
                     "never-revealed"):
            self.assertNotIn(code, codes)

    def test_each_reveal_is_judged(self):
        found = [f for f in self.lint("Then: reveal next, reveal nxet, learn it")
                 if f.code == "dangling-reveal"]
        self.assertEqual(len(found), 1)
        self.assertIn("`nxet`", found[0].message)
        self.assertNotIn("nxet,", found[0].message)
        # ... on a second line too, and reported on THAT line.
        found = [f for f in self.lint("Then: reveal next\nThen: reveal nxet")
                 if f.code == "dangling-reveal"]
        self.assertEqual(len(found), 1)
        first = [f for f in self.lint("Then: reveal nxet") if f.code == "dangling-reveal"]
        self.assertEqual(found[0].line, first[0].line + 1)

    def test_each_verb_is_judged(self):
        found = [f for f in self.lint("Then: reveal next, hail brief")
                 if f.code == "unknown-then-verb"]
        self.assertEqual(len(found), 1)
        self.assertIn("hail", found[0].message)
        self.assertNotIn("unknown-then-verb", self.codes("Then: reveal next, learn a b c"))
        # A lone bare value is a reveal and is not second-guessed, as before.
        self.assertNotIn("unknown-then-verb", self.codes("Then: next"))

    def test_a_reveal_in_a_list_still_reveals_for_never_revealed(self):
        """`never-revealed` needs the mission's story; ask the rule itself."""
        from sbs_utils.procedural import amd_core
        from sbs_utils.procedural.amd_lint import amd_lint_never_revealed
        index = {"quoted_words": set()}
        for then, expect in (("Then: learn it, reveal next", False),
                             ("Then: learn it", True)):
            text = THEN_MISSION.replace("{then}", then)
            found = [f for f in amd_lint_never_revealed(amd_core.parse(text), text, index)
                     if "Report Home" in f.message]
            self.assertEqual(bool(found), expect, then)

    def test_a_fact_taught_in_a_list_is_known_to_a_guard(self):
        text = THEN_MISSION.replace("{then}", "Then: reveal next, learn the ledger page") + """
## [Dialogue](dialogue)

### [Quill](quill_later)
---
Speaker: quill
When: hail
---
% Well?

- [We read it.]() if learned the ledger page
"""
        self.assertNotIn("guard-learned-shape", _then_codes(text))
        self.assertNotIn("guard-learned-unknown", _then_codes(text))


if __name__ == "__main__":
    unittest.main()
