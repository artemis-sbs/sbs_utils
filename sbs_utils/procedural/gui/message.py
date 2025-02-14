from ...helpers import FrameContext
from ...futures import Trigger

class MessageTrigger(Trigger):
    def __init__(self, task, layout_item, label=None):
        # This will remap to include this as the message handler
        task.main.page.add_tag(layout_item, self)
        self.task = task
        self.layout_item = layout_item
        # Needs to be set by Mast
        # Pure mast this is active Label
        # Python ith should be a callable
        self.label = label
        if label is None:
            self.label = task.active_label 
        # 0 for python the node loc of the on in Mast
        self.loc = 0


    def on_message(self, event):
        if event.sub_tag == self.layout_item.tag:
            self.task.set_value_keep_scope("__ITEM__", self.layout_item)
            data = self.layout_item.data
            self.task.push_inline_block(self.label, self.loc, data)
            self.task.tick_in_context()

def gui_message(layout_item):
    """Trigger to watch when the specified layout element has a message

    Args:
        layout_item (layout object): The object to watch

    Returns:
        trigger: A trigger watches something and runs something when the trigger is reached
    """    
    task = FrameContext.task
    return MessageTrigger(task, layout_item)
