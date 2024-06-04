class Vec3(object):
    """class Vec3"""
    def __add__ (self, v):
        """operator add immutable
        
        Args:
            v ( Vec3 or number): the other vector
        
        Returns:
            (Vec3):  new vector """
    def __eq__ (self, v) -> bool:
        """operator equals immutable
        
        Args:
            v ( Vec3): the other vector
        
        Returns:
            (bool):  new vector """
    def __iadd__ (self, v):
        """operator inline add (+=) mutable
        
        Args:
            v ( Vec3 or number): the other vector
        
        Returns:
            (Vec3):  new vector """
    def __imul__ (self, v):
        """operator inline multiply mutable
        
        Args:
            v ( Vec3 or number): the other vector
        
        Returns:
            (Vec3):  new vector """
    def __init__ (self, *args):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def __isub__ (self, v):
        """operator inline subtract mutable
        
        Args:
            v ( Vec3 or number): the other vector
        
        Returns:
            (Vec3):  new vector """
    def __iter__ (self):
        ...
    def __itruediv__ (self, v):
        """operator inline divide mutable
        
        Args:
            v ( Vec3 or number): the other vector
        
        Returns:
            (Vec3):  new vector """
    def __matmul__ (self, v):
        """operator matrix multiply (@) dot product immutable
        
        Args:
            v ( Vec3 or number): the other vector
        
        Returns:
            (Vec3):  new vector """
    def __mul__ (self, v):
        """operator multiply immutable
        
        Args:
            v ( Vec3 or number): the other vector
        
        Returns:
            (Vec3):  new vector """
    def __neg__ (self):
        """operator Negate a vector immutable
        
        Returns:
            (Vec3):  new vector negated version of this one"""
    def __sub__ (self, v):
        """operator sub immutable
        
        Args:
            v ( Vec3 or number): the other vector
        
        Returns:
            (Vec3):  new vector """
    def __truediv__ (self, v):
        """operator divide immutable
        
        Args:
            v ( Vec3 or number): the other vector
        
        Returns:
            (Vec3):  new vector """
    def _set (self, v):
        ...
    def add (self, v):
        """add immutable
        
        Args:
            v ( Vec3 or number): the other vector
        
        Returns:
            (Vec3):  new vector """
    def angleTo (self, a):
        """angle to
        
        Args:
            a (Vec3): The other point
        
        Returns:
            float: Angle in radians"""
    def create (v):
        ...
    def cross (self, v):
        """cross product immutable
        
        Args:
            v ( Vec3 or number): the other vector
        
        Returns:
            (Vec3):  new vector """
    def divide (self, v):
        """divide immutable
        
        Args:
            v ( Vec3 or number): the other vector
        
        Returns:
            (Vec3):  new vector """
    def dot (self, v):
        """dot product immutable
        
        Args:
            v ( Vec3): the other vector
        
        Returns:
            (Vec3):  new vector """
    def equals (self, v):
        """equals immutable
        
        Args:
            v ( Vec3): the other vector
        
        Returns:
            (bool):  if they are equal"""
    def length (self):
        """length immutable
        
        Returns:
            (float):  The length of the vector"""
    def max (self):
        """max of x,y,z
        
        Returns:
            (float):  max of x,y,z"""
    def min (self):
        """min of x,y,z
        
        Returns:
            (float):  min of x,y,z"""
    def multiply (self, v):
        """multiply immutable
        
        Args:
            v ( Vec3 or number): the other vector
        
        Returns:
            (Vec3):  new vector """
    def neg (self):
        """Negate a vector immutable
        
        Returns:
            (Vec3):  new vector negated version of this one"""
    def rand_in_sphere (radius, outer=0, only_top_half=False, ring=False):
        """random within a sphere
        
        Args:
            radius ( float): radius
            outer ( float): outer radius if 0 r is outer, if non-zero r is inner radius. default=0
            only_top_half ( bool): limit to top half
            ring ( bool): limit to 2d ring
        
        Returns:
            (Vec3):  A randomly offset vector within the sphere/ring"""
    def rand_offset (self, r, outer=0, top_only=False, ring=False):
        """random spherical offset
        
        Args:
            r ( float): radius
            outer ( float): outer radius if 0 r is outer, if non-zero r is inner radius. default=0
            top_only ( bool): limit to top half
            ring ( bool): limit to 2d ring
        
        Returns:
            (Vec3):  A randomly offset vector within the sphere/ring"""
    def rotate_around (self, o, ax, ay, az, degrees=True):
        """Rotate around a point
        
        Args:
            o (Vec3): origin
            ax (float): x angle
            ay (float): y angle
            az (float): z angle
            degrees (bool, optional): Use degrees if true, radians if false. Defaults to True.
        
        Returns:
            Vec3: The new vector"""
    def subtract (self, v):
        """subtract immutable
        
        Args:
            v ( Vec3 or number): the other vector
        
        Returns:
            (Vec3):  new vector """
    def toAngles (self):
        """polar angles
        
        Returns:
            theta, phi (float, float):  tuple containing theta and phi"""
    def unit (self):
        """unit vector immutable
        
        Returns:
            (Vec3):  new vector """
    @property
    def xyz (self):
        """Get the vector as a tuple
        Useful for passing to arguments e.g. player.spawn(sim, *v.xyz())
        
        Returns:
            values (tuple): a tuple with x,y,z"""
