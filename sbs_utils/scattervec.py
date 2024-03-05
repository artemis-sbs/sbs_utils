from . import scatter

def arc(count, v, r, start=0.0, end=90.0, random=False):
    """Calculate the points along an circular arc

    Args:
        count (int): The number of points to generate
        v (Vec3): the center point/origin
        r (float): radius
        start (float, optional): the angle to start at in degrees. Default 0
        end (float, optional): the angle to end at in degrees default 360

    Returns:
        points (generator): A generator of Vec3
    """
    return scatter.arc(count, v.x,v.y,v.z, r, start, end, random)

def line(count, start, end, random=False):
    """Calculate the points along a line
    
    Args:
        count (int): The number of points to generate
        start (Vec3): the start point/origin
       
        end (Vec3): the end point/origin
       
    Returns:
        points (generator): A generator of Vec3
    """
    return scatter.line(count, start.x,start.y,start.z, end.x,end.y,end.z, random)


def rect_fill(cw, cd, v, w, d, random=False):
    """Calculate the points within a rect

    This assumes it to be on y
    
    Args:
        cw (int): The number of points to generate for each line width (x)
        cd (int): The number of points to generate for each line depth (z)
        v (Vec3): the start point/origin
        w (float): the width (x)
        d (float): the depth (z)
        random (bool): when true pointw will be randomly placed
            when false points will be evenly placed
    
    Returns:
        points (generator): A generator of Vec3
    """
    return scatter.rect_fill(cw, cd, v.x, v.y, v.z, w, d, random)

def box_fill(cw, ch, cd, v, w, h, d, random=False):
    """Calculate the points within a box
        the box is subdivide to ideally avoid overlap
        
    Args:
        cw (int):The number of points to generate for each line width (x)
        ch (int):The number of points to generate for each line height (y)
        cd (int):The number of points to generate for each line width (z)
        v (Vec3):the start point/origin
        w (float):the width
        h (float):the height
        d (float):the depth
        random (bool):when true pointw will be randomly placed when false points will be evenly placed

    Returns:
        points (generator): A generator of Vec3    
    """
    return scatter.box_fill(cw, ch, cd, v.x, v.y, v.z, w, h, d, random)

def box(count, v1, v2, centered=False, a=None, degrees=True):
    """Calculate the points within a box

    Args:
    count (int): The number of points to generate

    v1 (Vec2): the start point/origin
        if center is true this is the center
        if center is False this is the left, bottom, front
    v2 (Vec3): if center is true this is the width, height, depth
        if center is false this is the right, top, back 

    center (bool): when true x,y,z and its the center point
        when true x2,y2,z2 is the width, height, depth
        when false x,y,z is left, bottom, front
        when false x2,y2,z2 is right, top, back

    Returns:
        points (generator): A generator of Vec3
    """

    if a is not None:
        return scatter.box(count, v1.x,v1.y, v1.z, v2.x, v2.y, v2.z, centered, a.x, a.y,a.z, degrees)
    else:
        return scatter.box(count, v1.x,v1.y, v1.z, v2.x, v2.y, v2.z, centered)
    

def ring(ca, cr, v, outer_r, inner_r=0, start=0.0, end=90.0, random=False):
    """Calculate the points on rings with each ring has same count
    
    Args:
        ca (int): The number of points to generate on each ring
        cr (int): The number of rings
        v (Vec3): the start point/origin
        outer_r (float): the radius
        inner_r (float, optional): the radius inner
        start (float): degrees start angle
        end (float): degrees start angle
        random (bool): when true pointw will be randomly placed. when false points will be evenly placed

    Returns:
        points (generator): A generator of Vec3
    """
    return scatter.ring(ca, cr, v.x,v.y,v.z, outer_r, inner_r, start, end, random)

def ring_density(counts, v,  outer_r, inner_r=0, start=0.0, end=90.0, random=False):
    """Calculate the points on rings with each ring specifying count in array
        
    Args:
        count (int): The number of points to generate
        v (Vec3): the start point/origin
        outer_r (float): the radius
        inner_r (float, optional): the radius inner
        start (float):  (degrees) start angle
        end (float):  (degrees) start angle
        random (bool): when true pointw will be randomly placed. 
            when false points will be evenly placed

    Returns:
        points (generator): A generator of Vec3
    """
    return scatter.ring_density(counts, v.x,v.y,v.z,  outer_r, inner_r, start, end, random)

def sphere(count, v, r, outer=0, top_only=False, ring=False):
    """Calculate the points within a sphere or ring
        
    Args:
        count (int): The number of points to generate
        v (Vec3): the start point/origin
        r (float): the radius if outer is spedified this is the inner
        outer (float = 0 optional): the height
        top_only (bool): generate only top hemispher 
        ring (bool): generate a flat ring
    
    Returns:
        points (generator): A generator of Vec3
    """
    return scatter.sphere(count, v.x,v.y,v.z, r, outer, top_only, ring)