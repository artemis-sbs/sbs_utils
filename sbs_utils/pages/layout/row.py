from .bounds import Bounds
from .column import Column
from .clickable import Clickable
from .dirty import Dirty
from ...helpers import FrameContext
import weakref

class Row:
    def __init__(self, cols=None, width=0, height=0) -> None:
        self.height = height
        self.width = width
        self.columns = cols if cols else []
        self.left=0
        self.top=0

        self.padding = None
        self.border = None
        self.margin = None

        self.padding_style = None
        self.border_style = None
        self.margin_style = None
        self.bounds_style = None


        # cascading props
        self.default_color = None
        self.default_justify = None
        self.default_font = None
        self.default_height = None
        self.default_width = None

        self.background_color = None
        self.background_image = "smallWhite"
        self.border_image = "smallWhite"
        self.border_color = None

        self.tag = None
        self.region_tag = ""
        self.click_text  = None
        self._click_tag  = None
        self.click_font  = None
        self.click_color  = None
        self.click_background = None
        self.clicked = False
        self.client_id = None
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

    def show(self, _show):
        if not _show:
            # Needs to be different than section to truly know it is hidden
            self.set_bounds(Bounds(-1011,-1011, -999,-999))
        else:
            self.set_bounds(self.restore_bounds)
        self.mark_layout_dirty()

    @property
    def is_hidden(self):
        return self.bounds.left < -1000
    

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
    def bounds(self):
        return Bounds(self.left,self.top, self.left+self.width, self.top + self.height)


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

    def set_row_height(self, height):
        self.default_height = height

    def set_padding(self, padding):
        self.padding = padding

    def set_margin(self, margin):
        self.margin = margin

    def set_border(self, border):
        self.border = border

    def set_col_width(self, width):
        self.default_width = width

    def clear(self):
        self.columns = []
        return self

    def add(self, col):
        self.columns.append(col)
        return self
    
    def add_front(self, col):
        self.columns.insert(0,col)
        return self
    
    def represent(self, event):
        if self.client_id:
            self.present(event)


    def present(self, event):
        self.client_id = event.client_id
        col:Column
        ctx = FrameContext.context

        border = Bounds(self.bounds)
        border.shrink(self.margin)
        padding= Bounds(border)
        padding.shrink(self.border)
   
        if self.border is not None and self.border_color is not None:
            #bb_props = f"image:{self.border_image}; color:{self.border_color};draw_layer:{self.draw_layer};" # sub_rect: 0,0,etc"
            bb_props = f"image:{self.border_image}; color:{self.border_color};" # sub_rect: 0,0,etc"
            ctx.sbs.send_gui_image(event.client_id, self.region_tag,
                "__bb:"+self.tag, bb_props,
                border.left, 
                border.top, 
                border.right, 
                border.bottom)
            
        if self.background_color is not None:
            #props = f"image:{self.background_image}; color:{self.background_color};draw_layer:{self.draw_layer};" # sub_rect: 0,0,etc"
            props = f"image:{self.background_image}; color:{self.background_color};" # sub_rect: 0,0,etc"
            ctx.sbs.send_gui_image(event.client_id, self.region_tag,
                "__bg:"+self.tag, props,
                padding.left, 
                padding.top, 
                padding.right, 
                padding.bottom)
            
        for col in self.columns:
            col.present(event)
        self._post_present(event)

    def invalidate_regions(self):
        for col in self.columns:
            col.invalidate_regions()

    def _post_present(self, event):
        if self.click_text is not None:
            ctx = FrameContext.context
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

            #TODO: This looks wrong
            ctx.sbs.send_gui_clickregion(event.client_id, self.region_tag,
                self.click_tag, click_props,
                self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)
            
    def is_message_for(self, event):
        """Used by MessageTrigger i.e. gui_message to know if message is for this object

        Args:
            event (EVENT): the engine event

        Returns:
            bool: if the gui_message MessageTrigger should be True
        """
        return event.sub_tag == self.tag or event.sub_tag == self.click_tag
  
    def on_message(self, event):
        if event.sub_tag == self.click_tag:
            Clickable.clicked[event.client_id] = self
            return

        col:Column
        for col in self.columns:
            col.on_message(event)

    def on_end_presenting(self, client_id):
        col:Column
        for col in self.columns:
            col.on_end_presenting(client_id)

    def on_begin_presenting(self, client_id):
        col:Column
        for col in self.columns:
            col.on_begin_presenting(client_id)
