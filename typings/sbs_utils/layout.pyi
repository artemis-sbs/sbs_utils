def wrap (left, top, width, height, col=1, h_gutter=1, v_gutter=1, v_dir=1, h_dir=1):
    """wrap
    
    A generator function that returns a tuple for screen locations for the next component.
    
    The layout will calculate a new horizontal location columns for the number of columns specified it wraps to the next row.
    
    :param left: The starting location
    :type left: float
    :param top: The starting location
    :type top: float
    :param height: The starting location
    :type height: float
    :param col: The number of columns
    :type col: int
    :param h_gutter: The starting location
    :type h_gutter: float
    :param v_gutter: The starting location
    :type v_gutter: float
    :param v_dir: Vertical direction
    :type v_dir: int 1 = downward -1 = upward
    :param h_dir: Horizontal direction
    :type h_dir: int 1 = left -1 = right
    
    :return: a generator that returns a tuple of the left, top, right, bottom
    :rtype: generator of (float,float,float,float)"""
