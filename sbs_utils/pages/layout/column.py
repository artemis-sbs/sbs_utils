from .bounds import Bounds
from ...helpers import FrameContext
from ...agent import Agent
from .clickable import Clickable
from .dirty import Dirty
import weakref

class Column:
    def __init__(self, left=0, top=0, right=0, bottom=0) -> None:
        self.bounds = Bounds(left,top,right,bottom)
        self.restore_bounds = self.bounds
        

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

        self.color = None
        self.default_color = None
        self.justify = None
        self.default_justify = None
        self.font = None
        self.default_font = None

        self.square = False
        self.default_width = None
        self.default_height = None
        
        self.tag = None
        self.region_tag = ""
        self.click_text = None
        self.click_color = None
        self.click_background = None
        self.click_font = None
        self._click_tag = None
        self.data = None
        self.var_scope_id = None
        self.var_name = None
        self.on_message_cb = None
        self.client_id = None
        self._parent = None

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
    def parent(self):
        if self._parent is None:
            return None

        return self._parent()
        
    @parent.setter
    def parent(self, v):
        
        self._parent = weakref.ref(v)
        

    def mark_layout_dirty(self):
        Dirty.mark_dirty(self.parent)

    def mark_visual_dirty(self):
        #
        # I think the engine handles this wrong, but this workaround 
        # fixes it, or is the right thing to do
        if self.region_tag != "":
            Dirty.mark_dirty(self.parent)
            return
        Dirty.mark_dirty(self)


    def set_bounds(self, bounds) -> None:
        self.bounds.left=bounds.left
        self.bounds.top=bounds.top
        self.bounds.right=bounds.right
        self.bounds.bottom=bounds.bottom
        if bounds.left > -1000:
            self.restore_bounds = bounds


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
        

    def set_row_height(self, height):
        self.default_height = height

    def set_col_width(self, width):
        self.default_width = width

    def set_padding(self, padding):
        self._padding = padding

    def set_padding(self, padding):
        self._padding = padding

    
    def get_color(self):
        if self.color is not None:
            return self.color
        
        if self.default_color is not None:
            return self.default_color
        return self.color
    
    def get_justify(self):
        if self.justify is not None:
            return self.justify
        if self.default_justify is not None:
            return self.default_justify
        return self.justify
    
    def get_font(self):
        # self.font is set by calc
        if self.font is not None:
            return self.font
        if self.default_font is not None:
            return self.default_font
        return self.font
    
    def get_cascade_props(self,font = False, color = False, justify = False):
        props = ""
        if font:
            prop = self.get_font()
            if prop is not None:
                props += f"font:{prop};"
        if color:
            prop = self.get_color()
            if prop is not None:
                props += f"color:{prop};"
        if justify:
            prop = self.get_justify()
            if prop is not None:
                props += f"justify:{prop};"
        return props

    def set_margin(self, margin):
        self.margin = margin

    def set_border(self, border):
        self.border = border

    def represent(self, event):
        if self.client_id is None:
            return
        self.present(event)

    def present(self, event):
        self.client_id = event.client_id
        self._pre_present(event)
        self._present(event)
        self._post_present(event)

    def _present(self, event):
        pass

    def _pre_present(self, event):
        ctx = FrameContext.context
        if self.border is not None and self.border_color is not None:
            bb = Bounds(self.bounds)
            bb.grow(self.padding)
            bb.grow(self.border)
            #bb_props = f"image:{self.border_image}; color:{self.border_color};draw_layer:{self.draw_layer};" # sub_rect: 0,0,etc"
            bb_props = f"image:{self.border_image}; color:{self.border_color};" # sub_rect: 0,0,etc"
            ctx.sbs.send_gui_image(event.client_id, self.region_tag,
                "__bb:"+self.tag, bb_props,
                bb.left, bb.top, bb.right, bb.bottom)
            
        if self.background_color is not None:
            #props = f"image:{self.background_image}; color:{self.background_color};draw_layer:{self.draw_layer};" # sub_rect: 0,0,etc"
            props = f"image:{self.background_image}; color:{self.background_color};" # sub_rect: 0,0,etc"
            
            #
            # Bounds include padding, margin for column
            # Layout Calc fills this in
            #
            bg = Bounds(self.bounds)
            bg.grow(self.padding)
            ctx.sbs.send_gui_image(event.client_id, self.region_tag,
                "__bg:"+self.tag, props,
                bg.left, bg.top, bg.right, bg.bottom)

    def _post_present(self, event):
        if self.click_text is not None or self.click_tag is not None:
            click_props = ""
            if self.click_text is not None:
                click_props = f"$text:{self.click_text};"
            if self.click_color:
                click_props += f"color: {self.click_color};"
            if self.click_font:
                click_props += f"font: {self.click_font};"
            if self.click_tag is None:
                self.click_tag = f"__click:{self.tag}"
            if self.click_background is not None:
                click_props += f"background_color:{self.click_background};"
            else:
                click_props += f"background_color: white;"

            ctx = FrameContext.context
            #
            #
            #
            bounds = Bounds(self.bounds)
            if self.padding is not None:
                bounds.grow(self.padding)
            
            ctx.sbs.send_gui_clickregion(event.client_id, self.region_tag,
                self.click_tag, click_props,
                bounds.left, bounds.top, bounds.right, bounds.bottom)
            
    def invalidate_regions(self):
        pass

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
        elif self.on_message_cb is not None:
            self.on_message_cb(event, self)

    def update(self, props):
        pass

    def calc(self, client_id):
        pass # Unused but here to be compatible with sub sections

    def on_end_presenting(self, client_id):
        pass
    def on_begin_presenting(self, client_id):
        pass

    def update_variable(self):
        if self.var_scope_id:
            scope = Agent.get(self.var_scope_id)
            if scope is not None:
                scope.set_variable(self.var_name, self.value)

    def get_variable(self, default=None):
        if self.var_scope_id:
            scope = Agent.get(self.var_scope_id)
            if scope is not None:
                return scope.get_variable(self.var_name, default)
        return default

    @property
    def value(self):
        return None
    @value.setter
    def value(self, a):
        pass
        

