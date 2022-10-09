from sbs_utils.vec import Vec3
import unittest
class TestVec3(unittest.TestCase):

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

    def test_neg(self):
        v = Vec3(1,2,3)
        n = v.neg()
        self.assertEqual(v.x, 1)
        self.assertEqual(v.y, 2)
        self.assertEqual(v.z, 3)
        self.assertEqual(n.x, -1)
        self.assertEqual(n.y, -2)
        self.assertEqual(n.z, -3)
        # test __neg__ overload
        v = Vec3(1,2,3)
        n = -v
        self.assertEqual(v.x, 1)
        self.assertEqual(v.y, 2)
        self.assertEqual(v.z, 3)
        self.assertEqual(n.x, -1)
        self.assertEqual(n.y, -2)
        self.assertEqual(n.z, -3)

    def test_add(self):
        v1 = Vec3(1,2,3)
        v2 = Vec3(4,5,6)
        n = v1.add(v2)
        self.assertEqual(n.x, 5)
        self.assertEqual(n.y, 7)
        self.assertEqual(n.z, 9)

        self.assertEqual(v1.x, 1)
        self.assertEqual(v1.y, 2)
        self.assertEqual(v1.z, 3)
        self.assertEqual(v2.x, 4)
        self.assertEqual(v2.y, 5)
        self.assertEqual(v2.z, 6)

        v1 = Vec3(1,2,3)
        v2 = Vec3(4,5,6)
        n = v1 + v2
        self.assertEqual(n.x, 5)
        self.assertEqual(n.y, 7)
        self.assertEqual(n.z, 9)

        v1 = Vec3(10,20,30)
        v1 += 5
        self.assertEqual(v1.x, 15)
        self.assertEqual(v1.y, 25)
        self.assertEqual(v1.z, 35)

    def test_sub(self):
        v1 = Vec3(1,2,3)
        v2 = Vec3(4,5,6)
        n = v1.subtract(v2)
        self.assertEqual(n.x, -3)
        self.assertEqual(n.y, -3)
        self.assertEqual(n.z, -3)

        self.assertEqual(v1.x, 1)
        self.assertEqual(v1.y, 2)
        self.assertEqual(v1.z, 3)
        self.assertEqual(v2.x, 4)
        self.assertEqual(v2.y, 5)
        self.assertEqual(v2.z, 6)

        v1 = Vec3(1,2,3)
        v2 = Vec3(4,5,6)
        n = v1 - v2
        self.assertEqual(n.x, -3)
        self.assertEqual(n.y, -3)
        self.assertEqual(n.z, -3)

        v1 = Vec3(10,20,30)
        v1 -= 5
        self.assertEqual(v1.x, 5)
        self.assertEqual(v1.y, 15)
        self.assertEqual(v1.z, 25)

    def test_mul(self):
        v1 = Vec3(1,2,3)
        v2 = Vec3(4,5,6)
        n = v1.multiply(v2)

        self.assertEqual(n.x, 4)
        self.assertEqual(n.y, 10)
        self.assertEqual(n.z, 18)

        self.assertEqual(v1.x, 1)
        self.assertEqual(v1.y, 2)
        self.assertEqual(v1.z, 3)
        self.assertEqual(v2.x, 4)
        self.assertEqual(v2.y, 5)
        self.assertEqual(v2.z, 6)

        v1 = Vec3(1,2,3)
        v2 = Vec3(4,5,6)
        n = v1 * v2
        self.assertEqual(n.x, 4)
        self.assertEqual(n.y, 10)
        self.assertEqual(n.z, 18)

        v1 = Vec3(1,2,3)
        n = v1 * 5
        self.assertEqual(n.x, 5)
        self.assertEqual(n.y, 10)
        self.assertEqual(n.z, 15)

        v1 = Vec3(10,20,30)
        v1 *= 5
        self.assertEqual(v1.x, 50)
        self.assertEqual(v1.y, 100)
        self.assertEqual(v1.z, 150)

    def test_div(self):
        v1 = Vec3(10,20,30)
        v2 = Vec3(4,5,6)
        n = v1.divide(v2)

        self.assertEqual(n.x, 2.5)
        self.assertEqual(n.y, 4)
        self.assertEqual(n.z, 5)

        self.assertEqual(v1.x, 10)
        self.assertEqual(v1.y, 20)
        self.assertEqual(v1.z, 30)
        self.assertEqual(v2.x, 4)
        self.assertEqual(v2.y, 5)
        self.assertEqual(v2.z, 6)

        v1 = Vec3(10,20,30)
        v2 = Vec3(4,5,6)
        n = v1 / v2
        self.assertEqual(n.x, 2.5)
        self.assertEqual(n.y, 4)
        self.assertEqual(n.z, 5)

        v1 = Vec3(10,20,30)
        n = v1 / 5
        self.assertEqual(n.x, 2)
        self.assertEqual(n.y, 4)
        self.assertEqual(n.z, 6)

        # inline
        v1 = Vec3(10,20,30)
        v1 /= 5
        self.assertEqual(v1.x, 2)
        self.assertEqual(v1.y, 4)
        self.assertEqual(v1.z, 6)

    def test_dot(self):
        v1 = Vec3(10,20,30)
        v2 = Vec3(4,5,6)
        n = v1.dot(v2)

        self.assertEqual(n, 320)

        self.assertEqual(v1.x, 10)
        self.assertEqual(v1.y, 20)
        self.assertEqual(v1.z, 30)
        self.assertEqual(v2.x, 4)
        self.assertEqual(v2.y, 5)
        self.assertEqual(v2.z, 6)

        v1 = Vec3(10,20,30)
        v2 = Vec3(4,5,6)
        n = v1 @ v2
        self.assertEqual(n, 320)


