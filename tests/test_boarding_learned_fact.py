"""`if learned <fact>`: a choice that waits on ONE thing the party worked out.

`; learn manifest` records a fact; `if learned >= 2` counted them and was the only
question a room could ask. A door that should open once the party has read the MANIFEST -
not once it has read any two things - had no way to say so, and `if learned manifest` was
read as one long job name nobody holds: never offered, nothing logged.

Both forms are driven through the real scene parser and the real choice list.

    python -m unittest tests.test_boarding_learned_fact
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs as sbs
from tests.reset_helper import reset_mock

from sbs_utils.gui import GuiClient
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.procedural import boarding as A
from sbs_utils.procedural import crew
from sbs_utils.procedural.amd import amd_choice_label
from sbs_utils.procedural.amd_dialogue import dialogue_scenes
from sbs_utils.procedural.amd_doc import amd_document, amd_section
from sbs_utils.procedural.amd_lint import amd_lint
from sbs_utils.procedural.amd_mission import amd_mission_data
from sbs_utils.procedural.inventory import set_inventory_value
from sbs_utils.procedural.links import link
from sbs_utils.procedural.query import to_id
from sbs_utils.procedural.sides import side_ensure
from sbs_utils.procedural.spawn import player_spawn

HELM = 0x8000000000000001

PLACE = """# [Mission](mission)

## [Scenes](scenes)

### [The Hold](hold)
% Crates to the ceiling, and a terminal still lit.
%{learned manifest} The manifest said bay nine. Bay nine is right there.

- [Read the manifest](hold) ; learn manifest
- [Read the duty roster](hold) ; learn roster
- [Read the cold start card](hold) ; learn cold start
- [Open bay nine](bay) if learned manifest
- [Run the cold start](bay) if learned cold start
- [Force the inner door](bay) if learned >= 2
- [Leave it sealed](hold) if learned manifest < 1
- [Return to the ship]()

### [Bay Nine](bay)
% Open.

- [Return to the ship]()
"""


class _Base(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        TickDispatcher.clear()
        crew.crew_clear()
        A.boarding_clear()
        self.addCleanup(TickDispatcher.clear)
        self.addCleanup(crew.crew_clear)
        self.addCleanup(A.boarding_clear)
        side_ensure("tsn")
        self.ship = to_id(player_spawn(0, 0, 0, "Artemis", "tsn", "tsn_light_cruiser"))
        self.scenes = dialogue_scenes(amd_section(
            amd_document(PLACE, data_parser=amd_mission_data), "scenes"))
        GuiClient(HELM)
        set_inventory_value(HELM, "CONSOLE_TYPE", "helm")
        link(self.ship, "consoles", HELM)
        crew.crew_assign(HELM, self.ship, "helm")
        A.boarding_visit(self.ship, self.scenes, "hold", title="The Hold")
        A.boarding_beam_down(HELM)

    def offered(self):
        return [amd_choice_label(c.get("label")) for c in A.boarding_choices(HELM)]

    def take(self, starts_with):
        index = next(i for i, text in enumerate(self.offered()) if text.startswith(starts_with))
        A.boarding_answer(HELM, index, A.boarding_seq())


class ANamedFactTests(_Base):
    def test_it_is_not_offered_before_the_fact_is_learned(self):
        self.assertNotIn("Open bay nine", self.offered())

    def test_it_is_offered_once_that_fact_is_learned(self):
        self.take("Read the manifest")
        self.assertIn("Open bay nine", self.offered())

    def test_another_fact_does_not_open_it(self):
        self.take("Read the duty roster")
        self.assertNotIn("Open bay nine", self.offered())

    def test_a_fact_of_two_words(self):
        self.assertNotIn("Run the cold start", self.offered())
        self.take("Read the cold start card")
        self.assertIn("Run the cold start", self.offered())

    def test_capitals_do_not_matter(self):
        self.take("Read the manifest")
        lf = A.boarding_me(HELM)
        from sbs_utils.procedural.amd_dialogue import dialogue_guard_ok
        for guard in ("learned manifest", "Learned Manifest", "learned MANIFEST >= 1"):
            self.assertTrue(dialogue_guard_ok(guard, lf, None), guard)
        self.assertFalse(dialogue_guard_ok("learned manifesto", lf, None))

    def test_not_yet_can_be_asked_with_a_sign(self):
        self.assertIn("Leave it sealed", self.offered())
        self.take("Read the manifest")
        self.assertNotIn("Leave it sealed", self.offered())

    def test_a_line_can_wait_on_a_fact_too(self):
        self.assertNotIn("bay nine is right there", A.boarding_line().lower())
        self.take("Read the manifest")
        lines = set()
        for _ in range(40):
            A.boarding_scene_begin(self.scenes, "hold")
            lines.add(A.boarding_line())
        self.assertTrue(any("Bay nine is right there" in line for line in lines), lines)

    def test_a_named_fact_is_never_a_job_to_forward(self):
        """Forwarding hands an orphaned JOB to whoever is there. A fact nobody has
        learned is not a job nobody holds - handing it over would give the door away."""
        A.boarding_forwarding(True)
        self.assertFalse(A._is_job_guard("learned manifest"))
        self.assertFalse(A._is_job_guard("learned manifest >= 1"))
        self.assertEqual([amd_choice_label(c.get("label")) for c in A.boarding_orphan_choices()],
                         [])

    def test_the_fact_belongs_to_the_place(self):
        self.take("Read the manifest")
        A.boarding_visit_end()
        A.boarding_visit(self.ship, self.scenes, "hold", title="Another Hold")
        A.boarding_beam_down(HELM)
        self.assertNotIn("Open bay nine", self.offered())


class TheCountIsUnchangedTests(_Base):
    def test_the_count_still_counts(self):
        self.assertNotIn("Force the inner door", self.offered())
        self.take("Read the manifest")
        self.assertNotIn("Force the inner door", self.offered())
        self.take("Read the duty roster")
        self.assertIn("Force the inner door", self.offered())

    def test_the_same_fact_twice_counts_once(self):
        self.take("Read the manifest")
        self.take("Read the manifest")
        self.assertNotIn("Force the inner door", self.offered())
        self.assertEqual(A.boarding_learned(), 1)

    def test_the_metric_answers_the_bare_word_with_the_count(self):
        self.take("Read the manifest")
        self.take("Read the duty roster")
        self.assertEqual(A._boarding_metric("learned", None, None), 2)
        self.assertEqual(A._boarding_metric("Learned", None, None), 2)
        self.assertEqual(A._boarding_metric("learned manifest", None, None), 1)
        self.assertEqual(A._boarding_metric("learned nothing", None, None), 0)


MINE = ("guard-learned-shape", "guard-learned-unknown", "guard-names-a-fact",
        "unreadable-guard", "guard-joined")


def codes(text):
    return sorted(f.code for f in amd_lint(file_path="mission.amd", content=text,
                                            cross_file=False) if f.code in MINE)


class LintKnowsBothTests(unittest.TestCase):
    def test_the_scene_above_is_clean(self):
        self.assertEqual(codes(PLACE), [])

    def test_a_fact_nothing_learns_is_reported(self):
        text = PLACE.replace("if learned manifest\n", "if learned manifst\n")
        self.assertEqual(codes(text), ["guard-learned-unknown"])
        found = [f for f in amd_lint(file_path="mission.amd", content=text, cross_file=False)
                 if f.code == "guard-learned-unknown"]
        self.assertIn("manifst", found[0].message)
        self.assertIn("manifest", found[0].message)        # what it could have been

    def test_a_gated_line_is_judged_the_same_way(self):
        text = PLACE.replace("%{learned manifest}", "%{learned manifst}")
        self.assertEqual(codes(text), ["guard-learned-unknown"])

    def test_a_number_with_no_sign_is_still_a_slip(self):
        text = PLACE.replace("if learned >= 2", "if learned 2")
        self.assertEqual(codes(text), ["guard-learned-shape"])

    def test_a_named_fact_that_can_never_be_two(self):
        text = PLACE.replace("if learned manifest < 1", "if learned manifest >= 2")
        self.assertEqual(codes(text), ["guard-learned-shape"])

    def test_a_file_that_learns_nothing_is_not_second_guessed(self):
        """The fact may be learned in another file; with none learned here there is
        nothing to judge the word against."""
        text = PLACE
        for line in ("; learn manifest", "; learn roster", "; learn cold start"):
            text = text.replace(line, "")
        self.assertEqual(codes(text), [])

    def test_a_bare_fact_is_told_the_new_way_to_ask(self):
        text = PLACE.replace("if learned manifest\n", "if manifest\n")
        found = [f for f in amd_lint(file_path="mission.amd", content=text, cross_file=False)
                 if f.code == "guard-names-a-fact"]
        self.assertEqual(len(found), 1)
        self.assertIn("if learned manifest", found[0].message)


if __name__ == "__main__":
    unittest.main()
