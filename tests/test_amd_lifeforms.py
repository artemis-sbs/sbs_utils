"""amd_lifeforms - author a mission's named characters (crew, contacts, comms NPCs) as an AMD
section and spawn them as lifeforms via face_resolve, returning a {key: lifeform} map.

Run: python -m unittest tests.test_amd_lifeforms
"""
import unittest
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.faces import get_face
from sbs_utils.procedural.roles import has_role
from sbs_utils.procedural.amd_lifeforms import (
    lifeforms_from_section, lifeforms_spawn, lifeform_speaker, lifeform_speaker_of, amd_lifeform_data)


def _section():
    # mimic document_get_amd_file's parsed shape: children with key/display_text/description/data
    return {"children": [
        {"key": "deck_chief", "display_text": "Deck Chief Renner", "description": "Keeps the logs.",
         "data": {"face": "terran_male", "roles": "informant"}},
        {"key": "cargo_master", "display_text": "Cargo Master Pell", "description": "",
         "data": {"face": "terran_female", "roles": "informant", "color": "#0cf"}},
    ]}


class AmdLifeformsTests(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        SpaceObject.clear()

    def test_records_read(self):
        recs = lifeforms_from_section(_section())
        self.assertEqual(len(recs), 2)
        self.assertEqual(recs[0].key, "deck_chief")
        self.assertEqual(recs[0].name, "Deck Chief Renner")
        self.assertEqual(recs[0].face, "terran_male")
        self.assertEqual(recs[0].color, "green")        # default
        self.assertEqual(recs[1].color, "#0cf")         # authored

    def test_spawn_map(self):
        cast = lifeforms_spawn(_section())
        self.assertEqual(set(cast.keys()), {"deck_chief", "cargo_master"})
        dc = cast["deck_chief"]
        self.assertEqual(dc.name, "Deck Chief Renner")
        self.assertTrue(get_face(dc.id))                 # Face keyword resolved to a face string
        self.assertTrue(has_role(dc.id, "informant"))    # Roles assigned

    def test_speaker_card(self):
        recs = lifeforms_from_section(_section())
        sp = lifeform_speaker(recs, "cargo_master")
        self.assertEqual(sp.name, "Cargo Master Pell")
        self.assertEqual(sp.color, "#0cf")
        self.assertIsNone(lifeform_speaker(recs, "not_a_key"))

    def test_data_parser_default_coercion(self):
        d = amd_lifeform_data("Face: terran_male\nRoles: informant")
        self.assertEqual(d.get("face"), "terran_male")
        self.assertEqual(d.get("roles"), "informant")

    def test_speaker_of_spawned_lifeform(self):
        # the cast route resolves the speaker from the hailed lifeform itself
        cast = lifeforms_spawn(_section())
        sp = lifeform_speaker_of(cast["cargo_master"].id)
        self.assertEqual(sp.name, "Cargo Master Pell")
        self.assertEqual(sp.key, "cargo_master")
        self.assertEqual(sp.color, "#0cf")            # stored lf_color
        self.assertEqual(sp.leans, {})
        self.assertIsNone(lifeform_speaker_of(None))

    def test_none_section_safe(self):
        self.assertEqual(lifeforms_from_section(None), [])
        self.assertEqual(lifeforms_spawn(None), {})


if __name__ == "__main__":
    unittest.main()
