from ...gui import get_client_aspect_ratio
from ...helpers import FrameContext
from ...mast.parsers import LayoutAreaParser, ContentSize
from enum import IntEnum
from .bounds import Bounds
from .hole import Hole
# for type hints
from .row import Row 
from .column import Column
from .dirty import Dirty

import weakref
        

def calc_float_attribute(name, col, row, sec, aspect_ratio_axis, font_size):
    att = None
    if col is not None and hasattr(col, name)and getattr(col, name, None) is not None:
        att = getattr(col, name, None)
    elif row is not None and hasattr(row, name) and getattr(row, name, None) is not None:
        att = getattr(row, name, None)
    elif sec is not None and hasattr(sec, name) and getattr(sec, name, None) is not None:
        att = getattr(sec, name, None)

    if att is not None:
        #
        # A content size is a marker, not an expression -- it cannot be
        # resolved without the widgets, so hand it back for calc to interpret.
        # This check must come BEFORE the float test, since compute() would
        # blow up on it. One identity comparison per resolution is the entire
        # cost content sizing imposes on a layout that does not use it.
        #
        if att.__class__ is ContentSize:
            return att
        if not isinstance(att, float):
            return LayoutAreaParser.compute(att, None,aspect_ratio_axis, font_size)
    return att


def effective_font(col, row_font):
    """The font a column renders with.

    Note the precedence is ROW-first, not column-first: a row font overrides
    the column's own default_font. That is long-standing behaviour and is
    relied on by existing layouts, so it is preserved exactly. It is hoisted
    into one place only so the width pass and the presentation pass can never
    drift apart on it -- a measure pass that used a different font than the
    renderer would mis-size every cell.
    """
    return row_font if row_font is not None else col.default_font


def resolved_size(value):
    """A resolved size as a number, or None when it is not one yet.

    calc_float_attribute returns either a percentage or a ContentSize marker.
    Call sites that do arithmetic use this to fall back to flex sizing for a
    content value they cannot yet resolve, instead of letting a marker reach
    a subtraction.
    """
    return None if value.__class__ is ContentSize else value


def cascade_attribute(name, col, row, sec):
    att = None
    if col is not None and hasattr(col, name) is not None:
        att = getattr(col, name, None)
    elif row is not None and hasattr(row, name) is not None:
        att = getattr(row, name, None)
    elif sec is not None and hasattr(sec, name) is not None:
        att = getattr(sec, name, None)

    return att


# def calc_bounds_attribute(name, col, row, sec, aspect_ratio, font_size):
#     att = None
#     if col is not None and hasattr(col, name) is not None:
#         att = getattr(col, name, None)
#     elif row is not None and hasattr(row, name) is not None:
#         att = getattr(row, name, None)
#     elif sec is not None and hasattr(sec, name) is not None:
#         att = getattr(sec, name, None)

#     return calc_bounds(att, aspect_ratio, font_size)

def calc_bounds(att, aspect_ratio, font_size):
    if att is not None:
        if not isinstance(att, Bounds):
            i = 1
            values=[]
            for ast in att:
                if i >0:
                    ratio =  aspect_ratio.x
                else:
                    ratio =  aspect_ratio.y
                i=-i
                if ratio == 0:
                    ratio = 1
                values.append(LayoutAreaParser.compute(ast, None,ratio,font_size))
            return Bounds(*values)
    return att
                
def get_font_size(font):
    if font is not None:
        font = font.strip().lower()
    sizes = {             # MIN  2k 4k
        "smallest": 18,   # LB   -- -- 
        "gui-1": 22,      # BD   LB -- 
        "gui-2": 24,      # H3   BD LB 
        "gui-3": 28,      # H2   H3 BD  
        "gui-4": 32,      # H1   H2 H3
        "gui-5": 36,      # TT   H1 H2
        "gui-6": 52,      # __   TT H1/TT
    }
    return sizes.get(font, 30)

class RegionType(IntEnum):
    SECTION_AREA_ABSOLUTE = 0,       # Not a window layout, Old school layout
    REGION_ABSOLUTE = 100,   # a Sub region that use 0,0,100,100 of screen
    REGION_RELATIVE = 200,   # TODO: Sub Region that uses pixel size of area as aspect ration
    # CHILD_WINDOW = 2,          
    
from .clickable import Clickable
class Layout(Clickable):
    
        
    def __init__(self, tag=None,  rows = None, 
                left=0, top=0, right=100, bottom=50, region_type=RegionType.SECTION_AREA_ABSOLUTE) -> None:
        self.rows = rows if rows else []
        self.set_bounds(Bounds(left,top,right,bottom))
        self.restore_bounds = self.bounds
        self.default_height = None
        self.default_width = None
        self.default_color = None
        self.default_justify = None
        self.default_font = None

        self.square = False

        self.padding = None
        self.border = None
        self.margin = None

        self.padding_style = None
        self.border_style = None
        self.margin_style = None
        self.bounds_style = None


        self.background_color = None
        self.background_image = "smallWhite"
        self.border_image = "smallWhite"
        self.border_color = None

        self.tag = tag
        self.parent_region_tag = ""
        
        self.click_text  = None
        self._click_tag  = None
        self.click_font  = None
        self.click_color  = None
        self.click_background = None
        self.client_id = None

        self.region = None
        self.region_type = region_type
        self.representing = False
        self._show = True
        self.orientation = 0 # 0 = Top to bottom, 1 = bottom to top

        self.runtime_node = None
        self.on_message_cb = None
        self._parent = None


    @property
    def parent(self):
        return self._parent
        
    @parent.setter
    def parent(self, v):
        self._parent = weakref.ref(v)

    def mark_layout_dirty(self):
        Dirty.mark_dirty(self.parent)

    def mark_visual_dirty(self):
        Dirty.mark_dirty(self)


    @property
    def drawing_region_tag(self):
        if self.region_type != RegionType.SECTION_AREA_ABSOLUTE:
            return self.tag + "$$"
        return self.region_tag

    def set_bounds(self, bounds):
        self.bounds = bounds
        if bounds.left > -995:
            self.restore_bounds = bounds

    
    
    def get_content_bounds(self, merge_self):
        b = Bounds()
        if merge_self:
            b = Bounds(self.bounds)

        for row in self.rows:
            b.merge(row.bounds)
        return b
        
    def resize_to_content(self):
        self.bounds = self.get_content_bounds(True)


    @property
    def is_hidden(self):
        return not self._show #bounds.left == -1000
    
    @property
    def color(self):
        return self.default_color

    @color.setter
    def color(self, v):
        self.default_color = v

    @property
    def justify(self):
        return self.default_justify

    @justify.setter
    def justify(self, v):
        self.default_justify = v

    @property
    def font(self):
        return self.default_font

    @font.setter
    def font(self, v):
        self.default_font = v

    def set_orientation(self, s):
        s = s.strip().upper()
        if s == "TB":
            self.orientation = 0
        elif s == "BT":
            self.orientation = 1
    
    def set_padding(self, padding):
        self.padding = padding

    def set_border(self, border):
        self.border = border

    def set_margin(self, margin):
        self.margin = margin

    def set_row_height(self, height):
        self.default_height = height

    def set_col_width(self, width):
        self.default_width = width

    def add(self, row:Row):
        self.rows.append(row)

    def rebuild(self):
        self.rows = [Row()]

    def show(self, _show):
        if _show == self._show:
            return
        self._show = _show

        if not _show:
            self.set_bounds(Bounds(-1000,-1000, -999,-999))
        else:
            self.set_bounds(self.restore_bounds)
        self.mark_visual_dirty()

    # Called when the content is clear and not presented
    # Meaning all the children no longer exist
    # So THEY need to recreate any regions they have
    # If the are shown again
    def invalidate_children(self):
        for r in self.rows:
            r.invalidate_regions()
    
    def invalidate_regions(self):
        self.region = None

    def invalidate_all(self):
        self.invalidate_regions()
        self.invalidate_children()

    def represent(self, event):
        if self.client_id is None:
            return
        #self.representing = True
        # if self.region_type == RegionType.SECTION_AREA_ABSOLUTE:
        #     self.calc(event.client_id)
        #     self.present(event)
        #     #self.representing = False
        #     return
        # el
        if not self.is_hidden:
            self.calc(event.client_id)
            self.present(event)
            #self.representing = False
            return
        else:  # is_hidden 
            self.calc(event.client_id)
            self.present(event)
            # #self.calc(event.client_id)
            # self.region_begin(event.client_id)
            # self.invalidate_children()
            # self.region_end(event.client_id)
        #self.representing = False

        

    def _resolve_col_widths(self, row, row_bounds_area, aspect_ratio, row_font):
        """Decide how wide each visible column in `row` gets to be.

        Returns (actual_cols, col_widths, square_width, square_height), where
        col_widths is parallel to actual_cols and holds the width BEFORE the
        square override and Hole donation are applied. None if the row has no
        visible columns.

        Split out of calc() so width can be resolved independently of the
        presentation pass. Content-sized rows need their columns' widths before
        their height can be measured (text wraps to the width it is given), and
        that ordering is impossible while the two are interleaved.

        Behaviour is deliberately unchanged here -- see
        tests/test_layout_geometry_golden.py, which pins every rect this
        produces across a corpus of layouts and three aspect ratios.

        Note squares are sized from row_bounds_area.HEIGHT, so column width
        depends on row height whenever a square is present. That knot is why a
        content row containing squares has to be resolved in two steps.
        """
        actual_cols = []
        fixed_widths = []
        squares = 0
        assigned_space = 0
        assigned_cols = 0

        col: Column
        for col in row.columns:
            if col.is_hidden:
                continue
            squares += 1 if col.square else 0
            col_font_size = get_font_size(effective_font(col, row_font))
            # A content width is not resolvable yet, so the column stays in the
            # flex pool for now (S3 measures it).
            default_width = resolved_size(calc_float_attribute(
                "default_width", col, row, self, aspect_ratio.x, col_font_size))
            if default_width is not None:
                assigned_space += default_width
                assigned_cols += 1
            actual_cols.append(col)
            fixed_widths.append(default_width)

        if len(actual_cols) == 0:
            return None

        # get the width and the height of a cell in pixels
        actual_width = row_bounds_area.width/len(actual_cols) * aspect_ratio.x / 100
        actual_height =  row_bounds_area.height * aspect_ratio.y /100

        # get the low of these two as a percentage of the window width
        if actual_height < actual_width:
            square_width = (actual_height/aspect_ratio.x) * 100
            square_height = (actual_height/aspect_ratio.y) * 100
        else:
            square_width = (actual_width/aspect_ratio.x) *100
            square_height = (actual_width/aspect_ratio.y) * 100

        if len(actual_cols) != squares:
            need_assigned = max(len(actual_cols)-squares-assigned_cols,1)
            rect_col_width = (row_bounds_area.width-assigned_space-(squares*square_width))/need_assigned
            if square_width> rect_col_width:
                square_width= rect_col_width
                rect_col_width = (row_bounds_area.width-(squares*square_width))/need_assigned
        else:
            rect_col_width = square_width

        col_widths = [rect_col_width if w is None else w for w in fixed_widths]
        return actual_cols, col_widths, square_width, square_height

    def calc(self, client_id):
        aspect_ratio = get_client_aspect_ratio(client_id)
        self.client_id = client_id
        
        sec_font_size = get_font_size(self.default_font)
        if self.bounds_style is None:
            bounds_area = Bounds(self.bounds)
        elif self.bounds is not None and self.is_hidden:
            bounds_area = Bounds(self.bounds)
        else:
            bounds_area = Bounds(calc_bounds(self.bounds_style, aspect_ratio, sec_font_size))
            self.bounds = Bounds(bounds_area)

        if self.region_type == RegionType.REGION_RELATIVE:
            w = bounds_area.width
            h = bounds_area.height
            bounds_area = Bounds(0,0,w,h)

        rows = self.rows
        #if self.orientation == 1:
        #    rows = list(reversed(rows))
        
        # remove empty
        #self.rows = [x for x in self.rows if len(x.columns)>0]
        if len(rows):
            self.margin = Bounds(calc_bounds(self.margin_style, aspect_ratio, sec_font_size))
            self.padding =Bounds(calc_bounds(self.padding_style, aspect_ratio, sec_font_size))
            self.border =Bounds(calc_bounds(self.border_style, aspect_ratio, sec_font_size))

            bounds_area.shrink(self.margin)
            bounds_area.shrink(self.border)
            bounds_area.shrink(self.padding)
            
            section_height = resolved_size(
                calc_float_attribute("default_height", None, None, self, aspect_ratio.y, 20)
            ) if self.default_height is not None else None

            if section_height is not None:
                layout_row_height = section_height
            else:
                layout_row_height = bounds_area.height
                flex_rows = len(rows)
                for row in rows:
                    row_font = self.default_font
                    if row.default_font is not None:
                        row_font = row.default_font

                    if row.default_height is not None:
                        row_font_height  = get_font_size(row_font)
                        value = resolved_size(calc_float_attribute("default_height", None, row, self, aspect_ratio.y, row_font_height))
                        # A content height is not resolvable yet, so the row
                        # stays in the flex pool for now (S4 measures it).
                        if value is not None:
                            layout_row_height -= value
                            flex_rows -= 1

                if flex_rows>0:
                    layout_row_height /= flex_rows
            
            row : Row
            row_top = bounds_area.top
            row_bottom = bounds_area.bottom
            
            for row in rows:
                #
                # REGION STUFF
                #
                row.region_tag = self.drawing_region_tag
                # Cascading padding
                row_font = row.default_font
                if row_font is None:
                    row_font = self.default_font

                row_font_height  = get_font_size(row_font)
                row.margin = Bounds(calc_bounds(row.margin_style, aspect_ratio, row_font_height))
                row.padding =Bounds(calc_bounds(row.padding_style, aspect_ratio, row_font_height))
                row.border =Bounds(calc_bounds(row.border_style, aspect_ratio, row_font_height))

                # This is for drawing background and border?
                row_height = None
                if row.default_height is not None:
                    row_height = resolved_size(calc_float_attribute("default_height", None, row, None,  aspect_ratio.y, row_font_height))
                if row_height is None:
                    row_height = layout_row_height

                row_bounds_area = Bounds(bounds_area)
                # row_bounds_area.height = row_height
                #row.left = bounds_area.left
                #row.width = bounds_area.width
                if self.orientation==0:
                    row_bounds_area.top = row_top
                    row_top += row_height
                    row_bounds_area.bottom = row_top # + row_bounds_area.height
                else:
                    row_bounds_area.bottom=row_bottom
                    row_bottom -= row_height
                    row_bounds_area.top = row_bottom

                row.left = row_bounds_area.left
                row.top = row_bounds_area.top
                row.right = row_bounds_area.right
                row.bottom = row_bounds_area.bottom
                row.width = row.right - row.left
                row.height = row.bottom - row.top
                # SET Parent
                row.parent = self
                

                row_bounds_area.shrink(row.margin)
                row_bounds_area.shrink(row.padding)
                row_bounds_area.shrink(row.border)

                if len(row.columns)==0:
                    continue

                resolved = self._resolve_col_widths(row, row_bounds_area,
                                                    aspect_ratio, row_font)
                if resolved is None:
                    continue
                actual_cols, col_widths, square_width, square_height = resolved

                # bit of a hack to make sure face aren't the biggest things
                col: Column
                col_left = row_bounds_area.left
                hole_size = 0
                for col_index, col in enumerate(actual_cols):
                    col_font = effective_font(col, row_font)
                    col.font = col_font
                    col_font_size  = get_font_size(col_font)

                    col.margin = Bounds(calc_bounds(col.margin_style, aspect_ratio, col_font_size))
                    col.padding =Bounds(calc_bounds(col.padding_style, aspect_ratio, col_font_size))
                    col.border =Bounds(calc_bounds(col.border_style, aspect_ratio, col_font_size))

                    col_bounds_area = Bounds(row_bounds_area)
                    col_bounds_area.left = col_left

                    # Width already resolved by _resolve_col_widths. It used to
                    # be recomputed here, duplicating a calc_float_attribute per
                    # column on every calc for an identical result.
                    assigned_space = col_widths[col_index]


                    if col.square:
                        col_bounds_area.width = square_width
                        col_bounds_area.height = square_height
                        # Square ignores holes?
                        hole_size = 0
                    elif col.__class__ == Hole:
                        hole_size += assigned_space
                        continue
                    
                    else:
                        col_bounds_area.width =  assigned_space + hole_size
                        hole_size = 0

                    col_left = col_bounds_area.right

                    #
                    # A sub section is a Layout stored as a column, so it appears
                    # in BOTH passes. It applies its own margin/border/padding in
                    # its calc() below, so applying them here too insets its
                    # content twice. Leaf columns have no pass of their own, so
                    # the parent still applies the box model for them.
                    #
                    if not isinstance(col, Layout):
                        col_bounds_area.shrink(col.margin)
                        col_bounds_area.shrink(col.border)
                        col_bounds_area.shrink(col.padding)

                    

                    ##############
                    ### Cascade other attributes
                    if col.color is None:
                        if col.default_color is not None:
                            col.color = col.default_color
                        elif row.default_color is not None:
                            col.color = row.default_color
                        elif self.default_color is not None:
                            col.color = self.default_color

                    if col.justify is None:
                        if col.default_justify is not None:
                            col.justify = col.default_justify
                        elif row.default_justify is not None:
                            col.justify = row.default_justify
                        elif self.default_justify is not None:
                            col.justify = self.default_justify

                    
                    ##################
                    col.set_bounds(col_bounds_area)
                    #
                    # REGION STUFF
                    #
                    col.region_tag = self.drawing_region_tag
                    # SET Parent
                    col.parent = self

                    col.calc(client_id)

    @property
    def click_tag(self):
        if self._click_tag is not None:
            return self._click_tag
        if self.click_text is not None:
            return f"__click:{self.tag}"
        
    @click_tag.setter
    def click_tag(self, v):
        self._click_tag = v

    @property
    def region_tag(self):
        # if self.region_type != RegionType.SECTION_AREA_ABSOLUTE:
        #     return self.local_region_tag
        return self.parent_region_tag

    @region_tag.setter
    def region_tag(self, t):
        # Setting the region tag of a layout is really 
        # setting the parent region tag
        self.parent_region_tag = t
    

    def present(self, event):
        # Sections are different their bounds are the whole container
        
        self.region_begin(event.client_id)

        ctx = FrameContext.context
        border = Bounds(self.bounds)
        border.shrink(self.margin)
        padding= Bounds(border)
        padding.shrink(self.border)
   
        if self.border is not None and self.border_color is not None:
            bb_props = f"image:{self.border_image}; color:{self.border_color};draw_layer:1000;"
            ctx.sbs.send_gui_image(event.client_id, self.region_tag,
                "__bb:"+self.tag, bb_props,
                border.left, 
                border.top, 
                border.right, 
                border.bottom)
            
        if self.background_color is not None:
            props = f"image:{self.background_image}; color:{self.background_color};draw_layer:1000;"
            ctx.sbs.send_gui_image(event.client_id, self.region_tag,
                "__bg:"+self.tag, props,
                padding.left, 
                padding.top, 
                padding.right, 
                padding.bottom)

            
        row:Row
        for row in self.rows:
            if row.bounds.left > 100 or row.bounds.right < 0 or row.bounds.top>100 or row.bounds.bottom <0:
                continue
            if row.bounds.left > self.bounds.right or row.bounds.right < self.bounds.left or row.bounds.top>self.bounds.bottom or row.bounds.bottom < self.bounds.top:
                continue
            row.present(event)

        self._post_present(event)
        self.region_end(event.client_id)


    def region_begin(self, client_id):
        #if self.representing and self.region:
        # if self.region:
        #     if self.region_type != RegionType.SECTION_AREA_ABSOLUTE:
        #         print(f"clear {self.region_tag}")
        #         sbs.send_gui_clear(client_id, self.drawing_region_tag)
        # elif not self.region:
        SBS = FrameContext.context.sbs
        if self.region_type == RegionType.REGION_ABSOLUTE:
            self.region = True
            SBS.send_gui_sub_region(client_id, self.region_tag, self.drawing_region_tag, "draggable:True;", 0.0,0.0,100.0,100.0)
            SBS.send_gui_clear(client_id, self.drawing_region_tag)
        elif self.region_type == RegionType.REGION_RELATIVE:
            #
            # TODO: This should be bounds
            #
            self.region = True
            SBS.send_gui_sub_region(client_id, self.region_tag, self.drawing_region_tag, "draggable:True;", 0,0,50,50)
            SBS.send_gui_clear(client_id, self.drawing_region_tag)
    
        
    def region_end(self, client_id):
        # There should always be the root

        #if self.representing:
        #    self.representing = False
        SBS = FrameContext.context.sbs
        if self.region_type != RegionType.SECTION_AREA_ABSOLUTE:
            SBS.send_gui_complete(client_id, self.drawing_region_tag)

        

    def _post_present(self, event):
        if self.click_text is not None:
            click_props = f"$text:{self.click_text};"
            if self.click_color is not None:
                click_props += f"color: {self.click_color};"
            if self.click_font is not None:
                click_props += f"font: {self.click_font};"
            if self.click_tag is None:
                self.click_tag = f"__click:{self.tag}"
            if self.click_background is not None:
                click_props += f"background_color:{self.click_background};"
            else:
                click_props += f"background_color: white;"

            bounds = Bounds(self.bounds)
            bounds.shrink(self.margin)
            bounds.shrink(self.border)

            ctx = FrameContext.context
            ctx.sbs.send_gui_clickregion(event.client_id, self.drawing_region_tag,
                self.click_tag, click_props,
                bounds.left, bounds.top, bounds.right, bounds.bottom)

    def is_message_for(self, event):
        """Used by MessageTrigger i.e. gui_message to know if message is for this object

        Args:
            event (EVENT): the engine event

        Returns:
            bool: if the gui_message MessageTrigger should be True
        """
        return event.sub_tag == self.tag or event.sub_tag == self.click_tag
  

    def on_message(self, event):
        # If this is clickable handle it
        if event.sub_tag == self.click_tag:
            Layout.clicked[event.client_id] = self

        if self.runtime_node is not None:
            self.runtime_node.on_message(event)
        if self.on_message_cb is not None:
            self.on_message_cb.on_message(event, self)
        # Else propagate messages
        row:Row
        for row in self.rows:
            row.on_message(event)

    def on_end_presenting(self, client_id):
        # Else propagate messages
        row:Row
        for row in self.rows:
            row.on_end_presenting(client_id)

    def on_begin_presenting(self, client_id):
        # Else propagate messages
        row:Row
        for row in self.rows:
            row.on_begin_presenting(client_id)





        
        



