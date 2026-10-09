"""Campaign facts: what the crew learned on the bridge is known everywhere, and is kept.

A boarding party's facts belong to the PLACE they were learned in. A hail answered on the
bridge has no place, so `; learn manifest` there files the fact under the campaign - and
so does a quest step's `Then: learn manifest`. What this file pins:

* a fact learned in a real bridge hail is asked for by name in a later hail;
* the NAMED guard (`if learned manifest`) asked inside an away site also sees a campaign
  fact; the COUNT (`if learned >= 2`) is still the place's alone;
* `Then: learn <fact>` on a quest step is read, runs on completion, and is a campaign
  fact; `Then:` still takes `reveal` and `signal`;
* a saved game gets every place's facts from the state provider and hands them back,
  REPLACING what is known;
* `sbs lint` knows `Then: learn`, a fact learned in ANOTHER file of the mission, and the
  quest field `Was:`.

Driven through the real readers, `dialogue_register_scenes`, the hail path
(`hail_offer` / `hail_accept` / `hail_answer`), `boarding_visit` / `boarding_answer`,
`quest_grant_amd` and `quest_mark_complete`.

    python -m unittest tests.test_campaign_facts
"""
import os
import shutil
import tempfile
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401
from cosmos_dev.mock import sbs as mock_sbs
from tests.reset_helper import reset_mock

from sbs_utils.agent import Agent
from sbs_utils.gui import GuiClient
from sbs_utils.handlerhooks import reset_mission_audit, reset_mission_state
from sbs_utils.procedural import amd_dialogue as D
from sbs_utils.procedural import boarding as B
from sbs_utils.procedural import crew
from sbs_utils.procedural import hail as H
from sbs_utils.procedural import persistence as P
from sbs_utils.procedural.amd import amd_choice_label
from sbs_utils.procedural.amd_crew import amd_crew_data
from sbs_utils.procedural.amd_dialogue import dialogue_scenes
from sbs_utils.procedural.amd_doc import amd_document, amd_section
from sbs_utils.procedural.amd_lifeforms import lifeforms_spawn
from sbs_utils.procedural.amd_lint import amd_lint
from sbs_utils.procedural.amd_mission import amd_mission_data
from sbs_utils.procedural.amd_quest import THEN_VERBS, amd_quest_data
from sbs_utils.procedural.inventory import set_inventory_value
from sbs_utils.procedural.links import link
from sbs_utils.procedural.quest import quest_get_data, quest_get_state
from sbs_utils.procedural.quest_driver import quest_grant_amd, quest_mark_complete
from sbs_utils.procedural.query import to_id
from sbs_utils.procedural.roles import add_role
from sbs_utils.procedural.sides import side_ensure
from sbs_utils.procedural.spawn import player_spawn

COMMS = 0x8000000000000001
ENG = 0x8000000000000002

# What a writer types: a bridge hail that teaches something, a later hail that asks for
# it, a quest step that teaches something, and a site whose door asks for all of it.
MISSION = """# [Mission](mission)

## [Characters](characters)

### [Harbormaster Quill](quill)
---
Face: terran_female
---
Runs the yard.

## [Dialogue](dialogue)

### [Quill Explains](quill_brief)
---
Speaker: quill
When: hail
Title: The yard calls
---
% The manifest was altered before it reached us.

- [Log it.]() ; learn manifest
- [Not our business.]()

### [Quill Asks Again](quill_later)
---
Speaker: quill
When: hail
Title: The yard calls again
---
%{learned manifest < 1} You never did look at that manifest.
%{learned manifest} So you saw it too.

- [We know about the manifest.]() if learned manifest ; signal told_quill
- [Remind me.]()

## [Quests](quests)

### [Find the Ledger](find_ledger)
---
Beat
Done when: signal ledger_found
Then: learn ledger page
---
The page is in the purser's safe.

### [Report Home](report_home)
---
Beat
Starts when: revealed
Done when: signal home
Then: reveal find_ledger
---

## [The Watch](watch)
---
crew
Ship: Artemis
---

### [Chief Okoro](okoro)
---
Console: engineering
Roles: engineering
---

## [Scenes](boarding)

### [The Airlock](airlock)
%{learned < 2} Locked.
%{learned >= 2} Open.

- [Read the panel](airlock) if engineering ; learn panel
- [Read the log](airlock) if engineering ; learn log
- [Use what the yard told us](airlock) if learned manifest
- [Use the ledger page](airlock) if learned Ledger  Page
- [Open the door](airlock) if learned >= 2
- [Return to the ship]()
"""


class _Base(unittest.TestCase):
    def setUp(self):
        reset_mock(mock_sbs)
        mock_sbs.resume_sim()
        self.addCleanup(reset_mission_state)
        self._resolver = D._METRIC_RESOLVER
        D.dialogue_set_metric_resolver(None)
        self.addCleanup(D.dialogue_set_metric_resolver, self._resolver)
        side_ensure("tsn")
        self.ship = to_id(player_spawn(0, 0, 0, "Artemis", "tsn", "tsn_light_cruiser"))
        self.doc = amd_document(MISSION, data_parser=amd_mission_data)
        lifeforms_spawn(amd_section(self.doc, "characters"))
        D.dialogue_register_scenes(amd_section(self.doc, "dialogue"))
        quest_grant_amd(Agent.SHARED_ID, amd_section(self.doc, "quests"))
        # A comms console, for the bridge hail.
        seat = Agent()
        seat.id = COMMS
        seat.add()
        for r in ("console", "comms"):
            add_role(COMMS, r)
        link(self.ship, "consoles", COMMS)
        mock_sbs.assign_client_to_ship(COMMS, self.ship)
        # An engineer, for the away site.
        crew.crew_declare_amd(amd_document(MISSION, data_parser=amd_crew_data))
        self.scenes = dialogue_scenes(amd_section(amd_document(MISSION), "boarding"))
        GuiClient(ENG)
        set_inventory_value(ENG, "CONSOLE_TYPE", "engineering")
        link(self.ship, "consoles", ENG)
        crew.crew_assign(ENG, self.ship, "engineering")

    # -- the bridge -------------------------------------------------------------------
    def call(self, scene):
        H.hail_offer(self.ship, scene=scene)
        H.hail_accept(self.ship)
        beat = H.hail_beat(self.ship)
        while H.hail_advance(self.ship):
            pass
        return (beat.get("text") if beat else None,
                [c.get("label") for c in (H.hail_active(self.ship) or {}).get("choices") or []])

    def answer(self, words):
        labels = [c.get("label") for c in (H.hail_active(self.ship) or {}).get("choices") or []]
        index = next(i for i, l in enumerate(labels) if l.startswith(words))
        return H.hail_answer(self.ship, index, COMMS)

    # -- the away site ----------------------------------------------------------------
    def visit(self, title):
        self.assertIsNotNone(B.boarding_visit(self.ship, self.scenes, "airlock", title=title))
        self.assertIsNotNone(B.boarding_beam_down(ENG))

    def labels(self):
        return [amd_choice_label(c.get("label")) for c in B.boarding_choices(ENG)]

    def press(self, starts):
        for i, label in enumerate(self.labels()):
            if label.startswith(starts):
                return B.boarding_answer(ENG, i, B.boarding_seq())
        self.fail("%r is not offered: %r" % (starts, self.labels()))


class LearnedOnTheBridge(_Base):
    def test_a_bridge_hail_files_the_fact_under_the_campaign(self):
        self.call("quill_brief")
        self.answer("Log it")
        self.assertEqual(B.boarding_place(), "", "the bridge is no place")
        self.assertEqual(B.boarding_facts(""), ["manifest"])

    def test_a_later_hail_can_ask_for_it_by_name(self):
        line, answers = self.call("quill_later")
        self.assertEqual(line, "You never did look at that manifest.")
        self.assertEqual(answers, ["Remind me."])
        self.answer("Remind me")
        self.call("quill_brief")
        self.answer("Log it")
        line, answers = self.call("quill_later")
        self.assertEqual(line, "So you saw it too.")
        self.assertIn("We know about the manifest.", answers)

    def test_a_named_guard_inside_a_site_sees_a_campaign_fact(self):
        self.visit("The Hulk")
        self.assertNotIn("Use what the yard told us", self.labels())
        B.boarding_visit_end()
        self.call("quill_brief")
        self.answer("Log it")
        self.visit("The Hulk")
        self.assertEqual(B.boarding_place(), "The Hulk")
        self.assertIn("Use what the yard told us", self.labels())

    def test_the_count_is_still_the_places_alone(self):
        self.call("quill_brief")
        self.answer("Log it")
        self.visit("The Hulk")
        self.assertEqual(B.boarding_learned(), 0, "the campaign's fact is not counted here")
        self.assertEqual(B.boarding_line(), "Locked.")
        self.press("Read the panel")
        self.assertNotIn("Open the door", self.labels(), "one of two, whatever the bridge knows")
        self.press("Read the log")
        self.assertIn("Open the door", self.labels())

    def test_a_hail_answered_with_a_party_on_offer_still_teaches_the_campaign(self):
        """WHO is asking decides, not where the ship is parked. With a party open at a
        ruin's door the place is that ruin - and a hail answered on the bridge used to
        file its fact there, where the same question two systems later could not see
        it."""
        self.visit("The Hulk")
        self.assertEqual(B.boarding_place(), "The Hulk")
        self.call("quill_brief")
        self.answer("Log it")
        self.assertEqual(B.boarding_facts(""), ["manifest"])
        self.assertEqual(B.boarding_facts("The Hulk"), [])
        B.boarding_visit_end()
        line, answers = self.call("quill_later")
        self.assertEqual(line, "So you saw it too.")

    def test_a_count_asked_in_a_hail_counts_what_the_campaign_knows(self):
        self.visit("The Hulk")
        self.press("Read the panel")
        self.press("Read the log")
        self.assertTrue(D.dialogue_guard_ok("learned >= 2", None, None), "the party, here")
        self.assertFalse(D.dialogue_guard_ok("learned >= 1", self.ship, None),
                         "the bridge knows none of it")
        self.call("quill_brief")
        self.answer("Log it")
        self.assertTrue(D.dialogue_guard_ok("learned >= 1", self.ship, None))
        self.assertFalse(D.dialogue_guard_ok("learned >= 3", None, None),
                         "and the place does not count the bridge's")

    def test_a_fact_learned_in_a_site_stays_in_that_site(self):
        self.visit("The Hulk")
        self.press("Read the panel")
        B.boarding_visit_end()
        self.assertEqual(B.boarding_facts(""), [], "nothing reached the campaign")
        self.assertFalse(D.dialogue_guard_ok("learned panel", self.ship, None))

    def test_a_resolver_of_a_missions_own_can_still_answer_it(self):
        """Open Universe installs its own resolver; this is the call it makes."""
        self.assertIsNone(B.boarding_learned_guard("credits"))
        self.assertIsNone(B.boarding_learned_guard("standing"))
        self.assertEqual(B.boarding_learned_guard("learned manifest"), 0)
        self.assertEqual(B.boarding_learned_guard("learned"), 0)
        B.boarding_learn("manifest", place="")
        self.assertEqual(B.boarding_learned_guard("Learned  Manifest"), 1)
        self.assertEqual(B.boarding_learned_guard("learned"), 1)


class ThenLearn(_Base):
    def test_learn_is_a_then_verb_and_the_fact_may_be_several_words(self):
        self.assertEqual(THEN_VERBS, ("reveal", "signal", "learn"))
        self.assertEqual(amd_quest_data("Then: learn ledger page"), {"learn": "ledger page"})
        # The two it always took are read as they always were.
        self.assertEqual(amd_quest_data("Then: reveal next_step"), {"reveal": "next_step"})
        self.assertEqual(amd_quest_data("Then: signal alarm"), {"signal": "alarm"})

    def test_finishing_the_step_is_how_the_crew_comes_to_know_it(self):
        self.assertEqual(quest_get_data(Agent.SHARED_ID, "find_ledger").get("learn"),
                         "ledger page")
        self.assertEqual(B.boarding_facts(""), [])
        quest_mark_complete(Agent.SHARED_ID, "find_ledger")
        self.assertEqual(quest_get_state(Agent.SHARED_ID, "find_ledger"), 99)
        self.assertEqual(B.boarding_facts(""), ["ledger page"])

    def test_it_is_a_campaign_fact_even_when_the_step_is_finished_inside_a_site(self):
        self.visit("The Hulk")
        self.assertNotIn("Use the ledger page", self.labels())
        quest_mark_complete(Agent.SHARED_ID, "find_ledger")
        self.assertEqual(B.boarding_facts("The Hulk"), [])
        self.assertEqual(B.boarding_facts(""), ["ledger page"])
        # ...and the door inside asks for it with other capitals and spacing.
        self.assertIn("Use the ledger page", self.labels())

    def test_a_step_with_no_learn_teaches_nothing(self):
        quest_mark_complete(Agent.SHARED_ID, "report_home")
        self.assertEqual(B.boarding_facts(""), [])


class KeptByASave(_Base):
    def test_every_places_facts_are_written_down(self):
        self.call("quill_brief")
        self.answer("Log it")
        self.visit("The Hulk")
        self.press("Read the panel")
        self.assertTrue(P.persist_providers_dirty(), "a fact learned asks to be saved")
        saved = P.persist_providers_snapshot()
        self.assertEqual(saved["boarding_facts"], {"": ["manifest"], "The Hulk": ["panel"]})

    def test_a_restore_brings_them_back_and_a_hail_can_ask(self):
        saved = {"boarding_facts": {"": ["manifest"], "The Hulk": ["panel", "log"]}}
        # The next launch: nothing is known.
        self.assertFalse(D.dialogue_guard_ok("learned manifest", self.ship, None))
        P.persist_providers_restore(saved)
        line, answers = self.call("quill_later")
        self.assertEqual(line, "So you saw it too.")
        self.assertIn("We know about the manifest.", answers)
        self.answer("Remind me")
        self.visit("The Hulk")
        self.assertEqual(B.boarding_learned(), 2)
        self.assertIn("Open the door", self.labels())

    def test_a_restore_replaces_what_was_known(self):
        B.boarding_learn("stale", place="")
        P.persist_providers_restore({"boarding_facts": {"": ["manifest"]}})
        self.assertEqual(B.boarding_facts(""), ["manifest"])
        P.persist_providers_restore({})                     # a new game
        self.assertEqual(B.boarding_facts(""), [])

    def test_nothing_survives_the_mission_reset(self):
        P.persist_providers_restore({"boarding_facts": {"": ["manifest"]}})
        reset_mission_state()
        self.assertEqual(B.boarding_facts(""), [])
        # (The mock's own objects are a new sim's to clear, not the reset's.)
        left = {k: v for k, v in reset_mission_audit().items() if not k.startswith("mock.")}
        self.assertEqual(left, {})


# --- lint --------------------------------------------------------------------------------

def _codes(text, path=None):
    return sorted(f.code for f in amd_lint(file_path=path, content=text, cross_file=False))


QUEST_FILE = """# [Mission](mission)

## [Quests](quests)

### [Find the Ledger](find_ledger)
---
Beat
Done when: signal ledger_found
{extra}
---
The page is in the purser's safe.

### [Report Home](report_home)
---
Beat
Starts when: at once
Done when: signal home
Then: reveal find_ledger
---
"""

SITE_FILE = """# [Site](site)

## [Scenes](boarding)

### [The Airlock](airlock)
% Cold and dark.

- [Use what the yard told us](airlock) if learned {fact}
- [Return to the ship]()
"""

HAIL_FILE = """# [Hails](hails)

## [Characters](characters)

### [Harbormaster Quill](quill)
---
Face: terran_female
---

## [Dialogue](dialogue)

### [Quill Explains](quill_brief)
---
Speaker: quill
When: hail
---
% The manifest was altered.

- [Log it.]() ; learn manifest
"""


class Lint(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="campaign_facts_lint_")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        with open(os.path.join(self.root, "story.mast"), "w", encoding="utf-8") as f:
            f.write("# a mission\n")

    def write(self, name, text):
        path = os.path.join(self.root, name)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        return path

    def test_then_learn_is_a_known_verb_and_names_no_record(self):
        codes = _codes(QUEST_FILE.replace("{extra}", "Then: learn ledger page"))
        self.assertNotIn("unknown-then-verb", codes)
        self.assertNotIn("dangling-reveal", codes)
        # A word that is NOT a verb is still told so.
        self.assertIn("unknown-then-verb",
                      _codes(QUEST_FILE.replace("{extra}", "Then: teach ledger page")))

    def test_a_fact_a_quest_step_teaches_is_known_to_a_guard_in_the_same_file(self):
        both = (QUEST_FILE.replace("{extra}", "Then: learn ledger page")
                + SITE_FILE.split("\n", 1)[1].replace("{fact}", "ledger page"))
        self.assertNotIn("guard-learned-unknown", _codes(both))
        wrong = both.replace("if learned ledger page", "if learned ledger pgae")
        self.assertIn("guard-learned-unknown", _codes(wrong))

    def test_a_fact_learned_in_another_file_of_the_mission_is_known(self):
        self.write("hails.amd", HAIL_FILE)
        site = self.write("site.amd", SITE_FILE.replace("{fact}", "manifest"))
        self.assertNotIn("guard-learned-unknown", _codes(None, site))

    def test_a_fact_no_file_teaches_is_still_reported_and_says_where_it_looked(self):
        self.write("hails.amd", HAIL_FILE)
        site = self.write("site.amd", SITE_FILE.replace("{fact}", "manfest"))
        found = [f for f in amd_lint(file_path=site, cross_file=False)
                 if f.code == "guard-learned-unknown"]
        self.assertEqual(len(found), 1)
        self.assertIn("this mission", found[0].message)
        self.assertIn("manifest", found[0].message, "it lists what IS learned")

    def test_a_file_on_its_own_with_nothing_learned_anywhere_is_not_second_guessed(self):
        site = self.write("site.amd", SITE_FILE.replace("{fact}", "manifest"))
        self.assertNotIn("guard-learned-unknown", _codes(None, site))

    def test_another_missions_files_do_not_count(self):
        other = tempfile.mkdtemp(prefix="campaign_facts_other_")
        self.addCleanup(shutil.rmtree, other, ignore_errors=True)
        with open(os.path.join(other, "story.mast"), "w", encoding="utf-8") as f:
            f.write("# another mission\n")
        with open(os.path.join(other, "hails.amd"), "w", encoding="utf-8") as f:
            f.write(HAIL_FILE)
        self.write("more.amd", HAIL_FILE.replace("learn manifest", "learn tide table"))
        site = self.write("site.amd", SITE_FILE.replace("{fact}", "manifest"))
        self.assertIn("guard-learned-unknown", _codes(None, site))

    def test_was_is_a_field_of_a_quest(self):
        text = QUEST_FILE.replace("{extra}", "Was: find_book")
        self.assertEqual(amd_quest_data("Was: find_book, find_page"),
                         {"was": ["find_book", "find_page"]})
        codes = _codes(text)
        self.assertNotIn("unknown-field", codes)
        self.assertFalse([c for c in codes if c.startswith("was-")], codes)

    def test_was_naming_a_key_still_in_the_file_is_said(self):
        self.assertIn("was-key-still-used",
                      _codes(QUEST_FILE.replace("{extra}", "Was: report_home")))

    def test_was_naming_its_own_key_is_said(self):
        self.assertIn("was-own-key",
                      _codes(QUEST_FILE.replace("{extra}", "Was: find_ledger")))


if __name__ == "__main__":
    unittest.main()
