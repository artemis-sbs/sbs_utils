from ...gui import get_client_aspect_ratio
from ..layout import layout as layout
import sbs
from ... import fs
from ...helpers import FrameContext, FakeEvent
from ...mast.parsers import LayoutAreaParser
from ...procedural.style import apply_control_styles




class SubPage:
    """A class for use with the layout listbox to make using the procedural gui function work
    """
    def __init__(self, tag_prefix, region_tag, task, client_id) -> None:
        self.tags = set()
        self.tag_prefix = tag_prefix
        self.tag = 0
        self.active_layout = None
        self.layouts=[]
        self.sub_sections=[]
        self.slot = 0
        self.pending_row = None
        # Incase it is needed by the layout elements
        self.client_id = client_id
        self.gui_task = task
        self.region_tag = region_tag

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
    
    def push_sub_section(self, style, layout_item, is_rebuild):
        sub_section_data = (self.active_layout, self.pending_row)

        if layout_item is None:
            tag = self.get_tag()
            layout_item = layout.Layout(tag, None, 0,0, 100, 90)
            apply_control_styles(".section", style, layout_item, self.gui_task)

        self.sub_sections.append(sub_section_data)

        self.active_layout =  layout_item

        self.pending_row = None
        if len(layout_item.rows) >0:
            self.pending_row = layout_item.rows.pop()

    def pop_sub_section(self, add, is_rebuild):
        (sec,p_row) = self.sub_sections.pop()
        if add:
            p_row.add(self.active_layout)
        self.active_layout = sec
        self.pending_row = p_row

    
    def present(self, event):
        for sec in self.layouts:
            sec.region_tag = self.local_region_tag,
            sec.calc(event.client_id)
            sec.present(event)



class LayoutListbox(layout.Column):
    """
      A widget to list things passing function/lamdas to get the data needed for option display of
       a template 
    """

    def __init__(self, left, top, tag_prefix, items, 
                 item_template=None, title_template=None, 
                 section_style=None, title_section_style=None,
                 select=False, multi=False) -> None:
        super().__init__(left,top,33,44)

        self.tag_prefix = tag_prefix
        self.tag  = tag_prefix
        self.gui_state = "blank"
        self.region = None
        self.local_region_tag = tag_prefix+"$$"
        
        self.cur = 0
        # self.bottom = top
        # self.right = left+33
        self.items = items
        self.select_color = "#bbb3"
        self.click_color = "black"
        self.cur = 0
        
        self.title_background=None
        self.default_item_width = None
        self.default_item_height = None
        self.select = select
        self.multi= multi
        self.square_width_percent = 0
        #self.sections = []
        self.title_height = 2
        self.template_func = item_template
        self.item_template = None
        if isinstance(self.template_func, str):
            self.item_template = item_template
            self.template_func = self.default_item_template

        self.title_template_func = title_template
        self.title_template = None
        if isinstance(self.title_template_func, str):
            self.title_template = title_template
            self.title_template_func = self.default_title_template

        self.selected = set()
        self.last_tags = None
        self.horizontal = None
        self.client_id = None
        self.section_style = section_style
        if section_style is None:
            self.section_style = "padding: 2px,2px,2px,2px;"

        self.title_section_style = title_section_style
        if title_section_style is None:
            self.title_section_style = "padding: 2px,2px,2px,2px;"

        tokens = LayoutAreaParser.lex("1em")
        self.slider_style =  LayoutAreaParser.parse_e2(tokens)
        

    def set_row_height(self, height):
        self.default_item_height = height

    def set_col_width(self, width):
        self.default_item_width = width

    def default_item_template(self, item):
        from ...procedural.gui import gui_row, gui_text
        gui_row("row-height: 1.2em;padding:13px")
        task = FrameContext.task
        task.set_variable("LB_ITEM", item)
        msg = task.compile_and_format_string(self.item_template)
        gui_text(msg)

    def default_title_template(self):
        from ...procedural.gui import gui_row, gui_text
        gui_row("row-height: 1.2em;padding:13px")
        task = FrameContext.task
        msg = task.compile_and_format_string(self.title_template)
        gui_text(msg)

    def _present(self, event):
        """ present

        builds/manages the content of the widget
     
        :param sim: simulation
        :type sim: Artemis Cosmos simulation
        :param CID: Client ID
        :type CID: int
        """
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
        extra_slot_count = len(self.items)-max_slots

        

        if extra_slot_count <0:
            extra_slot_count = 0
            self.cur = 0
        
        top = self.bounds.top
        left = self.bounds.left
        right = self.bounds.right
        bottom = self.bounds.bottom

        

        if extra_slot_count > 0:
            self.extra_slot_count = extra_slot_count
            em2 = LayoutAreaParser.compute(self.slider_style, None, aspect_ratio.y, 20)
            #print(f"adding scroll bar font size {em2} {self.bounds} == {self.tag} -- {self.tag_prefix}")
            if self.horizontal:
                sbs.send_gui_slider(CID, self.local_region_tag,f"{self.tag_prefix}cur", int(self.cur), f"low:0.0; high: {(extra_slot_count+0.5)}; show_number:no",
                        left, bottom-em2,
                        self.bounds.right, bottom)
                bottom-=em2
            else:
                em2 = LayoutAreaParser.compute(self.slider_style, None, aspect_ratio.x, 20)
                sbs.send_gui_slider(CID, self.local_region_tag, f"{self.tag_prefix}cur", int(extra_slot_count-self.cur +0.5), f"low:0.0; high: {(extra_slot_count+0.5)}; show_number:no",
                        (right-em2), top,
                        right, self.bounds.bottom)
                right -= em2
        #else:
        #    print("No scrollbar needed")
            # sbs.send_gui_slider(CID, f"{self.tag_prefix}cur", 0, f"low:0.0; high: 1.0; show_number:no",
            #             -1000, -1000,
            #             -1000, -1000)

        #self.cur = 0
        slot = 0
        cur = self.cur

        restore = FrameContext.page
        task = restore.gui_task

        sub_page = SubPage(self.tag_prefix, self.local_region_tag, restore.gui_task, event.client_id)
        restore = FrameContext.page
        FrameContext.page = sub_page


        if self.title_template_func is not None:
            tag = f"{self.tag_prefix}"
            sec = layout.Layout(tag+":title", None, left, top, right, top+2)
            sec.region_tag = self.local_region_tag
            apply_control_styles("", self.title_section_style, sec, task)
            #self.title_section_style
            sub_page.next_slot(-1, sec)
            self.title_template_func()
            #
            # Set the task values
            #
            sec.calc(CID)
            #sbs.target_gui_sub_region(CID, self.tag)
            sec.present(event)
            sec.resize_to_content()
            top += sec.bounds.height
            # sub_page.tags |= sec.get_tags()

        #draw_slots = max_slot
        print(f"{cur=} {max_slots=}" )
        for slot in range(max_slots):
            if cur >= len(self.items):
                print("BROKE")
                break

            item = self.items[cur]
            tag = f"{self.tag_prefix}:{slot}"
            this_right =   left+item_width
            this_bottom =   top+item_height
            if self.horizontal:
                this_bottom = bottom
            else:
                this_right = right
            
            
            sec = layout.Layout(tag+":sec", None, left, top, this_right, this_bottom)
            #print(f"BREAK {cur}  {tag} {left=} {top=}")
            if self.select or self.multi:
                sec.click_text = "__________________"
                sec.click_background = "white"
                sec.click_color = "black"
                if cur in self.selected:
                    sec.background_color = self.select_color
                else:
                    sec.background_color = "#0000"
                sec.click_tag = f"{tag}:__click"
                
                
            sub_page.next_slot(slot, sec)
            self.template_func(item)
            #
            # Set the task values
            #
            sec.calc(CID)
            sec.present(event)
            sec.resize_to_content()
            #sub_page.tags |= sec.get_tags()

            cur += 1
            if self.horizontal:
                left+= item_width
            else:
                top+= item_height

            
        
        # sub_page.present(event)   
        FrameContext.page = restore
        #
        # I the slot should not show
        # if self.last_tags is not None:
        #     diff = self.last_tags - sub_page.tags
        #     #print(f"tags {len(self.last_tags)} {len(sub_page.tags)} {len(diff)}")
        #     for t in diff:
        #         sbs.send_gui_text(
        #             CID, t, "text:_",
        #                 -1000, -1000, -999,-999)
        # self.last_tags = sub_page.tags
        #sbs.target_gui_sub_region(CID, "")

    def present(self, event):
        CID = event.client_id
        is_update = self.region is not None
        # If first time create sub region
        if not is_update:
            #print("Listbox CREATE present")
            sbs.send_gui_sub_region(CID, self.region_tag, self.local_region_tag, "draggable:True;", 0,0,100,100)
            self.region = True
            sbs.send_gui_clear(CID, self.local_region_tag,)
            super().present(event)
            sbs.send_gui_complete(CID, self.local_region_tag,)
        else:
            #print("Listbox UPDATE present")
            sbs.send_gui_sub_region(CID, self.region_tag, self.local_region_tag, "draggable:True;", 0,0,100,100)
            self.region = True
            sbs.send_gui_clear(CID, self.local_region_tag,)
            super().present(event)
            
            sbs.send_gui_complete(CID, self.local_region_tag,)

        #sbs.target_gui_sub_region(CID, "")
        
    def represent(self, event):
        super().represent(event)
        
    def invalidate_regions(self):
        self.region = None

    def on_message(self, event):
        if self.client_id != event.client_id:
            return
        
        if event.sub_tag == f"{self.tag_prefix}cur":
            if self.horizontal:
                value = int(event.sub_float)
            else:
                value = int(-event.sub_float+self.extra_slot_count+0.5)
            if value != self.cur:
                self.cur = value
                self.gui_state = "redraw"
                self.represent(event)
                return

        if not self.select and not self.multi:
            return
        if not event.sub_tag.startswith(self.tag_prefix):
            return
        sec = event.sub_tag.split(":")
        if len(sec) != 3:
            return
        if sec[0] != self.tag_prefix:
            return
        if sec[2] != "__click":
            return
        #print(sec[1])
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
        self.represent(event)


        
    def get_selected(self):
        ret = []
        for item in self.selected:
            ret.append(self.items[item])
        if self.multi:
            return ret
        if len(ret)==1:
            return ret[0]
        return None
        

    def get_selected_index(self):
        ret = list(self.selected)
        if self.multi:
            return ret
        if len(ret)==1:
            return ret[0]
        return None
    
    def set_selected_index(self, v):
        self.selected = set()
        if v is not None:
            self.selected.add(v)

        self.redraw_if_showing()
    
    def select_all(self):
        if self.multi:
            self.selected = set()
            for item in range(len(self.items)):
                self.selected.add(item)

            self.redraw_if_showing()

    
    def redraw_if_showing(self):
        """ 
        Redraw if this is already one screen.
        Since sub_region is used if you present too early it will confuse the gui.
        """
        if self.region is None:
            return
        self.gui_state = "redraw"
        # Pure hackery or brilliant, time will tell
        e = FakeEvent(FrameContext.client_id)
        self.present(e)

    def select_none(self):
        self.selected = set()
        self.redraw_if_showing()

    def convert_value(self, item):
        return item
    
    @property
    def value(self):
        return self.get_value()
    
    @value.setter
    def value(self, v):
        self.set_value(v)

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
                 template_func=None, title_template=None, 
                 section_style=None, title_section_style=None,
                 select=False, multi=False):
    # The gui_content sets the values
    return LayoutListbox(0, 0, "mast", items,
                 template_func, title_template, 
                 section_style, title_section_style,
                 select,multi)
