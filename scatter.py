import math
from random import uniform
from .vec import Vec3

def arc(count, x,y,z, r, start=0.0, end=90.0, random=False):
    r"""Calculate the points along an circular arc

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
        the angle to end at in degrees
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
    r"""Calculate the points along a line
    
    Parameters
    ----------
    count: int
        The number of points to generate
    start_x,start_y,start_z: float,float,float
        the start point/origin
    end_x,end_y,end_z: float,float,float
        the end point
    """

    v1 =  Vec3(start_x, start_y, start_z)
    v2 =  Vec3(end_x, end_y, end_z)

    v = v2 - v1
    d = v.length()
    u = v.divide(d)
   
    delta = u * (d/(count-1))
    for i in range(0,count):
        if random:
            yield v1 + (delta * uniform(0,count))
        else:
            yield v1 + (delta * i)


def rect_fill(cw, cd, x, y, z, w, d, random=False):
    r"""Calculate the points within a rect

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
        when false points will be evenly placed
    """
    return box_fill(cw, 1, cd, x, y, z, w, 1, d, random)
   
def box_fill(cw, ch, cd, x, y, z, w, h, d, random=False):
    r"""Calculate the points within a box

        
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
        when false points will be evenly placed
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
        if random:
            _y =  bottom + uniform(0,ch) * h_diff
        else:
            _y =  bottom + layer * h_diff
        for row in range(0,cd):
            if random:
                _z =  front + uniform(0,cd) * d_diff
            else:
                _z = front + row * d_diff
            for col in range(0,cw):
                if random:
                    _x =  left + uniform(0,cw) * w_diff
                else:
                    _x = left + col * w_diff
                yield Vec3(_x,_y,_z)


def ring(ca, cr, x,y,z, outer_r, inner_r=0, start=0.0, end=90.0, random=False):
    r"""Calculate the points on rings with each ring has same count
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
        when false points will be evenly placed
    """
    #Make clockwise by negating
    a_start = -math.radians(start)
    a_end = -math.radians(end)
    a_diff = (a_end-a_start)
    r_diff = (outer_r - inner_r) / (cr-1)
    for r in range(0, cr):
        dist = inner_r + (r* r_diff)
        for i in range(0,ca):
            if random:
                angle = uniform(a_start, a_end)
            else:
                angle=(i/ca)*a_diff + a_start
            yield Vec3(x+math.cos(angle)*dist, y, z+math.sin(angle)*dist)

def ring_density(counts, x,y,z,  outer_r, inner_r=0, start=0.0, end=90.0, random=False):
    r"""Calculate the points on rings with each ring specifying count in array
        
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
        when false points will be evenly placed

    """
    #Make clockwise by negating
    a_start = -math.radians(start)
    a_end = -math.radians(end)
    a_diff = (a_end-a_start)
    r_diff = (outer_r - inner_r) / (len(counts)-1)
    for r in range(0, len(counts)):
        dist = inner_r + (r* r_diff)
        ca = counts[r]
        print(f'count {ca}')
        for i in range(0,ca):
            if random:
                angle = uniform(a_start, a_end)
            else:
                angle=i*(a_diff/ca) + a_start
            yield Vec3(x+math.cos(angle)*dist, y, z+math.sin(angle)*dist)


def sphere(count, x,y,z, r, outer=0, top_only=False, ring=False):
    r"""Calculate the points within a sphere or ring
        
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
        generate a flat ring
    """
    # y should be odd
    origin = Vec3(x,y,z)
    for _ in range(0,count):
        yield origin.rand_offset(r, outer, top_only, ring)
    