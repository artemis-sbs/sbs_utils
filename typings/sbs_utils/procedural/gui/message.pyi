from sbs_utils.helpers import FrameContext
from sbs_utils.message_chain import MessageChain
from sbs_utils.futures import Trigger
def _handler_site (task, label, loc):
    ...
def _signal_event_is_for (layout_item, event):
    """Whether a GUI event is aimed at this widget.
    
    Layout.on_message hands on_message_cb every event delivered to the item during
    the page's walk of the layout tree, not only its own (see the note in
    epadd._app_tile), so the callback has to filter. A listbox filters first and
    only calls back for a row click; its rows carry the listbox's tag prefix."""
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
def gui_signal (layout_item, name, data=None):
    """Emit a signal whenever a control is used.
    
    The control does not run anything itself; the signal's routes do. That keeps
    the widget free of handler plumbing, and lets the SAME control drive a
    ``//shared/signal`` route (state, once on the server) and a ``//signal``
    route (a repaint, on each console) - see SIGNAL_ROUTING.md for which is which.
    
    Works on any control: button, icon button, cycle button, checkbox, dropdown,
    slider and listbox (on a row click). It is added alongside the widget's other
    handlers (``on_press``, ``on gui_message``), never in place of them.
    
    The route gets these variables:
    
    - every key of ``data``, when it is a dict (anything else is ``SIGNAL_DATA``)
    - ``SIGNAL_CLIENT_ID``: the console that used the control
    - ``SIGNAL_ITEM``: the control itself
    - ``SIGNAL_VALUE``: its value after the click - the checkbox state, the
      dropdown text, the slider value, the listbox selection, the cycle button's
      state; None for a plain button
    
    Args:
        layout_item: the control, as returned by its ``gui_*`` function.
        name (str): the signal to emit.
        data (dict, optional): extra variables for the route. Defaults to None.
    
    Returns:
        the layout item, so the call can wrap the builder.
    
    Example:
        gui_signal(gui_checkbox("Shields", var="shields_on"), "shields_toggled")
    
        //shared/signal/shields_toggled
            set_shields(SIGNAL_CLIENT_ID, SIGNAL_VALUE)"""
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
def signal_control_value (layout_item):
    """What a control holds right now, as a signal payload's ``SIGNAL_VALUE``.
    
    The value AFTER the click: the widget's own on_message has already run (a
    checkbox has toggled, a cycle button advanced) by the time a callback fires.
    A plain button has no value - its ``.value`` is its props string - so None."""
def signal_emit_from_gui (name, data, client_id, item, **extra):
    """Emit a signal for a GUI interaction.
    
    The payload is the author's ``data`` (a dict is copied, anything else is
    passed as ``SIGNAL_DATA``) plus ``SIGNAL_CLIENT_ID`` and ``SIGNAL_ITEM`` and
    any ``extra`` keys.
    
    The sender task is whichever task is current when the click arrives, unless
    it has ended, in which case there is no sender. ``Mast.signal_emit`` drops a
    signal whose sender is finished, and a widget's builder is often finished by
    the time anyone clicks (a ``//gui`` route body, a scheduled builder)."""
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
