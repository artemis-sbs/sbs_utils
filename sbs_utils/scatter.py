import math
from random import uniform
from .vec import Vec3

def arc(count, x,y,z, r, start=0.0, end=90.0, random=False):
    """Calculate the points along an circular arc

    Args:
        count (int): The number of points to generate
        x,y,z (float,float,float): the center point/origin
        r (float): radius
        start (float, optional): the angle to start at in degrees. Default 0
        end (float, optional): the angle to end at in degrees default 360

    Returns:
        points (generator): A generator of Vec3
    """
    #Make clockwise by negating
    a_start = -math.radians(start-90)
    a_end = -math.radians(end-90)
    a_diff = (a_end-a_start) / count
    for i in range(0,count):
        if random:
            angle = uniform(a_start, a_end)
        else:
            angle=i*a_diff + a_start
        yield Vec3(x+math.cos(angle)*r, y, z+math.sin(angle)*r)


def line(count, start_x,start_y,start_z, end_x,end_y,end_z, random=False):
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
        points (generator): A generator of Vec3
    """

    v1 =  Vec3(start_x, start_y, start_z)
    v2 =  Vec3(end_x, end_y, end_z)

    v = v2 - v1
    d = v.length()
    u = v.divide(d)
   
    delta = 0
    if count >1:
        delta = u * (d/(count-1))
    
    for i in range(0,count):
        if random:
            yield v1 + (delta * uniform(0,count))
        else:
            yield v1 + (delta * i)


def rect_fill(cw, cd, x, y, z, w, d, random=False):
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
        points (generator): A generator of Vec3
    """
    return box_fill(cw, 1, cd, x, y, z, w, 1, d, random)
   
def box_fill(cw, ch, cd, x, y, z, w, h, d, random=False):
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
        points (generator): A generator of Vec3    
    """
    front = z-d/2
    bottom = y-h/2
    left = x-w/2
    # right = x+w/2
    if cw >1:
        w_diff = w/(cw-1)
    else: 
        w_diff = 1
    if ch >1:
        h_diff = h/(ch-1)
    else: 
        h_diff = 1
        bottom = y
    if cd >1:
        d_diff = d/(cd-1)
    else: 
        d_diff = 1
    for layer in range(0,ch):
        _y =  bottom + layer * h_diff
        for row in range(0,cd):
            _z = front + row * d_diff
            for col in range(0,cw):
                if random:
                    _y =  bottom + uniform(0,ch) * h_diff
                    _x =  left + uniform(0,cw) * w_diff
                    _z =  front + uniform(0,cd) * d_diff
                else:
                    _x = left + col * w_diff
                yield Vec3(_x,_y,_z)

def box(count, x,y, z, x2, y2, z2, centered=False, ax=0,ay=0,az=0, degrees=True):
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
        points (generator): A generator of Vec3
    """

    rotate = ax!=0 or ay != 0 or az != 0
    # for simplicity for rotation convert to centered
    origin = Vec3(x,y,z)
    w = x2
    h = y2
    d = z2
    if not centered:
        w = x2-x
        h = y2-y
        d = z2-z
        origin = Vec3(x+ w/2, y+h/2, z+d/2)


    for _ in range(0,count):
        _x =  uniform(origin.x-w/2,origin.x+w/2)
        _y =  uniform(origin.y-h/2,y+h/2)
        _z =  uniform(origin.z-d/2,z+d/2)
        v = Vec3(_x,_y,_z)
        if rotate:
            v = v.rotate_around(origin, ax,ay,az, degrees)
        yield v

def ring(ca, cr, x,y,z, outer_r, inner_r=0, start=0.0, end=90.0, random=False):
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
        points (generator): A generator of Vec3
    """
    #Make clockwise by negating
    a_start = -math.radians(start)
    a_end = -math.radians(end)
    a_diff = (a_end-a_start)
    r_diff = 0
    if cr>1:
        r_diff  = (outer_r - inner_r) / (cr-1)
    for r in range(0, cr):
        dist = inner_r + (r* r_diff)
        for i in range(0,ca):
            if random:
                angle = uniform(a_start, a_end)
            else:
                angle=(i/ca)*a_diff + a_start
            yield Vec3(x+math.cos(angle)*dist, y, z+math.sin(angle)*dist)

def ring_density(counts, x,y,z,  outer_r, inner_r=0, start=0.0, end=90.0, random=False):
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
        points (generator): A generator of Vec3
    """
    #Make clockwise by negating
    a_start = -math.radians(start)
    a_end = -math.radians(end)
    a_diff = (a_end-a_start)
    r_diff = 0
    if len(counts)>1:
        r_diff = (outer_r - inner_r) / (len(counts)-1)
    for r in range(0, len(counts)):
        dist = inner_r + (r* r_diff)
        ca = counts[r]
        #print(f'count {ca}')
        for i in range(0,ca):
            if random:
                angle = uniform(a_start, a_end)
            else:
                angle=i*(a_diff/ca) + a_start
            yield Vec3(x+math.cos(angle)*dist, y, z+math.sin(angle)*dist)


def sphere(count, x,y,z, r, outer=0, top_only=False, ring=False):
    """Calculate the points within a sphere or ring
        
    Args:
        count (int): The number of points to generate
        x,y,z (float,float,float): the start point/origin
        r (float): the radius if outer is spedified this is the inner
        outer (float = 0 optional): the height
        top_only (bool): generate only top hemispher 
        ring (bool): generate a flat ring
    
    Returns:
        points (generator): A generator of Vec3
    """
    # y should be odd
    origin = Vec3(x,y,z)
    for _ in range(0,count):
        yield origin.rand_offset(r, outer, top_only, ring)
    