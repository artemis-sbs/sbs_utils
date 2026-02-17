from dataclasses import dataclass
import math
from random import uniform


#@dataclass
class Vec3:
    def __init__(self, *args):
        count = len(args)
        if count == 0:
            self. x = 0
            self. y = 0
            self. z = 0
        elif count==1:
            self. x = args[0].x
            self. y = args[0].y
            self. z = args[0].z
        elif count==2:
            self. x = args[0].x
            self. y = 0
            self. z = args[1].z
        elif count==3:
            self. x = args[0]
            self. y = args[1]
            self. z = args[2]

    @property
    def xyz(self):
        """Get the vector as a tuple
        Useful for passing to arguments e.g. player.spawn(sim, *v.xyz())

        Returns:
            values (tuple): a tuple with x,y,z
        """
        return (self.x,self.y,self.z)

    def __iter__(self):
        return iter((self.x,self.y,self.z))
  
    def neg(self):
        """Negate a vector immutable

        Returns:
            (Vec3):  new vector negated version of this one
        """
        return self.__neg__()

    def __neg__(self):
        """operator Negate a vector immutable

        Returns:
            (Vec3):  new vector negated version of this one
        """
        return Vec3(-self.x, -self.y, -self.z)

    def __add__(self, v):
        """ operator add immutable

        Args:
            v ( Vec3 or number): the other vector

        Returns:
            (Vec3):  new vector 
        """
        return self.add(v)

    def __iadd__(self, v):
        """operator inline add (+=) mutable

        Args:
            v ( Vec3 or number): the other vector

        Returns:
            (Vec3):  new vector 
        """
        r = self.add(v)
        return self._set(r)
    
    @staticmethod
    def create(v):
        ret = Vec3()
        ret._set(v)
        return ret
    
    @staticmethod
    def from2x_coord(x,y,z):
        ret = Vec3(100_000-x, y, 100_000-z)
        return ret


    def _set(self, v):
        self.x = v.x
        self.y = v.y
        self.z = v.z
        return self

    def add(self, v):
        """add immutable

        Args:
            v ( Vec3 or number): the other vector

        Returns:
            (Vec3):  new vector 
        """
        if isinstance(v, Vec3):
            return Vec3(self.x + v.x, self.y + v.y, self.z + v.z)
        else:
            return Vec3(self.x + v, self.y + v, self.z + v)

    def subtract(self, v):
        """subtract immutable

        Args:
            v ( Vec3 or number): the other vector

        Returns:
            (Vec3):  new vector 
        """
        return self.__sub__(v)

    def __sub__(self, v):
        """operator sub immutable

        Args:
            v ( Vec3 or number): the other vector

        Returns:
            (Vec3):  new vector 
        """
        if isinstance(v, Vec3):
            return Vec3(self.x - v.x, self.y - v.y, self.z - v.z)
        else:
            return Vec3(self.x - v, self.y - v, self.z - v)

    def __isub__(self, v):
        """operator inline subtract mutable
        
        Args:
            v ( Vec3 or number): the other vector

        Returns:
            (Vec3):  new vector 
        """
        r = self.__sub__(v)
        return self._set(r)

    def multiply(self, v):
        """multiply immutable

        Args:
            v ( Vec3 or number): the other vector

        Returns:
            (Vec3):  new vector 
        """
        return self.__mul__(v)

    def __mul__(self, v):
        """operator multiply immutable

        Args:
            v ( Vec3 or number): the other vector

        Returns:
            (Vec3):  new vector 
        """
        if isinstance(v, Vec3):
            return Vec3(self.x * v.x, self.y * v.y, self.z * v.z)
        else:
            return Vec3(self.x * v, self.y * v, self.z * v)

    def __imul__(self, v):
        """operator inline multiply mutable

        Args:
            v ( Vec3 or number): the other vector

        Returns:
            (Vec3):  new vector 
        """
        r = self.__mul__(v)
        return self._set(r)

    def divide(self, v):
        """divide immutable

        Args:
            v ( Vec3 or number): the other vector

        Returns:
            (Vec3):  new vector 
        """
        return self.__truediv__(v)

    def __truediv__(self, v):
        """operator divide immutable

        Args:
            v ( Vec3 or number): the other vector

        Returns:
            (Vec3):  new vector 
        """
        if isinstance(v, Vec3):
            return Vec3(self.x / v.x, self.y / v.y, self.z / v.z)
        else:
            return Vec3(self.x / v, self.y / v, self.z / v)

    def __itruediv__(self, v):
        """operator inline divide mutable

        Args:
            v ( Vec3 or number): the other vector

        Returns:
            (Vec3):  new vector 
        """
        r = self.__truediv__(v)
        return self._set(r)

    def equals(self, v):
        """equals immutable

        Args:
            v ( Vec3): the other vector

        Returns:
            (bool):  if they are equal
        """
        return self.__eq__(v)

    def __eq__(self, v) -> bool:
        """operator equals immutable

        Args:
            v ( Vec3): the other vector

        Returns:
            (bool):  new vector 
        """
        return self.x == v.x and self.y == v.y and self.z == v.z

    def dot(self, v):
        """dot product immutable

        Args:
            v ( Vec3): the other vector

        Returns:
            (Vec3):  new vector 
        """
        return self.x * v.x + self.y * v.y + self.z * v.z

    def __matmul__(self, v):
        """operator matrix multiply (@) dot product immutable

        Args:
            v ( Vec3 or number): the other vector

        Returns:
            (Vec3):  new vector 
        """
        return self.dot(v)

    # def __imatmul__(self, v):
    #     r = self.dot(v)
    #     return self._set(r)

    def cross(self, v):
        """cross product immutable

        Args:
            v ( Vec3 or number): the other vector

        Returns:
            (Vec3):  new vector 
        """
        return Vec3(
            self.y * v.z - self.z * v.y,
            self.z * v.x - self.x * v.z,
            self.x * v.y - self.y * v.x
        )

    def length(self):
        """length immutable

        Returns:
            (float):  The length of the vector
        """
        return math.sqrt(self.dot(self))

    def unit(self):
        """unit vector immutable

        Returns:
            (Vec3):  new vector 
        """
        length = self.length()
        if length==0:
            return Vec3()
        return self.divide(length)

    def min(self):
        """min of x,y,z

        Returns:
            (float):  min of x,y,z
        """
        return math.min(math.min(self.x, self.y), self.z)

    def max(self):
        """max of x,y,z

        Returns:
            (float):  max of x,y,z
        """
        return math.max(math.max(self.x, self.y), self.z)

    def toAngles(self):
        """polar angles
        
        Returns:
            theta, phi (float, float):  tuple containing theta and phi
        """
        return {
            'theta': math.atan2(self.z, self.x),
            'phi': math.asin(self.y / self.length())
        }

    def angleTo(self, a):
        """ angle to

        Args:
            a (Vec3): The other point

        Returns:
            float: Angle in radians
        """        
        return math.acos(self.dot(a) / (self.length() * a.length()))

    def rand_offset(self, r, outer=0, top_only=False, ring=False):
        """ random spherical offset

        Args:
            r ( float): radius
            outer ( float): outer radius if 0 r is outer, if non-zero r is inner radius. default=0
            top_only ( bool): limit to top half
            ring ( bool): limit to 2d ring

        Returns:
            (Vec3):  A randomly offset vector within the sphere/ring
        """
        v = Vec3.rand_in_sphere(r, outer, top_only, ring)
        if ring:
            v.y = 0
        return self + v

    def rand_in_sphere(radius, outer=0, only_top_half=False, ring=False):
        """ random within a sphere

        Args:
            radius ( float): radius
            outer ( float): outer radius if 0 r is outer, if non-zero r is inner radius. default=0
            only_top_half ( bool): limit to top half
            ring ( bool): limit to 2d ring

        Returns:
            (Vec3):  A randomly offset vector within the sphere/ring
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
        if ring:
            ret.y = 0
            ret = ret.unit()
            ret = ret.multiply(radius)


        return ret
    
    def rotate_around(self, o, ax, ay, az, degrees=True):
        """Rotate around a point

        Args:
            o (Vec3): origin 
            ax (float): x angle
            ay (float): y angle
            az (float): z angle
            degrees (bool, optional): Use degrees if true, radians if false. Defaults to True.

        Returns:
            Vec3: The new vector
        """        
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
