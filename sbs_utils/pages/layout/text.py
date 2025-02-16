from .column import Column
from ...helpers import FrameContext

class Text(Column):
    def __init__(self, tag, message) -> None:
        super().__init__()
        
        self.message = message
        self.tag = tag

    def _present(self, event):
        ctx = FrameContext.context
        message = self.message
        if "$text:" not in message:
            if "text:" not in message:
                message = f"$text:{message};"

        message += self.get_cascade_props(True, True, True)

        ctx.sbs.send_gui_text(event.client_id, self.region_tag,
            self.tag, message,  
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)

    def update(self, message):
        self.message = message

    
    @property
    def value(self):
         return self.message
       
    @value.setter
    def value(self, v):
        self.message = v
