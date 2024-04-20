from ..gui import Page, get_client_aspect_ratio
from ..agent import Agent
import sbs
import struct # for images sizes
from .. import fs
import os
from ..helpers import FrameContext
from ..mast.parsers import LayoutAreaParser,LayoutAreaNode

class Bounds:
    def __init__(self, left=0, top=0, right=0, bottom=0) -> None:
        if left is None:
            self.left=0
            self.top=0
            self.right=0
            self.bottom=0
        elif isinstance(left, Bounds):
            self.left=left.left
            self.top=left.top
            self.right=left.right
            self.bottom=left.bottom
        else:
            self.left=left
            self.top=top
            self.right=right
            self.bottom=bottom

    def __str__(self) -> str:
        return f"l: {self.left} r: {self.right} t: {self.top} b: {self.bottom}"
    @property
    def height(self):
        return self.bottom-self.top
    
    @height.setter
    def height(self, h):
        self.bottom = self.top+h

    @property
    def width(self):
        return self.right-self.left
    @width.setter
    def width(self, w):
        self.right = self.left + w

    def __repr__(self) -> str:
        return f"{self.left}, {self.top}, {self.right}, {self.bottom}"

    def __add__(self, o):
        return Bounds(self.left+o.left,
            self.top+o.top,
            self.right+o.right,
            self.bottom+o.bottom)
    
    def __sub__(self, o):
        return Bounds(self.left-o.left,
            self.top-o.top,
            self.right-o.right,
            self.bottom-o.bottom)
    
    
    def shrink(self, o):
        if o is None:
            return
        self.left   +=  o.left
        self.top    += o.top
        self.right  -= o.right
        self.bottom -= o.bottom
    
    def grow(self, o):
        if o is None:
            return
        self.left   -=  o.left
        self.top    -= o.top
        self.right  += o.right
        self.bottom += o.bottom

    def merge(self, b):
        if b is None:
            return
        self.left = min(b.left, self.left)
        self.top= min(b.top, self.top)
        self.right= max(b.right, self.right)
        self.bottom = max(b.bottom, self.bottom)


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
        self.click_text  = None
        self.click_tag  = None
        self.click_font  = None
        self.click_color  = None
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
    
    def represent(self, event):
        self.present(event)

    def get_tags(self):
        tags = set()
        if self.tag:
            tags.add(self.tag)
        if self.border_color:
            tags.add("__bb:"+self.tag)
        if self.background_color:
            tags.add("__bg:"+self.tag)
        if self.click_tag:
            tags.add(self.click_tag)
        return tags

    def present(self, event):
        col:Column
        ctx = FrameContext.context

        
        border = self.border
        if self.border is None:
            border = Bounds()

        margin = self.margin
        if self.margin is None:
            margin  = Bounds()

        if self.border is not None and self.border_color is not None:
            bb_props = f"image:{self.border_image}; color:{self.border_color};" # sub_rect: 0,0,etc"
            ctx.sbs.send_gui_image(event.client_id, 
                "__bb:"+self.tag, bb_props,
                self.left  + margin.left, 
                self.top   + margin.top, 
                self.left+self.width - margin.right, 
                self.top+self.height - margin.bottom)
            
        if self.background_color is not None:
            props = f"image:{self.background_image}; color:{self.background_color};" # sub_rect: 0,0,etc"
            ctx.sbs.send_gui_image(event.client_id, 
                "__bg:"+self.tag, props,
                self.left  + margin.left    + border.left, 
                self.top   + margin.top     + border.top, 
                self.left+self.width - margin.right - border.right, 
                self.top+self.height - margin.bottom - border.bottom)
            
        for col in self.columns:
            col.present(event)
        self._post_present(event)

    def _post_present(self, event):
        if self.click_text is not None:
            ctx = FrameContext.context
            click_props = f"text:{self.click_text};"
            if self.click_color is not None:
                click_props += f"color: {self.click_color};"
            if self.click_font is not None:
                click_props += f"font: {self.click_font};"
            if self.click_tag is None:
                self.click_tag = f"__click:{self.tag}"

            #TODO: This looks wrong
            ctx.sbs.send_gui_clickregion(event.client_id, 
                self.click_tag, click_props,
                self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)

    def on_message(self, event):
        if event.sub_tag == self.click_tag:
            Layout.clicked[event.client_id] = self
            return

        col:Column
        for col in self.columns:
            col.on_message(event)

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
        self.click_text = None
        self.click_color = None
        self.click_font = None
        self.click_tag = None
        self.data = None
        self.var_scope_id = None
        self.var_name = None

    def set_bounds(self, bounds) -> None:
        self.bounds.left=bounds.left
        self.bounds.top=bounds.top
        self.bounds.right=bounds.right
        self.bounds.bottom=bounds.bottom
        if bounds.left != -1000:
            self.restore_bounds = self.bounds


    def show(self, _show):
        if not _show:
            # Needs to be different than section to truly know it is hidden
            self.set_bounds(Bounds(-1011,-1011, -999,-999))
        else:
            self.set_bounds(self.restore_bounds)

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

    def get_tags(self):
        tags = set()
        if self.tag:
            tags.add(self.tag)
        if self.border_color:
            tags.add("__bb:"+self.tag)
        if self.background_color:
            tags.add("__bg:"+self.tag)
        if self.click_tag:
            tags.add(self.click_tag)
        return tags

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
        self.present(event)

    def present(self, event):
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
            bb_props = f"image:{self.border_image}; color:{self.border_color};" # sub_rect: 0,0,etc"
            ctx.sbs.send_gui_image(event.client_id, 
                "__bb:"+self.tag, bb_props,
                bb.left, bb.top, bb.right, bb.bottom)
            
        if self.background_color is not None:
            props = f"image:{self.background_image}; color:{self.background_color};" # sub_rect: 0,0,etc"
            
            #
            # Bounds include padding, margin for column
            # Layout Calc fills this in
            #
            bg = Bounds(self.bounds)
            bg.grow(self.padding)
            ctx.sbs.send_gui_image(event.client_id, 
                "__bg:"+self.tag, props,
                bg.left, bg.top, bg.right, bg.bottom)

    def _post_present(self, event):
        if self.click_text is not None:
            click_props = f"text:{self.click_text};"
            if self.click_color:
                click_props += f"color: {self.click_color};"
            if self.click_font:
                click_props += f"font: {self.click_font};"
            if self.click_tag is None:
                self.click_tag = f"__click:{self.tag}"

            ctx = FrameContext.context
            #
            #
            #
            bounds = Bounds(self.bounds)
            if self.padding is not None:
                bounds.grow(self.padding)

            ctx.sbs.send_gui_clickregion(event.client_id, 
                self.click_tag, click_props,
                bounds.left, bounds.top, bounds.right, bounds.bottom)

   
    def on_message(self, event):
        if event.sub_tag == self.click_tag:
            Layout.clicked[event.client_id] = self

    def update(self, props):
        pass

    def calc(self, client_id):
        pass # Unused but here to be compatible with sub sections

    def update_variable(self):
        if self.var_scope_id:
            scope = Agent.get(self.var_scope_id)
            if scope is not None:
                # print(f"{self.var_name} {self.value}")
                scope.set_variable(self.var_name, self.value)

    def get_variable(self, default):
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
        


    
class Text(Column):
    def __init__(self, tag, message) -> None:
        super().__init__()
        
        self.message = message
        self.tag = tag

    def _present(self, event):
        ctx = FrameContext.context
        message = self.message
        if "text:" not in message:
            message = f"text:{message};"

        message += self.get_cascade_props(True, True, True)

        ctx.sbs.send_gui_text(event.client_id, 
            self.tag, message,  
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)

    def update(self, message):
        # print(f"{message}")
        self.message = message

    
    @property
    def value(self):
         return self.message
       
    @value.setter
    def value(self, v):
        self.message = v
    

class Button(Column):
    def __init__(self, tag, message) -> None:
        super().__init__()
        self.tag = tag
        if "text:" not in message:
            self.message = f"text:{message};"
        else:
            self.message = message

    def _present(self,  event):
        ctx = FrameContext.context
        message = self.message
        message += self.get_cascade_props(True, True, True)
        ctx.sbs.send_gui_button(event.client_id, 
            self.tag, message, 
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)
        

    def update(self, message):
        if "text:" not in message:
            message = f"text:{message};"
        self.message = message


    @property
    def value(self):
        return self.message

    @value.setter
    def value(self, v):
        if "text:" not in v:
            v = f"text:{v}"

        self.message = v

class Slider(Column):
    def __init__(self,  tag, value, props, is_int=False) -> None:
        super().__init__()
        self.tag = tag
        self._value = value
        self.props = props
        self.is_int = is_int
        

    def _present(self, event):
        if self.is_int:
            if self._value is None:
                self._value = 0
            self._value = int(self._value)
        ctx = FrameContext.context
        ctx.sbs.send_gui_slider(event.client_id, 
            self.tag, 
            self._value, self.props,
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom,
            )
        
    def on_message(self, event):
        if event.sub_tag == self.tag:
            self.value = event.sub_float
        else:
            super().on_message(event)

    def update(self, props):
        self.props = props


    @property
    def value(self):
        return self._value
    
    
    @value.setter
    def value(self, v):
        if self.is_int:
            self._value = int(v)
        else:
            self._value = v
        self.update_variable()

class Checkbox(Column):
    def __init__(self, tag, message, value=False) -> None:
        super().__init__()
        if "text:" not in message:
            message = f"text:{message};"
        self.message = message
        self.tag = tag
        self._value = value
        
    def _present(self, event):
        message = f"state: {self._value};{self.message}"
        message += self.get_cascade_props(True, True, True)
        #print(f"{self.tag} {message}")
        ctx = FrameContext.context
        ctx.sbs.send_gui_checkbox(event.client_id, 
            self.tag, message, 
            # 1 if self._value else 0,
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)
    
    def on_message(self, event):
        if event.sub_tag == self.tag:
            self.value= not self.value
            
            self.present(event)
        else:
            super().on_message(event)
            #self.value = int(event.sub_float)

    def update(self, message):
        if "text:" not in message:
            message = f"text:{message};"
        self.message = message


    @property
    def value(self):
        return self._value
    
    @value.setter
    def value(self, v):
        self._value= v
        self.update_variable()


def split_props(s, def_key):
    ret = {}

    # get key
    start = 0
    key = -1
    end = -1
    while start < len(s):
        key = s.find(":", start)
        if key == -1:
            ret[def_key] = s
            return ret
        s_key = s[start:key]
        key += 1
        end = s.find(";", key)
        if end ==-1:
            s_value = s[key:]
            start = len(s)
        else:
            s_value = s[key:end]
            start = end+1
        ret[s_key] = s_value
    return ret
        
def merge_props(d):
    s=""
    for k,v in d.items():
        s += f"{k}:{v};"
    return s  


IMAGE_FIT = 0
IMAGE_ABSOLUTE = 1
IMAGE_KEEP_ASPECT = 2
IMAGE_KEEP_ASPECT_CENTER = 3


class Image(Column):
    #"image:icon-bad-bang; color:blue; sub_rect: 0,0,etc"
    def __init__(self, tag, file, mode=1) -> None:
        super().__init__()
        self.tag = tag
        self.update(file)
        self.mode = mode

    def update(self, file):
        fs.get_artemis_data_dir()
        props = split_props(file, "image")
        # to get size get absolute path
        self.file = os.path.abspath(props["image"].strip())
        # Make the file relative to artemis dir
        rel_file = os.path.relpath(props["image"].strip(), fs.get_artemis_data_dir()+"\\graphics")
        props["image"] = rel_file
        self.props = merge_props(props)
        #print(f"{self.file} \n>>\n{rel_file}\nPROPS: {self.props} ")

        self.width = -1
        self.height = -1
        self.get_image_size()
        
    def _present(self, event):
        ctx = FrameContext.context
        if self.width == -1:
            message = f"text: IMAGE NOT FOUND {self.file}"
            ctx.sbs.send_gui_text(event.client_id, 
                self.tag, message,
                self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)
        elif self.mode == IMAGE_ABSOLUTE:
            ar = get_client_aspect_ratio(event.client_id)
            x = 100* self.width / ar.x
            y = 100* self.height / ar.y

            ctx.sbs.send_gui_image(event.client_id, 
                self.tag, self.props,
                self.bounds.left, self.bounds.top, 
                self.bounds.left+x, self.bounds.top+y)
        elif self.mode >= IMAGE_KEEP_ASPECT:
            ar = get_client_aspect_ratio(event.client_id)
            # Get section in pixels
            space_x = (self.bounds.right-self.bounds.left)/100
            space_y = (self.bounds.bottom-self.bounds.top)/100
            pixels_x  = (space_x*ar.x)
            pixels_y  = (space_y*ar.y)

            r = pixels_x / self.width
            if r*self.height > pixels_y: 
                r = pixels_y / self.height 

            x = 100* self.width / ar.x  * r
            y = 100* self.height / ar.y * r
            ox=0
            oy=0
            if self.mode == IMAGE_KEEP_ASPECT_CENTER:
                ox = (space_x*100-x)/2
                oy = (space_y*100 - y)/2
            
            
            
            ctx.sbs.send_gui_image(event.client_id, 
                self.tag, self.props,
                self.bounds.left+ox, self.bounds.top+oy, 
                self.bounds.left+ox+x, self.bounds.top+oy+y)
        else:
            ctx.sbs.send_gui_image(event.client_id, 
                self.tag, self.props,
                self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)

    # Get image width and height of image
    def get_image_size(self):
        try:
            with open(self.file+".png", 'rb') as f:
                data = f.read(26)
                #print("Opened")
                # Chck if is png
                #if (data[:8] == '\211PNG\r\n\032\n'and (data[12:16] == 'IHDR')):
                w, h = struct.unpack('>LL', data[16:24])
                self.width = int(w)
                self.height = int(h)
                #print(f"Images size {w} {h}")
        except Exception:
            self.width = -1
            self.height = -1
    @property
    def value(self):
         return self._value
       
    @value.setter
    def value(self, v):
        self._value= v

class Dropdown(Column):
    def __init__(self, tag, props) -> None:
        super().__init__()
        self.values = props
        self.tag = tag
        #TODO: Prase out default ?
        self._value = ""
        
    def _present(self, event):
        ctx = FrameContext.context
        ctx.sbs.send_gui_dropdown(event.client_id, 
            self.tag, self.values,
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)
        
    def on_message(self, event):
        if event.sub_tag == self.tag:
            self.value = event.value_tag
        else:
            super().on_message(event)

    def update(self, props):
        self.props = props

    @property
    def value(self):
        return self._value
       
    @value.setter
    def value(self, v):
        self._value= v
        self.update_variable()

class TextInput(Column):
    def __init__(self, tag, props) -> None:
        super().__init__()
        if "text:" in props:
            #TODO: Need to parse out value    
            pass
        self._value = props
        self.tag = tag
        self.props = props
        
    def _present(self, event):
        ctx = FrameContext.context
        props = self.props
        props += self.get_cascade_props(True, True, True)
        ctx.sbs.send_gui_typein(event.client_id, 
            self.tag, props,
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)
        
    def on_message(self, event):
        if event.sub_tag == self.tag:
            self.value = event.value_tag
        else:
            super().on_message(event)
        
    @property
    def value(self):
         return self._value
       
    @value.setter
    def value(self, v):
        self._value= v
        self.update_variable()


class Blank(Column):
    def __init__(self) -> None:
        super().__init__()
    def _present(self, client_id):
        pass

class Hole(Column):
    def __init__(self) -> None:
        super().__init__()
    def _present(self, client_id):
        pass

# Allows the layout of a enginer widget
class ConsoleWidget(Column):
    def __init__(self, widget) -> None:
        super().__init__()
        self.widget = widget

    def _present(self, event):
        ctx = FrameContext.context
        ctx.sbs.send_client_widget_rects(event.client_id, 
                self.widget, 
                self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom, 
                self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom) 



class Face(Column):
    def __init__(self, tag, face) -> None:
        super().__init__()
        self.face = face
        self.tag = tag
        self.square = True

    def _present(self, event):
        ctx = FrameContext.context
        ctx.sbs.send_gui_face(event.client_id, 
            self.tag, self.face,
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)

    def update(self, face):
        self.face = face

    @property
    def value(self):
         return self.face
       
    @value.setter
    def value(self, v):
        self.face= v

class Ship(Column):
    def __init__(self, tag, ship) -> None:
        super().__init__()
        if "hull_tag:" not in ship:
            ship = f"hull_tag:{ship}"

        self.ship = ship
        self.tag = tag
        #self.square = False

    def _present(self, event):
        ctx = FrameContext.context
        ctx.sbs.send_gui_3dship(event.client_id, 
            self.tag, self.ship,  
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)
    @property
    def value(self):
         return self.ship
       
    @value.setter
    def value(self, v):
        self.ship= v

    def update(self, ship):
        self.ship = ship


class Icon(Column):
    def __init__(self, tag, props) -> None:
        super().__init__()
        self.props = props
        self.tag = tag
        self.square = True

    def _present(self, event):
        #TODO: This should be ctx.aspect_ratio
        ctx = FrameContext.context
        ctx.sbs.send_gui_icon(event.client_id, self.tag,self.props, 
                    self.bounds.left,self.bounds.top, self.bounds.right, self.bounds.bottom)

    @property
    def value(self):
         return self.icon
       
    @value.setter
    def value(self, v):
        self.icon= v

    def update(self, props):
        self.props = props


class IconButton(Column):
    def __init__(self, tag, props) -> None:
        super().__init__()
        self.tag = tag
        self.props = props

    def _present(self,  event):
        ctx = FrameContext.context
        ctx.sbs.send_gui_iconbutton(event.client_id, 
            self.tag, self.props, 
            self.bounds.left,self.bounds.top, self.right, self.bottom)
    @property
    def value(self):
         return self.props
       
    @value.setter
    def value(self, v):
        self.props = v
    def update(self, props):
        self.props = props



        
class GuiControl(Column):
    def __init__(self,  tag,content) -> None:
        super().__init__()
        self.tag = tag
        self.content = content
        self.content.tag_prefix = tag
        self._value=self.content.get_value()

    def _present(self, event):
        self.content.present(event)
    def on_message(self, event):
        self.content.on_message(event)
        v = self.content.get_value()
        if v != self._value:
            self._value = v
            self.update_variable()

        
  
    def set_bounds(self, bounds) -> None:
        super().set_bounds(bounds)
        self.content.left = self.bounds.left
        self.content.top = self.bounds.top
        self.content.right = self.bounds.right
        self.content.bottom = self.bounds.bottom
        self.content.gui_state = ""

    @property
    def value(self):
         return self._value
       
    @value.setter
    def value(self, v):
        self._value = v
        self.content.set_value(v)
        self.update_variable()

    def update(self, props):
        self.content.update(props)

def calc_float_attribute(name, col, row, sec, aspect_ratio_axis, font_size):
    att = None
    if col is not None and hasattr(col, name)and getattr(col, name, None) is not None:
        att = getattr(col, name, None)
    elif row is not None and hasattr(row, name) and getattr(row, name, None) is not None:
        att = getattr(row, name, None)
    elif sec is not None and hasattr(sec, name) and getattr(sec, name, None) is not None:
        att = getattr(sec, name, None)

    if att is not None:
        if not isinstance(att, float):
            return LayoutAreaParser.compute(att, None,aspect_ratio_axis, font_size)
    return att


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
    sizes = {             # MIN  2k 4k
        "smallest": 12,   # LB   -- -- 
        "gui-1": 16,      # BD   LB -- 
        "gui-2": 20,      # H3   BD LB 
        "gui-3": 24,      # H2   H3 BD  
        "gui-4": 28,      # H1   H2 H3
        "gui-5": 32,      # TT   H1 H2
        "gui-6": 48,      # __   TT H1/TT
    }
    return sizes.get(font, 20)

class Layout:
    clicked = {}
    
    def __init__(self, tag=None,  rows = None, 
                left=0, top=0, right=100, bottom=50,
                left_pixels=False, top_pixels=False, right_pixels=False, bottom_pixels=False) -> None:
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
        self.click_text  = None
        self.click_tag  = None
        self.click_font  = None
        self.click_color  = None
        self.click_background = None
        self.client_id = None

    def get_tags(self):
        tags = set()
        if self.tag:
            tags.add(self.tag)
        if self.border_color:
            tags.add("__bb:"+self.tag)
        if self.background_color:
            tags.add("__bg:"+self.tag)
        if self.click_tag:
            tags.add(self.click_tag)
        return tags


    def set_bounds(self, bounds):
        self.bounds = bounds
        if bounds.left != -1000:
            self.restore_bounds = self.bounds

    def get_content_bounds(self):
        b = Bounds(self.bounds)
        for row in self.rows:
            b.merge(row.bounds)
        return b
    
    def resize_to_content(self):
        self.bounds = self.get_content_bounds()


    @property
    def is_hidden(self):
        return self.bounds.left == -1000
    
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

    def show(self, _show):
        if not _show:
            self.set_bounds(Bounds(-1000,-1000, -999,-999))
        else:
            self.set_bounds(self.restore_bounds)

    def represent(self, event):
        self.calc(event.client_id)
        self.present(event)

    def calc(self, client_id):
        aspect_ratio = get_client_aspect_ratio(client_id)
        # print(f"Calc AR: {aspect_ratio.x},{aspect_ratio.y}")
        self.client_id = client_id
        
        sec_font_size = get_font_size(self.default_font)
        if self.bounds_style is None:
            bounds_area = Bounds(self.bounds)
        elif self.bounds is not None and self.is_hidden:
            bounds_area = Bounds(self.bounds)
        else:
            bounds_area = Bounds(calc_bounds(self.bounds_style, aspect_ratio, sec_font_size))
            self.bounds = Bounds(bounds_area)

        
        # remove empty
        #self.rows = [x for x in self.rows if len(x.columns)>0]
        if len(self.rows):
            self.margin = Bounds(calc_bounds(self.margin_style, aspect_ratio, sec_font_size))
            self.padding =Bounds(calc_bounds(self.padding_style, aspect_ratio, sec_font_size))
            self.border =Bounds(calc_bounds(self.border_style, aspect_ratio, sec_font_size))

            bounds_area.shrink(self.margin)
            bounds_area.shrink(self.border)
            bounds_area.shrink(self.padding)
            
            if self.default_height is not None:
                layout_row_height = calc_float_attribute("default_height", None, None, self, aspect_ratio.y, 20)
            else:
                layout_row_height = bounds_area.height
                flex_rows = len(self.rows)
                for row in self.rows:
                    row_font = self.default_font
                    if row.default_font is not None:
                        row_font = row.default_font

                    if row.default_height is not None:
                        row_font_height  = get_font_size(row_font)
                        value = calc_float_attribute("default_height", None, row, self, aspect_ratio.y, row_font_height)
                        layout_row_height -= value
                        flex_rows -= 1
                        
                if flex_rows>0:
                    layout_row_height /= flex_rows
            
            row : Row
            row_top = bounds_area.top
            #print(f"SEC Bounds {bounds_area}")

            
            for row in self.rows:
                row_bounds_area = Bounds(bounds_area)
                row_bounds_area.top = row_top
                
                # Cascading padding
                row_font = row.default_font
                if row_font is None:
                    row_font = self.default_font

                row_font_height  = get_font_size(row_font)
                row.margin = Bounds(calc_bounds(row.margin_style, aspect_ratio, row_font_height))
                row.padding =Bounds(calc_bounds(row.padding_style, aspect_ratio, row_font_height))
                row.border =Bounds(calc_bounds(row.border_style, aspect_ratio, row_font_height))

                # This is for drawing background and border?
                if row.default_height is not None:
                    row_height = calc_float_attribute("default_height", None, row, None,  aspect_ratio.y, row_font_height)
                    #print(f"RRR {row_height} {row_font_height}")
                else:
                    row_height = layout_row_height

                #print(f"RRR {row_height}")
                row_bounds_area.height = row_height
                row.left = row_bounds_area.left
                row.width = row_bounds_area.width
                row.top = row_bounds_area.top
                row.height = row_bounds_area.height

                row_bounds_area.shrink(row.margin)
                row_bounds_area.shrink(row.padding)
                row_bounds_area.shrink(row.border)

                squares = 0

                col: Column
                if len(row.columns)==0:
                    continue
                
                actual_cols = []
                assigned_space = 0
                assigned_cols = 0
                for col in row.columns:
                    if col.is_hidden:
                        continue
                    squares += 1 if col.square else 0
                    col_font = row_font
                    if col_font is None:
                        col_font = col.default_font

                    col_font_size  = get_font_size(col_font)
                    default_width = calc_float_attribute("default_width", col, row, self, aspect_ratio.x, col_font_size)
                    if default_width is not None:
                        assigned_space += default_width
                        assigned_cols += 1

                    actual_cols.append(col)

                if len(actual_cols)==0:
                    continue
                
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

                #print(f"   ROW Bounds {row_bounds_area} RCW {rect_col_width}")

                # bit of a hack to make sure face aren't the biggest things
                col_left = row_bounds_area.left
                hole_size = 0
                for col in actual_cols:
                    col_font = row_font
                    if col_font is None:
                        col_font = col.default_font
                    col.font = col_font
                    col_font_size  = get_font_size(col_font)

                    col.margin = Bounds(calc_bounds(col.margin_style, aspect_ratio, col_font_size))
                    col.padding =Bounds(calc_bounds(col.padding_style, aspect_ratio, col_font_size))
                    col.border =Bounds(calc_bounds(col.border_style, aspect_ratio, col_font_size))

                    col_bounds_area = Bounds(row_bounds_area)
                    col_bounds_area.left = col_left
                    
                    assigned_space = rect_col_width
                    default_width = calc_float_attribute("default_width", col, row, self, aspect_ratio.x, col_font_size)
                    if default_width is not None:
                        assigned_space = default_width


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


                    col_bounds_area.shrink(col.margin)
                    col_bounds_area.shrink(col.border)
                    col_bounds_area.shrink(col.padding)

                    col_left = col_bounds_area.right

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
                    #print(f"       COL Bounds {col_bounds_area}")
                    col.set_bounds(col_bounds_area)
                    col.calc(client_id)

         
                row_top += row_height
         


    def present(self, event):
        # Sections are different their bounds are the whole container
        if self.border_color is not None:
            bounds = Bounds(self.bounds)
            bounds.shrink(self.margin)

            ctx = FrameContext.context
            props = f"image:{self.border_image}; color:{self.border_color};" # sub_rect: 0,0,etc"
            ctx.sbs.send_gui_image(event.client_id, 
                    "__bb:"+self.tag, props,
                    bounds.left, bounds.top, bounds.right, bounds.bottom)


        if self.background_color is not None:
            bounds = Bounds(self.bounds)
            bounds.shrink(self.margin)
            bounds.shrink(self.border)

            ctx = FrameContext.context
            props = f"image:{self.background_image}; color:{self.background_color};" # sub_rect: 0,0,etc"
            ctx.sbs.send_gui_image(event.client_id, 
                    "__bg:"+self.tag, props,
                    bounds.left, bounds.top, bounds.right, bounds.bottom)
        row:Row
        for row in self.rows:
            row.present(event)

        self._post_present(event)


    def _post_present(self, event):
        if self.click_text is not None:
            click_props = f"text:{self.click_text};"
            if self.click_color is not None:
                click_props += f"color: {self.click_color};"
            if self.click_font is not None:
                click_props += f"font: {self.click_font};"
            if self.click_tag is None:
                self.click_tag = f"__click:{self.tag}"
            if self.click_background is not None:
                click_props += f"background_color:{self.click_background};"
            click_props += f"background_color: white;"

            bounds = Bounds(self.bounds)
            bounds.shrink(self.margin)
            bounds.shrink(self.border)

            ctx = FrameContext.context
            ctx.sbs.send_gui_clickregion(event.client_id, 
                self.click_tag, click_props,
                bounds.left, bounds.top, bounds.right, bounds.bottom)

    def on_message(self, event):
        # If this is clickable handle it
        if event.sub_tag == self.click_tag:
            Layout.clicked[event.client_id] = self

        # Else propagate messages
        row:Row
        for row in self.rows:
            row.on_message(event)
    

class RadioButton(Column):
    def __init__(self, tag,  message, parent, value=False) -> None:
        super().__init__()
        self.message = message
        self.tag = tag
        self._value = value
        self.parent = parent
        self.group = parent.group
        
    def _present(self, event):
        ctx = FrameContext.context
        props = f"state:{self._value==1};text:{self.message};"
        ctx.sbs.send_gui_checkbox(event.client_id, 
            self.tag, props,
            # 1 if self._value else 0,
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)
    
    def on_message(self, event):
        if event.sub_tag == self.tag:
            self.value = 1
            
            for e in self.group:
                if e != self:
                    e.value = 0
                e.present(event)
            #
            #
            self.parent.update_variable()
        else:
            super().on_message(event)

    @property
    def value(self):
         return self._value
       
    @value.setter
    def value(self, v):
        self._value= v


        
class RadioButtonGroup(Column):
    def __init__(self, tag, buttons, value, vertical) -> None:
        super().__init__()
        buttons = buttons.split(",")
        self.tag = tag
        group = []
        self.group = group
        self.group_layout = Layout()
        row = Row()
        i=0
        for button in buttons:
            button = button.strip()
            radio =RadioButton(f"{tag}:{i}", button, self,  value==button)
            group.append(radio)
            row.add(radio)
            i+=1
            if vertical:
                self.group_layout.add(row)
                row = Row()
        self.group_layout.add(row)
        
    def set_bounds(self, bounds) -> None:
        self.group_layout.set_bounds(bounds)
        #self.group_layout.calc()

    def _present(self, event):
        #aspect_ratio = get_client_aspect_ratio(event.client_id)
        self.group_layout.calc(event.client_id)
        self.group_layout.present(event)
    
    def on_message(self, event):
        self.group_layout.on_message(event)

    @property
    def value(self):
        for item in self.group:
            if item.value:
                return item.message 
        return ""
       
    @value.setter
    def value(self, v):
        for item in self.group:
            if item.message == v:
                item.value = 1
            else:
                item.value = 0
        #
        #
        self.group.update_variable()

    def update(self, props):
        #print(f"update {props}")
        if props is None:
            return
        buts = props.split(",")
        i  = 0
        for but in buts:
            if i >= len(self.group):
                break
            self.group[i].message = but
            i+=1
            
        
        


class LayoutPage(Page):
    def __init__(self) -> None:
        super().__init__()
        self.gui_state = 'repaint'
        self.layout = Layout()
        self.aspect_ratio = sbs.vec3(1024,768,0)
        

    def _present(self, event):
        """ Present the gui """
        aspect_ratio = get_client_aspect_ratio(event.client_id)
        sz = ctx.aspect_ratio
        if self.aspect_ratio.x != sz.x or self.aspect_ratio.y != sz.y:
            self.aspect_ratio.x = sz.x
            self.aspect_ratio.y = sz.y
            self.layout.calc(event.client_id)
            self.gui_state = 'repaint'

        ctx = FrameContext.context
        match self.gui_state:
            case  "repaint":
                ctx.sbs.send_gui_clear(event.client_id)
                # Setting this to a state we don't process
                # keeps the existing GUI displayed
                self.gui_state = "presenting"
                self.layout.present(event)
                ctx.sbs.send_gui_complete(event.client_id)
                


