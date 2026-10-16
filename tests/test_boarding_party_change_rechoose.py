"""A party change rebuilds every member's open menu - on the SAME beat.

Seen in the engine (author course 3, lesson 3): Engineering beamed down first and, the party
being short a medic, was offered `Read the name tags on the suits (covering for medical)`.
Dr Hale (medical) then beamed down - and Engineering's open menu still offered the covering
choice until the party moved rooms. The reader derived a beat's choices once, when the beat
opened, and nothing about the beat changed when the party did.

    python -m unittest tests.test_boarding_party_change_rechoose
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  import first (circular imports)
import cosmos_dev.mock.sbs as sbs
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.agent import clear_shared
from sbs_utils.gui import GuiClient
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural import boarding as A
from sbs_utils.procedural.inventory import set_inventory_value
from sbs_utils.pages.layout.text_area import TextArea
from sbs_utils.pages.layout.bounds import Bounds

ENG = 0x8000000000000002
SCI = 0x8000000000000003

BODY = """% A row of suits still on their hooks.
- [Go aft](inside)
- [Read the name tags on the suits](inside) if medical >= 1
"""

SCENE = {
    "airlock": {"key": "airlock", "display_text": "airlock", "description": BODY,
                "data": {"speaker": "hulk"}},
    "inside": {"key": "inside", "display_text": "inside",
               "description": "% Cold.\n", "data": {"speaker": "hulk"}},
}

COVER = "(covering for medical)"


class PartyChangeRechooseTests(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        SpaceObject.clear()
        clear_shared()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(0, "test"))
        A.boarding_clear()
        A.boarding_forwarding(False)
        A.boarding_metric_install()
        self.addCleanup(A.boarding_clear)
        self.addCleanup(A.boarding_forwarding, False)
        self.addCleanup(A.boarding_metric_uninstall)
        self.ship = 1
        self.crew(ENG, "engineering", "Chief Okoro", "engineering")
        self.crew(SCI, "science", "Dr Hale", "medical")
        A.boarding_invite_crew(self.ship, title="The Hulk", consoles=[ENG, SCI])
        # Engineering goes first, so the medic's reading is forwarded to it.
        A.boarding_beam_down(ENG)
        A.boarding_scene_begin(SCENE, "airlock", speaker="hulk")

    def tearDown(self):
        FrameContext.context = None

    def crew(self, client_id, console, name, roles):
        GuiClient(client_id)
        set_inventory_value(client_id, "CONSOLE_TYPE", console)
        set_inventory_value(client_id, "CREW_NAME", name)
        set_inventory_value(client_id, "CREW_ROLES", roles)

    def area(self, client_id, in_region=False):
        ta = TextArea(f"ta{client_id}", "")
        ta.bounds = Bounds(0, 0, 100, 100)
        A.boarding_reader(ta, client_id, in_region=in_region)
        return ta

    def test_the_fixture_forwards_the_medics_reading_to_engineering(self):
        self.assertIn(COVER, A.boarding_reader_text(ENG))

    def test_an_open_menu_drops_the_cover_when_its_owner_beams_down(self):
        ta = self.area(ENG)
        self.assertIn(COVER, str(ta.value))
        seq = A.boarding_seq()
        A.boarding_beam_down(SCI)
        self.assertEqual(A.boarding_seq(), seq, "same beat - nothing moved rooms")
        # The area on screen was rewritten, without anybody rebuilding the screen.
        self.assertNotIn(COVER, str(ta.value))
        self.assertIn("Go aft", str(ta.value))
        self.assertIn("A row of suits", str(ta.value))
        # And the medic herself is offered it, plainly.
        sci = A.boarding_reader_text(SCI)
        self.assertIn("Read the name tags on the suits", sci)
        self.assertNotIn(COVER, sci)

    def test_the_line_is_not_repeated(self):
        self.area(ENG)
        A.boarding_beam_down(SCI)
        self.assertEqual(A.boarding_reader_text(ENG).count("A row of suits"), 1)

    def test_a_reader_in_a_region_asks_its_owner_to_rebuild(self):
        self.area(ENG, in_region=True)
        before = A.boarding_reader_revision(ENG)
        A.boarding_beam_down(SCI)
        self.assertNotEqual(A.boarding_reader_revision(ENG), before)
        # The owner rebuilds in band - and what it reads then is the new menu.
        self.assertNotIn(COVER, str(self.area(ENG, in_region=True).value))

    def test_the_xess_revision_moves(self):
        from sbs_utils.procedural.gui.xess import _boarding_revision
        before = _boarding_revision(ENG)
        A.boarding_beam_down(SCI)
        self.assertNotEqual(_boarding_revision(ENG), before)

    def test_beaming_back_up_hands_the_cover_back(self):
        A.boarding_beam_down(SCI)
        ta = self.area(ENG)
        self.assertNotIn(COVER, str(ta.value))
        A.boarding_beam_up(SCI)
        self.assertIn(COVER, str(ta.value))


if __name__ == "__main__":
    unittest.main()
