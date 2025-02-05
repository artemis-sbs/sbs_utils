from ..layout import layout as layout
from ...helpers import FrameContext


class Control(layout.Column):
    def __init__(self, left, top, right, bottom) -> None:
        super().__init__(left,top, right, bottom)
        self.region = None
        self.absolute = False


    @property
    def local_region_tag(self):
        """ self.tag is inject after init"""
        return self.tag+"$$"

    def present(self, event):
        CID = event.client_id
        SBS = FrameContext.context.sbs
        # If first time create sub region
        the_bounds = self.bounds
        is_update = self.region is not None
        if not is_update:
            if self.absolute:
                SBS.send_gui_sub_region(CID, self.region_tag, self.local_region_tag, "draggable:True;", 0,0,100,100)
            else:
                SBS.send_gui_sub_region(CID, self.region_tag, self.local_region_tag, "draggable:True;", the_bounds.left,the_bounds.top,the_bounds.right,the_bounds.bottom)
            self.region = True
        else:
            if self.absolute:
                SBS.send_gui_sub_region(CID, self.region_tag, self.local_region_tag, "draggable:True;", 0,0,100,100)
            else:
                SBS.send_gui_sub_region(CID, self.region_tag, self.local_region_tag, "draggable:True;", the_bounds.left,the_bounds.top,the_bounds.right,the_bounds.bottom)
            
        SBS.send_gui_clear(CID, self.local_region_tag)
        super().present(event)
        SBS.send_gui_complete(CID, self.local_region_tag)
        
    def invalidate_regions(self):
        self.region = None
        super().invalidate_regions()


