"""face_resolve (sbs_utils.faces): declarative face spec -> face string. Promoted from OU.

Run: python -m unittest tests.test_face_resolve
"""
import unittest
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.faces import face_resolve


class FaceResolveTests(unittest.TestCase):
    def test_keyword_makes_a_face(self):
        for kw in ("terran", "male", "female", "fluid", "Terran_Male"):
            f = face_resolve(kw)
            self.assertIsInstance(f, str)
            self.assertTrue(f)                 # a real face string
            self.assertNotEqual(f, kw)         # not the keyword itself

    def test_literal_face_passthrough(self):
        lit = "ter #964b00 8 1;ter #fff 3 5;"
        self.assertEqual(face_resolve(lit), lit)

    def test_empty_defaults_to_terran(self):
        self.assertTrue(face_resolve(None))
        self.assertTrue(face_resolve(""))


if __name__ == "__main__":
    unittest.main()
