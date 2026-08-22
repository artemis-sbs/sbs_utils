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
        """Change the face shown, and REPAINT it.

        The dirty mark is the whole point. Without it `the_face.value = ...` set the string
        and nothing re-sent `send_gui_face`, so a face only changed on a full page present -
        which is why the avatar editor's sliders moved and the preview did not. Every other
        widget's `update` marks itself; this one did not, and a face is the widget most
        likely to be driven from a live control.

        `is_hidden_by_script` and not `is_hidden`, matching Text: a face merely clipped by
        its parent this frame must still register the change, or it scrolls back into view
        showing the previous person.
        """
        self.face = face
        if not self.is_hidden_by_script:
            # Visual-only. A face is `square = True`, never content-sized, so its measured
            # size cannot move and the expensive layout branch is never the right one.
            self.mark_visual_dirty()

    @property
    def value(self):
         return self.face
       
    @value.setter
    def value(self, v):
        # THROUGH update(), not straight at the field - that is what marks it dirty. This
        # setter is how nearly every caller changes a face (`the_face.value = ...`), so
        # assigning `self.face` here bypassed the repaint for all of them.
        self.update(v)
