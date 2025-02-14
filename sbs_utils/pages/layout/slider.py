from .column import Column
from ...helpers import FrameContext

class Slider(Column):
    def __init__(self,  tag, value, props, is_int=False) -> None:
        super().__init__()
        self.tag = tag
        self._value = value
        self.props = props
        self.is_int = is_int
        

    def _present(self, event):
        if self.is_int:
            if self._value is None:
                self._value = 0
            self._value = int(self._value)
        ctx = FrameContext.context
        ctx.sbs.send_gui_slider(event.client_id, self.region_tag,
            self.tag, 
            self._value, self.props,
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom,
            )
        
    def on_message(self, event):
        if event.sub_tag == self.tag:
            self.value = event.sub_float
        else:
            super().on_message(event)

    def update(self, props):
        self.props = props


    @property
    def value(self):
        return self._value
    
    
    @value.setter
    def value(self, v):
        if self.is_int:
            self._value = int(v)
        else:
            self._value = v
        self.update_variable()
