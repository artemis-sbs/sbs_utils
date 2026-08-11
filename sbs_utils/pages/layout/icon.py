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
        """Change what the glyph looks like - a new index, or a recolor.

        The dirty mark is the whole point: the props alone are only what the NEXT
        present would send, and a present only happens when something else rebuilds
        the page. A status icon that recolors on damage would have gone on drawing
        its old color until the console was left and re-entered.
        """
        self.props = props
        if not self.is_hidden_by_script:
            # Visual-only: a glyph is square and sized by its row, so its props
            # cannot move the layout the way a text change can.
            self.mark_value_dirty()

