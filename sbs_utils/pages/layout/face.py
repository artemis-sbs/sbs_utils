from .column import Column
from ...helpers import FrameContext


class Face(Column):
    def __init__(self, tag, face) -> None:
        super().__init__()
        self.face = face
        self.tag = tag
        self.square = True

    def _present(self, event):
        ctx = FrameContext.context
        ctx.sbs.send_gui_face(event.client_id, self.region_tag,
            self.tag, self.face,
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)

    def update(self, face):
        self.face = face

    @property
    def value(self):
         return self.face
       
    @value.setter
    def value(self, v):
        self.face= v
