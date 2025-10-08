from ...helpers import FrameContext
from ..style import apply_control_styles
from ...futures import Promise


class ButtonResult:
    def __init__(self, layout_item, client_id):
        self.layout_item = layout_item
        self.client_id = client_id
    
    @property
    def value(self):
        return self.layout_item.value
    
    @property
    def data(self):
        return self.layout_item.data
        

class MessageHandler:
    def __init__(self, layout_item, task, handler, is_sub_task) -> None:
        self.layout_item = layout_item
        self.handler = handler
        self.task = task
        self.is_sub_task = is_sub_task
        

    def on_message(self, event):
        if event.sub_tag == self.layout_item.tag:
            restore = FrameContext.task
            FrameContext.task = self.task
            self.task.set_variable("__ITEM__", self.layout_item)
            if isinstance(self.handler, Promise):

                self.handler.set_result(ButtonResult(self.layout_item, event.client_id))
            elif callable(self.handler):
                self.handler()
            elif not self.is_sub_task:
                self.task.jump(self.handler)
            else:
                sub_task = self.task.start_sub_task(self.handler, inputs=self.layout_item.data, defer=True)
                sub_task.tick_in_context()
            
                
            FrameContext.task = restore

from ...pages.layout.button import Button
def gui_button(props, style=None, data=None, on_press=None, is_sub_task=False):
    """Add a gui button

    Args:
        props (str): Properties. Usually just the text on the button
        style (str, optional): Style. Defaults to None. End each style with a semicolon, e.g. `color:red;`
        data (object): The data to pass to the button's label
        on_press (label, callable, Promise): Handle a button press, label is jumped to, callable is called, Promise has results set

    Valid Styles:
        area: 
            Format as `top, left, bottom, right`. 
            Just numbers indicates percentage of the section or page to cover. 
            Can also use `px` (pixels) or `em` (1em = height of text font)
        color:
            The color of the text
        background-color:
            The background color of the button
        padding:
            A gap inside the element (makes the button smaller, but the background still is there.)
        margin: 
            The gap outside the element (makes the button smaller). 
        col-width: 
            The width of the button
        justify:
            Where the text is placed inside the button. `left`, `center`, or `right`
        font:
            The font to use. Overrides the font in prefernces.json
        
        

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
    runtime_item = MessageHandler(layout_item, task, on_press, is_sub_task)

    page.add_content(layout_item, runtime_item)
    return layout_item