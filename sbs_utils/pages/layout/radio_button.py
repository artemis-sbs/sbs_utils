from .column import Column
from ...helpers import FrameContext


class RadioButton(Column):
    def __init__(self, tag,  message, parent, value=False) -> None:
        super().__init__()
        self.message = message
        self.tag = tag
        self._value = value
        self.parent = parent
        self.group = parent.group
        
    def _present(self, event):
        ctx = FrameContext.context
        props = f"state:{self._value==1};$text:{self.message};"
        ctx.sbs.send_gui_checkbox(event.client_id, self.region_tag,
            self.tag, props,
            # 1 if self._value else 0,
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)
    
    def on_message(self, event):
        if event.sub_tag == self.tag:
            self.value = 1
            
            for e in self.group:
                if e != self:
                    e.value = 0
                e.present(event)
            #
            #
            self.parent.update_variable()
        super().on_message(event)

    @property
    def value(self):
         return self._value
       
    @value.setter
    def value(self, v):
        self._value= v
