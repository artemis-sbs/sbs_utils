from ..layout import layout as layout
from ...helpers import FrameContext, FakeEvent
from ...procedural.gui.gui import gui_percent_from_pixels, gui_page_for_client, gui_task_for_client
from ...agent import Agent
from ...tickdispatcher import TickDispatcher
from .layout_listbox import SubPage
import traceback

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
        self.flash_task = None
        self.sec = None

    def present_panel(self, event, panel, icon_size):
        CID = event.client_id
        self.client_id = CID
        space = 1.1
        
        top = self.bounds.top
        left = self.bounds.left + icon_size.x * space
        width = self.bounds.width - icon_size.x * space
        height = self.bounds.height

        if self.tab_location ==1:        
            left = self.bounds.left 
        if self.tab_location == 2: # top
            left = self.bounds.left
            top = self.bounds.top + icon_size.y  * space
            width = self.bounds.width
            height = self.bounds.height - icon_size.y * space
        if self.tab_location == 3: # bottom
            height = self.bounds.height - icon_size.y * space
            width = self.bounds.width
            left = self.bounds.left
            top = self.bounds.top

        show = panel.get("show")
        path = panel.get("path")
        task = gui_task_for_client(CID)
        if task is not None:
            task.set_variable("$INFO_PATH", path) 

        self.sec = None
        if show is not None:
            #restore = gui_task_for_client(event.client_id)
            restore = FrameContext.page 
            sub_page = SubPage(self.tag_prefix, self.local_region_tag, restore.gui_task, CID)
            FrameContext.page = sub_page
            sec = layout.Layout(self.tag_prefix+":subsec", None, left, top, left+width, top+height)
            sec.region_tag = self.local_region_tag
            sec.item_index = 0
            sub_page.next_slot(0, sec)
            self.sec = sec
            try:
                show(event.client_id, left, top, width, height)
            except Exception as e:
               print(e)
               print(traceback.format_exc())

            #
            sec.calc(CID)
            sec.present(event)
            #
            # Add tags to the client_page
            # May needs this for click?
            #
            FrameContext.page = restore
            page = gui_page_for_client(CID)
            page.tag_map |= sub_page.tag_map
            
            
            

    def present_icon(self, event, icon, index, icon_size):
        CID = event.client_id
        self.client_id = CID
        SBS = FrameContext.context.sbs
        space = 1.1
        
        top = self.bounds.top + index*(icon_size.y*space)
        left = self.bounds.left
        if self.tab_location == 1:        
            top = self.bounds.top + index*(icon_size.y*space)
            left = self.bounds.right - icon_size.x
        if self.tab_location == 2: # top
            top = self.bounds.top
            left = self.bounds.left + index * (icon_size.x*space)
        if self.tab_location == 3: # bottom
            top = self.bounds.bottom - icon_size.y
            left = self.bounds.left + index * (icon_size.x*space)

        color = "#aaa"
        if index == self.current:
            color = "#0a0"

        SBS.send_gui_icon(event.client_id, self.local_region_tag, f"{self.tag_prefix}:icon_",
                    f"icon_index:{icon};color:{color};draw_layer:1000;",
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
                    try:
                        hide(event.client_id, 0,0,0,0)
                    except Exception as e:
                        print(e.message)
                        print(traceback.format_exc())
                        

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
        # Clear any flash_task
        if self.flash_task is not None:
            self.flash_task.stop()
            self.flash_task = None

    
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

        if self.sec is not None:
            self.sec.on_message(event)
        

    def unflash_tab(self, t):
        set_to = t.prev_tab
        self.set_tab(set_to)
        t.stop()

    def find_tab(self, tab):
        if not isinstance(tab, str):
            return tab
        for index, p in enumerate(self.panels):
            path = p.get("path")
            if path == tab:
                return index
        return tab


    def flash_tab(self, tab, time):
        tab = self.find_tab(tab)
        if tab == self.current:
            e = FakeEvent(self.client_id)
            self.represent(e)

        prev_tab = self.current
        back_tab = None
        if self.flash_task is not None:
            back_tab = self.flash_task.prev_tab
            self.flash_task.stop()
            self.flash_task = None

        self.set_tab(tab)
        if time==0:
            return
        
        self.flash_task = TickDispatcher.do_once(self.unflash_tab, time)
        if back_tab is not None and prev_tab == self.current:
            self.flash_task.prev_tab = back_tab
        else:
            self.flash_task.prev_tab = prev_tab



def tabbed_panel_control(tag_prefix, items, tab=0, tab_location=0):
    return TabbedPanel(0, 0, 10,10, tag_prefix, items, tab, tab_location)
