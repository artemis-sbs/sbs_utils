"""Declarative sides: side_create (Python port of prefab_side_generic) + the AMD loader.

Run: python -m unittest tests.test_amd_sides
"""
import unittest
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural.sides import side_create, to_side_id, side_are_enemies, side_are_allies
from sbs_utils.procedural.inventory import get_inventory_value
from sbs_utils.procedural.amd_doc import amd_document
from sbs_utils.procedural.amd_sides import amd_side_data, sides_declare, sides_declare_amd, sides_from_section, sides_load_amd


class FakeEvent:
    client_id = 0; tag = ""; sub_tag = ""; origin_id = 0; selected_id = 0
    parent_id = 0; value_tag = ""; extra_tag = ""; extra_extra_tag = ""
    sub_float = 0.0; source_point = None; event_time = 0


class SideCreateTests(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        SpaceObject.clear()

    def test_creates_side_with_fields(self):
        sid = side_create("tsn", "TSN", desc="The navy", color="#07F")
        self.assertIsNotNone(sid)
        self.assertEqual(to_side_id("tsn"), sid)
        self.assertEqual(get_inventory_value(sid, "side_name"), "TSN")
        self.assertEqual(get_inventory_value(sid, "side_desc"), "The navy")

    def test_idempotent_reconfigures(self):
        a = side_create("tsn", "TSN")
        b = side_create("tsn", "TSN2")
        self.assertEqual(a, b)
        self.assertEqual(get_inventory_value(a, "side_name"), "TSN2")

    def test_relations_applied(self):
        side_create("tsn", "TSN")
        side_create("raider", "Raider", enemies="tsn")
        self.assertTrue(side_are_enemies("tsn", "raider"))


class DeclareTests(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        SpaceObject.clear()

    def test_forward_referenced_relation_two_pass(self):
        # tsn names raider as an enemy BEFORE raider is created -> two-pass must still link it
        recs = [{"key": "tsn", "name": "TSN", "enemies": "raider"},
                {"key": "raider", "name": "Raider"}]
        sides_declare(recs)
        self.assertTrue(side_are_enemies("tsn", "raider"))

    def test_capitalized_keys_read(self):
        # sides_from_section must read fence keys regardless of case: a parser that keeps the
        # author's natural case (Color/Enemies) must resolve the same as a lowercasing one.
        node = {"children": [{"key": "tsn", "display_text": "TSN", "description": "The navy.",
                              "data": {"Color": "#07F", "Enemies": "raider"}}]}
        recs = sides_from_section(node)
        self.assertEqual(recs[0].get("color"), "#07F")
        self.assertEqual(recs[0].get("enemies"), "raider")
        self.assertEqual(recs[0].get("name"), "TSN")

    def test_load_amd_bakes_in_parser(self):
        # sides_load_amd must apply amd_side_data itself, so a `Color: #07F` value survives
        # (the default YAML reader would drop it - `#` starts a comment).
        import tempfile, os
        import sbs_utils.fs as fs
        fd, path = tempfile.mkstemp(suffix=".amd")
        os.close(fd)
        with open(path, "w") as f:
            f.write("# [TSN](tsn)\n---\nColor: #07F\nEnemies: raider\n---\nThe navy.\n"
                    "# [Raider](raider)\n---\nColor: #F00\n---\n")
        orig = fs.get_mission_dir_filename
        fs.get_mission_dir_filename = lambda p: path
        try:
            ids = sides_load_amd("ignored.amd")
        finally:
            fs.get_mission_dir_filename = orig
            os.remove(path)
        self.assertEqual(set(ids), {"tsn", "raider"})
        self.assertTrue(side_are_enemies("tsn", "raider"))

    def test_amd_flat_file(self):
        doc = amd_document(
            "# [TSN](tsn)\n---\nColor: #07F\nEnemies: raider\n---\nThe navy.\n"
            "# [Raider](raider)\n---\nColor: #F00\n---\n"
            "# [Civ](civ)\n---\nAllies: tsn\n---\n",
            data_parser=amd_side_data)
        ids = sides_declare_amd(doc)
        self.assertEqual(set(ids), {"tsn", "raider", "civ"})
        self.assertTrue(side_are_enemies("tsn", "raider"))
        self.assertTrue(side_are_allies("civ", "tsn"))
        self.assertEqual(get_inventory_value(ids["tsn"], "side_desc"), "The navy.")


if __name__ == "__main__":
    unittest.main()
