from .column import Column
from ...helpers import FrameContext


class Dropdown(Column):
    def __init__(self, tag, props) -> None:
        super().__init__()
        self.values = props
        self.tag = tag
        #TODO: Prase out default ?
        self._value = ""
        
    def _present(self, event):
        ctx = FrameContext.context
        ctx.sbs.send_gui_dropdown(event.client_id, self.region_tag,
            self.tag, self.values,
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)
        
    def on_message(self, event):
        if event.sub_tag == self.tag:
            self.value = event.value_tag
        else:
            super().on_message(event)

    def update(self, props):
        self.props = props

    @property
    def value(self):
        return self._value
       
    @value.setter
    def value(self, v):
        self._value= v
        self.update_variable()
