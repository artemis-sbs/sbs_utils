from .column import Column
from ...helpers import FrameContext


class Icon(Column):
    def __init__(self, tag, props) -> None:
        super().__init__()
        self.props = props
        self.tag = tag
        self.square = True

    def _present(self, event):
        #TODO: This should be ctx.aspect_ratio
        ctx = FrameContext.context
        ctx.sbs.send_gui_icon(event.client_id, self.region_tag, self.tag,self.props, 
                    self.bounds.left,self.bounds.top, self.bounds.right, self.bounds.bottom)

    @property
    def value(self):
         return self.icon
       
    @value.setter
    def value(self, v):
        self.icon= v

    def update(self, props):
        self.props = props

