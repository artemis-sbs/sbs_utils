from sbs_utils.pages.layout.column import Column
from sbs_utils.helpers import FrameContext
class Icon(Column):
    """class Icon"""
    def __init__ (self, tag, props) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _present (self, event):
        ...
    def update (self, props):
        """Change what the glyph looks like - a new index, or a recolor.
        
        The dirty mark is the whole point: the props alone are only what the NEXT
        present would send, and a present only happens when something else rebuilds
        the page. A status icon that recolors on damage would have gone on drawing
        its old color until the console was left and re-entered."""
    @property
    def value (self):
        ...
    @value.setter
    def value (self, v):
        ...
