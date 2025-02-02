from sbs_utils.vec import Vec3
import math
from functools import reduce

def rotate_around(v, cv, angle):
    x = v[0]
    y = v[1]
    z = v[2]
    cx = cv[0]
    cy = cv[1]
    cz = cv[2]
    v = Vec3(x,y,z) 
    v = v.rotate_around(Vec3(cx,cy,cz), 0, angle,0)
    return v

def calc_hex_points(center_x,center_z, rings, size, rotate=False ):
    """ layout a pointy hexagon of pointy hexagons
    Only support this style since tiled only supports pointy

    Args:
        center_x (_type_): _description_
        center_z (_type_): _description_
        rings (_type_): _description_
        size (_type_): _description_
        flat_outer (bool, optional): _description_. Defaults to True.
        flat_inner (bool, optional): _description_. Defaults to False.

    Returns:
        _type_: _description_
    """
    max_radius = size 
    count = rings*2+1
    dist = max_radius /count
    sq3 = math.sqrt(3)
    #sq3 =1
    the_size = dist
    v_spacing = the_size*3/2
    h_spacing = sq3 * the_size
    points = []
    
    for _ in range(count):
        points.append([])
    x_offset = center_x - rings * h_spacing
    #if rings != 0:
    x_offset -= h_spacing/2
    count = rings*2+1
    lines = rings+1

    for line in range(lines):
        if line == 0:
            count = rings*2+1
        else:
            count -=  1 
        
        x_offset += h_spacing/2

        for r in range(count):
            z_spacing = line * v_spacing 
            x_spacing = r*h_spacing
            index = abs(- rings + line)
            above = (x_offset + x_spacing , 0, center_z-z_spacing )
            if rotate:
                v = rotate_around(above, (center_x, 0, center_z), -90)
                above = (v.x, v.y, v.z)
            points[index].append(above)
            if line != 0:
                below = (x_offset + x_spacing , 0, center_z+z_spacing )
                if rotate:
                    v = rotate_around(below, (center_x, 0, center_z), -90)
                    below = (v.x, v.y, v.z)
                index = rings + line
                points[index].append(below)

    return points



rings = 8
expected = 1
for i in range(rings+1):
    expected += 6 * i
points = calc_hex_points(0,0, rings, 1000, True)
count = reduce(lambda x, a: x+len(a), points, 0)
print(f"{count} ?= {expected}" )
# for p in points:
#     print(p)



