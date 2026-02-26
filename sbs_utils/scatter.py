import math
from random import uniform, choices
from .vec import Vec3
from collections.abc import Generator
def arc(count, x,y,z, r, start=0.0, end=90.0, random=False) -> Generator:
    """
    Calculate the points along an circular arc.

    Args:
        count (int): The number of points to generate.
        x (float): The start point.
        y (float): The start point.
        z (float): The start point.
        r (float): The radius of the arc.
        start (float, optional): The angle to start at in degrees. Default is 0.
        end (float, optional): The angle to end at in degrees default 360. Default is 90.0.
        random (bool): Should the points be randomly placed along the arc (True), or evenly spaced (False)?

    Returns:
        points (Generator): A generator of Vec3
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


def line(count, start_x,start_y,start_z, end_x,end_y,end_z, random=False) -> Generator:
    """
    Calculate the points along a line.
    
    Args:
        count (int): The number of points to generate
        start_x (float): The start point/origin
        start_y (float): The start point/origin
        start_z (float): The start point/origin
        end_x (float): The end point/origin
        end_y (float): The end point/origin
        end_z (float): The end point/origin
        random (bool, optional): Should the points be placed randomly along the line? Default is False.

    Returns:
        points (Generator): A generator of Vec3
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


def rect_fill(cw, cd, x, y, z, w, d, random=False, ax=0,ay=0,az=0, degrees=True) -> Generator:
    """
    Calculate the points within a rect.
    This assumes it to be flat on the y axis.
    
    Args:
        cw (int): The number of points to generate for each line width (x)
        cd (int): The number of points to generate for each line depth (z)
        x (float): The start point
        y (float): The start point
        z (float): The start point
        w (float): The width (x)
        d (float): The depth (z)
        random (bool, optional): When True, points will be randomly placed. When False, points will be evenly placed. Default is True.
    
    Returns:
        points (Generator): A generator of Vec3
    """
    return box_fill(cw, 1, cd, x, y, z, w, 1, d, random,ax,ay,az,degrees)
   
def box_fill(cw, ch, cd, x, y, z, w, h, d, random=False, ax=0,ay=0,az=0, degrees=True) -> Generator:
    """
    Calculate the points within a box.
    The box is subdivided to ideally avoid overlap.

    Args:
        cw (int): The number of points to generate for each line width (x)
        ch (int): The number of points to generate for each line height (y)
        cd (int): The number of points to generate for each line width (z)
        x (float): The start point/origin
        y (float): The start point/origin
        z (float): The start point/origin
        w (float): The width
        h (float): The height
        d (float): The depth
        random (bool, optional): When True, points will be randomly placed. When False, points will be evenly placed. Default is True.
        ax (float, optional): Rotate the box around the x axis by this amount. Default is 0.
        ay (float, optional): Rotate the box around the y axis by this amount. Default is 0.
        az (float, optional): Rotate the box around the z axis by this amount. Default is 0.
        degrees (bool, optional): True if the axis rotation values use degrees, False if they use radians. Default is True.

    Returns:
        points (Generator): A generator of Vec3    
    """
    rotate = ax!=0 or ay != 0 or az != 0
    front = z-d/2
    bottom = y-h/2
    left = x-w/2
    origin = Vec3(x,y,z)
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
                v = Vec3(_x,_y,_z)
                if rotate:
                    v = v.rotate_around(origin, ax,ay,az, degrees)
                yield Vec3(_x,_y,_z)

def box(count, x,y, z, x2, y2, z2, centered=False, ax=0,ay=0,az=0, degrees=True) -> Generator:
    """
    Calculate the points within a box.
    If `centered` is True, `x`,`y`,`z` are the center of the box, and `x2`,`y2`,`z2` are the width, height, and depth, respectively.
    Otherwise, `x`,`y`,`z` are left, bottom, and front, respectively, while `x2`,`y2`,`z2` are right, top, and back.

    Args:
        count (int): The number of points to generate
        x (float): The start point/origin. If `centered` is true this is the center. If `centered` is False this is the left.
        y (float): The start point/origin. If `centered` is true this is the center. If `centered` is False this is the bottom.
        z (float): The start point/origin. If `centered` is true this is the center. If `centered` is False this is the front.
        x2 (float): If `centered` is True, this is the width. If `centered` is False, this is the right.
        y2 (float): If `centered` is True, this is the height. If `centered` is False, this is the top.
        z2 (float): If `centered` is True, this is the depth. If `centered` is False, this is the back.
        center (bool, optional): When True, x,y,z are the center point. Default is False.
        ax (float): Rotate the box around the x axis by this amount.
        ay (float): Rotate the box around the y axis by this amount.
        az (float): Rotate the box around the z axis by this amount.
        degrees (bool, optional): True if the axis rotation values use degrees, False if they use radians. Default is True.

    Returns:
        points (Generator): A generator of Vec3
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
        _y =  uniform(origin.y-h/2,origin.y+h/2)
        _z =  uniform(origin.z-d/2,origin.z+d/2)
        v = Vec3(_x,_y,_z)
        if rotate:
            v = v.rotate_around(origin, ax,ay,az, degrees)
        yield v

def ring(ca, cr, x,y,z, outer_r, inner_r=0, start=0.0, end=90.0, random=False) -> Generator:
    """
    Calculate the points on rings with each ring has same count.

    Args:
        ca (int): The number of points to generate on each ring
        cr (int): The number of rings
        x (float): The start point/origin
        y (float): The start point/origin
        z (float): The start point/origin
        outer_r (float): The radius
        inner_r (float, optional): The inner radius. Default is 0.
        start (float): degrees start angle. Default is 0.
        end (float): degrees start angle. Default is 90.0.
        random (bool): When True, points will be randomly placed. When False, points will be evenly placed.

    Returns:
        points (Generator): A generator of Vec3
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

def ring_density(counts, x,y,z,  outer_r, inner_r=0, start=0.0, end=90.0, random=False) -> Generator:
    """
    Calculate the points on rings with each ring specifying count in array.
        
    Args:
        counts (list[int]): The number of points to generate per ring.
        x (float): The start point/origin
        y (float): The start point/origin
        z (float): The start point/origin
        outer_r (float): The radius of the outer ring.
        inner_r (float, optional): The inner radius of the ring. Default is 0.
        start (float): Start angle, in degrees.
        end (float): Start angle, in degrees.
        random (bool): When true pointw will be randomly placed. When false points will be evenly placed.

    Returns:
        points (Generator): A generator of Vec3
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
        for i in range(0,ca):
            if random:
                angle = uniform(a_start, a_end)
            else:
                angle=i*(a_diff/ca) + a_start
            yield Vec3(x+math.cos(angle)*dist, y, z+math.sin(angle)*dist)


def sphere(count, x,y,z, r, outer=0, top_only=False, ring=False) -> Generator:
    """
    Calculate the points within a sphere or ring.
        
    Args:
        count (int): The number of points to generate.
        x (float): The start point/origin
        y (float): The start point/origin
        z (float): The start point/origin
        r (float): The radius. If `outer` is specified, this is the inner radius.
        outer (float, optional): The outer radius of the ring or sphere. Default is 0.
        top_only (bool, optional): Generate only the top hemisphere. Default is False.
        ring (bool, optional): Generate a flat ring. Default is False.
    
    Returns:
        points (Generator): A generator of Vec3
    """
    # y should be odd
    origin = Vec3(x,y,z)
    for _ in range(0,count):
        yield origin.rand_offset(r, outer, top_only, ring)

def simple_noise(count, x,y, z, x2, y2, z2, count_x, count_y,count_z, radius=None, centered=False, ax=0,ay=0,az=0, degrees=True, drift=1.0):
    """ Builds a simple noise distribution withing a grid. 

    Args:
        count (_type_): The maximum number of points to return. It could be less if grid is too small, or radius removes too many items. if None or 0. It returns all

        x (_type_): Left or center x based on centered
        y (_type_): Top or center y based on centered
        z (_type_): Front or center z based on centered

        x2 (_type_): Right or width based on centered
        y2 (_type_): Bottom or height  based on centered
        z2 (_type_): BAck or depth based on centered

        gx (_type_): grid chunk size x
        gy (_type_): grid chunk size y
        gz (_type_): grid chunk size z

        radius (_type_, optional): If supplied it will remove grid locations that are outside the radius
        centered (bool, optional): _description_. Defaults to False.
        ax (int, optional): rotation applied to points. Defaults to 0.
        ay (int, optional): rotation applied to points. Defaults to 0.
        az (int, optional): rotation applied to points. Defaults to 0.
        degrees (bool, optional): if angles are in degrees. Defaults to True.
        drift (float): amount of drift from grid center point as a percentage of grid radius
    """

    center_x = x; center_y = y; center_z = z
    w = x2; h = y2; d = z2
    hw = w/2; hh = h/2; hd = d/2
    left = center_x-hw; right = center_x+hw; top = center_y-hh; bottom = center_y+hh; front = center_z-hd; back=center_z+hd

    if not centered:
        left = x; right = x2; top = y; bottom = y2; front = z; back=z2
        w = (right - left)/2; h = (bottom - top)/2; d = (front - back)/2
        hw = w/2; hh = h/2; hd = d/2
        center_x = left + hw; center_y = top + hh; center_z = front + hd

    count_x = max(count_x,1)
    count_y = max(count_y,1)
    count_z = max(count_z,1)

    w_diff = w / count_x
    h_diff = h / count_y
    d_diff = d / count_z
    rotate = ax!=0 or ay!=0 or az!=0
    origin = Vec3(x,y,z)

    
    # Calculate the length of the grid item 
    # a = w_diff/2;b = d_diff/2
    # t = math.sqrt(a*a+b*b) / 2
    # grid_length = t * drift
    grid_length = drift * w_diff / (2 * math.sqrt(2))

    # print(f"NOISE {grid_length:0.1f}")

    if radius is not None:
        r = radius - grid_length
        r_squared = r*r
    


    # Instead of a generator this will build points up front
    grid_point = []
    
    for layer in range(0,count_y):
        _y =  top + layer * h_diff
        for row in range(0,count_z):
            _z = front + row * d_diff
            for col in range(0,count_x):
                _x = left + col * w_diff

                # Now we have a center point
                v = Vec3(_x,_y,_z)
                # wiggle the point within the grid
                v = v.rand_offset(grid_length, ring=count_y==1)
                v.y = uniform(top,bottom)
                
                if radius is not None:
                    diff = origin - v
                    lsq = diff.dot(diff)
                    if  lsq >= r_squared:
                        continue

                

                if rotate:
                    v = v.rotate_around(origin, ax,ay,az, degrees)
                grid_point.append(v)


    if len(grid_point) ==0:
        v = origin
        # wiggle the point within the grid
        v = v.rand_offset(grid_length, ring=count_y==1)
        v.y = uniform(top,bottom)
        return [v]

    if count is None or count == 0:
        return grid_point
    
    
    ret_count = min(count, len(grid_point))
    return choices(grid_point, k=ret_count)

    

        