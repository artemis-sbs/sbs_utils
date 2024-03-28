from ..gui import Page, get_client_aspect_ratio
from ..agent import Agent
import sbs
import struct # for images sizes
from .. import fs
import os
from ..helpers import FrameContext
from ..procedural.inventory import get_inventory_value

class Bounds:
    def __init__(self, left=0, top=0, right=0, bottom=0) -> None:
        self.left=left
        self.top=top
        self.right=right
        self.bottom=bottom
    @property
    def height(self):
        return self.bottom-self.top
    @property
    def width(self):
        return self.right-self.left
    def __repr__(self) -> str:
        return f"{self.left}, {self.top}, {self.right}, {self.bottom}"


class Row:
    def __init__(self, cols=None, width=0, height=0) -> None:
        self.height = height
        self.width = width
        self.columns = cols if cols else []
        self.left=0
        self.top=0
        self.padding = None
        self.default_height = None
        self.default_width = None
        self.background = None
        self.tag = None
        self.click_text  = None
        self.click_tag  = None
        self.click_font  = None
        self.click_color  = None
        self.clicked = False

    def set_row_height(self, height):
        self.default_height = height

    def set_padding(self, padding):
        self.padding = padding


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

    def present(self, event):
        col:Column
        ctx = FrameContext.context
        if self.background is not None:
            props = f"image:smallWhite; color:{self.background};" # sub_rect: 0,0,etc"
            if self.padding:
                ctx.sbs.send_gui_image(event.client_id, 
                    "__row-bg:"+self.tag, props,
                    self.left+self.padding.left, 
                    self.top+self.padding.top, 
                    self.left+self.width-self.padding.right, 
                    self.top+self.height-self.padding.bottom)
            else:
                ctx.sbs.send_gui_image(event.client_id, 
                    "__row-bg:"+self.tag, props,
                    self.left, self.top, self.left+self.width, self.top+self.height)
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
                self.click_tag = f"click:{self.tag}:{self.click_text}"
            
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
        self.square = False
        self.background = None
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
        self.padding = padding

    def represent(self, event):
        self.present(event)

    def present(self, event):
        self._pre_present(event)
        self._present(event)
        self._post_present(event)

    def _present(self, event):
        pass

    def _pre_present(self, event):
        if self.background is not None:
            props = f"image:smallWhite; color:{self.background};" # sub_rect: 0,0,etc"

            #
            # Bounds include padding for column
            #
            ctx = FrameContext.context
            ctx.sbs.send_gui_image(event.client_id, 
                    "__bg:"+self.tag, props,
                    self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)

    def _post_present(self, event):
        if self.click_text is not None:
            click_props = f"text:{self.click_text};"
            if self.click_color:
                click_props += f"color: {self.click_color};"
            if self.click_font:
                click_props += f"font: {self.click_font};"
            if self.click_tag is None:
                self.click_tag = f"click:{self.tag}:{self.click_text}"

            ctx = FrameContext.context
            ctx.sbs.send_gui_clickregion(event.client_id, 
                self.click_tag, click_props,
                self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)

   
    def on_message(self, event):
        if event.sub_tag == self.click_tag:
            Layout.clicked[event.client_id] = self

    def update(self, props):
        pass

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
        task = get_inventory_value(event.client_id, "GUI_TASK")
        if task is not None:
            message = task.format_string(self.message)
        else:
            message = self.message
        if "text:" not in message:
            message = f"text:{message}"

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
            self.message = f"text:{message}"
        else:
            self.message = message

    def _present(self,  event):
        ctx = FrameContext.context
        ctx.sbs.send_gui_button(event.client_id, 
            self.tag, self.message, 
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)
        

    def update(self, message):
        if "text:" not in message:
            message = f"text:{message}"
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
            message = f"text:{message}"
        self.message = message
        self.tag = tag
        self._value = value
        
    def _present(self, event):
        message = f"state: {self._value};{self.message}"
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
            message = f"text:{message}"
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
        ctx.sbs.send_gui_typein(event.client_id, 
            self.tag, self.props,
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



class Layout:
    clicked = {}
    
    def __init__(self, tag=None,  rows = None, 
                left=0, top=0, right=100, bottom=100,
                left_pixels=False, top_pixels=False, right_pixels=False, bottom_pixels=False) -> None:
        self.rows = rows if rows else []
        self.set_bounds(Bounds(left,top,right,bottom))
        self.restore_bounds = self.bounds
        self.default_height = None
        self.default_width = None
        self.padding = None
        self.background = None
        self.tag = tag
        self.click_text  = None
        self.click_tag  = None
        self.click_font  = None
        self.click_color  = None
        self.click_background = None
        self.client_id = None
        
        

    def set_bounds(self, bounds):
        self.bounds = bounds
        if bounds.left != -1000:
            self.restore_bounds = self.bounds

    @property
    def is_hidden(self):
        return self.bounds.left == -1000
    
    def set_padding(self, padding):
        self.padding = padding

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
        self.client_id = client_id
        # remove empty
        #self.rows = [x for x in self.rows if len(x.columns)>0]
        if len(self.rows):
            padding = self.padding if self.padding else Bounds()
            
            if self.default_height is not None:
                layout_row_height = self.default_height
            else:
                layout_row_height = self.bounds.height / len(self.rows)

            for row in self.rows:
                if row.default_height is not None:
                    layout_row_height += (layout_row_height-row.default_height)

            # if self.default_width is not None:
            #     layout_col_width = self.default_width
            # else:
            #     layout_col_width = None

            row : Row
            left = self.bounds.left
            top = self.bounds.top
            # Find rows with assign height and adjust other height 
            # to account for that
            
            for row in self.rows:
                # Cascading padding
                if row.padding:
                    padding.left += row.padding.left
                    padding.right+= row.padding.right
                    padding.top += row.padding.top
                    padding.bottom += row.padding.bottom

                if row.default_height is not None:
                    row_height = row.default_height
                else:
                    row_height = layout_row_height
                row.height = row_height
                row.left = left
                row.top = top
                row.width = self.bounds.width
                squares = 0

                col: Column
                if len(row.columns)==0:
                    continue
                
                actual_cols = []
                for col in row.columns:
                    if col.is_hidden:
                        continue
                    squares += 1 if col.square else 0
                    actual_cols.append(col)

                if len(actual_cols)==0:
                    continue

                # get the width and the height of a cell in pixels
                actual_width = row.width/len(actual_cols) * aspect_ratio.x / 100
                actual_height =  row.height * aspect_ratio.y /100

                # get the low of these two as a percentage of the window width
                if actual_height < actual_width:
                    square_width = (actual_height/aspect_ratio.x) * 100
                    square_height = (actual_height/aspect_ratio.y) * 100
                else:
                    square_width = (actual_width/aspect_ratio.x) *100
                    square_height = (actual_width/aspect_ratio.y) * 100

                # if layout_col_width is not None:
                #     rect_col_width = layout_col_width
                # el
                if len(actual_cols) != squares:
                    rect_col_width = (row.width-(squares*square_width))/(len(actual_cols)-squares)
                    if square_width> rect_col_width:
                        square_width= rect_col_width
                        rect_col_width = (row.width-(squares*square_width))/(len(actual_cols)-squares)
                else:
                    rect_col_width = square_width

                # bit of a hack to make sure face aren't the biggest things
                

                col_left = left
                hole_size = 0
                for col in actual_cols:
                    if col.padding is not None:
                        padding.left += col.padding.left
                        padding.right+= col.padding.right
                        padding.top += col.padding.top
                        padding.bottom += col.padding.bottom


                    bounds = Bounds(col_left,0,0,0)
                    bounds.top = top
                    bounds.bottom = top+row_height
                    if col.square:
                        bounds.right = bounds.left + square_width
                        #print(f"SW {square_width} SH {square_height}")
                        bounds.bottom = top+square_height
                        # Square ignores holes?
                        hole_size = 0
                    elif col.__class__ == Hole:
                        hole_size += rect_col_width
                        continue
                    else:
                        bounds.right = bounds.left+rect_col_width + hole_size
                        hole_size = 0
                    col_left = bounds.right

                    # Add padding 
                    bounds.left=bounds.left+padding.left
                    bounds.top=bounds.top+padding.top
                    bounds.right=bounds.right-padding.right
                    bounds.bottom=bounds.bottom-padding.bottom

                    col.set_bounds(bounds)
                    # remove column padding
                    if col.padding is not None:
                        padding.left -= col.padding.left
                        padding.right-= col.padding.right
                        padding.top -= col.padding.top
                        padding.bottom -= col.padding.bottom
                top += row_height
                # remove the row's padding
                if row.padding:
                    padding.left -= row.padding.left
                    padding.right-= row.padding.right
                    padding.top -= row.padding.top
                    padding.bottom -= row.padding.bottom
                #print(f"calc w: {bounds.right-bounds.left}")


    def present(self, event):
        
        if self.background is not None:
            ctx = FrameContext.context
            props = f"image:smallWhite; color:{self.background};" # sub_rect: 0,0,etc"
            ctx.sbs.send_gui_image(event.client_id, 
                    "__section-bg:"+self.tag, props,
                    self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)
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
                self.click_tag = f"click:{self.tag}:{self.click_text}"
            if self.click_background is not None:
                click_props += f"background_color:{self.click_background};"
            click_props += f"background_color: white;"

            ctx = FrameContext.context
            ctx.sbs.send_gui_clickregion(event.client_id, 
                self.click_tag, click_props,
                self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)

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
                


