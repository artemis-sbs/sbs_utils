"""A roster member written `Face: terran_male` gets a real face, everywhere it is drawn.

`Face:` on a crew member may be a face KEYWORD (`terran_male`, `female`, `terran`...) as
well as a face string. `_member_face` handed the keyword straight back as the face, so the
console's CREW_FACE - and the boarding body made from it - was the string "terran_male",
which send_gui_face draws as nothing. Seen in the engine (author course 3, lesson 2):
Chief Okoro and Dr Hale had an empty gap where their face goes on the Boarding Party app,
in the xESS transcript and over a roll, while an unrostered Helm officer had a face.

Through the front door: the roster as AMD, `crew_assign`, then the party built from the
consoles.

    python -m unittest tests.test_crew_face_keyword
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs as sbs
from tests.reset_helper import reset_mock

from sbs_utils.faces import get_face
from sbs_utils.gui import GuiClient
from sbs_utils.procedural import boarding as A
from sbs_utils.procedural import crew
from sbs_utils.procedural.amd_crew import amd_crew_data
from sbs_utils.procedural.amd_doc import amd_document
from sbs_utils.procedural.inventory import get_inventory_value, set_inventory_value
from sbs_utils.procedural.query import to_id
from sbs_utils.procedural.sides import side_ensure
from sbs_utils.procedural.spawn import player_spawn

SCI = 0x8000000000000001
ENG = 0x8000000000000002
HELM = 0x8000000000000003

# The c3-02 course roster, plus a literal face string that must stay as written.
ROSTER = """# [Mission](mission)

## [The Watch](watch)
---
crew
Ship: Artemis
Names: locked
---
The people aboard for this story.

### [Chief Okoro](okoro)
---
Console: engineering
Face: terran_male
Roles: engineering
---

### [Dr Hale](hale)
---
Console: science
Face: terran_female
Roles: medical
---

### [Ensign Vale](vale)
---
Console: helm
Face: ter #fff 0 0;
---
"""

KEYWORDS = ("terran_male", "terran_female", "terran", "male", "female", "fluid")


def _is_face_string(face):
    """A face string is `alias #color col row;...` - never one bare word."""
    return bool(face) and ";" in face and face.strip().lower() not in KEYWORDS


class CrewFaceKeywordTests(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        crew.crew_clear()
        A.boarding_clear()
        self.addCleanup(crew.crew_clear)
        self.addCleanup(A.boarding_clear)
        side_ensure("tsn")
        self.ship = to_id(player_spawn(0, 0, 0, "Artemis", "tsn", "tsn_light_cruiser"))
        crew.crew_declare_amd(amd_document(ROSTER, data_parser=amd_crew_data))

    def sit(self, client_id, console):
        GuiClient(client_id)
        set_inventory_value(client_id, "CONSOLE_TYPE", console)
        return crew.crew_assign(client_id, self.ship, console)

    def test_a_keyword_face_is_published_as_a_face_string(self):
        post = self.sit(ENG, "engineering")
        self.assertEqual(post.name, "Chief Okoro")
        self.assertTrue(_is_face_string(post.face), post.face)
        self.assertTrue(_is_face_string(get_inventory_value(ENG, "CREW_FACE", "")))

    def test_the_boarding_body_wears_the_resolved_face(self):
        self.sit(SCI, "science")
        bodies = A.boarding_crew_roster(self.ship, consoles=[SCI], assign_missing=False)
        self.assertEqual(len(bodies), 1)
        self.assertTrue(_is_face_string(get_face(to_id(bodies[0]))))

    def test_the_face_is_rolled_once_and_kept(self):
        """Stable for the game: sitting down again does not re-roll the face."""
        first = self.sit(ENG, "engineering").face
        for _ in range(5):
            self.assertEqual(self.sit(ENG, "engineering").face, first)

    def test_a_literal_face_string_is_left_as_written(self):
        self.assertEqual(self.sit(HELM, "helm").face, "ter #fff 0 0;")

    def test_the_keyword_reader(self):
        self.assertEqual(crew._face_keyword("terran_female"), ("terran", "female"))
        self.assertEqual(crew._face_keyword(" Male "), ("terran", "male"))
        self.assertIsNone(crew._face_keyword("ter #fff 0 0;"))
        self.assertIsNone(crew._face_keyword(""))


if __name__ == "__main__":
    unittest.main()
