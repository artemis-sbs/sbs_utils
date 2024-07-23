from ...gui import Widget
from ..layout import layout as layout
import sbs
from ... import fs
from ...procedural import ship_data


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
        # If first time create sub region
        the_bounds = self.bounds
        is_update = self.region is not None
        if not is_update:
            #print(f"Control {self.__class__.__name__} CREATE ~{self.region_tag}~ {self.local_region_tag}")
            if self.absolute:
                sbs.send_gui_sub_region(CID, self.region_tag, self.local_region_tag, "draggable:True;", 0,0,100,100)
            else:
                sbs.send_gui_sub_region(CID, self.region_tag, self.local_region_tag, "draggable:True;", the_bounds.left,the_bounds.top,the_bounds.right,the_bounds.bottom)
            self.region = True
        else:
            #print(f"Control {self.__class__.__name__} UPDATE ~{self.region_tag}~  {self.local_region_tag}")
            if self.absolute:
                sbs.send_gui_sub_region(CID, self.region_tag, self.local_region_tag, "draggable:True;", 0,0,100,100)
            else:
                sbs.send_gui_sub_region(CID, self.region_tag, self.local_region_tag, "draggable:True;", the_bounds.left,the_bounds.top,the_bounds.right,the_bounds.bottom)
            
        sbs.send_gui_clear(CID, self.local_region_tag)
        super().present(event)
        sbs.send_gui_complete(CID, self.local_region_tag)
        # else:
        #     sbs.send_gui_clear(CID, self.region_tag)
        #     super().present(event)
        #     sbs.send_gui_complete(CID, self.region_tag)

        #sbs.target_gui_sub_region(CID, "")
        
    def invalidate_regions(self):
        # print(f"Invalidate Control {self.region_tag}")
        self.region = None
        super().invalidate_regions()


