class Vec3(object):
    """Vec3(x: float, y: float, z: float)"""
    def __add__ (self, v):
        """operator add immutable
        
        :param v: the other vector
        :type v: Vec3 or number
        :return: new vector
        :rtype: Vec3"""
    def __eq__ (self, v) -> bool:
        """operator equals immutable
        
        :param v: the other vector
        :type v: Vec3
        :return: new vector
        :rtype: bool"""
    def __iadd__ (self, v):
        """operator inline add (+=) mutable
        
        :param v: the other vector
        :type v: Vec3 or number
        :return: new vector
        :rtype: Vec3"""
    def __imul__ (self, v):
        """operator inline multiply mutable
        
        :param v: the other vector
        :type v: Vec3 or number
        :return: new vector
        :rtype: Vec3"""
    def __init__ (self, x: float, y: float, z: float) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def __isub__ (self, v):
        """operator inline subtract mutable
        
        :param v: the other vector
        :type v: Vec3 or number
        :return: new vector
        :rtype: Vec3"""
    def __iter__ (self):
        ...
    def __itruediv__ (self, v):
        """operator inline divide mutable
        
        :param v: the other vector
        :type v: Vec3 or number
        :return: new vector
        :rtype: Vec3"""
    def __matmul__ (self, v):
        """operator matrix multiply (@) dot product immutable
        
        :param v: the other vector
        :type v: Vec3 or number
        :return: new vector
        :rtype: Vec3"""
    def __mul__ (self, v):
        """operator multiply immutable
        
        :param v: the other vector
        :type v: Vec3 or number
        :return: new vector
        :rtype: Vec3"""
    def __neg__ (self):
        """operator Negate a vector immutable
        
        :return: new vector negated version of this one
        :rtype: Vec3"""
    def __repr__ (self):
        """Return repr(self)."""
    def __sub__ (self, v):
        """operator sub immutable
        
        :param v: the other vector
        :type v: Vec3 or number
        :return: new vector
        :rtype: Vec3"""
    def __truediv__ (self, v):
        """operator divide immutable
        
        :param v: the other vector
        :type v: Vec3 or number
        :return: new vector
        :rtype: Vec3"""
    def _set (self, v):
        ...
    def add (self, v):
        """add immutable
        
        :param v: the other vector
        :type v: Vec3 or number
        :return: new vector
        :rtype: Vec3"""
    def angleTo (self, a):
        ...
    def cross (self, v):
        """cross product immutable
        
        :param v: the other vector
        :type v: Vec3 or number
        :return: new vector
        :rtype: Vec3"""
    def divide (self, v):
        """divide immutable
        
        :param v: the other vector
        :type v: Vec3 or number
        :return: new vector
        :rtype: Vec3"""
    def dot (self, v):
        """dot product immutable
        
        :param v: the other vector
        :type v: Vec3
        :return: new vector
        :rtype: Vec3"""
    def equals (self, v):
        """equals immutable
        
        :param v: the other vector
        :type v: Vec3
        :return: if they are equal
        :rtype: bool"""
    def length (self):
        """length immutable
        
        :return: The length of the vector
        :rtype: float"""
    def max (self):
        """max of x,y,z
        
        :return: max of x,y,z
        :rtype: float"""
    def min (self):
        """min of x,y,z
        
        :return: min of x,y,z
        :rtype: float"""
    def multiply (self, v):
        """multiply immutable
        
        :param v: the other vector
        :type v: Vec3 or number
        :return: new vector
        :rtype: Vec3"""
    def neg (self):
        """Negate a vector immutable
        
        :return: new vector negated version of this one
        :rtype: Vec3"""
    def rand_in_sphere (radius, outer=0, only_top_half=False, ring=False):
        """random within a sphere
        
        :param radius: radius
        :type radius: float
        :param outer: outer radius if 0 r is outer, if non-zero r is inner radius. default=0
        :type outer: float
        :param only_top_half: limit to top half
        :type only_top_half: bool
        :param ring: limit to 2d ring
        :type ring: bool
        :return: A randomly offset vector within the sphere/ring
        :rtype: Vec3"""
    def rand_offset (self, r, outer=0, top_only=False, ring=False):
        """random spherical offset
        
        :param r: radius
        :type r: float
        :param outer: outer radius if 0 r is outer, if non-zero r is inner radius. default=0
        :type outer: float
        :param top_only: limit to top half
        :type top_only: bool
        :param ring: limit to 2d ring
        :type ring: bool
        :return: A randomly offset vector within the sphere/ring
        :rtype: Vec3"""
    def subtract (self, v):
        """subtract immutable
        
        :param v: the other vector
        :type v: Vec3 or number
        :return: new vector
        :rtype: Vec3"""
    def toAngles (self, v):
        """polar angles
        
        :return: theta and phi
        :rtype: theta: float, phi: float"""
    def unit (self):
        """unit vector immutable
        
        :return: new vector
        :rtype: Vec3"""
    @property
    def xyz (self):
        """Get the vector as a tuple
        Useful for passing to arguments e.g. player.spawn(sim, *v.xyz())
        
        :return: a tuple with x,y,z
        :rtype: (float,float,float)"""
