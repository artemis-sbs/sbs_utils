from ..layout import layout as layout
from ...helpers import FrameContext, FakeEvent
from ...procedural.gui.gui import gui_percent_from_ems, gui_percent_from_pixels
from ...agent import Agent

#
# 350 x 270
# ICon panel 30x30
# Means 9 possible panels 
#   Ship Data/text waterfall sliver
#   Objectives
#   Text 
#   Messages
# Try to limit interaction to only panel selections

# Also possible transient panels
#   i.e. Shows up and goes away after a period 
#        Information is still available elsewhere
#   Objective Announcements
#   Message: Face + Title + Text

class TabbedPanel(layout.Column):
    def __init__(self, left, top, right, bottom, tag_prefix, panels=None, tab=0, tab_location=0, icon_size=0) -> None:
        super().__init__(left,top, right, bottom)
        self.tag_prefix = tag_prefix
        self.local_region_tag = tag_prefix+"$$"
        self.tag  = tag_prefix
        self.client_id = None
        self.current = tab
        self.tab_location = tab_location
        self.icon_size = icon_size if icon_size >0 else 30
        
        self.panels = panels

    def present_panel(self, event, panel, icon_size):
        CID = event.client_id
        self.client_id = CID
        SBS = FrameContext.context.sbs


        top = self.bounds.top
        left = self.bounds.left + icon_size.x
        width = self.bounds.width - icon_size.x
        height = self.bounds.height

        if self.tab_location ==1:        
            left = self.bounds.left
        if self.tab_location == 2: # top
            left = self.bounds.left
            top = self.bounds.top + icon_size.y
            width = self.bounds.width
            height = self.bounds.height - icon_size.y
        if self.tab_location == 3: # bottom
            height = self.bounds.height - icon_size.y
            width = self.bounds.width
            left = self.bounds.left
            top = self.bounds.top

        show = panel.get("show")
        if show is not None:
            show(event.client_id, left, top, width, height)

    

    def present_icon(self, event, icon, index, icon_size):
        CID = event.client_id
        self.client_id = CID
        SBS = FrameContext.context.sbs
        
        top = self.bounds.top + index*icon_size.y
        left = self.bounds.left
        if self.tab_location == 1:        
            top = self.bounds.top + index*icon_size.y
            left = self.bounds.right - icon_size.x
        if self.tab_location == 2: # top
            top = self.bounds.top
            left = self.bounds.left + index * icon_size.x
        if self.tab_location == 3: # bottom
            top = self.bounds.bottom - icon_size.y
            left = self.bounds.left + index * icon_size.x

        SBS.send_gui_icon(event.client_id, self.local_region_tag, f"{self.tag_prefix}:icon_",
                    f"icon_index:{icon};color:#aaa;draw_layer:1000;",
                    left, top, left+icon_size.x, top+icon_size.y)
        SBS.send_gui_clickregion(event.client_id, self.local_region_tag, 
                    f"{self.tag_prefix}icon:{index}", "background_color:#6663",
                    left, top, left+icon_size.x, top+icon_size.y)
        

    @property
    def value(self):
        return self.current
    
    @value.setter
    def value(self, v):
        self.set_tab(v)

    def _present(self, event):
        if self.client_id is None:
            # First draw blindly hide ship_data
            for p in self.panels:
                hide = p.get("hide")
                if hide is not None:
                    hide(event.client_id, 0,0,0,0)
        left = self.bounds.left
        top = self.bounds.top
        icon_size = gui_percent_from_pixels(event.client_id, self.icon_size)
        for index, panel in enumerate(self.panels):
            icon = panel.get("icon", 0)
            self.present_icon(event, icon,index,icon_size )
            if index == self.current:
                self.present_panel(event, panel, icon_size)

    def set_tab(self, tab):

        if tab == self.current:
            return
        cur = self.panels[self.current]
        hide = cur.get("hide")
        self.current = tab

        if hide:
            icon_size = gui_percent_from_pixels(self.client_id, self.icon_size)
            hide(self.client_id, self.bounds.left+icon_size.x, self.bounds.top, self.bounds.width-icon_size.x, self.bounds.height)

        e = FakeEvent(self.client_id)
        self.represent(e)
    
    def present(self, event):
        CID = event.client_id
        SBS = FrameContext.context.sbs
        SBS.send_gui_sub_region(CID, self.region_tag, self.local_region_tag, "draggable:True;", 0,0,100,100)
        self.region = True
        SBS.send_gui_clear(CID, self.local_region_tag)
        super().present(event)
        SBS.send_gui_complete(CID, self.local_region_tag)

    def on_message(self, event):
        if self.client_id != event.client_id:
            return
        if not event.sub_tag.startswith(self.tag_prefix):
            return
        
        if event.sub_tag.startswith(self.tag_prefix+"icon:"):
            chop = len(self.tag_prefix+"icon:")
            #left = len(event.sub_tag)
            n = event.sub_tag[chop:].strip()
            icon = int(n)
            self.set_tab(icon)
            
def tabbed_panel_control(tag_prefix, items, tab=0, tab_location=0):
    return TabbedPanel(0, 0, 10,10, tag_prefix, items, tab, tab_location)
