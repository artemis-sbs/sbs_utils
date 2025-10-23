from ...gui import get_client_aspect_ratio
from ..layout import layout as layout
from ...helpers import FrameContext, FakeEvent
from ...mast.parsers import LayoutAreaParser
#from ...mast.core_nodes.label import Label
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
        self.tag_map = {}

    def get_tag(self):
        self.tag += 1
        tag =  f"{self.tag_prefix}:{self.slot}:{self.tag}"
        self.tags.add(tag)
        return tag
    
    def add_tag(self, layout_item, runtime_node):
        self.tag_map[layout_item.tag] = (layout_item, runtime_node)
    
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
        if add and p_row is not None:
            p_row.add(self.active_layout)
        self.active_layout = sec
        self.pending_row = p_row

    
    def present(self, event):
        for sec in self.layouts:
            sec.region_tag = self.region_tag
            sec.calc(event.client_id)
            sec.present(event)


class LayoutListBoxHeader:
    def __init__(self, label, collapse):
        self.label = label
        self.collapse = collapse


class LayoutListbox(layout.Column):
    """
      A widget to list things passing function/lamdas to get the data needed for option display of
       a template 
    """

    def __init__(self, left, top, tag_prefix, items, 
                 item_template=None, title_template=None, 
                 section_style=None, title_section_style=None,
                 select=False, multi=False, carousel=False, collapsible=False, read_only=False) -> None:
        super().__init__(left,top,33,44)

        self.tag_prefix = tag_prefix
        self.tag  = tag_prefix
        self.gui_state = "blank"
        self.region = None
        self.local_region_tag = tag_prefix+"$$"
        
        self.cur = 0
        # self.bottom = top
        # self.right = left+33
        self.unfiltered_items = items
        self._items = items
        self.select_color = "#bbb3"
        self.click_color = "black"
        self.cur = 0
        self.carousel = carousel
        self.collapsible = collapsible
        self.read_only = read_only
        
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
        if self.template_func == None:
            self.template_func = self.default_item_template
            # self.item_template = self.default_item_template
        # elif isinstance(self.template_func, Label):
        #     self.item_template = self.template_func
        #     self.template_func = self.label_item_template

        # First we assume that title_template is None or callable
        self.title_template_func = title_template
        self.title_template = None
        if isinstance(self.title_template_func, str):
            self.title_template = title_template
            self.title_template_func = self.default_title_template
        

        self.selected = set()
        self.locked_selections = set()
        self.last_tags = None
        self.horizontal = None
        self.client_id = None
        self.section_style = section_style
        if section_style is None:
            self.section_style = "padding: 2px,2px,2px,2px;"

        self.title_section_style = title_section_style
        if title_section_style is None:
            self.title_section_style = "row-height: 1.2em;padding: 2px,2px,2px,2px;"

        tokens = LayoutAreaParser.lex("1em")
        self.slider_style =  LayoutAreaParser.parse_e2(tokens)
        if self.carousel:
            self.set_selected_index(self.cur)
        self.sections = []

    @property
    def items(self):
        return self._items

    @items.setter
    def items(self, items):
        self.unfiltered_items = items
        self._items = items

    def set_row_height(self, height):
        # Row_height for a listbox is the gap height
        self.default_item_height = height

    def set_col_width(self, width):
        # col_width for a listbox is the gap width
        self.default_item_width = width

    def default_item_template(self, item):
        from ...procedural.gui import gui_row, gui_text
        gui_row("row-height: 1.2em;")
        task = FrameContext.task
        task.set_variable("LB_ITEM", item)
        if self.item_template is not None:
            msg = task.compile_and_format_string(self.item_template)
        else:
            msg = item
        collapsable =  isinstance(item, LayoutListBoxHeader)
        if collapsable:
            if not item.collapse:
                gui_text(f"$text:{item.label};justify: center;color:#02FF;", "background: #FFFC")
            else:
                gui_text(f"$text:{item.label};justify: center;color:#FFF;", "background: #0173")
        else:
            gui_text(f"$text:{msg};justify: left;")
        # gui_text(msg)

    # def label_item_template(self, item):
    #     task = FrameContext.task
    #     st = task.start_sub_task(self.item_template, {"item": item, "LB_ITEM": item}, defer=True)
    #     for _ in range(2):
    #         st.tick_in_context()


    def default_title_template(self):
        from ...procedural.gui import gui_row, gui_text
        gui_row("row-height: 1.2em;padding:13px")
        task = FrameContext.task
        msg = task.compile_and_format_string(self.title_template)
        gui_text(msg)

    def calc_max(self, CID):
        max_width = 0
        max_height = 0

        restore = FrameContext.page
        sub_page = SubPage(self.tag_prefix, self.local_region_tag, restore.gui_task, CID)
        FrameContext.page = sub_page
        
        
        slot = 0
        collapsed = False
        if self.collapsible:
            self._items = []

        for item in self.unfiltered_items:
            if self.collapsible:
                is_header = isinstance(item, LayoutListBoxHeader)
                if collapsed and not is_header:
                    continue
                self._items.append(item)
                collapsed =  is_header and item.collapse

            
            sec = layout.Layout("unused", None, 0, 0, 100, 100)
            sub_page.next_slot(slot, sec)
            slot+=1
            size = self.template_func(item)
            sec.calc(CID)
            b = sec.get_content_bounds(False)
            max_height = max(max_height, b.height)
            max_width = max(max_width, b.height)

        FrameContext.page = restore
        f = len(self._items)
        uf = len(self.unfiltered_items)
        #print(f"LISTBOX  {self.collapsible} {uf} {f}")
        return max_width, max_height


    def _present(self, event):
        """ present

        builds/manages the content of the widget
        Args:
            event (event): The event that triggered the gui to update
        """
        
        CID = event.client_id
        self.client_id = CID
        SBS = FrameContext.context.sbs

        
        item_width = 0# self.bounds.width 
        item_height = 0 #self.bounds.height
        aspect_ratio = get_client_aspect_ratio(event.client_id)
        if not self.horizontal:
            item_width = self.bounds.width 
            item_height = 0 #self.bounds.height
        else:
            item_width = 0 #self.bounds.width 
            item_height = self.bounds.height
        
        if self.default_item_width:
            item_width = LayoutAreaParser.compute(self.default_item_width, None, aspect_ratio.x, 20)
            if self.horizontal is None:
                self.horizontal = True
        if self.default_item_height:
            item_height = LayoutAreaParser.compute(self.default_item_height, None, aspect_ratio.y, 20)


     
        
        # At this point is should assume it is vertical
        if self.horizontal is None:
            self.horizontal = False


        max_item_width, max_item_height = self.calc_max(CID)
        

        max_item_width += item_width
        max_item_height += item_height
        
        # This can be because len items == 0
        if max_item_width == 0:
            max_item_width = 1
        if max_item_height == 0:
            max_item_height = 1


        if self.horizontal:
            max_slots = (self.bounds.right - self.bounds.left) // max_item_width #max(item_width,5) 
        else:
            max_slots = (self.bounds.bottom - self.bounds.top) // max_item_height #max(item_height,5) 


        max_slots = int(max_slots)
        if self.carousel:
            max_slots = 1
        extra_slot_count = len(self._items)-max_slots

        if extra_slot_count <0:
            extra_slot_count = 0
            self.cur = 0
        
        top = self.bounds.top
        left = self.bounds.left
        right = self.bounds.right
        bottom = self.bounds.bottom

        
        em2 = LayoutAreaParser.compute(self.slider_style, None, aspect_ratio.y, 20)
        if self.carousel and not self.horizontal:
            icon_size = em2*2
            if self.cur>0:
                SBS.send_gui_icon(event.client_id, self.local_region_tag, f"{self.tag_prefix}idec",
                    "icon_index:152;color:#aaa;draw_layer:1000;",
                    self.bounds.left, self.bounds.bottom-icon_size*2, self.bounds.left+icon_size, self.bounds.bottom)
                    #self.bounds.left, self.bounds.top, self.bounds.left+icon_size, self.bounds.bottom)
                SBS.send_gui_clickregion(event.client_id, self.local_region_tag, 
                    f"{self.tag_prefix}dec", "background_color:#6663",
                    self.bounds.left, self.bounds.top, self.bounds.left+em2*5, self.bounds.bottom)
            max_item = len(self._items)-1
            if self.cur<max_item:
                SBS.send_gui_icon(event.client_id, self.local_region_tag, f"{self.tag_prefix}iinc",
                    "icon_index:153;color:#aaa;draw_layer:1000;",
                    self.bounds.right-icon_size , self.bounds.bottom-icon_size*2, self.bounds.right, self.bounds.bottom)
                    #self.bounds.right-icon_size , self.bounds.top, self.bounds.right, self.bounds.bottom)
                SBS.send_gui_clickregion(event.client_id, self.local_region_tag,
                    f"{self.tag_prefix}inc", "background_color:#6663",
                    self.bounds.right-em2*5, self.bounds.top, self.bounds.right, self.bounds.bottom)
        elif self.carousel and self.horizontal:
            pass
        elif extra_slot_count > 0:
            self.extra_slot_count = extra_slot_count
            em2 = LayoutAreaParser.compute(self.slider_style, None, aspect_ratio.y, 20)
            if self.horizontal:
                SBS.send_gui_slider(CID, self.local_region_tag,f"{self.tag_prefix}cur", int(self.cur), f"low:0.0; high: {(extra_slot_count+0.5)}; show_number:no",
                        left, bottom-em2,
                        self.bounds.right, bottom)
                bottom-=em2
            else:
                em2 = LayoutAreaParser.compute(self.slider_style, None, aspect_ratio.x, 20)
                SBS.send_gui_slider(CID, self.local_region_tag, f"{self.tag_prefix}cur", int(extra_slot_count-self.cur +0.5), f"low:0.0; high: {(extra_slot_count+0.5)}; show_number:no",
                        (right-em2), top,
                        right, self.bounds.bottom)
                right -= em2

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
            #
            # Allow item to force size
            #
            size = self.title_template_func()
            #
            # Set the task values
            #
            sec.calc(CID)
            if size is None:
                sec.resize_to_content()
                top += sec.bounds.height
            else:
                top+= size
            sec.present(event)
            # sub_page.tags |= sec.get_tags()

        #draw_slots = max_slot
        self.sections = []
        collapse = False


        if len(self.items) <= max_slots:
            cur = 0

        while slot < max_slots and cur < len(self._items):
            item = self._items[cur]
            #
            # Look for the next header
            #
            if collapse:
                # if not a header - skip
                if not isinstance(item, LayoutListBoxHeader):
                    cur += 1
                    continue
            #
            #  Should be header or non-collapsed item
            #     


            tag = f"{self.tag_prefix}:{slot}"
            this_right =   left #+item_width
            this_bottom =   top #+item_height
            if self.horizontal:
                this_bottom = bottom
            else:
                this_right = right
            
            
            sec = layout.Layout(tag+":sec", None, left, top, this_right, this_bottom)
            sec.region_tag = self.local_region_tag
            sec.item_index = cur
            
            
            if (self.select or self.multi) and not self.carousel:
                #sec.click_text = "__________________"
                sec.click_text = ""
                sec.click_background = "#aaaa"
                sec.click_color = "black"
                if item in self.selected:
                    sec.background_color = self.select_color
                else:
                    sec.background_color = "#0000"
                sec.click_tag = f"{tag}:__click"
            
            if isinstance(item, LayoutListBoxHeader):
                sec.click_text = ""
                sec.click_background = "#aaaa"
                sec.click_color = "black"
                sec.background_color = self.select_color
                sec.click_tag = f"{tag}:__collapse"
                collapse = item.collapse
                
            sub_page.next_slot(slot, sec)
            size = self.template_func(item)
            sec.calc(CID)

            # if self.horizontal:
            #     left+= item_width
            # else:
            #     top+= item_height

            if size is None:
                sec.resize_to_content()
                if self.horizontal:
                    size = sec.bounds.width + item_width
                else:
                    size = sec.bounds.height + item_height
            if self.horizontal:
                left+= size
            else:
                top+= size

            sec.present(event)
            
            self.sections.append(sec)
            #sub_page.tags |= sec.get_tags()

            cur += 1
            slot += 1
            

            
        
        # sub_page.present(event)   
        FrameContext.page = restore
        

    def present(self, event):
        CID = event.client_id
        # #is_update = self.region is not None
        # is_update = True
        # # If first time create sub region
        # if not is_update:
        #     sbs.send_gui_sub_region(CID, self.region_tag, self.local_region_tag, "draggable:True;", 0,0,100,100)
        #     self.region = True
        #     sbs.send_gui_clear(CID, self.local_region_tag)
        #     super().present(event)
        #     sbs.send_gui_complete(CID, self.local_region_tag)
        # else:

        SBS = FrameContext.context.sbs
        SBS.send_gui_sub_region(CID, self.region_tag, self.local_region_tag, "draggable:True;", 0,0,100,100)
        self.region = True
        SBS.send_gui_clear(CID, self.local_region_tag)
        super().present(event)
        SBS.send_gui_complete(CID, self.local_region_tag)
        

        #sbs.target_gui_sub_region(CID, "")
        
    def represent(self, event):
        # Don't represent if we've never been presented.
        # This was causing ghost images 
        # with property grid
        if self.client_id is None:
            return
        # sbs.get_debug_gui_tree(event.client_id, "pre off state", False)
        # sbs.get_debug_gui_tree(event.client_id, "pre ON state", True)
        super().represent(event)
        # sbs.get_debug_gui_tree(event.client_id, "post off state", False)
        # sbs.get_debug_gui_tree(event.client_id, "post ON state", True)
        
    def invalidate_regions(self):
        self.region = None


    def on_message(self, event):
        self._on_message(event)
        super().on_message(event)
        
    def _on_message(self, event):
        if self.client_id != event.client_id:
            return
        if not event.sub_tag.startswith(self.tag_prefix):
            return

        # Listbox can have selection, but is readonly
        for sec in self.sections:
            sec.on_message(event)
            
        if event.sub_tag.endswith("cur"):
            return self.on_scroll(event)

        if event.sub_tag.endswith("__collapse"):
            return self.on_collapse_header(event)
        
        if event.sub_tag.endswith("__click"):
            return self.on_click(event)
        
        if self.carousel:
            return self.on_carousel_click(event)

    def on_scroll(self, event):
        # Scroll bar
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
        

    def on_carousel_click(self, event):
        was = self.cur
        if event.sub_tag == f"{self.tag_prefix}dec":
            if self.read_only:
                return
            self.cur -= 1
            if self.cur <0:
                self.cur = 0
            if was != self.cur:
                self.set_selected_index(self.cur)
                self.gui_state = "redraw"
                self.represent(event)
                return
    
        if event.sub_tag == f"{self.tag_prefix}inc":
            if self.read_only:
                return
            self.cur += 1
            if self.cur >= len(self._items):
                self.cur = len(self._items)-1
            if was != self.cur:
                self.set_selected_index(self.cur)
                self.gui_state = "redraw"
                self.represent(event)
                return

        

    def on_click(self, event):
        if not self.select and not self.multi:
            return
        if self.read_only:
            return
        if not event.sub_tag.startswith(self.tag_prefix):
            return
        sec = event.sub_tag.split(":")
        if len(sec) != 3:
            return
        if sec[0] != self.tag_prefix:
            return
        if not sec[1].isdigit():
            return
        #index = int(sec[1]) +self.cur

        slot_index = int(sec[1])
        if slot_index > len(self.sections):
            self.represent(event)
            return
        
        index = self.sections[slot_index].item_index

        if sec[2] != "__click":
            return
        
        if index > len(self.items):
            self.represent(event)
            return
        
        item = self.items[index]
        if item in self.locked_selections:
            return
        
        if self.multi:
            if item in self.selected:
                self.selected.discard(item)
            else:
                self.selected.add(item)
        elif self.select:
            self.selected = {item}
        else:
            return
        self.represent(event)

    def on_collapse_header(self, event):
        sec = event.sub_tag.split(":")
        if len(sec) != 3:
            return
        if sec[0] != self.tag_prefix:
            return
        if not sec[1].isdigit():
            return
        index = int(sec[1]) +self.cur
        if index > len(self.items):
            self.represent(event)
            return
        #item = self.sections[index]
        item = self._items[index]
        if isinstance(item, LayoutListBoxHeader):
            item.collapse = not item.collapse
            self.represent(event)
        return


        
    def get_selected(self):
        ret = list(self.selected)
        if self.multi:
            return ret
        if len(ret)==1:
            return ret[0]
        return None
        

    def get_selected_index(self):
        ret = []
        i = 0
        for item in self.unfiltered_items:
            if item in self.selected:
                ret.append(i)
            i+=1

        if self.multi:
            return ret
        if len(ret)==1:
            return ret[0]
        return None

    
    def set_selected_index(self, i, set_cur=True):
        self.selected = set()
        if i is not None and i < len(self.unfiltered_items):
            self.selected.add(self.unfiltered_items[i])
            if set_cur:
                self.cur = i
        self.redraw_if_showing()
    
    def select_all(self):
        if self.multi:
            self.selected = set(self.unfiltered_items)
            # for item in self._items:
            #     self.selected.add(item)

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
        e = FakeEvent(self.client_id)
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
        ret = list(self.selected)
        if self.multi:
            return ret
        elif len(ret):
            return ret[0]


        
        # if self.convert_value:
        #     for item in self.selected:
        #         if item < len(self._items):
        #             ret.append(self.convert_value(self._items[item]))
        # else:
        #     ret = self.get_selected()

        # if self.multi:
        #     return ret
        # elif len(ret):
        #     return ret[0]
        # else:
        #     return None
    
    def set_value(self, value):
        self.selected = set()
        self.selected.add(value)
        # i = 0
        # for item in self._items:
        #     if self.convert_value:
        #         v = self.convert_value(item)
        #         if v == value:
        #             self.selected.add(i)
        #     elif item == value:
        #         self.selected.add(i)
        #     i+=1
    
    def update(self, props):
        pass

    def set_read_only(self, v):
        self.read_only = v

    def set_selection_lock_index(self, i, lock):
        if i is not None and i < len(self.unfiltered_items):
            if lock:
                self.locked_selections.add(self.unfiltered_items[i])
            else:
                self.locked_selections.discard(self.unfiltered_items[i])

    def set_selection_lock(self, o, lock):
        if lock:
            self.locked_selections.add(o)
        else:
            self.locked_selections.discard(o)

    def clear_selection_locks(self):
        self.locked_selections = set()

    




def layout_list_box_control(items,
                 template_func=None, title_template=None, 
                 section_style=None, title_section_style=None,
                 select=False, multi=False, carousel=False, collapsible=False,read_only=False):
    # The gui_content sets the values
    return LayoutListbox(0, 0, "mast", items,
                 template_func, title_template, 
                 section_style, title_section_style,
                 select,multi, carousel, collapsible, read_only)
