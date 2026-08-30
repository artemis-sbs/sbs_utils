from .column import Column
from ...helpers import FrameContext


def _parse_alt(alt):
    """An explicit second rect, as "l,t,r,b" or a 4-sequence. None means none."""
    if alt is None:
        return None
    if isinstance(alt, str):
        alt = [p.strip() for p in alt.split(",")]
    if len(alt) != 4:
        raise ValueError(
            f"an engine widget's alt rect is 'left,top,right,bottom', got {alt!r}")
    return tuple(float(v) for v in alt)


# Allows the layout of a engine widget
class ConsoleWidget(Column):
    def __init__(self, widget, alt=None) -> None:
        super().__init__()
        self.widget = widget
        # send_client_widget_rects takes TWO rects and the engine chooses between
        # them; data/guiboxdata.txt gives every stock widget a different pair. A
        # layout can only compute one, so the same rect goes in both slots unless
        # a caller supplies the second - which is how a console reproduces a stock
        # widget's own placement exactly rather than flattening it to one variant.
        self.alt_bounds = _parse_alt(alt)

    def _present(self, event):
        ctx = FrameContext.context
        b = self.bounds
        alt = self.alt_bounds or (b.left, b.top, b.right, b.bottom)
        ctx.sbs.send_client_widget_rects(event.client_id,
                self.widget,
                b.left, b.top, b.right, b.bottom,
                *alt)
        # This console OWNS this widget's position now, and says where. Recorded so
        # the widget can be parked offscreen when it falls off the console's widget
        # list and put back HERE when it returns, rather than at a guess. Both rects,
        # so putting it back restores what was actually sent. Local import: gui
        # reaches back into the layout package.
        from ...gui import Gui
        Gui.record_widget_rect(event.client_id, self.widget,
                               b.left, b.top, b.right, b.bottom, *alt)
