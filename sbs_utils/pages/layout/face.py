from .column import Column
from ...helpers import FrameContext


class Face(Column):
    """A face box.

    A FACE CANNOT CARRY A DRAW LAYER, and that is an engine API limit rather than an
    omission here. `send_gui_face`'s fourth argument is the face string itself, where every
    other widget takes a style::

        send_gui_text (clientID, parent, tag, style,       l,t,r,b)
        send_gui_image(clientID, parent, tag, style,       l,t,r,b)
        send_gui_face (clientID, parent, tag, face_string, l,t,r,b)   <- nowhere for one

    Audited across every `send_gui_*` in the typings, this is the ONLY drawable widget
    without a style parameter, so it is the only one that cannot be raised. It therefore
    always paints at the engine default (1001), and there is deliberately no
    `get_cascade_props` call below - there is nothing to send it in.

    WHAT THAT MEANS FOR CALLERS: an opaque background raised above 1001 will hide a face
    sitting in the same row. Build the fill AROUND the face - put it on gutter columns
    either side and leave the face's own column bare, which costs nothing because a face
    square is opaque. `procedural/gui/hail_gui.py` does this in `_hail_screen_builder`.
    """

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
