from collections.abc import Generator
from sbs_utils.vec import Vec3
def arc (count, x, y, z, r, start=0.0, end=90.0, random=False) -> collections.abc.Generator:
    """Calculate the points along an circular arc.
    
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
        points (Generator): A generator of Vec3"""
def box (count, x, y, z, x2, y2, z2, centered=False, ax=0, ay=0, az=0, degrees=True) -> collections.abc.Generator:
    """Calculate the points within a box.
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
        points (Generator): A generator of Vec3"""
def box_fill (cw, ch, cd, x, y, z, w, h, d, random=False, ax=0, ay=0, az=0, degrees=True) -> collections.abc.Generator:
    """Calculate the points within a box.
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
        points (Generator): A generator of Vec3    """
def line (count, start_x, start_y, start_z, end_x, end_y, end_z, random=False) -> collections.abc.Generator:
    """Calculate the points along a line.
    
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
        points (Generator): A generator of Vec3"""
def rect_fill (cw, cd, x, y, z, w, d, random=False, ax=0, ay=0, az=0, degrees=True) -> collections.abc.Generator:
    """Calculate the points within a rect.
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
        points (Generator): A generator of Vec3"""
def ring (ca, cr, x, y, z, outer_r, inner_r=0, start=0.0, end=90.0, random=False) -> collections.abc.Generator:
    """Calculate the points on rings with each ring has same count.
    
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
        points (Generator): A generator of Vec3"""
def ring_density (counts, x, y, z, outer_r, inner_r=0, start=0.0, end=90.0, random=False) -> collections.abc.Generator:
    """Calculate the points on rings with each ring specifying count in array.
    
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
        points (Generator): A generator of Vec3"""
def simple_noise (count, x, y, z, x2, y2, z2, gx, gy, gz, radius=None, centered=False, ax=0, ay=0, az=0, degrees=True, drift=1.0):
    """Builds a simple noise distribution withing a grid.
    
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
        drift (float): amount of drift from grid center point as a percentage of grid radius"""
def sphere (count, x, y, z, r, outer=0, top_only=False, ring=False) -> collections.abc.Generator:
    """Calculate the points within a sphere or ring.
    
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
        points (Generator): A generator of Vec3"""
