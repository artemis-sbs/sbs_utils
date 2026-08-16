from sbs_utils.helpers import FrameContext
from sbs_utils.message_chain import MessageChain
from sbs_utils.futures import Trigger
def _handler_site (task, label, loc):
    ...
def dead_handler_site_count ():
    ...
def dead_handler_sites_clear ():
    """Per-mission reset -- see handlerhooks.reset_mission_state."""
def gui_host_task (task):
    """The page's live GUI task -- who can tick a handler this task registered."""
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
def gui_message_clear (layout_item):
    """Drop EVERY gui_message handler attached to a widget, on both channels.
    
    Handlers accumulate now (LM #614), so replacing rather than adding takes an
    explicit step: clear, then register. Before #614 a plain re-registration
    did this implicitly, by throwing the previous handler away.
    
    Args:
        layout_item: the widget to detach every handler from.
    
    Returns:
        int: how many registrations were removed."""
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
def host_handler_sub_task (builder, sub_task):
    """Give a handler sub-task a LIVE ticking parent when its builder has ended.
    
    A `gui_message(widget, label)` handler runs as a sub-task of the task that
    built the widget, and sub-tasks are only ever ticked by their parent's
    tick(). On a finished builder that is exactly one tick -- the
    tick_in_context() at the call site -- after which the handler stalls
    wherever it happens to be. Single-line handlers looked like they worked;
    anything that awaited did not.
    
    The page's gui_task takes over the TICKING only. root_task is deliberately
    left pointing at the builder, so the handler's variable scope is exactly
    what it is when the builder is alive.
    
    Returns True when the sub-task was re-hosted."""
def message_cb_add (layout_item, cb):
    """Register a Channel-2 callback WITHOUT dropping any already attached.
    
    Direct assignment (`item.on_message_cb = fn`) still means replace -- that is
    what the layout classes themselves do, and it is the only predictable
    meaning for `=`. This is the append form."""
def warn_dead_handler (task, label, loc, kind):
    """Report a click that landed on a task which has already finished.
    
    Without this the failure is completely silent: the widget draws, the click
    dispatches, the handler is discarded, and nothing is logged anywhere. That
    silence is most of what made LM issue #707 hard to place."""
class MessageTrigger(Trigger):
    """class MessageTrigger"""
    def __init__ (self, task, layout_item, label=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def on_message (self, event):
        ...
