class Bounds(object):
    """class Bounds"""
    def __add__ (self, o):
        ...
    def __init__ (self, left=0, top=0, right=0, bottom=0) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def __repr__ (self) -> str:
        """Return repr(self)."""
    def __str__ (self) -> str:
        """Return str(self)."""
    def __sub__ (self, o):
        ...
    def grow (self, o):
        ...
    @property
    def height (self):
        ...
    @height.setter
    def height (self, h):
        ...
    def merge (self, b):
        ...
    def shrink (self, o):
        ...
    @property
    def width (self):
        ...
    @width.setter
    def width (self, w):
        ...
