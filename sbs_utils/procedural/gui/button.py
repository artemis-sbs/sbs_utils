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
            # Should it use data here?
            if not self.is_sub_task:
                data = self.layout_item.data
                if data is not None and isinstance(data, dict):
                    for k,v in data.items():
                        self.task.set_variable(k, v)
                elif data is not None:
                    self.task.set_variable("data", data)

            if isinstance(self.handler, Promise):
                self.handler.set_result(ButtonResult(self.layout_item, event.client_id))
            elif callable(self.handler):
                self.handler()
            elif not self.is_sub_task and self.handler is not None:
                self.task.jump(self.handler)
            else:
                sub_task = self.task.start_sub_task(self.handler, inputs=self.layout_item.data, defer=True)
                sub_task.set_variable("__ITEM__", self.layout_item)
                sub_task.tick_in_context()
            
                
            FrameContext.task = restore

from ...pages.layout.button import Button
def gui_button(props, style=None, data=None, on_press=None, is_sub_task=False):
    """Add a button to the current GUI layout outside of an ``await gui()`` block.

    Unlike buttons declared with ``*`` or ``+`` inside ``await gui()``, this
    button is placed directly in the layout at the current position and fires
    its handler without ending the surrounding ``await gui()``. Use it for
    action buttons embedded in panels, listboxes, or info panels.

    Args:
        props (str): Button label text, optionally as a property string
            (e.g. ``"$text:Fire!;color:red;"``). Supports ``{var}``
            interpolation.
        style (str, optional): Additional CSS-like style overrides.
            End each property with a semicolon, e.g. ``"col-width:20%;"``.
            Defaults to None.
        data (object, optional): Arbitrary data passed to the handler.
            Available as ``__ITEM__`` and (if a dict) as individual variables.
            Defaults to None.
        on_press (label | callable | Promise, optional): What to do when the
            button is pressed. A label is jumped to; a callable is called; a
            Promise has its result set. Defaults to None.
        is_sub_task (bool, optional): When ``True`` the handler runs as an
            independent sub-task. Use ``False`` (default) only when pressing
            the button will rebuild the entire GUI via ``await gui()``.
            Defaults to False.

    Valid Styles:
        area: 
            Format as `top, left, bottom, right`. 
            Just numbers indicates percentage of the section or page to cover. 
            Can also use `px` (pixels) or `em` (1em = height of text font).
            Can combine different units, e.g. `5+5px, 3em, 100-10em, 50px;` is a valid area.
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