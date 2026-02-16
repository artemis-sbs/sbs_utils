from . import scatter
from collections.abc import Generator

def arc(count, v, r, start=0.0, end=90.0, random=False) -> Generator:
    """
    Calculate the points along an circular arc.

    Args:
        count (int): The number of points to generate.
        v (Vec3): The center point/origin
        r (float): The radius of the arc.
        start (float, optional): The angle to start at in degrees. Default is 0.
        end (float, optional): The angle to end at in degrees default 360. Default is 90.0.
        random (bool): Should the points be randomly placed along the arc (True), or evenly spaced (False)?

    Returns:
        points (Generator): A generator of Vec3
    """
    return scatter.arc(count, v.x,v.y,v.z, r, start, end, random)

def line(count, start, end, random=False) -> Generator:
    """
    Calculate the points along a line.
    
    Args:
        count (int): The number of points to generate
        start (Vec3): The start point/origin
        end (Vec3): The end point/origin
        random (bool, optional): Should the points be placed randomly along the line? Default is False.

    Returns:
        points (Generator): A generator of Vec3
    """
    return scatter.line(count, start.x,start.y,start.z, end.x,end.y,end.z, random)


def rect_fill(cw, cd, v, w, d, random=False) -> Generator:
    """
    Calculate the points within a rect.
    This assumes it to be flat on the y axis.
    
    Args:
        cw (int): The number of points to generate for each line width (x)
        cd (int): The number of points to generate for each line depth (z)
        v (Vec3): The start point
        w (float): The width (x)
        d (float): The depth (z)
        random (bool, optional): When True, points will be randomly placed. When False, points will be evenly placed. Default is True.
    
    Returns:
        points (Generator): A generator of Vec3
    """
    return scatter.rect_fill(cw, cd, v.x, v.y, v.z, w, d, random)

def box_fill(cw, ch, cd, v, w, h, d, random=False) -> Generator:
    """
    Calculate the points within a box.
    The box is subdivided to ideally avoid overlap.

    Args:
        cw (int): The number of points to generate for each line width (x)
        ch (int): The number of points to generate for each line height (y)
        cd (int): The number of points to generate for each line width (z)
        v (Vec3): The start point/origin
        w (float): The width
        h (float): The height
        d (float): The depth
        random (bool, optional): When True, points will be randomly placed. When False, points will be evenly placed. Default is True.

    Returns:
        points (Generator): A generator of Vec3    
    """
    return scatter.box_fill(cw, ch, cd, v.x, v.y, v.z, w, h, d, random)

def box(count, v1, v2, centered=False, a=None, degrees=True) -> Generator:
    """
    Calculate the points within a box.
    If `centered` is True, `v1` is the center of the box, and `v2` contains the width, height, and depth, respectively.
    Otherwise, `v1` is the left, bottom, and front, while `v2` is right, top, and back.

    Args:
        count (int): The number of points to generate
        v1 (Vec3): The start point/origin. If `centered` is True this is the center.
        v2 (Vec3): The size of the box. If `centered` is True, this is the width.
        center (bool, optional): When True, x,y,z are the center point. Default is False.
        a (Vec3): Rotate the box around the x axis by this amount.
        degrees (bool, optional): True if the axis rotation value uses degrees, False if it uses radians. Default is True.

    Returns:
        points (Generator): A generator of Vec3
    """

    if a is not None:
        return scatter.box(count, v1.x,v1.y, v1.z, v2.x, v2.y, v2.z, centered, a.x, a.y,a.z, degrees)
    else:
        return scatter.box(count, v1.x,v1.y, v1.z, v2.x, v2.y, v2.z, centered)
    

def ring(ca, cr, v, outer_r, inner_r=0, start=0.0, end=90.0, random=False) -> Generator:
    """
    Calculate the points on rings with each ring has same count.

    Args:
        ca (int): The number of points to generate on each ring
        cr (int): The number of rings
        v (Vec3): The start point/origin
        outer_r (float): The radius
        inner_r (float, optional): The radius inner. Default is 0.
        start (float): Degrees start angle. Default is 0.
        end (float): Degrees start angle. Default is 99.0.
        random (bool): When True, points will be randomly placed. When False, points will be evenly placed.

    Returns:
        points (Generator): A generator of Vec3
    """
    return scatter.ring(ca, cr, v.x,v.y,v.z, outer_r, inner_r, start, end, random)

def ring_density(counts, v,  outer_r, inner_r=0, start=0.0, end=90.0, random=False) -> Generator:
    """
    Calculate the points on rings with each ring specifying count in array.
        
    Args:
        counts (list[int]): The number of points to generate per ring.
        v (Vec3): The start point/origin
        outer_r (float): The radius of the outer ring.
        inner_r (float, optional): The inner radius of the ring. Default is 0.
        start (float): Start angle, in degrees.
        end (float): Start angle, in degrees.
        random (bool): When true pointw will be randomly placed. When false points will be evenly placed.

    Returns:
        points (Generator): A generator of Vec3
    """
    return scatter.ring_density(counts, v.x,v.y,v.z,  outer_r, inner_r, start, end, random)

def sphere(count, v, r, outer=0, top_only=False, ring=False) -> Generator:
    """
    Calculate the points within a sphere or ring.
        
    Args:
        count (int): The number of points to generate.
        v (Vec3): The start point/origin
        r (float): The radius. If `outer` is specified, this is the inner radius.
        outer (float, optional): The outer radius of the ring or sphere. Default is 0.
        top_only (bool, optional): Generate only the top hemisphere. Default is False.
        ring (bool, optional): Generate a flat ring. Default is False.
    
    Returns:
        points (Generator): A generator of Vec3
    """
    return scatter.sphere(count, v.x,v.y,v.z, r, outer, top_only, ring)

def simple_noise(count, v, v2, gx, gy,gz, radius=None, centered=False, ax=0,ay=0,az=0, degrees=True, drift=1.0):
    scatter.simple_noise(count, v.x,v.y, v.z, v2.x, v2.y, v2.z, gx, gy,gz, radius, centered, ax,ay,az, degrees, drift)