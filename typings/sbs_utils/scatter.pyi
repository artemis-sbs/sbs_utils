from sbs_utils.vec import Vec3
def arc (count, x, y, z, r, start=0.0, end=90.0, random=False):
    """Calculate the points along an circular arc
    
    Parameters
    ----------
    count: int
        The number of points to generate
    x,y,z: float,float,float
        the center point/origin
    r:radius
    start: float=0, optional
        the angle to start at in degrees
    end: float=360, optional
        the angle to end at in degrees"""
def box_fill (cw, ch, cd, x, y, z, w, h, d, random=False):
    """Calculate the points within a box
    
    
    Parameters
    ----------
    cw: int
        The number of points to generate for each line width (x)
    ch: int
        The number of points to generate for each line height (y)
    cd: int
        The number of points to generate for each line width (z)
    x,y,z: float,float,float
        the start point/origin
    w: float
        the width
    h: float
        the height
    d: float
        the depth
    random: bool
        when true pointw will be randomly placed
        when false points will be evenly placed"""
def line (count, start_x, start_y, start_z, end_x, end_y, end_z, random=False):
    """Calculate the points along a line
    
    Parameters
    ----------
    count: int
        The number of points to generate
    start_x,start_y,start_z: float,float,float
        the start point/origin
    end_x,end_y,end_z: float,float,float
        the end point"""
def rect_fill (cw, cd, x, y, z, w, d, random=False):
    """Calculate the points within a rect
    
    This assumes it to be on y
    
    Parameters
    ----------
    cw: int
        The number of points to generate for each line width (x)
    cd: int
        The number of points to generate for each line depth (z)
    x,y,z: float,float,float
        the start point/origin
    w: float
        the width (x)
    d: float
        the depth (z)
    random: bool
        when true pointw will be randomly placed
        when false points will be evenly placed"""
def ring (ca, cr, x, y, z, outer_r, inner_r=0, start=0.0, end=90.0, random=False):
    """Calculate the points on rings with each ring has same count
    Parameters
    ----------
    ca: int
        The number of points to generate on each ring
    cr: int
        The number of rings
    x,y,z: float,float,float
        the start point/origin
    outer_r: float
        the radius
    inner_r: float  = 0 optional
        the radius inner
    start: float (degrees)
        start angle
    end: float (degrees)
        start angle
    random: bool
        when true pointw will be randomly placed
        when false points will be evenly placed"""
def ring_density (counts, x, y, z, outer_r, inner_r=0, start=0.0, end=90.0, random=False):
    """Calculate the points on rings with each ring specifying count in array
    
    Parameters
    ----------
    count: int
        The number of points to generate
    x,y,z: float,float,float
        the start point/origin
    outer_r: float
        the radius
    inner_r: float  = 0 optional
        the radius inner
    start: float (degrees)
        start angle
    end: float (degrees)
        start angle
    random: bool
        when true pointw will be randomly placed
        when false points will be evenly placed"""
def sphere (count, x, y, z, r, outer=0, top_only=False, ring=False):
    """Calculate the points within a sphere or ring
    
    Parameters
    ----------
    count: int
        The number of points to generate
    x,y,z: float,float,float
        the start point/origin
    r: float
        the radius if outer is spedified this is the inner
    outer: float = 0 optional
        the height
    top_only: bool
        generate only top hemispher
    ring: bool
        generate a flat ring"""
