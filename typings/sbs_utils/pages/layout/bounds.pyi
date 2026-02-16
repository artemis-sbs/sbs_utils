class Bounds(object):
    """Represents a 2D rectangular bounding box with left, top, right, and bottom coordinates.
    
    This class provides utilities for manipulating rectangular bounds including growing,
    shrinking, and merging operations. It can be initialized from scalar values or by
    copying another Bounds instance.
    
    Attributes:
        left (float): Left edge coordinate.
        top (float): Top edge coordinate.
        right (float): Right edge coordinate.
        bottom (float): Bottom edge coordinate."""
    def __add__ (self, o):
        """Add two Bounds objects element-wise.
        
        Args:
            o (Bounds): Another Bounds object to add.
        
        Returns:
            Bounds: A new Bounds with coordinates summed from both objects."""
    def __init__ (self, left=0, top=0, right=0, bottom=0) -> None:
        """Initialize a Bounds object.
        
        Args:
            left (float or Bounds or None): Left coordinate, another Bounds to copy, or None.
                Defaults to 0.
            top (float): Top coordinate. Defaults to 0.
            right (float): Right coordinate. Defaults to 0.
            bottom (float): Bottom coordinate. Defaults to 0."""
    def __repr__ (self) -> str:
        """Return a string representation for debugging.
        
        Returns:
            str: Comma-separated coordinate values."""
    def __str__ (self) -> str:
        """Return a formatted string representation of the bounds.
        
        Returns:
            str: String in format "l: X.XX r: X.XX t: X.XX b: X.XX"."""
    def __sub__ (self, o):
        """Subtract two Bounds objects element-wise.
        
        Args:
            o (Bounds): Another Bounds object to subtract.
        
        Returns:
            Bounds: A new Bounds with coordinates from the difference."""
    def grow (self, o):
        """Grow this bounds by moving edges outward.
        
        Moves left and top edges outward (negative direction), and right and bottom
        edges outward (positive direction), effectively increasing the size.
        
        Args:
            o (Bounds or None): A Bounds object defining the growth amounts.
                If None, the operation is skipped."""
    @property
    def height (self):
        """Get the height of the bounds.
        
        Returns:
            float: The vertical distance (bottom - top)."""
    @height.setter
    def height (self, h):
        """Get the height of the bounds.
        
        Returns:
            float: The vertical distance (bottom - top)."""
    def merge (self, b):
        """Merge another Bounds into this one by expanding to contain both.
        
        Expands this bounds to encompass both itself and the provided bounds.
        Left and top are set to minimum values, right and bottom to maximum values.
        
        Args:
            b (Bounds or None): Another Bounds to merge in.
                If None, the operation is skipped."""
    def shrink (self, o):
        """Shrink this bounds by moving edges inward.
        
        Moves left and top edges inward (positive direction), and right and bottom
        edges inward (negative direction), effectively reducing the size.
        
        Args:
            o (Bounds or None): A Bounds object defining the shrink amounts.
                If None, the operation is skipped."""
    @property
    def width (self):
        """Get the width of the bounds.
        
        Returns:
            float: The horizontal distance (right - left)."""
    @width.setter
    def width (self, w):
        """Get the width of the bounds.
        
        Returns:
            float: The horizontal distance (right - left)."""
