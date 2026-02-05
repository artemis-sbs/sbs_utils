class Bounds:
    """Represents a 2D rectangular bounding box with left, top, right, and bottom coordinates.
    
    This class provides utilities for manipulating rectangular bounds including growing,
    shrinking, and merging operations. It can be initialized from scalar values or by
    copying another Bounds instance.
    
    Attributes:
        left (float): Left edge coordinate.
        top (float): Top edge coordinate.
        right (float): Right edge coordinate.
        bottom (float): Bottom edge coordinate.
    """
    
    def __init__(self, left=0, top=0, right=0, bottom=0) -> None:
        """Initialize a Bounds object.
        
        Args:
            left (float or Bounds or None): Left coordinate, another Bounds to copy, or None.
                Defaults to 0.
            top (float): Top coordinate. Defaults to 0.
            right (float): Right coordinate. Defaults to 0.
            bottom (float): Bottom coordinate. Defaults to 0.
        """
        if left is None:
            self.left=0
            self.top=0
            self.right=0
            self.bottom=0
        elif isinstance(left, Bounds):
            self.left=left.left
            self.top=left.top
            self.right=left.right
            self.bottom=left.bottom
        else:
            self.left=left
            self.top=top
            self.right=right
            self.bottom=bottom

    def __str__(self) -> str:
        """Return a formatted string representation of the bounds.
        
        Returns:
            str: String in format "l: X.XX r: X.XX t: X.XX b: X.XX".
        """
        return f"l: {self.left:3.2f} r: {self.right:3.2f} t: {self.top:3.2f} b: {self.bottom:3.2f}"
    @property
    def height(self):
        """Get the height of the bounds.
        
        Returns:
            float: The vertical distance (bottom - top).
        """
        return self.bottom-self.top
    
    @height.setter
    def height(self, h):
        """Set the height of the bounds by adjusting the bottom coordinate.
        
        Args:
            h (float): The desired height. Bottom is set to top + h.
        """
        self.bottom = self.top+h

    @property
    def width(self):
        """Get the width of the bounds.
        
        Returns:
            float: The horizontal distance (right - left).
        """
        return self.right-self.left
    
    @width.setter
    def width(self, w):
        """Set the width of the bounds by adjusting the right coordinate.
        
        Args:
            w (float): The desired width. Right is set to left + w.
        """
        self.right = self.left + w

    def __repr__(self) -> str:
        """Return a string representation for debugging.
        
        Returns:
            str: Comma-separated coordinate values.
        """
        return f"{self.left}, {self.top}, {self.right}, {self.bottom}"

    def __add__(self, o):
        """Add two Bounds objects element-wise.
        
        Args:
            o (Bounds): Another Bounds object to add.
        
        Returns:
            Bounds: A new Bounds with coordinates summed from both objects.
        """
        return Bounds(self.left+o.left,
            self.top+o.top,
            self.right+o.right,
            self.bottom+o.bottom)
    
    def __sub__(self, o):
        """Subtract two Bounds objects element-wise.
        
        Args:
            o (Bounds): Another Bounds object to subtract.
        
        Returns:
            Bounds: A new Bounds with coordinates from the difference.
        """
        return Bounds(self.left-o.left,
            self.top-o.top,
            self.right-o.right,
            self.bottom-o.bottom)
    
    
    def shrink(self, o):
        """Shrink this bounds by moving edges inward.
        
        Moves left and top edges inward (positive direction), and right and bottom
        edges inward (negative direction), effectively reducing the size.
        
        Args:
            o (Bounds or None): A Bounds object defining the shrink amounts.
                If None, the operation is skipped.
        """
        if o is None:
            return
        self.left   +=  o.left
        self.top    += o.top
        self.right  -= o.right
        self.bottom -= o.bottom
    
    def grow(self, o):
        """Grow this bounds by moving edges outward.
        
        Moves left and top edges outward (negative direction), and right and bottom
        edges outward (positive direction), effectively increasing the size.
        
        Args:
            o (Bounds or None): A Bounds object defining the growth amounts.
                If None, the operation is skipped.
        """
        if o is None:
            return
        self.left   -=  o.left
        self.top    -= o.top
        self.right  += o.right
        self.bottom += o.bottom

    def merge(self, b):
        """Merge another Bounds into this one by expanding to contain both.
        
        Expands this bounds to encompass both itself and the provided bounds.
        Left and top are set to minimum values, right and bottom to maximum values.
        
        Args:
            b (Bounds or None): Another Bounds to merge in.
                If None, the operation is skipped.
        """
        if b is None:
            return
        self.left = min(b.left, self.left)
        self.top= min(b.top, self.top)
        self.right= max(b.right, self.right)
        self.bottom = max(b.bottom, self.bottom)
