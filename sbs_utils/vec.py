from dataclasses import dataclass
import math
from random import uniform


@dataclass
class Vec3:
    x: float = 0
    y: float = 0
    z: float = 0

    @property
    def xyz(self):
        """Get the vector as a tuple
        Useful for passing to arguments e.g. player.spawn(sim, *v.xyz())

        :return: a tuple with x,y,z
        :rtype: (float,float,float)
        """
        return (self.x,self.y,self.z)

    def __iter__(self):
        return iter((self.x,self.y,self.z))
  
    def neg(self):
        """Negate a vector immutable

        :return: new vector negated version of this one
        :rtype: Vec3
        """
        return self.__neg__()

    def __neg__(self):
        """operator Negate a vector immutable

        :return: new vector negated version of this one
        :rtype: Vec3
        """
        return Vec3(-self.x, -self.y, -self.z)

    def __add__(self, v):
        """ operator add immutable

        :param v: the other vector
        :type v: Vec3 or number
        :return: new vector 
        :rtype: Vec3
        """
        return self.add(v)

    def __iadd__(self, v):
        """operator inline add (+=) mutable

        :param v: the other vector
        :type v: Vec3 or number
        :return: new vector 
        :rtype: Vec3
        """
        r = self.add(v)
        return self._set(r)

    def _set(self, v):
        self.x = v.x
        self.y = v.y
        self.z = v.z
        return self

    def add(self, v):
        """add immutable

        :param v: the other vector
        :type v: Vec3 or number
        :return: new vector 
        :rtype: Vec3
        """
        if isinstance(v, Vec3):
            return Vec3(self.x + v.x, self.y + v.y, self.z + v.z)
        else:
            return Vec3(self.x + v, self.y + v, self.z + v)

    def subtract(self, v):
        """subtract immutable

        :param v: the other vector
        :type v: Vec3 or number
        :return: new vector 
        :rtype: Vec3
        """
        return self.__sub__(v)

    def __sub__(self, v):
        """operator sub immutable

        :param v: the other vector
        :type v: Vec3 or number
        :return: new vector 
        :rtype: Vec3
        """
        if isinstance(v, Vec3):
            return Vec3(self.x - v.x, self.y - v.y, self.z - v.z)
        else:
            return Vec3(self.x - v, self.y - v, self.z - v)

    def __isub__(self, v):
        """operator inline subtract mutable

        :param v: the other vector
        :type v: Vec3 or number
        :return: new vector 
        :rtype: Vec3
        """
        r = self.__sub__(v)
        return self._set(r)

    def multiply(self, v):
        """multiply immutable

        :param v: the other vector
        :type v: Vec3 or number
        :return: new vector 
        :rtype: Vec3
        """
        return self.__mul__(v)

    def __mul__(self, v):
        """operator multiply immutable

        :param v: the other vector
        :type v: Vec3 or number
        :return: new vector 
        :rtype: Vec3
        """
        if isinstance(v, Vec3):
            return Vec3(self.x * v.x, self.y * v.y, self.z * v.z)
        else:
            return Vec3(self.x * v, self.y * v, self.z * v)

    def __imul__(self, v):
        """operator inline multiply mutable

        :param v: the other vector
        :type v: Vec3 or number
        :return: new vector 
        :rtype: Vec3
        """
        r = self.__mul__(v)
        return self._set(r)

    def divide(self, v):
        """divide immutable

        :param v: the other vector
        :type v: Vec3 or number
        :return: new vector 
        :rtype: Vec3
        """
        return self.__truediv__(v)

    def __truediv__(self, v):
        """operator divide immutable

        :param v: the other vector
        :type v: Vec3 or number
        :return: new vector 
        :rtype: Vec3
        """
        if isinstance(v, Vec3):
            return Vec3(self.x / v.x, self.y / v.y, self.z / v.z)
        else:
            return Vec3(self.x / v, self.y / v, self.z / v)

    def __itruediv__(self, v):
        """operator inline divide mutable

        :param v: the other vector
        :type v: Vec3 or number
        :return: new vector 
        :rtype: Vec3
        """
        r = self.__truediv__(v)
        return self._set(r)

    def equals(self, v):
        """equals immutable

        :param v: the other vector
        :type v: Vec3
        :return: if they are equal
        :rtype: bool
        """
        return self.__eq__(v)

    def __eq__(self, v) -> bool:
        """operator equals immutable

        :param v: the other vector
        :type v: Vec3
        :return: new vector 
        :rtype: bool
        """
        return self.x == v.x and self.y == v.y and self.z == v.z

    def dot(self, v):
        """dot product immutable

        :param v: the other vector
        :type v: Vec3
        :return: new vector 
        :rtype: Vec3
        """
        return self.x * v.x + self.y * v.y + self.z * v.z

    def __matmul__(self, v):
        """operator matrix multiply (@) dot product immutable

        :param v: the other vector
        :type v: Vec3 or number
        :return: new vector 
        :rtype: Vec3
        """
        return self.dot(v)

    # def __imatmul__(self, v):
    #     r = self.dot(v)
    #     return self._set(r)

    def cross(self, v):
        """cross product immutable

        :param v: the other vector
        :type v: Vec3 or number
        :return: new vector 
        :rtype: Vec3
        """
        return Vec3(
            self.y * v.z - self.z * v.y,
            self.z * v.x - self.x * v.z,
            self.x * v.y - self.y * v.x
        )

    def length(self):
        """length immutable

        :return: The length of the vector
        :rtype: float
        """
        return math.sqrt(self.dot(self))

    def unit(self):
        """unit vector immutable

        :return: new vector 
        :rtype: Vec3
        """
        return self.divide(self.length())

    def min(self):
        """min of x,y,z

        :return: min of x,y,z
        :rtype: float
        """
        return math.min(math.min(self.x, self.y), self.z)

    def max(self):
        """max of x,y,z

        :return: max of x,y,z
        :rtype: float
        """
        return math.max(math.max(self.x, self.y), self.z)

    def toAngles(self, v):
        """polar angles
        
        :return: theta and phi
        :rtype: theta: float, phi: float
        """
        return {
            'theta': math.atan2(self.z, self.x),
            'phi': math.asin(self.y / self.length())
        }

    def angleTo(self, a):
        return math.acos(self.dot(a) / (self.length() * a.length()))

    def rand_offset(self, r, outer=0, top_only=False, ring=False):
        """ random spherical offset

        :param r: radius
        :type r: float
        :param outer: outer radius if 0 r is outer, if non-zero r is inner radius. default=0
        :type outer: float
        :param top_only: limit to top half
        :type top_only: bool
        :param ring: limit to 2d ring
        :type ring: bool
        :return: A randomly offset vector within the sphere/ring
        :rtype: Vec3
        """
        v = Vec3.rand_in_sphere(r, outer, top_only, ring)
        return self + v

    def rand_in_sphere(radius, outer=0, only_top_half=False, ring=False):
        """ random within a sphere

        :param radius: radius
        :type radius: float
        :param outer: outer radius if 0 r is outer, if non-zero r is inner radius. default=0
        :type outer: float
        :param only_top_half: limit to top half
        :type only_top_half: bool
        :param ring: limit to 2d ring
        :type ring: bool
        :return: A randomly offset vector within the sphere/ring
        :rtype: Vec3
        """

        PI = math.pi
        yaw = uniform(-PI, PI)
        pitch = uniform(0, PI)
        if not only_top_half:
            pitch = uniform(-PI, PI)

        ret = Vec3(0, 0, 0)
        ret.y = math.sin(pitch) * radius

        outRad = math.cos(pitch) * radius
        ret.x = math.sin(yaw) * outRad
        ret.z = math.cos(yaw) * outRad

        # if there is an outer, r is an inner
        if outer > 0:
            r = uniform(radius, outer)
            if ring:
                ret.y = 0
            ret = ret.unit()

            ret = ret.multiply(r)

        return ret
    
    def rotate_around(self, o, ax, ay, az, degrees=True):
        px = self.x - o.x
        py = self.y - o.y
        pz = self.z - o.z
        # rotation on x, y, z
        tx = ax if not degrees else math.radians(ax)
        ty = ay if not degrees else math.radians(ay)
        tz = az if not degrees else math.radians(az)
        # The transformation matrices.
        rx = [1, 0, 0, 0, math.cos(tx), -math.sin(tx), 0, math.sin(tx), math.cos(tx)]
        ry = [math.cos(ty), 0, math.sin(ty), 0, 1, 0, -math.sin(ty), 0, math.cos(ty)]
        rz = [math.cos(tz), -math.sin(tz), 0, math.sin(tz), math.cos(tz), 0, 0, 0, 1]
        # Matrix multiplication
        rotatedX = [(rx[0] * px + rx[1] * py + rx[2] * pz), (rx[3] * px + rx[4] * py + rx[5] * pz), (rx[6] * px + rx[7] * py + rx[8] * pz)]
        px = rotatedX[0]
        py = rotatedX[1]
        pz = rotatedX[2]
        rotatedY = [(ry[0] * px + ry[1] * py + ry[2] * pz), (ry[3] * px + ry[4] * py + ry[5] * pz), (ry[6] * px + ry[7] * py + ry[8] * pz)]
        px = rotatedY[0]
        py = rotatedY[1]
        pz = rotatedY[2]
        rotatedZ = [(rz[0] * px + rz[1] * py + rz[2] * pz), (rz[3] * px + rz[4] * py + rz[5] * pz), (rz[6] * px + rz[7] * py + rz[8] * pz)]
        px = rotatedZ[0]
        py = rotatedZ[1]
        pz = rotatedZ[2]
        return Vec3(px + o.x, py + o.y, pz + o.z)
