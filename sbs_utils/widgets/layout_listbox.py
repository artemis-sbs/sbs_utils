from ..gui import Widget, get_client_aspect_ratio
from ..pages import layout as layout
from ..procedural.gui import apply_control_styles
import sbs
import struct # for images sizes
import os
from .. import fs
from ..helpers import FrameContext, FakeEvent



class SubPage:
    """A class for use with the layout listbox to make using the procedural gui function work
    """
    def __init__(self, tag_prefix, task, client_id) -> None:
        self.tags = set()
        self.tag_prefix = tag_prefix
        self.tag = 0
        self.active_layout = None
        self.layouts=[]
        self.slot = 0
        self.pending_row = None
        # Incase it is needed by the layout elements
        self.client_id = client_id
        self.gui_task = task

    def get_tag(self):
        self.tag += 1
        return f"{self.tag_prefix}:{self.slot}:{self.tag}"
    
    def add_tag(self, layout_item, runtime_node):
        pass
    
    def next_slot(self, slot, section):
        self.active_layout = section
        self.slot = slot
        self.pending_row = None


    def add_content(self, layout_item, runtime_node):
        self.add_tag(layout_item, runtime_node)
        if self.pending_row is None:
            self.add_row()
        self.pending_row.add(layout_item)

    def add_row(self):
        self.pending_row = layout.Row()
        # Rows have tags for background and/or clickable
        self.pending_row.tag = self.get_tag()
        self.active_layout.add(self.pending_row)
        return self.pending_row

    def get_pending_row(self):
        return self.pending_row
    
    def present(self, event):
        for sec in self.layouts:
            sec.calc(event.client_id)
            sec.present(event)



class LayoutListbox(Widget):
    """
      A widget to list things passing function/lamdas to get the data needed for option display of
       a template 
    """

    def __init__(self, left, top, tag_prefix, items, 
                 template_func=None, title=None, 
                 item_width=0,
                 item_height=0,
                 select=False, multi=False) -> None:
        super().__init__(left,top,tag_prefix)
        self.gui_state = "blank"
        self.title = title
        self.cur = 0
        self.bottom = top+40
        self.right = left+33
        self.items = items
        self.select_color = "#bbb3"
        self.click_color = "black"
        self.background= None
        self.title_background=None
        self.select = select
        self.multi= multi
        self.square_width_percent = 0
        self.sections = []
        self.item_width = item_width
        self.item_height = item_height
        self.title_height = 2
        self.template_func = template_func
        self.selected = set()
        self.last_tags = None
        self.horizontal = False
        self.client_id = None
        self.style = "padding: 2px,2px,2px, 2px;"

    def present(self, event):
        """ present

        builds/manages the content of the widget
     
        :param sim: simulation
        :type sim: Artemis Cosmos simulation
        :param CID: Client ID
        :type CID: int
        """
        CID = event.client_id
        self.client_id = CID
        

        if self.horizontal:
            max_slots = (self.right - self.left) // max(self.item_width,1) 
        else:
            max_slots = (self.bottom - self.top) // max(self.item_height,1) 


        max_slots = int(max_slots)
        slot_count = len(self.items)-max_slots
        top = self.top
        left = self.left
        right = self.right
        bottom = self.bottom


        if slot_count > 0:
            self.slot_count = slot_count
            if self.horizontal:
                sbs.send_gui_slider(CID, f"{self.tag_prefix}cur", int(self.cur), f"low:0.0; high: {(slot_count+0.5)}; show_number:no",
                        left, bottom-2,
                        self.right, bottom)
                bottom-=2
            else:
                sbs.send_gui_slider(CID, f"{self.tag_prefix}cur", int(slot_count-self.cur +0.5), f"low:0.0; high: {(slot_count+0.5)}; show_number:no",
                        (right-2), top,
                        right, self.bottom)
                right -= 2

        if self.title is not None:
            title = self.title
            if self.title_background is not None:
                props = f"image:smallWhite; color:{self.title_background};" # sub_rect: 0,0,etc"
                sbs.send_gui_image(CID, 
                    f"{self.tag_prefix}tbg", props,
                    self.left, self.top, right, top+self.title_height)
            sbs.send_gui_text(
                    CID, f"{self.tag_prefix}title", f"{title}",left, top, right, top+self.title_height)
            top += self.title_height


        # get_tag()
        # add_content()
        
        # self.sections = []
        slot = 0
        cur = self.cur

        restore = FrameContext.page
        sub_page = SubPage(self.tag_prefix, restore.gui_task, event.client_id)
        restore = FrameContext.page
        FrameContext.page = sub_page

        for slot in range(max_slots): 
            item = self.items[cur]
            tag = f"{self.tag_prefix}:{slot}"
            this_right =   left+self.item_width
            this_bottom =   top+self.item_height
            if self.horizontal:
                this_bottom = bottom
            else:
                this_right = right
            sec = layout.Layout(tag+":sec", None, left, top, this_right, this_bottom)

            apply_control_styles(".section",  self.style, sec, restore.gui_task)

            if self.select or self.multi:
                sec.click_text = "__________________"
                sec.click_background = "white"
                sec.click_color = "black"
                if cur in self.selected:
                    sec.background = self.select_color
                else:
                    sec.background = "#0000"
                sec.click_tag = f"{tag}:click"

            sub_page.next_slot(slot, sec)
            self.template_func(item)
            #
            # Set the task values
            #
            sec.calc(CID)
            sec.present(event)

            cur += 1
            if self.horizontal:
                left+= self.item_width
            else:
                top+=self.item_height

            if cur >= len(self.items):
                break
        
        # sub_page.present(event)   
        FrameContext.page = restore

        #
        # I the slot should not show
        # gui_hide(sec)

    def on_message(self, event):
        if self.client_id != event.client_id:
            return
        
        if event.sub_tag == f"{self.tag_prefix}cur":
            if self.horizontal:
                value = int(event.sub_float)
            else:
                value = int(-event.sub_float+self.slot_count+0.5)
            if value != self.cur:
                self.cur = value
                self.gui_state = "redraw"
                self.present(event)
            

        if not self.select and not self.multi:
            return
        if not event.sub_tag.startswith(self.tag_prefix):
            return
        sec = event.sub_tag.split(":")
        if len(sec) != 3:
            return
        if sec[0] != self.tag_prefix:
            return
        if sec[2] != "click":
            return
        print(sec[1])
        if not sec[1].isdigit():
            return
        slot = int(sec[1])
        # TODO: Resolver slot to offsets
        if self.multi:
            if slot in self.selected:
                self.selected.discard(slot)
            else:
                self.selected.add(slot)
        elif self.select:
            self.selected = {slot}
        else:
            return
        self.present(event)

        
            

        
    def get_selected(self):
        ret = []
        for item in self.selected:
            ret.append(self.items[item])
        return ret
    
    def select_all(self):
        if self.multi:
            self.selected = set()
            for item in range(len(self.items)):
                self.selected.add(item)
        self.gui_state = "redraw"
        # Pure hackery or brilliant, time will tell
        e = FakeEvent(FrameContext.client_id)
        self.present(e)

    def select_none(self):
        self.selected = set()
        self.gui_state = "redraw"
        # Pure hackery or brilliant, time will tell
        e = FakeEvent(FrameContext.client_id)
        self.present(e)

    def convert_value(self, item):
        return item
    
    def get_value(self):
        ret = []
        if self.convert_value:
            for item in self.selected:
                ret.append(self.convert_value(self.items[item]))
        else:
            ret = self.get_selected()

        if self.multi:
            return ret
        elif len(ret):
            return ret[0]
        else:
            return None
    
    def set_value(self, value):
        self.selected = set()
        i = 0
        for item in self.items:
            if self.convert_value:
                v = self.convert_value(item)
                if v == value:
                    self.selected.add(i)
            elif item == value:
                self.selected.add(i)
            i+=1
    
    def update(self, props):
        pass


#list_box_control(ships, text=lambda ship: ship.comms_id, ship=lambda ship: ship.art_id)



def layout_list_box_control(items, 
                 template_func=None, title=None, 
                 item_width=0,
                 item_height=0,
                 select=False, multi=False):
    # The gui_content sets the values
    return LayoutListbox(0, 0, "mast", items, 
                 template_func, title, 
                 item_width,
                 item_height,
                 select,multi)
