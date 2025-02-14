from .column import Column
from ...helpers import FrameContext
import re

class TextInput(Column):
    def __init__(self, tag, props) -> None:
        super().__init__()
        self._value = ""
        if "text:" in props:
            #TODO: Need to parse out value
            #     
            text = re.search(r"\$?text:(?P<text>.*);", props).group('text')
            if text:
                self._value = text

            fix_props = re.sub(r'\$?text:\s*.*;', "", props)
            props = fix_props
            
        self.tag = tag
        self.props = props
        
    def _present(self, event):
        ctx = FrameContext.context
        props = f"$text:{self._value};"
        props += self.props
        props += self.get_cascade_props(True, True, True)
        ctx.sbs.send_gui_typein(event.client_id, self.region_tag,
            self.tag, props,
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)
        
    def on_message(self, event):
        if event.sub_tag == self.tag:
            self.value = event.value_tag
        else:
            super().on_message(event)
        
    @property
    def value(self):
         return self._value
       
    @value.setter
    def value(self, v):
        self._value= v
        self.update_variable()
