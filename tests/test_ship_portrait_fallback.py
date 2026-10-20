"""A ship or station with no face of its own shows its PORTRAIT on Comms and in hails.

Open Universe spawns its stations with no face, so every station, side voice and captain
drew a blank where the face goes - on the Comms selection, in the waterfall, and on the
hail screen. Now the face falls back to the hull's portrait, staged by what the crew
knows: the SILHOUETTE until Science has scanned it, the hull after. An object that has
a face keeps it; a player ship is never given one; no sheet means no change at all.

    python -m unittest tests.test_ship_portrait_fallback
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  import first (circular import)
from cosmos_dev.mock import sbs as sbs
from tests.reset_helper import reset_mock

from sbs_utils import faces
from sbs_utils.procedural import ship_portraits as P
from sbs_utils.procedural import comms as C
from sbs_utils.procedural import hail as H
from sbs_utils.procedural.a2x.spawn import create_enemy
from sbs_utils.procedural.query import to_id
from sbs_utils.procedural.roles import add_role
from sbs_utils.procedural.science import science_set_scan_data


class Fallback(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        P.ship_portrait_clear()
        faces.faces_map.clear()                # ids repeat between tests on the mock
        self.addCleanup(faces.faces_map.clear)
        self.ship = to_id(create_enemy(0, 0, 0, "tsn_light_cruiser", name="Artemis"))
        add_role(self.ship, "__player__")
        self.station = to_id(create_enemy(900, 0, 0, "starbase_command", name="Kestrel Relay"))
        self.hull = P.ship_portrait_face("starbase_command")
        self.shape = P.ship_portrait_silhouette_face("starbase_command")
        self.assertTrue(self.hull, "the base sheet must have starbase_command for this test")

    def tearDown(self):
        P.ship_portrait_clear()

    def _scan(self):
        science_set_scan_data(self.ship, self.station, {"scan": "A station of an unaligned side."})

    # --- the helper ------------------------------------------------------------
    def test_scanned_is_the_hull(self):
        self._scan()
        self.assertEqual(P.ship_portrait_fallback_face(self.station, self.ship), self.hull)

    def test_unscanned_is_the_silhouette(self):
        self.assertEqual(P.ship_portrait_fallback_face(self.station, self.ship),
                         self.shape or P.ship_portrait_unknown_face())

    def test_no_origin_is_the_hull(self):
        self.assertEqual(P.ship_portrait_fallback_face(self.station), self.hull)

    def test_an_object_with_a_face_keeps_it(self):
        faces.set_face(self.station, "ter #fff 1 1;")
        self.assertEqual(P.ship_portrait_fallback_face(self.station, self.ship), "ter #fff 1 1;")

    def test_a_player_ship_is_never_given_one(self):
        self.assertEqual(P.ship_portrait_fallback_face(self.ship), "")

    def test_no_sheet_is_empty(self):
        P.ship_portrait_clear()
        P._base_offered_for = "nowhere-else"          # the base set is not offered again
        self.addCleanup(setattr, P, "_base_offered_for", None)
        import sbs_utils.procedural.media_paths as MP
        real = MP._mission_dir
        MP._mission_dir = lambda: "nowhere-else"
        self.addCleanup(setattr, MP, "_mission_dir", real)
        self.assertEqual(P.ship_portrait_fallback_face(self.station, self.ship), "")

    # --- the production paths ----------------------------------------------------
    # comms_selection_face is the one seam every Comms selection send goes through
    # (CommsPromise.show_buttons / selected / set_buttons, comms_info).
    def test_a_scanned_station_selected_on_comms_shows_its_portrait(self):
        self._scan()
        self.assertEqual(C.comms_selection_face(self.ship, self.station), self.hull)

    def test_the_selection_seam_is_what_the_sends_use(self):
        import inspect
        src = inspect.getsource(C)
        self.assertNotIn("self.face = faces.get_face(self.selected_id)", src)
        self.assertNotIn("self.face = faces.get_face(event.selected_id)", src)
        self.assertNotIn('send_comms_selection_info(origin_id, "", "white", "unknown")', src)

    def test_the_unknown_selection_shows_the_silhouette(self):
        self.assertEqual(C.comms_selection_face(self.ship, self.station, unknown=True),
                         self.shape or P.ship_portrait_unknown_face())

    def test_a_message_from_a_faceless_station_carries_its_portrait(self):
        got = []
        orig = sbs.send_comms_message_to_player_ship
        sbs.send_comms_message_to_player_ship = (
            lambda contactID, playerID, otherID, faceDesc, *a, **k: got.append(faceDesc))
        self.addCleanup(setattr, sbs, "send_comms_message_to_player_ship", orig)
        C.comms_message("Hollin looks after its own.", self.station, self.ship)
        self.assertEqual(got, [self.hull])

    def test_a_hail_from_a_station_speaker_gets_its_portrait(self):
        from sbs_utils.procedural import amd_action
        real = amd_action.amd_action_actors
        amd_action.amd_action_actors = lambda key: [self.station] if key == "kestrel" else []
        self.addCleanup(setattr, amd_action, "amd_action_actors", real)
        card = H.hail_speaker("kestrel", self.ship)
        self.assertEqual(card.get("face"), self.hull)


if __name__ == "__main__":
    unittest.main()
