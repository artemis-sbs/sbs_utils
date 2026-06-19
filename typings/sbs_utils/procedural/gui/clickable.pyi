from sbs_utils.helpers import FrameContext
from sbs_utils.mast.mast_node import Scope
from sbs_utils.futures import Trigger
def gui_click (name_or_layout_item=None, label=None):
    """Register a click handler for a named element or layout item.
    
    Attaches a ``ClickableTrigger`` to the current task. When the element is
    clicked, sets ``__CLICKED__`` to the click tag and runs ``label`` inline
    (or as a sub-task if a different label is specified).
    
    Args:
        name_or_layout_item (str | layout object | None, optional): A click-tag
            string, a layout item exposing ``click_tag``, or ``None`` to match
            any click. Defaults to None.
        label (optional): MAST label to run on click. Defaults to the currently
            active label.
    
    Returns:
        ClickableTrigger: The registered trigger.
    
    Example:
        btn = gui_button("Fire!", on_press=None)
        gui_click(btn, on_fire_pressed)
        ///on_fire_pressed
            ~~ fire_torpedo(SHIP_ID) ~~"""
class ClickableTrigger(Trigger):
    """class ClickableTrigger"""
    def __init__ (self, task, name, label=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def click (self, click_tag):
        ...
