"""AMD per-mission state splits in two, and getting it backwards breaks run 2.

CONTENT is read out of a mission's .amd at run time and MUST be cleared -
`OVERLAY_AMD` and the quest-tab console set were both module-level, uncleared and
absent from the reset ledger, so run 2 could fire a card keyed only by run 1 and
show a Quests tab on consoles it never enabled.

VOCABULARY is registered at module IMPORT time and MUST NOT be cleared.
`MastGlobals.mission_py_modules` is never reset and
`Mast.import_python_module_for_source` dedupes by file, so a mission's `*_amd.py`
is NOT re-executed on an in-process recompile - clearing the field tables would
delete the mission's own words with nothing left to re-register them. What the
ledger watches there is the DELTA, because a mission's words surviving into the
NEXT mission is a real hazard: two missions declaring one label differently make
amd_register_fields raise at startup.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.handlerhooks import (reset_mission_state, reset_mission_audit,
                                    _RESET_PROBES)
from sbs_utils.procedural import amd_schema as S
from sbs_utils.procedural.amd_overlay import OVERLAY_AMD, overlay_amd_count
from sbs_utils.procedural.quest import quest_console_enable, quest_consoles_count


class TestContentIsCleared(unittest.TestCase):
    def test_declared_overlays_do_not_survive(self):
        OVERLAY_AMD["probe_card"] = {"key": "probe_card", "kind": "toast"}
        self.assertEqual(overlay_amd_count(), 1)
        reset_mission_state()
        self.assertEqual(overlay_amd_count(), 0)

    def test_quest_consoles_do_not_survive(self):
        quest_console_enable("comms")
        quest_console_enable("science")
        self.assertEqual(quest_consoles_count(), 2)
        reset_mission_state()
        self.assertEqual(quest_consoles_count(), 0)

    def test_both_are_reported_by_name_when_dirty(self):
        OVERLAY_AMD["probe_card"] = {"key": "probe_card"}
        quest_console_enable("comms")
        audit = reset_mission_audit()
        self.assertIn("amd overlays", audit)
        self.assertIn("quest consoles", audit)
        reset_mission_state()
        self.assertEqual(reset_mission_audit(), {})


class TestVocabularyIsNotCleared(unittest.TestCase):
    def test_core_field_tables_survive_a_reset(self):
        # The direction that would be a silent disaster: a mission's *_amd.py is not
        # re-executed on an in-process recompile, so anything cleared here is gone.
        before = {k: dict(v) for k, v in S.ARCHETYPES.items()}
        reset_mission_state()
        self.assertEqual({k: dict(v) for k, v in S.ARCHETYPES.items()}, before)

    def test_registered_parsers_and_sections_survive(self):
        parsers, sections = dict(S._PARSERS), dict(S._SECTION_ALIASES)
        reset_mission_state()
        self.assertEqual(dict(S._PARSERS), parsers)
        self.assertEqual(dict(S._SECTION_ALIASES), sections)

    def test_added_words_are_visible_as_a_diagnostic(self):
        # NOT a ledger probe. The ledger means "must be empty after a reset", and
        # vocabulary must SURVIVE one - an entry there would report a leak on every
        # run after the first and turn the restart soak into noise. This is the
        # number to look at when two missions declare one label differently and
        # amd_register_fields raises at startup.
        from sbs_utils.handlerhooks import amd_vocabulary_added
        before = amd_vocabulary_added()
        S.amd_register_fields("quest", {"reset split probe": S.text()}, domain="test")
        try:
            self.assertGreater(amd_vocabulary_added(), before)
            reset_mission_state()
            self.assertGreater(amd_vocabulary_added(), before,
                               "a reset deleted vocabulary that nothing will re-register")
        finally:
            S.ARCHETYPES["quest"].pop("reset_split_probe", None)
            S._schema_changed()


if __name__ == "__main__":
    unittest.main()
