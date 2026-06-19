from sbs_utils.helpers import FrameContext
from sbs_utils.futures import Trigger
def gui_message (layout_item, label=None):
    """Register a MAST label to run when a layout element receives a GUI event.
    
    Attaches a ``MessageTrigger`` to the current task so that when the engine
    fires a ``gui_message`` event matching ``layout_item``'s tag, the given
    label is pushed and executed inline. Used to respond to clicks on custom
    layout items (sections, regions, etc.) that are not plain buttons.
    
    Args:
        layout_item: The layout object whose tag to watch. Must expose
            ``is_message_for(event)`` (all standard layout items do).
        label (optional): MAST label or inline block to run on the event.
            Defaults to the current active label.
    
    Returns:
        MessageTrigger: The registered trigger object.
    
    Example:
        region = gui_region(style="area:10,10,50,50;")
        gui_message(region, on_region_click)
        ///on_region_click
            gui_text("Region clicked!")"""
def gui_message_callback (layout_item, cb):
    """Set a Python callable to invoke when a layout element receives a GUI event.
    
    Attaches a callback directly to the layout item's ``on_message_cb``
    attribute. The callback is called with the event and the layout item when
    the engine fires a ``gui_message`` event matching the item's tag.
    Use this for pure-Python handlers; use ``gui_message`` for MAST label
    handlers.
    
    Args:
        layout_item: The layout object to attach the callback to.
        cb (callable): Function called as ``cb(event, layout_item)`` on event.
    
    Example:
        btn = gui_button("Fire!", on_press=None)
        gui_message_callback(btn, lambda e, item: fire_torpedo(SHIP_ID))"""
def gui_message_label (layout_item, label):
    """Schedule a MAST label as a sub-task when a layout element receives a GUI event.
    
    Similar to ``gui_message_callback`` but wraps the label in a
    ``gui_sub_task_schedule`` call, running it as an independent sub-task
    rather than inline in the current task.
    
    Args:
        layout_item: The layout object to attach the handler to.
        label: MAST label to schedule as a sub-task on event.
    
    Example:
        section = gui_sub_section(style="col-width:30%;")
        gui_message_label(section, handle_section_click)"""
class MessageTrigger(Trigger):
    """class MessageTrigger"""
    def __init__ (self, task, layout_item, label=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def on_message (self, event):
        ...
