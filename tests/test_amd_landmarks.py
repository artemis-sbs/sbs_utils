"""Declarative landmark placement (sbs_utils.procedural.amd_landmarks).

Parsing + position resolution (Loc / System + injected placer) are the interesting bits;
spawn is exercised against the mock. Run: python -m unittest tests.test_amd_landmarks
"""
import unittest
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural.amd_doc import amd_document, amd_section
from sbs_utils.procedural.amd import amd_parse_facts
from sbs_utils.procedural.query import to_object
from sbs_utils.procedural import amd_landmarks as L


class FakeEvent:
    client_id = 0; tag = ""; sub_tag = ""; origin_id = 0; selected_id = 0
    parent_id = 0; value_tag = ""; extra_tag = ""; extra_extra_tag = ""
    sub_float = 0.0; source_point = None; event_time = 0


class LandmarkParseTests(unittest.TestCase):
    def test_fence_fields(self):
        d = L.amd_landmark_data("Kind: station\nSide: tsn\nRoles: relay\n"
                                "Art: starbase_science\nLoc: 12000, 0, -8000\n")
        self.assertEqual(d["kind"], "station")
        self.assertEqual(d["side"], "tsn")
        self.assertEqual(d["loc"], [12000.0, 0.0, -8000.0])

    def test_loc_needs_three(self):
        self.assertIsNone(L.amd_landmark_data("Loc: 1, 2\n").get("loc"))


class LandmarkPosTests(unittest.TestCase):
    def setUp(self):
        L.landmark_set_placer(None)

    def test_explicit_loc(self):
        self.assertEqual(L.landmark_pos({"loc": [1, 2, 3]}), [1, 2, 3])

    def test_placer_used_for_system_without_loc(self):
        L.landmark_set_placer(lambda sysc, rec: [sysc[0] * 100, 0, sysc[1] * 100])
        self.assertEqual(L.landmark_pos({"system": [6, 4]}), [600, 0, 400])

    def test_system_plus_loc_is_offset(self):
        L.landmark_set_placer(lambda sysc, rec: [1000, 0, 0])
        self.assertEqual(L.landmark_pos({"system": [1, 0], "loc": [5, 0, 5]}), [1005, 0, 5])

    def test_no_loc_no_placer_is_origin(self):
        self.assertEqual(L.landmark_pos({}), [0.0, 0.0, 0.0])


class LandmarkSpawnTests(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        SpaceObject.clear()
        L.landmark_set_placer(None)

    def _section(self, body):
        doc = amd_document("# [Root](root)\n## [Landmarks](landmarks)\n" + body,
                           data_parser=lambda t: amd_parse_facts(t, L.amd_landmark_facts()))
        return amd_section(doc, "landmarks")

    def test_spawn_station_at_loc(self):
        sec = self._section(
            "### [Relay](relay)\n---\nKind: station\nSide: tsn\nRoles: relay\n"
            "Art: starbase_science\nLoc: 12000, 0, -8000\n---\n")
        objs = L.landmarks_spawn(sec)
        self.assertEqual(len(objs), 1)
        o = to_object(objs[0])
        self.assertAlmostEqual(o.pos.x, 12000, delta=1)
        self.assertAlmostEqual(o.pos.z, -8000, delta=1)

    def test_artless_skipped(self):
        sec = self._section("### [NoArt](noart)\n---\nKind: station\nLoc: 0,0,0\n---\n")
        self.assertEqual(L.landmarks_spawn(sec), [])


if __name__ == "__main__":
    unittest.main()
