"""What the lesson "Clues, side stories and cutscenes" found about cutscenes.

  * A held shot after a moving shot was filmed on the PREVIOUS subject: a move is a
    driver that re-aims the camera each tick, a held shot starts none, and nothing
    stopped the one before it.
  * Every cutscene failure was silent. An unknown cutscene key, a shot dropped for a
    subject that is not there: each was written to a log category with no file behind
    it, and `mast.runtime.log` stayed empty.
  * A Cutscenes section that no line of the story reads was `clean` in any mission that
    has a ruin, because lint assumed the ruin reader loads it. It does not.

    python -m unittest tests.test_cutscene_in_a_lesson
"""
import logging
import unittest
from unittest import mock

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401
from sbs_utils.procedural import amd_cutscene
from sbs_utils.procedural.amd_lint import amd_lint
from sbs_utils.procedural.gui import cutscene


class AHeldShotAfterAMovingOne(unittest.TestCase):
    def test_the_move_before_it_is_stopped_first(self):
        order = []
        with mock.patch.object(cutscene, "camera_move_stop", lambda cids: order.append("stop")), \
                mock.patch.object(cutscene, "camera_shot", lambda *a, **k: order.append("shot")):
            cutscene.shot_apply([1], {"subject": 7, "lens": (0, 0, 500), "seconds": 4})
        self.assertEqual(order, ["stop", "shot"])


class ACutsceneFailureIsSaid(unittest.TestCase):
    def test_it_reaches_the_log_a_writer_reads(self):
        with self.assertLogs("mast.runtime", level="WARNING") as heard:
            amd_cutscene._log("cutscene 'cairn_scen' is not declared in any loaded AMD")
        self.assertEqual(len(heard.output), 1)
        self.assertIn("Cutscene 'cairn_scen' is not declared", heard.output[0])


MISSION = """# [Sample Mission](sample_mission)

## [Quests](quests)

### [First Contact](first_contact)
---
Scope: shared
Starts when: at once
Done when: signal found
---
A derelict has drifted into the sector.

## [Cutscenes](cutscenes)

### [At the Cairn](cairn_scene)
---
Letterbox: true
---
"""

STORY = '''    shared MISSION_DOC = document_get_amd_file(get_mission_dir_filename("mission.amd"))
    quest_grant_amd(SHARED, amd_section(MISSION_DOC, "quests"))
    relics_spawn(get_mission_dir_filename("mission.amd"))
    signal_emit("quest_signal", {"SIGNAL_NAME": "found"})
'''


class ACutscenesSectionNothingReads(unittest.TestCase):
    def codes(self, story):
        # The check speaks only about a file the story names, so it needs a real one.
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "mission.amd")
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(MISSION)
            return [f.code for f in amd_lint(file_path=path, mast_sources=[story])]

    def test_a_ruin_in_the_mission_does_not_load_it(self):
        self.assertIn("section-not-loaded", self.codes(STORY))

    def test_the_line_that_reads_it_does(self):
        reads = STORY + '    amd_cutscenes(amd_section(MISSION_DOC, "cutscenes"))\n'
        self.assertNotIn("section-not-loaded", self.codes(reads))

    def test_a_ruins_own_section_reached_through_the_ruin_counts(self):
        reads = STORY + '    amd_cutscenes(relic_section(EVA_RELIC, "cutscenes"))\n'
        self.assertNotIn("section-not-loaded", self.codes(reads))


if __name__ == "__main__":
    unittest.main()
