from .column import Column
from ...helpers import FrameContext


class IconButton(Column):
    def __init__(self, tag, props) -> None:
        super().__init__()
        self.tag = tag
        self.props = props
        self.square = True

    def _present(self,  event):
        ctx = FrameContext.context
        ctx.sbs.send_gui_iconbutton(event.client_id, self.region_tag,
            self.tag, self.props, 
            self.bounds.left,self.bounds.top, self.bounds.right, self.bounds.bottom)
    @property
    def value(self):
         return self.props
       
    @value.setter
    def value(self, v):
        self.props = v
    def update(self, props):
        self.props = props

