from ...gui import Widget
from ..layout import layout as layout
import sbs
from ... import fs
from ...procedural import ship_data


class Control(layout.Column):
    def __init__(self, left, top, right, bottom) -> None:
        super().__init__(left,top, right, bottom)
        self.region = None

    @property
    def region_tag(self):
        return self.tag+"$$"

    def present(self, event):
        CID = event.client_id
        is_update = self.region is not None
        # If first time create sub region
        the_bounds = self.bounds
        if not is_update:
            print(f"Ship Picker CREATE present {self.region_tag}")
            sbs.send_gui_sub_region(CID, self.region_tag, "draggable:True;", the_bounds.left,the_bounds.top,the_bounds.right,the_bounds.bottom)
            sbs.send_gui_clear(CID, self.region_tag)
            self.region = True
            sbs.target_gui_sub_region(CID, self.region_tag)
            super().present(event)
            sbs.send_gui_complete(CID, self.region_tag)
        else:
            print(f"Ship Picker UPDATE present {self.region_tag}")
            sbs.target_gui_sub_region(CID, self.region_tag)
            sbs.send_gui_clear(CID, self.region_tag)
            
            super().present(event)
            sbs.send_gui_complete(CID, self.region_tag)

        sbs.target_gui_sub_region(CID, "")
        
    def invalidate_regions(self):
        print(f"Invalidate {self.region_tag}")
        self.region = None


