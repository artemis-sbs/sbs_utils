from ...gui import get_client_aspect_ratio
from ..layout import layout as layout
from ..layout.clickable import Clickable
from ...helpers import FrameContext, FakeEvent
from ...mast.parsers import LayoutAreaParser
#from ...mast.core_nodes.label import Label
from ...procedural.style import apply_control_styles
import inspect

def accepts_kwargs(func):
    if not callable(func):
        return False
    sig = inspect.signature(func)
    for param in sig.parameters.values():
        if param.kind == param.VAR_KEYWORD:
            return True
    return False

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
        self.layouts.append(section)
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
            p_row = layout.Row()
            p_row.tag = self.get_tag()
            layout_item.add(p_row)

        self.sub_sections.append(sub_section_data)

        self.active_layout =  layout_item

        self.pending_row = None
        if len(layout_item.rows) >0:
            self.pending_row = layout_item.rows.pop()
        return layout_item

    def pop_sub_section(self, add, is_rebuild):
        (sec,p_row) = self.sub_sections.pop()
        
        if add:
            if p_row is None:
                p_row = layout.Row()
                p_row.tag = self.get_tag()
                self.active_layout.add(p_row)

            p_row.add(self.active_layout)

        self.active_layout = sec
        self.pending_row = p_row

    
    def present(self, event):
        for sec in self.layouts:
            #sec.region_tag = self.region_tag
            #sec.calc(event.client_id)
            sec.present(event)


class LayoutListBoxHeader:
    def __init__(self, label, collapse, indent=0, selectable=False, data=None, visual_indent=None):
        self.label = label
        self.collapse = collapse
        self.indent = indent
        self.visual_indent = indent
        if visual_indent is not None:
            self.visual_indent = visual_indent
        self.data = data

        # Allow the header to be collapsable and selectable
        self.selectable = selectable
        # Lets the template specify the click 
        # Listbox will set this (only set if selectable)
        self.collapse_tag = None




def pack_slots(heights, avail, item_height=0.0, start=0):
    """How many rows fit starting at `start`, packing REAL heights."""
    used = 0.0
    slots = 0
    for h in heights[int(start):]:
        h = h + item_height
        if used + h > avail and slots > 0:
            break
        used += h
        slots += 1
    return slots


def reveal_cur(sel, cur, heights, avail, item_height=0.0):
    """Where the view must start so `sel` is visible, moving the LEAST.

    A selection the viewer cannot see is not a state anything wants, and the
    only lever the widget had was set_selected_index(i, True), which slams it to
    the top on every repaint. This is the smallest move instead:

      * above the window  -> scroll up to it
      * below the window  -> back-pack UPWARD from it until the next row would
                             not fit, putting it at the BOTTOM
      * never past the end, which would leave blank space below the last row

    Pure so it can be asserted on directly -- presenting a listbox needs a whole
    page context, and the packing is the part worth pinning. Heights are per
    row, because they are not uniform: `max_slots` depends on where you start.
    """
    count = len(heights)
    if count == 0:
        return 0
    cur = max(0, min(int(cur or 0), count - 1))
    if sel is None:
        return cur
    # Defensive: `sel` must be an index into THESE heights -- the displayed
    # rows. A collapsible list also has an unfiltered index space, and handing
    # one of those in points past the end and makes the back-pack meaningless.
    # Clamping turns a caller's mistake into a mild wrong position instead of a
    # scrollbar that thinks the list is the length of the visible slots.
    sel = max(0, min(int(sel), count - 1))

    slots = pack_slots(heights, avail, item_height, cur)
    if sel < cur:
        cur = sel
    elif sel >= cur + slots:
        used = 0.0
        first = sel
        for back in range(sel, -1, -1):
            h = heights[back] + item_height
            if used + h > avail and back != sel:
                break
            used += h
            first = back
        cur = first

    cur = max(0, cur)

    # Don't leave blank space below the last row. `cur + slots` can never exceed
    # the count (pack_slots stops at the end), so the real waste is a view
    # parked low in a box big enough for more: five rows drawn and half the box
    # empty, with rows sitting unseen ABOVE. Pull back while another row fits.
    used = sum(heights[i] + item_height
               for i in range(cur, min(count, cur + pack_slots(heights, avail, item_height, cur))))
    while cur > 0:
        h = heights[cur - 1] + item_height
        if used + h > avail:
            break
        used += h
        cur -= 1
    return cur


class LayoutListbox(layout.Column):
    """
      A widget to list things passing function/lamdas to get the data needed for option display of
       a template 
    """

    def __init__(self, left, top, tag_prefix, items, 
                 item_template=None, title_template=None, 
                 section_style=None, title_section_style=None,
                 select=False, multi=False, carousel=False, collapsible=False, read_only=False,
                 hint=None) -> None:
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
        self.select_color = "#bbb5"
        self.click_color = "black"
        self.cur = 0
        self.carousel = carousel
        self.collapsible = collapsible
        self.read_only = read_only
        
        self.default_item_width = None
        self.default_item_height = None
        self.select = select
        self.multi= multi
        # A repaint builds a DIFFERENT listbox -- new object, new tag, no
        # sections until it presents. `hint` is how the caller carries the view
        # across that break: get_selection_hint() on the old one, hand it to the
        # new one. Opaque on purpose, so what it carries can grow without
        # breaking a caller that only ever passes it along.
        self._hint = hint
        self._hint_applied = False
        self.square_width_percent = 0
        #self.sections = []
        self.title_height = 2
        self.indent_pixels = 25
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
        
        if not accepts_kwargs(self.template_func):
            funcy = self.template_func
            self.template_func = lambda item, **kwargs: funcy(item)

        # First we assume that title_template is None or callable
        self.title_template_func = title_template
        self.title_template = None
        if isinstance(self.title_template_func, str):
            self.title_template = title_template
            self.title_template_func = self.default_title_template
            
        if self.title_template_func is not None and not accepts_kwargs(self.title_template_func):
             funcy2 = self.title_template_func
             self.title_template_func = lambda **kwargs: funcy2()

        self.selected = []
        self.locked_selections = []
        self.last_tags = None
        self.horizontal = None
        self.client_id = None
        self.section_style = section_style
        if section_style is None:
            self.section_style = "padding: 2px,2px,2px,2px;"

        self.title_section_style = title_section_style
        if title_section_style is None:
            self.title_section_style = "row-height: 1.0;padding: 2px,2px,2px,2px;"

        tokens = LayoutAreaParser.lex("1em")
        self.slider_style =  LayoutAreaParser.parse_e2(tokens)
        if self.carousel:
            self.set_selected_index(self.cur)
        self.sections = []
        self.click_time = 0

    @property
    def items(self):
        return self._items

    @items.setter
    def items(self, items):
        self.unfiltered_items = items
        self._items = items
        self.mark_visual_dirty()

    def set_row_height(self, height):
        # Row_height for a listbox is the gap height
        self.default_item_height = height

    def set_col_width(self, width):
        # col_width for a listbox is the gap width
        self.default_item_width = width

    def default_item_template(self, item):
        from ...procedural.gui import gui_row, gui_text
        gui_row("row-height: 1.0;")
        task = FrameContext.task
        task.set_variable("LB_ITEM", item)
        if self.item_template is not None:
            msg = task.compile_and_format_string(self.item_template)
        else:
            msg = item
        collapsable =  isinstance(item, LayoutListBoxHeader)
        if collapsable:
            if not item.collapse:
                gui_text(f"$text:`{item.label}`;justify: center;color:#02FF;", "background: #FFFC")
            else:
                gui_text(f"$text:`{item.label}`;justify: center;color:#FFF;", "background: #0173")
        else:
            gui_text(f"$text:`{msg}`;justify: left;")
        # gui_text(msg)

    # def label_item_template(self, item):
    #     task = FrameContext.task
    #     st = task.start_sub_task(self.item_template, {"item": item, "LB_ITEM": item}, defer=True)
    #     for _ in range(2):
    #         st.tick_in_context()


    def default_title_template(self):
        from ...procedural.gui import gui_row, gui_text
        gui_row("row-height: 1em;padding:13px")
        task = FrameContext.task
        msg = task.compile_and_format_string(self.title_template)
        gui_text(msg)

    # Per-item heights measured by calc_max, consumed by _present's packer.
    _item_heights = {}

    def calc_max(self, CID):
        """Measure the items. Returns (max_width, max_height, avg_height).

        avg_height exists because slot budgeting used to divide the available
        space by the TALLEST item, which silently assumes every row is the same
        height. One tall row then shrank the whole list: eleven 48px consoles
        with a single 96px one showed six rows and left half the box empty.

        For a UNIFORM list avg == max, so every existing listbox budgets exactly
        as it did before. Only a list with genuinely varying rows changes.
        """
        max_width = 0
        max_height = 0
        total_height = 0
        counted = 0
        # Per-item heights, keyed by identity. The draw loop uses these to pack
        # exactly, instead of assuming every row is the tallest one.
        self._item_heights = {}

        restore = FrameContext.page
        sub_page = SubPage(self.tag_prefix, self.local_region_tag, restore.gui_task, CID)
        FrameContext.page = sub_page
        
        
        slot = 0
        collapsed = False
        if self.collapsible:
            self._items = []

        last_indent =0
        last_visual_indent =0
        for item in self.unfiltered_items:
            if self.collapsible:
                is_header = isinstance(item, LayoutListBoxHeader)
                if collapsed and not is_header:
                    continue
                if collapsed and is_header and item.indent > last_indent:
                    continue
                self._items.append(item)
                
                collapsed =  is_header and item.collapse
                if is_header and collapsed:
                    last_indent = item.indent
                    last_visual_indent = item.visual_indent

            
            sec = layout.Layout("unused", None, 0, 0, 100, 100)
            sub_page.next_slot(slot, sec)
            slot+=1
            #
            # This passes data, It is best to match the kwargs
            # But it may not be 100% needed
            #
            size = self.template_func(item, listbox=self, selected=False, section=sec, click_tag=None, collapse_tag=None)
            sec.calc(CID)
            b = sec.get_content_bounds(False)
            max_height = max(max_height, b.height)
            if size is not None:
                max_height = max(max_height, size)
            # This assure a minimum height
            # Listbox rows get_content_from_bounds
            # ONLY looks at rows
            max_height = max(max_height, 0.2)
            max_width = max(max_width, b.width)

            # This item's own height, for the average.
            this_height = b.height
            if size is not None:
                this_height = max(this_height, size)
            this_height = max(this_height, 0.2)
            self._item_heights[id(item)] = this_height
            total_height += this_height
            counted += 1

        FrameContext.page = restore
        # f = len(self._items)
        # uf = len(self.unfiltered_items)
        #print(f"LISTBOX  {self.collapsible} {uf} {f}")
        avg_height = (total_height / counted) if counted else max_height
        return max_width, max_height, avg_height


    def _present(self, event):
        """ present

        builds/manages the content of the widget
        Args:
            event (event): The event that triggered the gui to update
        """
        
        CID = event.client_id
        self.client_id = CID
        SBS = FrameContext.context.sbs

        restore = FrameContext.page
        task = restore.gui_task
        sub_page = SubPage(self.tag_prefix, self.local_region_tag, restore.gui_task, event.client_id)
        FrameContext.page = sub_page



        top = self.bounds.top
        left = self.bounds.left
        right = self.bounds.right
        bottom = self.bounds.bottom

# region Draw Title
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
            size = self.title_template_func(listbox=self)
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
# endregion


        
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


        max_item_width, max_item_height, avg_item_height = self.calc_max(CID)
        # Apply the caller's hint once, on the first pass that has items --
        # not in __init__, because a collapsible list filters its items after
        # construction and an index applied too early would point at the wrong
        # row.
        if self._hint is not None and not self._hint_applied:
            self._hint_applied = True
            self.apply_selection_hint(self._hint)

        # Where the visible window starts -- packing depends on it.
        cur_start = self.cur if self.cur and self.cur > 0 else 0
        
        max_item_width += item_width
        max_item_height += item_height
        avg_item_height += item_height
        
        # This can be because len items == 0
        if max_item_width == 0:
            max_item_width = 1
        if max_item_height == 0:
            max_item_height = 1
        if avg_item_height <= 0:
            avg_item_height = max_item_height


        if self.horizontal:
            max_slots = (self.bounds.right - self.bounds.left) // max_item_width #max(item_width,5) 
        else:
            #
            # PACK by each row's real height, rather than dividing the space by
            # the tallest row. Budgeting on the tallest silently assumes every
            # row is the same height: eleven 48px consoles with one 96px row
            # showed six and left half the box empty.
            #
            # For a UNIFORM list this produces exactly floor(available / height)
            # -- the same number as before -- so no existing listbox moves.
            #
            avail = self.bounds.bottom - top

            heights = [self._item_heights.get(id(it), avg_item_height)
                       for it in self.items]
            max_slots = pack_slots(heights, avail, item_height, cur_start)

            # REVEAL -- see reveal_cur(). Skipped for a carousel, whose window
            # is one item by definition.
            if self.select and not self.carousel:
                # DISPLAY index: heights, cur and max_slots are all in the
                # filtered space, and a collapsible list's unfiltered index can
                # point past the end of it.
                sel = self._selected_display_index()
                if sel is not None:
                    cur_start = reveal_cur(sel, cur_start, heights, avail, item_height)
                    max_slots = pack_slots(heights, avail, item_height, cur_start)
                    self.cur = cur_start


        max_slots = int(max_slots)
        if self.carousel:
            max_slots = 1
        extra_slot_count = len(self._items)-max_slots

        if extra_slot_count <0:
            extra_slot_count = 0
            self.cur = 0
        

# region Draw Carousel Nav Buttons
        from ...procedural.gui.icon_sheet import icon_props
        em2 = LayoutAreaParser.compute(self.slider_style, None, aspect_ratio.y, 20)
        if self.carousel and not self.horizontal:
            icon_size = em2*2
            if self.cur>0:
                # By NAME, so a mission that ships its own icon sheet re-skins the
                # carousel arrows too - see procedural/gui/icon_sheet.py.
                kind, props = icon_props("list.prev", "#aaa", "draw_layer:1000")
                send = SBS.send_gui_image if kind == "image" else SBS.send_gui_icon
                send(event.client_id, self.local_region_tag, f"{self.tag_prefix}idec",
                    props,
                    self.bounds.left, self.bounds.bottom-icon_size*2, self.bounds.left+icon_size, self.bounds.bottom)
                    #self.bounds.left, self.bounds.top, self.bounds.left+icon_size, self.bounds.bottom)

                # ctx.sbs.send_gui_text(CID, self.local_region_tag,
                #     tag, message,  
                #     bounds.left+indent*space_width, bounds.top, bounds.right, bounds.bottom)

                SBS.send_gui_text(event.client_id, self.local_region_tag, 
                    f"{self.tag_prefix}dec_text", f"$text:`prev`;font:gui-1;justify:center;color:#222;",
                    self.bounds.left, self.bounds.bottom-icon_size*2, self.bounds.left+icon_size, self.bounds.bottom)
                SBS.send_gui_clickregion(event.client_id, self.local_region_tag, 
                    f"{self.tag_prefix}dec", "background_color:#6663",
                    self.bounds.left, self.bounds.top, self.bounds.left+em2*5, self.bounds.bottom)
            max_item = len(self._items)-1
            if self.cur<max_item:
                kind, props = icon_props("list.next", "#aaa", "draw_layer:1000")
                send = SBS.send_gui_image if kind == "image" else SBS.send_gui_icon
                send(event.client_id, self.local_region_tag, f"{self.tag_prefix}iinc",
                    props,
                    self.bounds.right-icon_size , self.bounds.bottom-icon_size*2, self.bounds.right, self.bounds.bottom)
                    #self.bounds.right-icon_size , self.bounds.top, self.bounds.right, self.bounds.bottom)
                SBS.send_gui_text(event.client_id, self.local_region_tag, 
                    f"{self.tag_prefix}inc_text", f"$text:`next`;font:gui-1;justify:center;color:#222;",
                    self.bounds.right-icon_size , self.bounds.bottom-icon_size*2, self.bounds.right, self.bounds.bottom)
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
                
# endregion 

        slot = 0
        cur = self.cur


        
        #draw_slots = max_slot
        self.sections = []
        collapse = False

        if len(self.items) <= max_slots:
            cur = 0

        # Last indention level
        last_indent = 0

        # Have to walk them all for collapse to work    
        for i, item in enumerate(self.items):
            #
            # If this is a header at the same or higher indent level
            # Update collapse state
            #
            if not self.carousel:
                if isinstance(item, LayoutListBoxHeader) and item.indent <= last_indent:
                    collapse = item.collapse
                    last_indent = item.indent
                elif collapse and not isinstance(item, LayoutListBoxHeader):
                    # Skip non-headers if collapse    
                    continue
                # Or a sub header
                elif collapse and isinstance(item, LayoutListBoxHeader) and item.indent > last_indent:
                    continue
                # Check to collapse sub-header
                elif not collapse and isinstance(item, LayoutListBoxHeader) and item.indent > last_indent:
                    collapse = item.collapse
                    if collapse:
                        last_indent = item.indent
            #
            #
            # Scan until cur is reached
            if i<cur:
                continue
            #
            #  Should be header or non-collapsed item
            #     
            sel_width = 0
            item_indent= 0
            
            if (self.select or self.multi) and not self.carousel:
                pixel_indent = last_indent * self.indent_pixels
                
                if hasattr(item, "visual_indent"):
                    pixel_indent = item.visual_indent*self.indent_pixels
                elif hasattr(item, "indent"):
                    pixel_indent = item.indent*self.indent_pixels
                    
                item_indent = 100.0*(pixel_indent/aspect_ratio.x)
                sel_width = 100.0*(5/aspect_ratio.x)
                


            tag = f"{self.tag_prefix}:{slot}"
            this_right =   left + item_indent #+item_width
            this_bottom =   top #+item_height
            

          

            if self.horizontal:
                this_bottom = bottom
            else:
                this_right = right
                if self.carousel:
                    #
                    # A carousel shows exactly ONE item, so that item IS the
                    # panel -- give it the box's remaining height rather than
                    # starting it at zero like a stacked item.
                    #
                    # A zero-height section means NOTHING in the template can be
                    # sized against the panel: a flex row resolves to 0, so the
                    # only thing that works is a FIXED height, and a fixed height
                    # does not shrink with the window. That is how LM's mission
                    # picker (a `15em` description row) ran its text to 108% of
                    # the screen at 1024x600 -- correct at the resolution it was
                    # tuned at, off the bottom at a shorter one.
                    #
                    # The nav band is held back so item content is never drawn
                    # under the prev/next buttons, which are bottom-anchored
                    # em2*4 tall (see the nav region above).
                    #
                    this_bottom = max(top, self.bounds.bottom - em2 * 4)

            

            sec = layout.Layout(tag+":sec", None, left+item_indent, top, this_right, this_bottom, 100)
            sec.region_tag = self.local_region_tag
            sec.item_index = i
            
            is_sel = False
            click_tag = f"{tag}:__click"
            if (self.select or self.multi) and not self.carousel:
                is_sel =  item in self.selected

            if (self.select or self.multi) and not self.carousel:
                #sec.click_text = "__________________"
                sec.click_text = ""
                sec.click_background = "#aaaa"
                sec.click_color = "black"
                if is_sel:
                    sec.background_color = self.select_color
                else:
                    sec.background_color = "#0000"
                sec.click_tag = click_tag
            
            collapse_tag = f"{tag}:__collapse"
            if isinstance(item, LayoutListBoxHeader):
                # This needs to be the actual index
                #tag = f"{self.tag_prefix}:{cur}"
                if item.selectable:
                    item.collapse_tag = collapse_tag
                else:
                    sec.click_text = ""
                    sec.click_background = "#aaaa"
                    sec.click_color = "black"
                    sec.background_color = self.select_color
                    sec.click_tag = collapse_tag

            sub_page.next_slot(slot, sec)
            
            size = self.template_func(item, listbox=self, 
                        selected=is_sel, section=sec, click_tag=click_tag, collapse_tag=collapse_tag)
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
            #
            # Draw the selection Tick
            #
            if (self.select or self.multi) and not self.carousel and item in self.selected:
                props = "image:smallWhite; color:white;draw_layer:1000;" # sub_rect: 0,0,etc"
                SBS.send_gui_image(event.client_id, self.local_region_tag,
                    "__selbg:"+self.tag, props,left+item_indent, top, left+item_indent+sel_width, top+sec.bounds.height)
            
            if self.horizontal:
                left+= size
            else:
                top+= size

            # sec.present(event)
            
            self.sections.append(sec)
            #sub_page.tags |= sec.get_tags()

            #cur += 1
            slot += 1
            if slot >= max_slots or self.carousel:
                break

            

            
        
        sub_page.present(event)   
        FrameContext.page = restore
        

    def present(self, event):
        CID = event.client_id
        # #is_update = self.region is not None
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
            self.on_click(event)
            if self.on_message_cb is not None:
                self.on_message_cb(event, self)
            Clickable.clicked[event.client_id] = self
            return
        
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
        
        # This set a watchable item for any click
        # regardless of selection change
        self.click_time = FrameContext.sim_seconds
        
        if index > len(self.items):
            self.represent(event)
            return
        
        item = self.items[index]
        if item in self.locked_selections:
            return
        
        if self.multi:
            if item in self.selected:
                self.selected = [obj for obj in self.selected if obj != item]
                #self.selected.discard(item)
            else:
                self.selected.append(item)
        elif self.select:
            self.selected = [item]
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
        # index = int(sec[1]) +self.cur
        # if index > len(self._items):
        #     self.represent(event)
        #     return
        slot_index = int(sec[1])
        if slot_index > len(self.sections):
            self.represent(event)
            return
        
        index = self.sections[slot_index].item_index
        #item = self.sections[index]
        # item = self._items[index]
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

    
    def _selected_index(self):
        """Index of the selection in the UNFILTERED list, or None.

        THERE ARE TWO COORDINATE SYSTEMS and they are not interchangeable:
        `unfiltered_items` is everything, `_items` is what is actually on show
        (a collapsible list rebuilds it each present, skipping collapsed rows).
        `set_selected_index` takes an UNFILTERED index, so that is what a hint
        carries -- but `cur`, the packing and `sections[].item_index` are all in
        DISPLAY coordinates. Feeding one to the other gives an index past the end
        of the shorter list and a nonsense scroll position.
        """
        if not self.selected:
            return None
        try:
            return self.unfiltered_items.index(self.selected[0])
        except ValueError:
            return None

    def _selected_display_index(self):
        """Index of the selection among the rows actually SHOWN, or None -- the
        space `cur` and the packer work in."""
        if not self.selected or not self._items:
            return None
        try:
            return self._items.index(self.selected[0])
        except ValueError:
            return None

    def _selected_slot(self):
        """Which visible SLOT the selection occupies, or None.

        Read from `sections[].item_index` -- the same table `on_click` resolves
        against -- rather than computed as `selected - cur`. That arithmetic is
        wrong the moment a list has collapsible headers, a filter, or rows of
        different heights.
        """
        sel = self._selected_display_index()
        if sel is None:
            return None
        for slot, sec in enumerate(getattr(self, "sections", []) or []):
            if getattr(sec, "item_index", None) == sel:
                return slot
        return None

    def get_selection_hint(self):
        """An OPAQUE token describing where this listbox is looking.

        Hand it to the next clone of this listbox after a repaint:

            on change lb.value:
                saved = lb.get_selection_hint()
                jump repaint
            ...
            lb = gui_list_box(items, style, select=True, hint=saved)

        Do not inspect it. The contents are free to grow -- an item fingerprint,
        the bounds it was measured at -- and a caller that only passes it along
        keeps working.
        """
        return {
            "cur": self.cur,
            "selected_index": self._selected_index(),
            "slot": self._selected_slot(),
            "count": len(self.unfiltered_items) if self.unfiltered_items else 0,
            "bounds": (self.bounds.left, self.bounds.top,
                       self.bounds.right, self.bounds.bottom)
                      if getattr(self, "bounds", None) else None,
        }

    def apply_selection_hint(self, hint):
        """Apply a hint. Always a HINT: stale is the normal case -- a shorter
        list, a collapsed section, a different screen -- so everything is
        clamped, and the reveal pass at present time has the final word."""
        if not isinstance(hint, dict):
            return
        count = len(self.unfiltered_items) if self.unfiltered_items else 0
        sel = hint.get("selected_index")
        if sel is not None and 0 <= sel < count:
            self.set_selected_index(sel, False)
        cur = hint.get("cur") or 0
        self.cur = max(0, min(int(cur), max(0, count - 1)))

    def set_selected_index(self, i, set_cur=True):
        self.selected = []
        if i is not None and i < len(self.unfiltered_items):
            self.selected.append(self.unfiltered_items[i])
            if set_cur:
                self.cur = i
        self.redraw_if_showing()
    
    def select_all(self):
        if self.multi:
            self.selected = list(self.unfiltered_items)
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
        self.selected = []
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
        if value is None:
            self.selected = []
        else:
            self.selected = [value]
        #self.selected.add(value)
        # i = 0
        # for item in self._items:
        #     if self.convert_value:
        #         v = self.convert_value(item)
        #         if v == value:
        #             self.selected.add(i)
        #     elif item == value:
        #         self.selected.add(i)
        #     i+=1
        self.mark_visual_dirty()
    
    def update(self, props):
        pass

    def set_read_only(self, v):
        self.read_only = v

    def set_selection_lock_index(self, i, lock):
        if i is not None and i < len(self.unfiltered_items):
            self.set_selection_lock(self.unfiltered_items[i], lock)

    def set_selection_lock(self, o, lock):
        if lock:
            if o not in self.locked_selections:
                self.locked_selections.append(o)
        else:
            if o in self.locked_selections:
                self.locked_selections.remove(o)

    def clear_selection_locks(self):
        self.locked_selections = []

    




def layout_list_box_control(items,
                 template_func=None, title_template=None, 
                 section_style=None, title_section_style=None,
                 select=False, multi=False, carousel=False, collapsible=False,read_only=False):
    # The gui_content sets the values
    return LayoutListbox(0, 0, "mast", items,
                 template_func, title_template, 
                 section_style, title_section_style,
                 select,multi, carousel, collapsible, read_only)
