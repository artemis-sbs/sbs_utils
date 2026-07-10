import unittest
import itertools
import random

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils import faces


def _roundtrip(race, values, enables):
    s1 = faces.build_face(race, values, enables)
    p = faces.parse_face(s1)
    if p is None:
        return False, s1, None
    s2 = faces.build_face(p["race"], p["values"], p["enables"])
    return s1 == s2, s1, s2


class TestParseFace(unittest.TestCase):
    def test_unknown_returns_none(self):
        self.assertIsNone(faces.parse_face(""))
        self.assertIsNone(faces.parse_face("female"))
        self.assertIsNone(faces.parse_face("not a face"))

    def test_race_detected(self):
        self.assertEqual(faces.parse_face(faces.skaraan(0, 1, 2, 3, 4))["race"], "skaraan")
        self.assertEqual(faces.parse_face(faces.terran(0, 1, 2, None, None, None, None, None, 0, 0))["race"], "terran")

    def test_roundtrip_non_terran(self):
        for race in ("skaraan", "torgoth", "arvonian", "kralien", "ximni"):
            feats = faces.FACE_FEATURES[race]
            combos = list(itertools.product(*[range(f["max"] + 1) for f in feats]))
            random.Random(1).shuffle(combos)
            for vals in combos[:300]:
                rng = random.Random(hash(vals) & 0xffff)
                enables = [rng.getrandbits(1) == 1 if f.get("optional") else True for f in feats]
                ok, s1, s2 = _roundtrip(race, list(vals), enables)
                self.assertTrue(ok, f"{race} {vals} {enables}: {s1!r} != {s2!r}")

    def test_roundtrip_terran(self):
        rng = random.Random(2)
        maxes = [f["max"] for f in faces.FACE_FEATURES["terran"]]
        for _ in range(1500):
            # Eyes/Mouth over their cell range (0-5) keeps the face gender-consistent.
            vals = [rng.randint(0, 1), rng.randint(0, 5), rng.randint(0, 5)] + \
                   [rng.randint(0, m) for m in maxes[3:]]
            enables = [True] * 10
            for i in (3, 4, 5, 6, 7):
                enables[i] = rng.getrandbits(1) == 1
            ok, s1, s2 = _roundtrip("terran", vals, enables)
            self.assertTrue(ok, f"terran {vals} {enables}: {s1!r} != {s2!r}")


if __name__ == "__main__":
    unittest.main()
