from .column import Column
from ...helpers import FrameContext


# Allows the layout of a engine widget
class ConsoleWidget(Column):
    def __init__(self, widget) -> None:
        super().__init__()
        self.widget = widget

    def _present(self, event):
        ctx = FrameContext.context
        ctx.sbs.send_client_widget_rects(event.client_id, 
                self.widget, 
                self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom, 
                self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom) 
