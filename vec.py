from dataclasses import dataclass
import math
from random import uniform

@dataclass
class Vec3:
    x: float
    y: float
    z: float
    
    def neg(self): 
        return self.__NEG__()

    def __NEG__(self):
      return Vec3(-self.x, -self.y, -self.z);

    def __add__(self, v):
        return self.add(v)

    def add(self,v):
        if isinstance(v,Vec3):
            return Vec3(self.x + v.x, self.y + v.y, self.z + v.z)
        else:
            return Vec3(self.x + v, self.y + v, self.z + v)
    
    def subtract(self,v):
        return self.__sub__(v)

    def __sub__(self,v):
        if isinstance(v,Vec3):
             return Vec3(self.x - v.x, self.y - v.y, self.z - v.z)
        else:
           return Vec3(self.x - v, self.y - v, self.z - v)
  
    def multiply(self,v):
        return self.__mul__(v)

    def __mul__(self,v):
        if isinstance(v,Vec3): 
            return Vec3(self.x * v.x, self.y * v.y, self.z * v.z)
        else:
            return Vec3(self.x * v, self.y * v, self.z * v);
  
    def divide(self,v):
        return self.__div__(v)

    def __div__(self,v):
        if isinstance(v,Vec3):
            return Vec3(self.x / v.x, self.y / v.y, self.z / v.z)
        else:
            return Vec3(self.x / v, self.y / v, self.z / v);
  
    def equals(self,v):
        return self.__eq__(v)

    def __eq__(self, v) -> bool:
        return self.x == v.x and self.y == v.y and self.z == v.z
  
    def dot(self,v):
        return self.x * v.x + self.y * v.y + self.z * v.z
  
    def cross(self,v):
        return Vec3(
            self.y * v.z - self.z * v.y,
            self.z * v.x - self.x * v.z,
            self.x * v.y - self.y * v.x
        )
  
    def length(self):
        return math.sqrt(self.dot(self))
  
    def unit(self):
        return self.divide(self.length())
  
    def min(self):
        return math.min(math.min(self.x, self.y), self.z)
  
    def max(self,):
        return math.max(math.max(self.x, self.y), self.z)
  
    def toAngles(self,v):
        return {
            'theta': math.atan2(self.z, self.x),
            'phi': math.asin(self.y / self.length())
        }

    def angleTo(self,a):
        return math.acos(self.dot(a) / (self.length() * a.length()))


    def rand_offset(self, r, outer=0, top_only=False, ring=False):
        v = Vec3.rand_in_sphere(r, outer, top_only, ring)
        return self + v

    def rand_in_sphere(radius, outer=0, only_top_half=False, ring=False):
        PI = math.pi
        yaw = uniform(-PI, PI)
        pitch = uniform(0, PI)
        if not only_top_half:
            pitch = uniform(-PI, PI)
        
        ret = Vec3(0,0,0)
        ret.y = math.sin(pitch) * radius

        outRad = math.cos(pitch) * radius
        ret.x = math.sin(yaw) * outRad
        ret.z = math.cos(yaw) * outRad

        # if there is an outer, r is an inner
        if outer>0:
            r = uniform(radius, outer)
            if ring:
                ret.y = 0
            ret = ret.unit()
            
            ret = ret.multiply(r)
            
            
        return ret


