from sbs_utils.vec import Vec3
def arc (count, x, y, z, r, start=0.0, end=90.0, random=False):
    """Calculate the points along an circular arc
    
    Args:
        count (int): The number of points to generate
        x,y,z (float,float,float): the center point/origin
        r (float): radius
        start (float, optional): the angle to start at in degrees. Default 0
        end (float, optional): the angle to end at in degrees default 360
    
    Returns:
        points (generator): A generator of Vec3"""
def box (count, x, y, z, x2, y2, z2, centered=False, ax=0, ay=0, az=0, degrees=True):
    """Calculate the points within a box
    
    Args:
    count (int): The number of points to generate
    
    x,y,z (float,float,float): the start point/origin
        if center is true this is the center
        if center is False this is the left, bottom, front
    x2y2,z2 (float,float,float): if center is true this is the width, height, depth
        if center is false this is the right, top, back
    
    center (bool): when true x,y,z and its the center point
        when true x2,y2,z2 is the width, height, depth
        when false x,y,z is left, bottom, front
        when false x2,y2,z2 is right, top, back
    
    Returns:
        points (generator): A generator of Vec3"""
def box_fill (cw, ch, cd, x, y, z, w, h, d, random=False):
    """Calculate the points within a box
        the box is subdivide to ideally avoid overlap
    
    Args:
        cw (int):The number of points to generate for each line width (x)
        ch (int):The number of points to generate for each line height (y)
        cd (int):The number of points to generate for each line width (z)
        x,y,z (float,float,float):the start point/origin
        w (float):the width
        h (float):the height
        d (float):the depth
        random (bool):when true pointw will be randomly placed when false points will be evenly placed
    
    Returns:
        points (generator): A generator of Vec3    """
def line (count, start_x, start_y, start_z, end_x, end_y, end_z, random=False):
    """Calculate the points along a line
    
    Args:
        count (int): The number of points to generate
        start_x (float): the start point/origin
        start_y (float): the start point/origin
        start_z (float): the start point/origin
    
        end_x (float): the end point/origin
        end_y (float): the end point/origin
        end_z (float): the end point/origin
    
    Returns:
        points (generator): A generator of Vec3"""
def rect_fill (cw, cd, x, y, z, w, d, random=False):
    """Calculate the points within a rect
    
    This assumes it to be on y
    
    Args:
        cw (int): The number of points to generate for each line width (x)
        cd (int): The number of points to generate for each line depth (z)
        xy,z (float,float,float): the start point/origin
        w (float): the width (x)
        d (float): the depth (z)
        random (bool): when true pointw will be randomly placed
            when false points will be evenly placed
    
    Returns:
        points (generator): A generator of Vec3"""
def ring (ca, cr, x, y, z, outer_r, inner_r=0, start=0.0, end=90.0, random=False):
    """Calculate the points on rings with each ring has same count
    
    Args:
        ca (int): The number of points to generate on each ring
        cr (int): The number of rings
        x,y,z (float,float,float): the start point/origin
        outer_r (float): the radius
        inner_r (float, optional): the radius inner
        start (float): degrees start angle
        end (float): degrees start angle
        random (bool): when true pointw will be randomly placed. when false points will be evenly placed
    
    Returns:
        points (generator): A generator of Vec3"""
def ring_density (counts, x, y, z, outer_r, inner_r=0, start=0.0, end=90.0, random=False):
    """Calculate the points on rings with each ring specifying count in array
    
    Args:
        count (int): The number of points to generate
        x,y,z (float,float,float): the start point/origin
        outer_r (float): the radius
        inner_r (float  = 0 optional): the radius inner
        start (float (degrees)): start angle
        end (float (degrees)): start angle
        random (bool): when true pointw will be randomly placed.
            when false points will be evenly placed
    
    Returns:
        points (generator): A generator of Vec3"""
def sphere (count, x, y, z, r, outer=0, top_only=False, ring=False):
    """Calculate the points within a sphere or ring
    
    Args:
        count (int): The number of points to generate
        x,y,z (float,float,float): the start point/origin
        r (float): the radius if outer is spedified this is the inner
        outer (float = 0 optional): the height
        top_only (bool): generate only top hemispher
        ring (bool): generate a flat ring
    
    Returns:
        points (generator): A generator of Vec3"""
