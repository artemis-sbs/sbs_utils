from .bounds import Bounds
from .column import Column
from .clickable import Clickable
from ...helpers import FrameContext

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
        self.click_tag  = None
        self.click_font  = None
        self.click_color  = None
        self.click_background = None
        self.clicked = False


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
        self.present(event)


    def present(self, event):
        col:Column
        ctx = FrameContext.context

        margin = Bounds(self.bounds)
        margin.shrink(self.margin)
        border = Bounds(margin)
        border.shrink(self.border)
   
        if self.border is not None and self.border_color is not None:
            bb_props = f"image:{self.border_image}; color:{self.border_color};" # sub_rect: 0,0,etc"
            ctx.sbs.send_gui_image(event.client_id, self.region_tag,
                "__bb:"+self.tag, bb_props,
                border.left, 
                border.top, 
                border.right, 
                border.bottom)
            
        if self.background_color is not None:
            props = f"image:{self.background_image}; color:{self.background_color};" # sub_rect: 0,0,etc"
            #props = f"image:{self.background_image}; color:black;" # sub_rect: 0,0,etc"
            ctx.sbs.send_gui_image(event.client_id, self.region_tag,
                "__bg:"+self.tag, props,
                margin.left, 
                margin.top, 
                margin.right, 
                margin.bottom)
            
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
