from .column import Column
from ...helpers import FrameContext

class Button(Column):
    def __init__(self, tag, message) -> None:
        super().__init__()
        self.tag = tag
        if "$text:" not in message:
            self.message = f"$text:{message};"
        else:
            self.message = message

    def _present(self,  event):
        ctx = FrameContext.context
        message = self.message
        message += self.get_cascade_props(True, True, True)
        ctx.sbs.send_gui_button(event.client_id, self.region_tag,
            self.tag, message, 
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)
        

    def update(self, message):
        if "$text:" not in message:
            message = f"$text:{message};"
        self.message = message


    @property
    def value(self):
        return self.message

    @value.setter
    def value(self, v):
        if "$text:" not in v:
            v = f"$text:{v}"

        self.message = v
