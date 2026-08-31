from ...gui import get_client_aspect_ratio
from ..layout import layout as layout
from ..layout.clickable import Clickable
from ...helpers import FrameContext, FakeEvent, gui_text_escape
from ...message_chain import compose_handler, invoke_message_cb
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
    def __init__(self, tag_prefix, region_tag, task, client_id,
                 owner=None, register=True) -> None:
        self.tags = set()
        # The widget this sub-page builds for (the listbox / overlay / tabbed panel).
        # An author's `tag:` name resolves to a widget this thing rebuilds from a
        # template, so it is the owner that has to re-apply an update afterwards.
        self.owner = owner
        # False for a MEASURE pass. calc_max runs the template for EVERY item just to
        # size it and throws the widgets away -- registering those would fill the real
        # page's tag_map with dead widgets for rows that were never drawn.
        self.register = register
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
        # alias -> layout item, for the duplicate-name warning only.
        self.alias_owner = {}
        # Aliases registered since the last next_slot(), so the owner knows which
        # names belong to the slot it just built.
        self.aliases = []

    def get_tag(self):
        self.tag += 1
        tag =  f"{self.tag_prefix}:{self.slot}:{self.tag}"
        self.tags.add(tag)
        return tag
    
    def add_tag(self, layout_item, runtime_node):
        # compose, not assign -- see StoryPage.add_tag and message_chain (LM #614)
        tag = layout_item.tag
        self.tag_map[tag] = compose_handler(
            self.tag_map.get(tag), layout_item, runtime_node)
        click_tag = getattr(layout_item, "click_tag", None)
        if click_tag is not None:
            # StoryPage.add_tag has always registered this second key; this shim
            # never did, so a click region built by a row template was not resolvable.
            self.tag_map[click_tag] = compose_handler(
                self.tag_map.get(click_tag), layout_item, runtime_node)
        self.add_alias(layout_item, runtime_node)

    def add_alias(self, layout_item, runtime_node=None):
        """Register an author's `tag:` name for a widget built inside this sub-page.

        Same idiom as StoryPage.add_alias: an extra key in the same tag_map, which
        the owner then merges into the real page. The engine tag stays the
        slot-namespaced one this shim hands out, so the owner's
        `sub_tag.startswith(tag_prefix)` routing keeps working (LM #349).
        """
        alias = getattr(layout_item, "alias", None)
        if not alias:
            return
        if not self.register:
            # Measure pass. It runs the template for every item, so a name that is
            # perfectly unique per row would still be seen many times here -- warning
            # from this pass would be pure noise about code that is fine.
            return
        prev = self.alias_owner.get(alias)
        if prev is not None and prev is not layout_item:
            # One template naming every row the same thing: only the last row built
            # is reachable, and which row that is moves as the list scrolls.
            from ...procedural.execution import log
            log(f"tag '{alias}' was claimed by more than one row of this list. Only "
                f"the last one drawn can be reached by gui_update, and which row that "
                f"is changes as the list scrolls -- put something item-unique in the "
                f"name, e.g. \"tag:{alias}-{{item}}\".", "gui", "warning")
        self.alias_owner[alias] = layout_item
        self.aliases.append(alias)
        layout_item._alias_owner = self.owner
        self.tag_map[alias] = compose_handler(
            self.tag_map.get(alias), layout_item, runtime_node)
    
    def next_slot(self, slot, section):
        self.active_layout = section
        self.layouts.append(section)
        self.slot = slot
        self.pending_row = None
        self.aliases = []


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


def _back_pack(heights, avail, item_height, sel):
    """The topmost row that can start the view while row `sel` still fits at the
    BOTTOM. Packs upward from `sel`, taking rows until the next one overflows."""
    used = 0.0
    first = sel
    for back in range(sel, -1, -1):
        h = heights[back] + item_height
        if used + h > avail and back != sel:
            break
        used += h
        first = back
    return max(0, first)


def max_cur(heights, avail, item_height=0.0):
    """The largest `cur` that still shows the LAST row -- the scroll RANGE.

    Not `len(heights) - pack_slots(..., start=cur)`. That counts how many rows fit
    *from where the view happens to be*, which with real per-row heights changes as
    you scroll: the same 40-item list reported a range of 19 at cur=0 and 39 at
    cur=39, so the scrollbar's own `high` moved under the thumb and the list could
    scroll off its own end. This answer does not depend on `cur` at all.
    """
    count = len(heights)
    if count == 0:
        return 0
    return _back_pack(heights, avail, item_height, count - 1)


def reveal_cur(sel, cur, heights, avail, item_height=0.0):
    """Where the view must start so row `sel` is visible, moving the LEAST.

    `sel`, `cur` and `heights` are all in DISPLAY space -- the rows actually on
    show. A collapsible list also has an unfiltered index space; passing one of
    those in points past the end of the shorter list, which is how this broke the
    Control Gallery's index. Clamped rather than trusted.

    Above the window, scroll up to it. Below, back-pack UPWARD from it so it
    lands at the BOTTOM -- the smallest move that reveals it, where
    set_selected_index(i, True) would slam it to the top on every repaint.
    """
    count = len(heights)
    if count == 0:
        return 0
    cur = max(0, min(int(cur or 0), count - 1))
    if sel is None:
        return cur
    sel = max(0, min(int(sel), count - 1))

    slots = pack_slots(heights, avail, item_height, cur)
    if sel < cur:
        return sel
    if sel < cur + slots:
        return cur                      # already visible: do not move
    return _back_pack(heights, avail, item_height, sel)


class LayoutListbox(layout.Column):
    """
      A widget to list things passing function/lamdas to get the data needed for option display of
       a template 
    """

    def __init__(self, left, top, tag_prefix, items, 
                 item_template=None, title_template=None, 
                 section_style=None, title_section_style=None,
                 select=False, multi=False, carousel=False, collapsible=False, read_only=False,
                 reveal=False, hint=None) -> None:
        super().__init__(left,top,33,44)

        self.tag_prefix = tag_prefix
        self.tag  = tag_prefix
        # The task a row template must build under.
        #
        # Captured HERE, in the console build, because that is the last moment the right
        # answer is on the FrameContext. Rows are built later, at present time, and the
        # presenting context is not always this listbox's own: a comms route runs on the
        # SERVER task and presents under the SERVER page, so both `FrameContext.task` and
        # `FrameContext.page.gui_task` are the server's by then. Every var-bound widget in
        # a row then stamps var_scope_id with the server task, the value is written there
        # and read back from the console's own gui_task, and it is always "" at the reader
        # with nothing raising anywhere - measured as ship-to-ship comms sending nothing.
        self.owner_task = FrameContext.client_task
        if self.owner_task is None:
            self.owner_task = FrameContext.task
        # What THIS listbox last merged into the page's tag_map, so the next draw can
        # take back the entries for rows that are no longer on screen.
        self._merged = {}
        # alias -> props handed to gui_update, re-applied after the template rebuilds
        # a row, so an update survives a repaint (LM #349).
        self._alias_overrides = {}
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
        # The scroll range the last draw published. on_scroll inverts the slider
        # about it, and a draw with no scrollbar never sets it -- so it needs a
        # value from the start rather than an AttributeError.
        self.extra_slot_count = 0
        self.carousel = carousel
        self.collapsible = collapsible
        self.read_only = read_only
        
        self.default_item_width = None
        # The height of ONE row, and the spacing BETWEEN rows. These used to be a
        # single value: `row-height` was stored here and then spent as the gap. So a
        # list that declared the height its template already used rendered at twice the
        # pitch, and a template with no declared height collapsed into a zero-tall item
        # with a zero-tall CLICK REGION - visible, barely clickable.
        self.item_row_height = None
        self.item_gap = None
        self.select = select
        self.multi= multi
        # OPT-IN. A selection scrolled out of view is a real problem, but this
        # widget is load-bearing and multi-modal, and defaulting it on moves
        # every list in every mission. One caller at a time.
        self.reveal = reveal
        # ONCE, not continuously. Revealing on every present means the user
        # cannot scroll away from the selection at all -- the next frame drags
        # the view back and the list appears stuck on its first screenful.
        # Armed when the view is (re)established or the selection changes;
        # disarmed by the reveal itself, and by a deliberate scroll, which wins.
        self._reveal_pending = bool(reveal)
        # A repaint builds a DIFFERENT listbox, so `cur` starts at 0 and the
        # reveal -- which only guarantees VISIBILITY -- lands the selection at the
        # bottom of the window instead of where the user's mouse is. The hint is
        # how the caller carries the view across that break. Opaque: what it
        # holds can grow without breaking a caller that only passes it along.
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
        # Documented as per-item padding but never applied - and it carried a 2px
        # default, so the docs promised padding no list has ever had. Applied now, and
        # the default is NOTHING: switching the default on would change the height of
        # every row in every list, which is a separate decision from making the option
        # work.
        self.section_style = section_style

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
        # New data: whatever gui_update() had pinned to the old rows no longer
        # describes anything.
        self._alias_overrides = {}
        self.mark_visual_dirty()

    def set_row_height(self, height):
        """The height of ONE item row - what `row-height` means everywhere else.

        A FLOOR, not a cap: a template that needs more space grows past it, so a
        two-line row is never clipped into a one-line click region.
        """
        self.item_row_height = height

    def set_item_gap(self, gap):
        """The spacing BETWEEN items. This is what `row-height` used to mean here."""
        self.item_gap = gap

    def _listbox_size(self, value, aspect_axis):
        """Resolve a style value against the LISTBOX's own font.

        It was resolved against a hard-coded font size of 20, so `0.1em` on a listbox
        was never 0.1 of anything on screen - while the same expression in one of its
        rows used the row's real font.
        """
        if not value:
            return 0
        font = layout.effective_font(self, None)
        return LayoutAreaParser.compute(value, None, aspect_axis,
                                        layout.get_font_size(font))

    def set_col_width(self, width):
        # col_width for a listbox is the gap width
        self.default_item_width = width

    def default_item_template(self, item):
        from ...procedural.gui import gui_row, gui_text
        # A declared row-height has already sized the item, so an unstyled row fills
        # it. Otherwise 1.6em, which is font-relative. This was `1.0` - a bare number
        # is 1% of SCREEN HEIGHT, about 7px at 720p - so every list with no item
        # template drew ~16px text in a 7px row, with a 7px click region.
        gui_row(None if self.item_row_height else "row-height: 1.6em;")
        task = FrameContext.task
        task.set_variable("LB_ITEM", item)
        if self.item_template is not None:
            msg = task.compile_and_format_string(self.item_template)
        else:
            msg = item
        collapsable =  isinstance(item, LayoutListBoxHeader)
        if collapsable:
            if not item.collapse:
                gui_text(f"$text:{gui_text_escape(item.label)};justify: center;color:#02FF;", "background: #FFFC")
            else:
                gui_text(f"$text:{gui_text_escape(item.label)};justify: center;color:#FFF;", "background: #0173")
        else:
            gui_text(f"$text:{gui_text_escape(msg)};justify: left;")
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
        # Measure each item in a box the size it will actually be DRAWN in. It used to
        # be a full-screen 100x100 for every item, which is fine for a template whose
        # rows carry fixed heights (they measure the same in any box) and wrong for one
        # whose rows flex: those filled the 100 and the packer concluded a single item
        # filled the whole list. Falls back to 100 when nothing is declared, so every
        # list that declares no row-height measures exactly as it did before.
        row_floor = self._listbox_size(self.item_row_height,
                                       get_client_aspect_ratio(CID).y)
        measure_height = row_floor if row_floor else 100
        # Per-item heights, keyed by identity. The draw loop uses these to pack
        # exactly, instead of assuming every row is the tallest one.
        self._item_heights = {}

        restore = FrameContext.page
        restore_task = FrameContext._task
        sub_page = SubPage(self.tag_prefix, self.local_region_tag, restore.gui_task, CID,
                           register=False)
        FrameContext.page = sub_page
        # See self.owner_task: the row template builds under the task that owns THIS
        # listbox, not under whatever is presenting.
        FrameContext.task = self.owner_task if self.owner_task is not None else restore.gui_task
        try:
        
        
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

            
                sec = layout.Layout("unused", None, 0, 0, 100, measure_height)
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
                max_height = max(max_height, row_floor)
                max_width = max(max_width, b.width)

                # This item's own height, for the average.
                this_height = b.height
                if size is not None:
                    this_height = max(this_height, size)
                this_height = max(this_height, 0.2)
                # The declared row height is a FLOOR here too, so the packer and the draw
                # loop agree about how tall an item is. They used to be able to disagree.
                this_height = max(this_height, row_floor)
                self._item_heights[id(item)] = this_height
                total_height += this_height
                counted += 1

        finally:
            # A row template that RAISES must not leave the frame pointing at this
            # throwaway SubPage. Every gui_* call after that builds into a page
            # nothing presents, so the console goes blank and STAYS blank - and the
            # original exception is the only clue, far from where it lands.
            FrameContext.page = restore
            FrameContext._task = restore_task
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
        restore_task = FrameContext._task
        task = restore.gui_task
        sub_page = SubPage(self.tag_prefix, self.local_region_tag, restore.gui_task,
                           event.client_id, owner=self)
        FrameContext.page = sub_page
        # See self.owner_task.
        FrameContext.task = self.owner_task if self.owner_task is not None else task
        try:



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
            item_gap = 0 #self.bounds.height
            aspect_ratio = get_client_aspect_ratio(event.client_id)
            if not self.horizontal:
                item_width = self.bounds.width 
                item_gap = 0 #self.bounds.height
            else:
                item_width = 0 #self.bounds.width 
                item_gap = self.bounds.height
        
            if self.default_item_width:
                item_width = self._listbox_size(self.default_item_width, aspect_ratio.x)
                if self.horizontal is None:
                    self.horizontal = True
            if self.item_gap:
                item_gap = self._listbox_size(self.item_gap, aspect_ratio.y)
            # The floor every item section starts at. Zero when nothing is declared, which
            # is exactly the previous behaviour for every list that declares nothing.
            row_height = self._listbox_size(self.item_row_height, aspect_ratio.y)
        
            # At this point is should assume it is vertical
            if self.horizontal is None:
                self.horizontal = False


            max_item_width, max_item_height, avg_item_height = self.calc_max(CID)
            # Apply the hint once, here rather than in __init__: a collapsible list
            # rebuilds its shown items during present, and an index applied before
            # that points into the wrong list.
            if self._hint is not None and not self._hint_applied:
                self._hint_applied = True
                self.apply_selection_hint(self._hint)

            # Where the visible window starts -- packing depends on it.
            cur_start = self.cur if self.cur and self.cur > 0 else 0
        
            max_item_width += item_width
            max_item_height += item_gap
            avg_item_height += item_gap
        
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

                # The scroll RANGE, and the only place that knows the geometry it
                # depends on. Every path that moves the view -- set_selected_index,
                # apply_selection_hint, on_scroll, a bare `lb.cur = n` -- funnels
                # through here, so this is the one clamp instead of several that
                # would each need `heights` and `avail`. Without it
                # set_selected_index(35) of 40 scrolled past the end of the list and
                # the scrollbar grew its own `high` to cover for it.
                #
                # Not a carousel: its window is one item BY DEFINITION, so `cur`
                # picks which item rather than where a window starts, and a packed
                # range would pin it to the first one. Same carve-out as the reveal
                # below.
                scroll_max = max_cur(heights, avail, item_gap)
                if not self.carousel:
                    cur_start = min(cur_start, scroll_max)
                    self.cur = cur_start
                max_slots = pack_slots(heights, avail, item_gap, cur_start)

                # Opt-in, vertical only, never a carousel (whose window is one item
                # by definition), and never horizontal (a separate packing path with
                # known problems -- left alone deliberately).
                if (self.reveal and self._reveal_pending
                        and self.select and not self.carousel):
                    sel = None
                    if self.selected and self._items:
                        try:
                            sel = self._items.index(self.selected[0])   # DISPLAY space
                        except ValueError:
                            sel = None
                    if sel is not None:
                        cur_start = reveal_cur(sel, cur_start, heights, avail, item_gap)
                        max_slots = pack_slots(heights, avail, item_gap, cur_start)
                        self.cur = cur_start
                    self._reveal_pending = False


            max_slots = int(max_slots)
            if self.carousel:
                max_slots = 1
            if self.horizontal or self.carousel:
                # Uniform widths, and a carousel window is one item by definition --
                # both counts are already independent of where the view is.
                extra_slot_count = len(self._items)-max_slots
            else:
                extra_slot_count = scroll_max

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
                # A REAL height, not zero. A zero-height section makes every flex row
                # inside it resolve to 0 (the flex pass divides an available height of
                # zero), so an item whose template declares no height vanished - and the
                # click region, emitted from these bounds, went with it. The carousel
                # branch below already had to solve this for itself.
                this_bottom =   top + row_height
            

          

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

                if self.section_style:
                    apply_control_styles("", self.section_style, sec, task)
                sub_page.next_slot(slot, sec)
            
                size = self.template_func(item, listbox=self, 
                            selected=is_sel, section=sec, click_tag=click_tag, collapse_tag=collapse_tag)
                #
                # The template just rebuilt this row from the item data, discarding
                # anything gui_update() had put there. Put it back before the row is
                # measured and drawn, so an update survives scrolling away and back.
                #
                if self._alias_overrides:
                    for alias in sub_page.aliases:
                        props = self._alias_overrides.get(alias)
                        if props is None:
                            continue
                        entry = sub_page.tag_map.get(alias)
                        if entry is not None:
                            entry[0].update(props)
                sec.calc(CID)

                # if self.horizontal:
                #     left+= item_width
                # else:
                #     top+= item_gap

                if size is None:
                    sec.resize_to_content()
                    if self.horizontal:
                        size = sec.bounds.width + item_width
                    else:
                        size = sec.bounds.height + item_gap
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
        finally:
            # A row template that RAISES must not leave the frame pointing at this
            # throwaway SubPage. Every gui_* call after that builds into a page
            # nothing presents, so the console goes blank and STAYS blank - and the
            # original exception is the only clue, far from where it lands.
            FrameContext.page = restore
            FrameContext._task = restore_task
        self._merge_tags(CID, sub_page)
        

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
                invoke_message_cb(self.on_message_cb, event, self)
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
                # The user took control of the view. Do not drag it back.
                self._reveal_pending = False
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
        if slot_index >= len(self.sections):
            self.represent(event)
            return
        
        index = self.sections[slot_index].item_index

        if sec[2] != "__click":
            return
        
        # This set a watchable item for any click
        # regardless of selection change
        self.click_time = FrameContext.sim_seconds
        
        if index >= len(self.items):
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
        if slot_index >= len(self.sections):
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

    
    def get_selection_hint(self):
        """An OPAQUE token describing where this listbox is looking.

        Hand it to the next clone after a repaint, so the row under the user's
        mouse stays under it:

            on change lb.value:
                saved = lb.get_selection_hint()
                jump repaint
            ...
            lb = gui_list_box(items, style, select=True, reveal=True, hint=saved)

        Do not inspect it. `selected_index` is in UNFILTERED space because that
        is what set_selected_index takes; `slot` is a DISPLAY position, recorded
        for a future resize policy and not used to restore today. Mixing those
        two spaces is what broke this twice.
        """
        sel = None
        if self.selected:
            try:
                sel = self.unfiltered_items.index(self.selected[0])
            except ValueError:
                sel = None
        slot = None
        for i, sec in enumerate(getattr(self, "sections", []) or []):
            if getattr(sec, "item_index", None) is not None and self._items:
                try:
                    if self._items[sec.item_index] is (self.selected or [None])[0]:
                        slot = i
                        break
                except (IndexError, TypeError):
                    pass
        return {"cur": self.cur, "selected_index": sel, "slot": slot,
                "count": len(self.unfiltered_items) if self.unfiltered_items else 0}

    def apply_selection_hint(self, hint):
        """Apply a hint. Always a HINT -- stale is the normal case (a shorter
        list, a collapsed section, another screen entirely), so everything is
        clamped and the reveal has the final word."""
        if not isinstance(hint, dict):
            return
        count = len(self.unfiltered_items) if self.unfiltered_items else 0
        # An EXPLICIT selection wins over the hint's. The caller sets it after
        # construction, while the hint is applied at present time -- so applying
        # it unconditionally would let a stale hint override a deliberate choice,
        # which is exactly what the tour does when it moves the selection itself.
        # The hint's job is the VIEW; the selection is only a fallback.
        sel = hint.get("selected_index")
        if not self.selected and sel is not None and 0 <= sel < count:
            self.set_selected_index(sel, False)
        try:
            cur = int(hint.get("cur") or 0)
        except (TypeError, ValueError):
            cur = 0
        self.cur = max(0, min(cur, max(0, count - 1)))

    def set_selected_index(self, i, set_cur=True):
        # A new selection is worth showing; a scroll is not undone by it.
        self._reveal_pending = bool(getattr(self, "reveal", False))
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
    
    def _merge_tags(self, client_id, sub_page):
        """Publish this draw's row widgets to the real page, and retract the last one's.

        The other two SubPage users (overlay, tabbed panel) have always done the
        merge; the listbox never did, which is the whole of LM #349 -- gui_update
        resolves against page.tag_map, and the row widgets were never in it.

        The retraction is the part they are missing. A row that scrolled off the
        screen leaves an entry pointing at a widget that is no longer drawn; a later
        update would call present() on it and paint at coordinates that belong to
        nothing. Only entries THIS listbox put there and did not build again are
        taken back, so a same-named widget elsewhere on the page is untouched.
        """
        from ...procedural.gui.gui import gui_page_for_client
        # `or restore` for the same reason tabbed_panel.py:122 does it: the lookup is
        # documented nullable and really is None while a client's page is still being
        # established, and when listboxes NEST the enclosing page is a SubPage that
        # never appears in that registry. Its own owner merges it upward in turn.
        page = gui_page_for_client(client_id) or FrameContext.page
        tag_map = getattr(page, "tag_map", None)
        if tag_map is None:
            return
        fresh = sub_page.tag_map
        for k, v in self._merged.items():
            if k not in fresh and tag_map.get(k) is v:
                del tag_map[k]
        tag_map |= fresh
        self._merged = fresh

    def remember_alias_props(self, alias, props):
        """Hold what gui_update() wrote to a row, so the next draw can re-apply it.

        Without this the update lasts only until the list next draws -- the template
        rebuilds the row from the item data and the change is gone. Cleared whenever
        `items` is replaced, since new data makes old overrides meaningless.
        """
        self._alias_overrides[alias] = props

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
