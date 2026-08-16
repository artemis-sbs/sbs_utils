from sbs_utils.pages.layout.bounds import Bounds
from sbs_utils.pages.layout.clickable import Clickable
from sbs_utils.pages.layout.column import Column
from sbs_utils.pages.layout.dirty import Dirty
from sbs_utils.helpers import FrameContext
def backdrop_props (image, color, layer=None):
    """Props for a background / border fill.
    
    `layer` None keeps the historic 1000, which is UNDER content -- so a
    backdrop cannot hide a neighbour's spill unless the author raises it."""
def is_out_of_bounds (child, parent, tolerance=0.0):
    """Check if the child's bounds are within the parent's bounds, with an acceptable tolerance.
    
    This is a separate check from is_hidden() or equivalents. It shouldn't be used in scripting at all, it should be used in lower-level python to ensure that a child element is only visible when within the bounds its parent.
    
    Does not make any changes to anything, is purely a helper function.
    
    Args:
        child (layout_item): The child layout item
        parent (layout_item): The parent layout item
        tolerance (float, optional): The amount that the child is allowed to be outside its parent and still be visible. Default is 0.0.
    
    Returns:
        bool: True if it is out of bounds, False if it is within bounds."""
class Row(object):
    """class Row"""
    def __init__ (self, cols=None, width=0, height=0) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _apply_clipping (self):
        """Decide which columns are clipped out of view. See Layout._apply_clipping.
        
        Recurses into a column that is itself a section, so the whole tree is
        decided top-down before anything draws."""
    def _post_present (self, event):
        ...
    def _pre_present (self, event):
        ...
    def _present (self, event):
        ...
    def add (self, col):
        ...
    def add_front (self, col):
        ...
    @property
    def bounds (self):
        ...
    @bounds.setter
    def bounds (self, v):
        ...
    def clear (self):
        ...
    @property
    def click_tag (self):
        ...
    @click_tag.setter
    def click_tag (self, v):
        ...
    @property
    def color (self):
        ...
    @color.setter
    def color (self, v):
        ...
    @property
    def font (self):
        ...
    @font.setter
    def font (self, v):
        ...
    def get_layer (self):
        ...
    def invalidate_regions (self):
        ...
    @property
    def is_hidden (self):
        """Use :func:`is_hidden` only to check if the layout item is currently visible to the user.
        It checks both :func:`_show` and :func:`_is_shown`.
        If either of these are False, will return True."""
    @property
    def is_hidden_by_script (self):
        """Hidden because the SCRIPT asked -- show() / gui_hide().
        
        This is the question the LAYOUT pass must ask; see
        :func:`Column.is_hidden_by_script`."""
    def is_message_for (self, event):
        """Used by MessageTrigger i.e. gui_message to know if message is for this object
        
        Args:
            event (EVENT): the engine event
        
        Returns:
            bool: if the gui_message MessageTrigger should be True"""
    @property
    def justify (self):
        ...
    @justify.setter
    def justify (self, v):
        ...
    @property
    def layer (self):
        ...
    @layer.setter
    def layer (self, v):
        ...
    def mark_layout_dirty (self):
        ...
    def mark_visual_dirty (self):
        ...
    def on_begin_presenting (self, client_id):
        ...
    def on_end_presenting (self, client_id):
        ...
    def on_message (self, event):
        ...
    @property
    def parent (self):
        ...
    @parent.setter
    def parent (self, v):
        ...
    def present (self, event):
        ...
    def represent (self, event):
        ...
    def set_border (self, border):
        ...
    def set_col_width (self, width):
        ...
    def set_margin (self, margin):
        ...
    def set_padding (self, padding):
        ...
    def set_row_height (self, height):
        ...
    def show (self, _show):
        """Use to force the gui element to be hidden, or to allow it to be seen.
        If False - the gui element will always be hidden.
        If True - will be visible assuming that it is within the bounds of its parent.
        
        Args:
            _show (bool): Should the element be visible."""
