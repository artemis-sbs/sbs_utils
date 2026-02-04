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
    """Trigger to watch when the specified layout element has a message

    Args:
        layout_item (layout object): The object to watch

    Returns:
        trigger: A trigger watches something and runs something when the trigger is reached
    """    
    task = FrameContext.task
    return MessageTrigger(task, layout_item, label)


def gui_message_callback(layout_item, cb):
    """Trigger to watch when the specified layout element has a message

    Args:
        layout_item (layout object): The object to watch

    Returns:
        trigger: A trigger watches something and runs something when the trigger is reached
    """    
    layout_item.on_message_cb = cb


def gui_message_label(layout_item, label):
    from ..execution import gui_sub_task_schedule
    layout_item.on_message_cb = lambda e, s: gui_sub_task_schedule(label)

