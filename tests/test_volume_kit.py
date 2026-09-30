"""Wall KITS: a relic built from an art pack's pieces instead of grey plates.

The claims, each the kind that fails silently:

* a kit piece stands UPRIGHT - its local +Y is world up on a wall - where the plates'
  rotation put local +Y at world -Y on every side wall (harmless for a square slab, a
  statue on its head for anything with a top);
* a box's -Y face is its FLOOR and gets floor pieces, its +Y face ceiling pieces;
* a kit is BUDGETED - its pieces grow together until the relic fits `n`;
* a kit that did not load is a FALLBACK, never a half-registered style: `Walls: torgoth,
  plates` wears plates, and a pack whose art the engine would not find is not loaded;
* a `Dress:` set piece stands in for the generic primitive of the solid it dresses.

Run: python -m unittest tests.test_volume_kit
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import json
import math
import os
import tempfile
import unittest

import sbs_utils.mast_sbs.story_nodes  # noqa: F401 - import first, circular import

from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural.query import to_object
from sbs_utils.procedural.roles import role
from sbs_utils.procedural import volume_kit as K
from sbs_utils.procedural import amd_relics as R
from sbs_utils.procedural.volume import (volume_define, volume_box, volume_clear,
                                         volume_look_quat, volume_solid)
from sbs_utils.procedural.volume_dress import volume_dress, _dress_style, STYLES

MANIFEST = {
    "version": 1, "pack": "kt", "ships": "kt_ships", "units_per_metre": 10,
    "pieces": {
        "kt_wall_a": {"kind": "wall", "kit": "tk", "size": [40, 40, 4], "tris": 12},
        "kt_wall_b": {"kind": "wall", "kit": "tk", "size": [40, 40, 4], "tris": 12},
        "kt_floor": {"kind": "floor", "kit": "tk", "size": [40, 40, 2], "tris": 12},
        "kt_ceiling": {"kind": "ceiling", "kit": "tk", "size": [40, 40, 2], "tris": 12},
        "kt_trim": {"kind": "trim", "kit": "tk", "size": [40, 4, 2], "tris": 12},
        "kt_pillar": {"kind": "pillar", "kit": "tk", "size": [6, 40, 6], "tris": 12},
        "kt_statue": {"kind": "setpiece", "kit": "tk", "size": [20, 60, 20], "tris": 12},
        "kt_machine": {"kind": "setpiece", "kit": "tk", "size": [40, 20, 40], "tris": 12},
    },
    "kits": {"tk": {"scale": 8.0, "wall": ["kt_wall_a", "kt_wall_b"], "floor": ["kt_floor"],
                    "ceiling": ["kt_ceiling"], "trim": ["kt_trim"], "pillar": ["kt_pillar"],
                    "setpieces": ["kt_statue", "kt_machine"]}},
}


def _rotate(q, v):
    """Rotate vector v by quaternion q = (w, x, y, z)."""
    w, x, y, z = q
    vx, vy, vz = v
    # t = 2 * cross(q.xyz, v); v' = v + w t + cross(q.xyz, t)
    tx, ty, tz = 2 * (y * vz - z * vy), 2 * (z * vx - x * vz), 2 * (x * vy - y * vx)
    return (vx + w * tx + (y * tz - z * ty), vy + w * ty + (z * tx - x * tz),
            vz + w * tz + (x * ty - y * tx))


class TheLookQuat(unittest.TestCase):
    def close(self, a, b):
        for i in range(3):
            self.assertAlmostEqual(a[i], b[i], places=5)

    def test_a_wall_piece_is_upright_on_every_wall(self):
        for facing in ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0.6, 0, 0.8)):
            q = volume_look_quat(facing)
            self.close(_rotate(q, (0, 0, 1)), facing)
            self.close(_rotate(q, (0, 1, 0)), (0, 1, 0))

    def test_a_floor_faces_up_and_runs_its_pattern_along_z(self):
        q = volume_look_quat((0, 1, 0), (0, 1, 0), (0, 0, 1))
        self.close(_rotate(q, (0, 0, 1)), (0, 1, 0))
        self.close(_rotate(q, (0, 1, 0)), (0, 0, 1))

    def test_it_is_never_a_mirror(self):
        """x = y cross z: a proper rotation, so a piece is turned, never flipped."""
        for facing in ((1, 0, 0), (0, -1, 0), (0.3, 0.2, -0.9)):
            q = volume_look_quat(facing)
            x, y, z = (_rotate(q, (1, 0, 0)), _rotate(q, (0, 1, 0)), _rotate(q, (0, 0, 1)))
            cross = (y[1] * z[2] - y[2] * z[1], y[2] * z[0] - y[0] * z[2],
                     y[0] * z[1] - y[1] * z[0])
            self.close(cross, x)


class _KitBase(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        SpaceObject.clear()
        volume_clear()
        K.volume_kits_clear()

    def tearDown(self):
        K.volume_kits_clear()
        volume_clear()
        R.relics_clear()

    def props(self, tag="wall"):
        return [to_object(i) for i in role(tag)]

    def arts(self, tag="wall"):
        return [so.art_id for so in self.props(tag)]


class TheKitIsAStyle(_KitBase):
    def test_registering_a_kit_makes_it_nameable(self):
        self.assertEqual(K.volume_kit_register(MANIFEST), ["tk"])
        self.assertIn("tk", STYLES)
        self.assertEqual(_dress_style("tk").kit, "tk")

    def test_a_chain_falls_back_when_the_kit_is_absent(self):
        self.assertIs(_dress_style("tk, plates"), STYLES["plates"])
        K.volume_kit_register(MANIFEST)
        self.assertEqual(_dress_style("tk, plates").kit, "tk")

    def test_none_in_a_chain_is_an_answer(self):
        self.assertIsNone(_dress_style("none, plates"))

    def test_a_kit_cannot_replace_a_built_in(self):
        bad = json.loads(json.dumps(MANIFEST))
        bad["kits"] = {"plates": bad["kits"]["tk"]}
        K.volume_kit_register(bad)
        self.assertIsNone(STYLES["plates"].kit)

    def test_the_reset_forgets_the_kit_and_its_style(self):
        K.volume_kit_register(MANIFEST)
        K.volume_kits_clear()
        self.assertNotIn("tk", STYLES)
        self.assertEqual(K.volume_kits_count(), 0)


class ABoxIsARoom(_KitBase):
    def setUp(self):
        super().setUp()
        K.volume_kit_register(MANIFEST)
        volume_define("t", {})
        volume_box("t", "hall", 0, 0, 0, 1600, 640, 960)

    def test_the_floor_gets_floor_pieces_and_the_ceiling_ceiling_pieces(self):
        volume_dress("t", n=2000, seed=3, style="tk", roles="wall", debris=0, gaps=0.0)
        below = [so.art_id for so in self.props() if so.pos.y < -640]
        above = [so.art_id for so in self.props() if so.pos.y > 640]
        self.assertTrue(below and set(below) == {"kt_floor"}, below[:5])
        self.assertTrue(above and set(above) == {"kt_ceiling"}, above[:5])

    def test_walls_are_upright_and_face_the_room(self):
        volume_dress("t", n=2000, seed=3, style="tk", roles="wall", debris=0, gaps=0.0)
        walls = [so for so in self.props() if so.art_id in ("kt_wall_a", "kt_wall_b")]
        self.assertTrue(walls)
        for so in walls:
            q = so.engine_object.rot_quat
            q = (q.w, q.x, q.y, q.z)
            up = _rotate(q, (0, 1, 0))
            self.assertAlmostEqual(up[1], 1.0, places=4, msg="a wall piece stands upright")
            face = _rotate(q, (0, 0, 1))
            # Facing INTO the room: toward the centre from where it stands.
            to_centre = (-so.pos.x, 0.0, -so.pos.z)
            self.assertGreater(face[0] * to_centre[0] + face[2] * to_centre[2], 0.0)

    def test_a_face_is_covered_edge_to_edge(self):
        volume_dress("t", n=2000, seed=3, style="tk", roles="wall", debris=0, gaps=0.0)
        area = 0.0
        for so in self.props():
            if so.art_id != "kt_floor":
                continue
            ds = so.data_set
            area += (ds.get("local_scale_x_coeff", 0) * 40.0) * \
                (ds.get("local_scale_y_coeff", 0) * 40.0)
        self.assertAlmostEqual(area, 3200.0 * 1920.0, delta=1.0)

    def test_trims_and_corner_pillars_are_laid(self):
        volume_dress("t", n=2000, seed=3, style="tk", roles="wall", debris=0, gaps=0.0)
        arts = self.arts()
        self.assertIn("kt_trim", arts)
        self.assertEqual(arts.count("kt_pillar"), 4)

    def test_the_budget_grows_the_pieces_instead_of_blowing_the_count(self):
        volume_dress("t", n=2000, seed=3, style="tk", roles="wall", debris=0, gaps=0.0)
        many = sum(1 for a in self.arts() if a in ("kt_floor", "kt_ceiling", "kt_wall_a",
                                                   "kt_wall_b"))
        SpaceObject.clear()
        volume_define("t", {})
        volume_box("t", "hall", 0, 0, 0, 1600, 640, 960)
        volume_dress("t", n=40, seed=3, style="tk", roles="wall", debris=0, gaps=0.0)
        few = sum(1 for a in self.arts() if a in ("kt_floor", "kt_ceiling", "kt_wall_a",
                                                  "kt_wall_b"))
        self.assertLess(few, many)
        self.assertLessEqual(few, 40)

    def test_a_doorway_has_no_wall_and_no_trim_across_it(self):
        volume_box("t", "next", 2400, 0, 0, 900, 300, 300)     # opens off the +X wall
        volume_dress("t", n=4000, seed=3, style="tk", roles="wall", debris=0, gaps=0.0)
        for so in self.props():
            if so.art_id not in ("kt_wall_a", "kt_wall_b", "kt_trim"):
                continue
            in_door = (abs(so.pos.x - 1600) < 60 and abs(so.pos.y) < 280
                       and abs(so.pos.z) < 280)
            self.assertFalse(in_door, "%s at %s blocks the doorway" % (so.art_id, so.pos))

    def test_a_curved_room_reads_floor_wall_ceiling(self):
        volume_define("c", {"cave": (0, 0, 0, 1500)})
        volume_dress("c", n=300, seed=3, style="tk", roles="cave", debris=0)
        floors = [so for so in self.props("cave") if so.art_id == "kt_floor"]
        ceilings = [so for so in self.props("cave") if so.art_id == "kt_ceiling"]
        self.assertTrue(floors and ceilings)
        self.assertTrue(all(so.pos.y < 0 for so in floors))
        self.assertTrue(all(so.pos.y > 0 for so in ceilings))

    def test_a_kit_ignores_art_so_art_is_the_fallbacks(self):
        volume_dress("t", n=600, seed=3, style="tk", art="plain_asteroid_6", roles="wall",
                     debris=0)
        self.assertNotIn("plain_asteroid_6", self.arts())


RELIC_AMD = """# [Kit Test](kit_doc)

## [Relics](relics)

### [Kit Hall](khall)
---
Loc: 0, 0, 0
Walls: tk, plates
Debris: 0
Gaps: 0
---

### [hall](hall)
---
Relic: khall
Box: 0, 0, 0, 1600, 640, 960
---

### [the cradle](cradle)
---
Relic: khall
Solid: box, 800, -440, 0, 200, 200, 200
Dress: kt_machine
---

### [the statue](statue)
---
Relic: khall
Point: -1000, -300, 0
Dress: kt_statue 1.5, generic-cylinder
Facing: far_end
---

### [the far end](far_end)
---
Relic: khall
Point: 1400, -300, 0
---
"""


class RelicWalls(_KitBase):
    def load(self):
        R.relics_load("khall_test.amd", content=RELIC_AMD)
        R.relic_volume(R.relic_record("khall"))

    def test_without_the_kit_the_relic_wears_its_fallback(self):
        self.load()
        R.relic_walls("khall", roles="wall")
        arts = set(self.arts())
        self.assertIn("generic-rectangle", arts)
        self.assertFalse(any(a.startswith("kt_wall") for a in arts))

    def test_with_the_kit_the_relic_wears_it(self):
        K.volume_kit_register(MANIFEST)
        self.load()
        R.relic_walls("khall", roles="wall")
        arts = set(self.arts())
        self.assertIn("kt_floor", arts)
        self.assertNotIn("generic-rectangle", arts)

    def test_a_dressed_solid_is_the_piece_not_a_cube(self):
        K.volume_kit_register(MANIFEST)
        self.load()
        R.relic_walls("khall", roles="wall")
        arts = self.arts()
        self.assertEqual(arts.count("kt_machine"), 1)
        machine = [so for so in self.props() if so.art_id == "kt_machine"][0]
        self.assertAlmostEqual(machine.pos.x, 800.0)
        # Fitted INSIDE the box: 400 across, the piece 40 x 20 x 40 -> scale 10.
        self.assertAlmostEqual(machine.data_set.get("local_scale_x_coeff", 0), 10.0)

    def test_a_point_set_piece_stands_facing_its_facing(self):
        K.volume_kit_register(MANIFEST)
        self.load()
        R.relic_walls("khall", roles="wall")
        statue = [so for so in self.props() if so.art_id == "kt_statue"][0]
        q = statue.engine_object.rot_quat
        face = _rotate((q.w, q.x, q.y, q.z), (0, 0, 1))
        self.assertAlmostEqual(face[0], 1.0, places=4)     # towards the far end, +X
        self.assertAlmostEqual(statue.data_set.get("local_scale_y_coeff", 0), 12.0)

    def test_a_dress_list_falls_back_to_a_key_the_engine_knows(self):
        self.load()                                        # no kit: kt_statue unknown
        from sbs_utils.procedural import volume_dress as VD
        orig = VD._known_art
        VD._known_art = lambda keys: [k for k in keys if not k.startswith("kt_")]
        try:
            R.relic_walls("khall", roles="wall")
        finally:
            VD._known_art = orig
        self.assertIn("generic-cylinder", self.arts())


class LoadingAPack(_KitBase):
    def setUp(self):
        super().setUp()
        self.dir = tempfile.mkdtemp()
        with open(os.path.join(self.dir, "kt_kit.json"), "w", encoding="utf-8") as f:
            json.dump(MANIFEST, f)
        with open(os.path.join(self.dir, "kt_ships.json"), "w", encoding="utf-8") as f:
            f.write('{"#ship-list": []}\n')

    def test_a_manifest_on_disk_registers_its_kits(self):
        self.assertEqual(K.volume_kit_load("kt", path=self.dir, ships=False), ["tk"])
        self.assertEqual(K.volume_kit_load("kt", path=self.dir, ships=False), ["tk"])

    def test_a_missing_pack_registers_nothing(self):
        self.assertEqual(K.volume_kit_load("nope", path=self.dir), [])
        self.assertNotIn("tk", STYLES)

    def test_with_extra_ship_data_off_nothing_is_registered(self):
        from sbs_utils.procedural import ship_data as SD
        SD.extra_ship_data_force(False)
        try:
            self.assertEqual(K.volume_kit_load("kt", path=self.dir), [])
        finally:
            SD.extra_ship_data_force(None)
        self.assertNotIn("tk", STYLES)

    def test_art_the_engine_cannot_find_registers_nothing(self):
        from sbs_utils.procedural import ship_data as SD
        orig = SD._art_that_is_not_there
        SD._art_that_is_not_there = lambda text: [("kt_wall_a", "data/missions/x/kt")]
        SD.extra_ship_data_force(True)
        try:
            self.assertEqual(K.volume_kit_load("kt", path=self.dir), [])
        finally:
            SD._art_that_is_not_there = orig
            SD.extra_ship_data_force(None)
        self.assertNotIn("tk", STYLES)


if __name__ == "__main__":
    unittest.main()
