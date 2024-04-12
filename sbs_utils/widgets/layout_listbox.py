from ..gui import get_client_aspect_ratio
from ..pages import layout as layout
import sbs
import struct # for images sizes
import os
from .. import fs
from ..helpers import FrameContext, FakeEvent
from ..mast.parsers import LayoutAreaParser



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
        tag =  f"{self.tag_prefix}:{self.slot}:{self.tag}"
        self.tags.add(tag)
        return tag
    
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



class LayoutListbox(layout.Column):
    """
      A widget to list things passing function/lamdas to get the data needed for option display of
       a template 
    """

    def __init__(self, left, top, tag_prefix, items, 
                 template_func=None, title=None, 
                 section_style=None,
                 select=False, multi=False) -> None:
        super().__init__(left,top,33,44)

        self.tag_prefix = tag_prefix
        self.tag  = tag_prefix
        self.gui_state = "blank"
        self.title = title
        self.cur = 0
        # self.bottom = top
        # self.right = left+33
        self.items = items
        self.select_color = "#bbb3"
        self.click_color = "black"
        self.background= None
        self.title_background=None
        self.default_item_width = None
        self.default_item_height = None
        self.select = select
        self.multi= multi
        self.square_width_percent = 0
        #self.sections = []
        self.title_height = 2
        self.template_func = template_func
        self.selected = set()
        self.last_tags = None
        self.horizontal = None
        self.client_id = None
        self.section_style = section_style
        if section_style is None:
            self.section_style = "padding: 2px,2px,2px,2px;"

    def set_row_height(self, height):
        self.default_item_height = height

    def set_col_width(self, width):
        self.default_item_width = width


    def _present(self, event):
        """ present

        builds/manages the content of the widget
     
        :param sim: simulation
        :type sim: Artemis Cosmos simulation
        :param CID: Client ID
        :type CID: int
        """
        from ..procedural.gui import gui_hide
        CID = event.client_id
        self.client_id = CID

        item_width = self.bounds.width 
        item_height = self.bounds.height
        aspect_ratio = get_client_aspect_ratio(event.client_id)

        if self.default_item_width:
            item_width = LayoutAreaParser.compute(self.default_item_width, None, aspect_ratio.x, 20)
            if self.horizontal is None:
                self.horizontal = True
        
        if self.default_item_height:
            item_height = LayoutAreaParser.compute(self.default_item_height, None, aspect_ratio.y, 20)

        # At this point is should assume it is vertical
        if self.horizontal is None:
            self.horizontal = False
        

        if self.horizontal:
            max_slots = (self.bounds.right - self.bounds.left) // max(item_width,1) 
        else:
            max_slots = (self.bounds.bottom - self.bounds.top) // max(item_height,1) 


        max_slots = int(max_slots)
        slot_count = len(self.items)-max_slots
        top = self.bounds.top
        left = self.bounds.left
        right = self.bounds.right
        bottom = self.bounds.bottom


        if slot_count > 0:
            self.slot_count = slot_count
            if self.horizontal:
                sbs.send_gui_slider(CID, f"{self.tag_prefix}cur", int(self.cur), f"low:0.0; high: {(slot_count+0.5)}; show_number:no",
                        left, bottom-2,
                        self.bounds.right, bottom)
                bottom-=2
            else:
                sbs.send_gui_slider(CID, f"{self.tag_prefix}cur", int(slot_count-self.cur +0.5), f"low:0.0; high: {(slot_count+0.5)}; show_number:no",
                        (right-2), top,
                        right, self.bounds.bottom)
                right -= 2

        if self.title is not None:
            title = self.title
            if self.title_background is not None:
                props = f"image:smallWhite; color:{self.title_background};" # sub_rect: 0,0,etc"
                sbs.send_gui_image(CID, 
                    f"{self.tag_prefix}tbg", props,
                    self.bounds.left, self.bounds.top, right, top+self.title_height)
            sbs.send_gui_text(
                    CID, f"{self.tag_prefix}title", f"{title}",left, top, right, top+self.title_height)
            top += self.title_height


        # get_tag()
        # add_content()
        slot = 0
        cur = self.cur

        restore = FrameContext.page
        sub_page = SubPage(self.tag_prefix, restore.gui_task, event.client_id)
        restore = FrameContext.page
        FrameContext.page = sub_page

        for slot in range(max_slots): 
            item = self.items[cur]
            tag = f"{self.tag_prefix}:{slot}"
            this_right =   left+item_width
            this_bottom =   top+item_height
            if self.horizontal:
                this_bottom = bottom
            else:
                this_right = right

            sec = layout.Layout(tag+":sec", None, left, top, this_right, this_bottom)
            #self.sections.append(sec)


            #apply_control_styles(".section",  self.section_style, sec, restore.gui_task)

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
                left+= item_width
            else:
                top+= item_height

            if cur >= len(self.items):
                break
        
        # sub_page.present(event)   
        FrameContext.page = restore

        #
        # I the slot should not show
        if self.last_tags is not None:
            diff = self.last_tags - sub_page.tags
            #print(f"tags {len(self.last_tags)} {len(tags)} {len(diff)}")
            for t in diff:
                sbs.send_gui_text(
                    CID, t, "text:_",
                        -1000, -1000, -999,-999)
        self.last_tags = sub_page.tags

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
        slot = int(sec[1])+self.cur
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
                 section_style=None,
                 select=False, multi=False):
    # The gui_content sets the values
    return LayoutListbox(0, 0, "mast", items,
                 template_func, title, 
                 section_style,
                 select,multi)
