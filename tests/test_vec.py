from sbs_utils.vec import Vec3
import unittest
class TestStringMethods(unittest.TestCase):

    def test_init(self):
        v = Vec3(1,2,3)
        self.assertEqual(v.x, 1)
        self.assertEqual(v.y, 2)
        self.assertEqual(v.z, 3)

    def test_neg(self):
        v = Vec3(1,2,3)
        n = v.neg()
        self.assertEqual(v.x, 1)
        self.assertEqual(v.y, 2)
        self.assertEqual(v.z, 3)
        self.assertEqual(n.x, -1)
        self.assertEqual(n.y, -2)
        self.assertEqual(n.z, -3)

