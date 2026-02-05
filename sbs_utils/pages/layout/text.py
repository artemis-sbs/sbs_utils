from .column import Column
from ...helpers import FrameContext, merge_props, split_props

class Text(Column):
    def __init__(self, tag, message) -> None:
        super().__init__()
        self.message = message
        self.value = message
        self.tag = tag

    def _present(self, event):
        ctx = FrameContext.context
        message = self.message + self.get_cascade_props(True, True, True)
        ctx.sbs.send_gui_text(event.client_id, self.region_tag,
            self.tag, message,
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)

    def update(self, message):
        props = split_props(message, "$text")
        text = props.get("$text", props.get("text"))
        if text is None:
            props["$text"] = ""

        message = merge_props(props)
        self.message = message

    
    @property
    def value(self):
         return self.message
       
    @value.setter
    def value(self, v):
        self.update(v)
