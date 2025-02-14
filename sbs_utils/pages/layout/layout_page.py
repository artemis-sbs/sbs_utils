from .column import Column
from ...helpers import FrameContext
from ...gui import Page, get_client_aspect_ratio
from .layout import Layout



class LayoutPage(Page):
    def __init__(self) -> None:
        super().__init__()
        self.gui_state = 'repaint'
        self.layout = Layout()
        SBS = FrameContext.context.sbs
        self.aspect_ratio = SBS.vec3(1024,768,0)
        

    def _present(self, event):
        """ Present the gui """
        aspect_ratio = get_client_aspect_ratio(event.client_id)
        sz = ctx.aspect_ratio
        if self.aspect_ratio.x != sz.x or self.aspect_ratio.y != sz.y:
            self.aspect_ratio.x = sz.x
            self.aspect_ratio.y = sz.y
            self.layout.calc(event.client_id)
            self.gui_state = 'repaint'

        ctx = FrameContext.context
        match self.gui_state:
            case  "repaint":
                ctx.sbs.send_gui_clear(event.client_id, "")
                # Setting this to a state we don't process
                # keeps the existing GUI displayed
                self.gui_state = "presenting"
                self.layout.present(event)
                ctx.sbs.send_gui_complete(event.client_id, "")
                

