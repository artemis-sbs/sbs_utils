from .column import Column
from ...helpers import FrameContext

class Checkbox(Column):
    def __init__(self, tag, message, value=False) -> None:
        super().__init__()
        if "$text:" not in message:
            if "text:" not in message:
                message = f"$text:{message};"
        self.message = message
        self.tag = tag
        self._value = value
        
    def _present(self, event):
        message = f"state: {self._value};{self.message}"
        message += self.get_cascade_props(True, True, True)
        ctx = FrameContext.context
        ctx.sbs.send_gui_checkbox(event.client_id, self.region_tag,
            self.tag, message, 
            # 1 if self._value else 0,
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)
    
    def on_message(self, event):
        if event.sub_tag == self.tag:
            self.value= not self.value
            
            self.present(event)
        super().on_message(event)
            #self.value = int(event.sub_float)

    def update(self, message):
        if "$text:" not in message:
            message = f"$text:{message};"
        self.message = message


    @property
    def value(self):
        return self._value
    
    @value.setter
    def value(self, v):
        self._value= v
        self.update_variable()

