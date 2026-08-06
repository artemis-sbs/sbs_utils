from sbs_utils.pages.layout.column import Column
from sbs_utils.helpers import FrameContext
class Dropdown(Column):
    """class Dropdown"""
    def __init__ (self, tag, props) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _present (self, event):
        ...
    def measure (self, client_id, mode, avail_px, font, ar):
        """Deliberately unmeasurable -- do not "fix" this to measure the list.
        
        A dropdown's rendered width is its widest option PLUS engine-drawn
        chrome (the arrow, the border) whose size we cannot ask for. Sizing to
        the text alone would come out narrow, and because the engine does not
        clip, a narrow dropdown draws its label over its neighbour rather than
        truncating. Falling back to flex is the safe answer, and it is exactly
        what happened before content sizing existed."""
    def on_message (self, event):
        ...
    def update (self, props):
        ...
    @property
    def value (self):
        ...
    @value.setter
    def value (self, v):
        ...
