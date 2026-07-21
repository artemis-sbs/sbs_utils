from .column import Column
from ...helpers import FrameContext


class Dropdown(Column):
    def __init__(self, tag, props) -> None:
        super().__init__()
        self.values = props
        self.tag = tag
        #TODO: Prase out default ?
        self._value = ""
        
    def measure(self, client_id, mode, avail_px, font, ar):
        """Deliberately unmeasurable -- do not "fix" this to measure the list.

        A dropdown's rendered width is its widest option PLUS engine-drawn
        chrome (the arrow, the border) whose size we cannot ask for. Sizing to
        the text alone would come out narrow, and because the engine does not
        clip, a narrow dropdown draws its label over its neighbour rather than
        truncating. Falling back to flex is the safe answer, and it is exactly
        what happened before content sizing existed.
        """
        return None

    def _present(self, event):
        ctx = FrameContext.context
        ctx.sbs.send_gui_dropdown(event.client_id, self.region_tag,
            self.tag, self.values,
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)
        
    def on_message(self, event):
        if event.sub_tag == self.tag:
            self.value = event.value_tag
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
