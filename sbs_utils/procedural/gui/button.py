from ...helpers import FrameContext
from ..style import apply_control_styles

class MessageHandler:
    def __init__(self, layout_item, task, label, jump=False) -> None:
        self.layout_item = layout_item
        self.label = label
        self.task = task
        self.jump = jump

    def on_message(self, event):
        if event.sub_tag == self.layout_item.tag:
            restore = FrameContext.task
            FrameContext.task = self.task
            self.task.set_variable("__ITEM__", self.layout_item)
            if self.jump:
                sub_task = self.task.start_sub_task(self.label, inputs=self.layout_item.data, defer=True)
                sub_task.tick_in_context()
            else:
                self.label()
                
            FrameContext.task = restore

from ...pages.layout.button import Button
def gui_button(props, style=None, data=None, on_message=None, jump=None ):
    """Add a gui button

    Args:
        count (int): The number of columns to use
        style (_type_, optional): Style. Defaults to None.
        data (object): The data to pass to the button's label
        on_message (label): A label to handle a button press
        jump (label): A label to jump to a button press, ending the Await gui

    Returns:
        layout object: The Layout object created
    """        

    page = FrameContext.page
    task = FrameContext.task
    if page is None:
        return None
    tag = page.get_tag()
    props = task.compile_and_format_string(props)
    layout_item = Button(tag, props)
    layout_item.data = data
    apply_control_styles(".button", style, layout_item, task)
    # Last in case tag changed in style
    runtime_item = None
    if on_message is not None:
        runtime_item = MessageHandler(layout_item, task, on_message)
    elif jump is not None:
        runtime_item = MessageHandler(layout_item, task, jump, True)

    page.add_content(layout_item, runtime_item)
    return layout_item