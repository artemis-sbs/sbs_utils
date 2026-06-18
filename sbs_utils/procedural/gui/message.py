from ...helpers import FrameContext
from ...futures import Trigger

class MessageTrigger(Trigger):
    def __init__(self, task, layout_item, label=None):
        # This will remap to include this as the message handler
        task.main.page.add_tag(layout_item, self)
        page = FrameContext.page 
        #
        # This is an outlier 
        # Your in a sub page 
        #
        if page != task.main.page:
            page.add_tag(layout_item, self)

        self.task = task
        self.layout_item = layout_item
        # Needs to be set by Mast
        # Pure mast this is active Label
        # Python ith should be a callable
        self.label = label
        self.use_sub_task = False
        if label is None:
            self.label = task.active_label 
        else:
            self.use_sub_task = True
        # 0 for python the node loc of the on in Mast
        self.loc = 0



    def on_message(self, event):
        if self.layout_item.is_message_for(event):
            self.task.set_value_keep_scope("__ITEM__", self.layout_item)
            data = None
            if hasattr(self.layout_item, "data"):
                data = self.layout_item.data
            if not self.use_sub_task:
                self.task.push_inline_block(self.label, self.loc, data)
                self.task.tick_in_context()
            else:
                sub_task = self.task.start_sub_task(self.label, inputs=data, defer=True)
                sub_task.tick_in_context()

def gui_message(layout_item, label=None):
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
            gui_text("Region clicked!")
    """
    task = FrameContext.task
    return MessageTrigger(task, layout_item, label)


def gui_message_callback(layout_item, cb):
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
        gui_message_callback(btn, lambda e, item: fire_torpedo(SHIP_ID))
    """
    layout_item.on_message_cb = cb


def gui_message_label(layout_item, label):
    """Schedule a MAST label as a sub-task when a layout element receives a GUI event.

    Similar to ``gui_message_callback`` but wraps the label in a
    ``gui_sub_task_schedule`` call, running it as an independent sub-task
    rather than inline in the current task.

    Args:
        layout_item: The layout object to attach the handler to.
        label: MAST label to schedule as a sub-task on event.

    Example:
        section = gui_sub_section(style="col-width:30%;")
        gui_message_label(section, handle_section_click)
    """
    from ..execution import gui_sub_task_schedule
    layout_item.on_message_cb = lambda e, s: gui_sub_task_schedule(label)

