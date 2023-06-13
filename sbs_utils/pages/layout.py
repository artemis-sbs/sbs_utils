from ..gui import Page
import sbs
import struct # for images sizes
from .. import fs
from ..widgets.shippicker import ShipPicker
import os

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

    def present(self, ctx, event):
        col:Column
        for col in self.columns:
            col.present(ctx,event)

    def on_message(self, ctx, event):
        col:Column
        for col in self.columns:
            col.on_message(ctx,event)

class Column:
    def __init__(self, left=0, top=0, right=0, bottom=0) -> None:
        self.bounds = Bounds(left,top,right,bottom)
        self.padding = None
        self.square = False

    def set_bounds(self, bounds) -> None:
        if self.padding is None:
            self.bounds.left=bounds.left
            self.bounds.top=bounds.top
            self.bounds.right=bounds.right
            self.bounds.bottom=bounds.bottom
        

    def set_row_height(self, height):
        self.default_height = height

    def set_col_width(self, width):
        self.default_width = width

    def set_padding(self, padding):
        self.padding = padding

    def on_message(self, ctx, event):
        pass
    @property
    def value(self):
        return None
    @value.setter
    def value(self, a):
        pass
        


    
class Text(Column):
    def __init__(self, tag, message) -> None:
        super().__init__()
        if "text:" not in message:
            message = f"text:{message}"
        self.message = message
        self.tag = tag

    def present(self, ctx, event):
        ctx.sbs.send_gui_text(event.client_id, 
            self.tag, self.message,  
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)
    @property
    def value(self):
         return self.message
       
    @value.setter
    def value(self, v):
        if "text:" not in v:
            v = f"text:{v}"

        self.message = v
    

class Button(Column):
    def __init__(self, tag, message) -> None:
        super().__init__()
        
        self.tag = tag
        if "text:" not in message:
            self.message = f"text:{message}"
        else:
            self.message = message

    def present(self, ctx, event):
        ctx.sbs.send_gui_button(event.client_id, 
            self.tag, self.message, 
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)
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
        

    def present(self, ctx, event):
        if self.is_int:
            self._value = int(self._value)
        ctx.sbs.send_gui_slider(event.client_id, 
            self.tag, 
            self._value, self.props,
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom,
            )
        
    def on_message(self, ctx, event):
        if event.sub_tag == self.tag:
            self.value = event.sub_float
    @property
    def value(self):
        return self._value
    
    
    @value.setter
    def value(self, v):
        self._value = v

class Checkbox(Column):
    def __init__(self, tag, message, value=False) -> None:
        super().__init__()
        if "text:" not in message:
            message = f"text:{message}"
        self.message = message
        self.tag = tag
        self._value = value
        
    def present(self, ctx, event):
        message = f"{self.message};state:{'on' if self._value else 'off'}"
        ctx.sbs.send_gui_checkbox(event.client_id, 
            self.tag, message, 
            # 1 if self._value else 0,
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)
    
    def on_message(self, ctx, event):
        if event.sub_tag == self.tag:
            self.value = int(event.sub_float)

    @property
    def value(self):
        return self._value
    
    @value.setter
    def value(self, v):
        self._value= v


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



class Image(Column):
    #"image:icon-bad-bang; color:blue; sub_rect: 0,0,etc"
    def __init__(self, tag, file) -> None:
        super().__init__()
        fs.get_artemis_data_dir()
        props = split_props(file, "image")
        # to get size get absolute path
        self.file = os.path.abspath(props["image"].strip())
        # Make the file relative to artemis dir
        rel_file = os.path.relpath(props["image"].strip(), fs.get_artemis_data_dir()+"\graphics")
        props["image"] = rel_file
        self.props = merge_props(props)
        #print(f"{self.file} \n>>\n{rel_file}\nPROPS: {self.props} ")
        self.tag = tag
        self.width = -1
        self.height = -1
        self.get_image_size()
        
    def present(self, ctx, event):
        if self.width == -1:
            message = f"text: IMAGE NOT FOUND {self.file}"
            ctx.sbs.send_gui_text(event.client_id, 
                self.tag, message,
                self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)
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
        
    def present(self, ctx, event):
        ctx.sbs.send_gui_dropdown(event.client_id, 
            self.tag, self.values,
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)
        
    def on_message(self, ctx, event):
        if event.sub_tag == self.tag:
            self.value = event.value_tag
    @property
    def value(self):
        return self._value
       
    @value.setter
    def value(self, v):
        self._value= v

class TextInput(Column):
    def __init__(self, tag, props) -> None:
        super().__init__()
        if "text:" in props:
            #TODO: Need to parse out value    
            pass
        self._value = props
        self.tag = tag
        self.props = props
        
    def present(self, ctx, event):
        ctx.sbs.send_gui_typein(event.client_id, 
            self.tag, self.props,
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)
        
    def on_message(self, ctx, event):
        if event.sub_tag == self.tag:
            self.value = event.value_tag
        
    @property
    def value(self):
         return self._value
       
    @value.setter
    def value(self, v):
        self._value= v


class Blank(Column):
    def __init__(self) -> None:
        super().__init__()
    def present(self, ctx, client_id):
        pass

class Hole(Column):
    def __init__(self) -> None:
        super().__init__()
    def present(self, ctx, client_id):
        pass

# Allows the layout of a enginer widget
class ConsoleWidget(Column):
    def __init__(self, widget) -> None:
        super().__init__()
        self.widget = widget

    def present(self, ctx, event):
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

    def present(self, ctx, event):
        ctx.sbs.send_gui_face(event.client_id, 
            self.tag, self.face,
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)
            #self.left, self.top, self.left+(self.right-self.left)*.60, 100)
            #self.left, self.top, self.left+w, self.top+w)
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

    def present(self, ctx, event):
        ctx.sbs.send_gui_3dship(event.client_id, 
            self.tag, self.ship,  
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)
    @property
    def value(self):
         return self.ship
       
    @value.setter
    def value(self, v):
        self.ship= v

class Icon(Column):
    def __init__(self, tag, props) -> None:
        super().__init__()
        self.props = props
        self.tag = tag
        self.square = True

    def present(self, ctx, event):
        #TODO: This should be ctx.aspect_ratio
        aspect_ratio = ctx.aspect_ratio
        ctx.sbs.send_gui_icon(event.client_id, self.tag,self.props, 
                    self.bounds.left,self.bounds.top, self.right, self.bottom)

    @property
    def value(self):
         return self.icon
       
    @value.setter
    def value(self, v):
        self.icon= v

class IconButton(Column):
    def __init__(self, tag, props) -> None:
        super().__init__()
        self.tag = tag
        self.props = props

    def present(self, ctx, event):
        ctx.sbs.send_gui_iconbutton(event.client_id, 
            self.tag, self.props, 
            self.bounds.left,self.bounds.top, self.right, self.bottom)
    @property
    def value(self):
         return self.props
       
    @value.setter
    def value(self, v):
        self.props = v



        
class GuiControl(Column):
    def __init__(self,  tag,content) -> None:
        super().__init__()
        self.tag = tag
        self.content = content
        self.content.tag_prefix = tag
        self._value=""

    def present(self, ctx, event):
        self.content.present(ctx, event)
    def on_message(self, ctx, event):
        self.content.on_message(ctx,event)
        self._value = self.content.get_value()
        #return super().on_message(sim, event)

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
        self._value= v



class Layout:
    def __init__(self, clickable_tag=None, click_props=None, rows = None, 
                left=0, top=0, right=100, bottom=100,
                left_pixels=False, top_pixels=False, right_pixels=False, bottom_pixels=False) -> None:
        self.rows = rows if rows else []
        self.aspect_ratio = sbs.vec2(1920,1071)
        self.set_bounds(Bounds(left,top,right,bottom))
        self.default_height = None
        self.default_width = None
        self.padding = None
        self.click_props = click_props
        self.tag = clickable_tag

    def set_bounds(self, bounds):
        self.bounds = bounds

    def set_padding(self, padding):
        self.padding = padding

       
    def set_row_height(self, height):
        self.default_height = height

    def set_col_width(self, width):
        self.default_width = width

    def add(self, row:Row):
        self.rows.append(row)

    def calc(self):
        # remove empty
        #self.rows = [x for x in self.rows if len(x.columns)>0]
        if len(self.rows):
            padding = self.padding if self.padding else Bounds()
            
            if self.default_height is not None:
                layout_row_height = self.default_height
            else:
                layout_row_height = self.bounds.height / len(self.rows)

            # if self.default_width is not None:
            #     layout_col_width = self.default_width
            # else:
            #     layout_col_width = None

            row : Row
            left = self.bounds.left
            top = self.bounds.top
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
                row.width = self.bounds.width
                row.left = left
                row.top = top
                squares = 0

                col: Column
                if len(row.columns)==0:
                    continue
                
                for col in row.columns:
                    squares += 1 if col.square else 0
                # get the width and the height of a cell in pixels
                actual_width = row.width/len(row.columns) * self.aspect_ratio.x / 100
                actual_height =  row.height * self.aspect_ratio.y /100

                # get the low of these two as a percentage of the window width
                if actual_height < actual_width:
                    square_width = (actual_height/self.aspect_ratio.x) * 100
                    square_height = (actual_height/self.aspect_ratio.y) * 100
                else:
                    square_width = (actual_width/self.aspect_ratio.x) *100
                    square_height = (actual_width/self.aspect_ratio.y) * 100

                # if layout_col_width is not None:
                #     rect_col_width = layout_col_width
                # el
                if len(row.columns) != squares:
                    rect_col_width = (row.width-(squares*square_width))/(len(row.columns)-squares)
                    if square_width> rect_col_width:
                        square_width= rect_col_width
                        rect_col_width = (row.width-(squares*square_width))/(len(row.columns)-squares)
                else:
                    rect_col_width = square_width

                # bit of a hack to make sure face aren't the biggest things
                

                col_left = left
                hole_size = 0
                for col in row.columns:
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
                top += row_height

    def present(self, ctx, event):
        row:Row
        for row in self.rows:
            row.present(ctx,event)
        if self.click_props is not None:
            ctx.sbs.send_gui_clickregion(event.client_id, self.tag, self.click_props,
                                     self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)
    
    def on_message(self, ctx, event):
        row:Row
        for row in self.rows:
            row.on_message(ctx,event)
    

class RadioButton(Column):
    def __init__(self, tag,  message, group, value=False) -> None:
        super().__init__()
        self.message = message
        self.tag = tag
        self._value = value
        self.group = group
        
    def present(self, ctx, event):
        props = f"text:{self.message};state:{'on' if self._value else 'off'}"
        ctx.sbs.send_gui_checkbox(event.client_id, 
            self.tag, props,
            # 1 if self._value else 0,
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)
    
    def on_message(self, ctx, event):
        if event.sub_tag != self.tag:
            return
        self.value = 1
        for e in self.group:
            if e != self:
                e.value = 0
            e.present(ctx, event)

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
            radio =RadioButton(f"{tag}:{i}", button, group,  value==button)
            group.append(radio)
            row.add(radio)
            i+=1
            if vertical:
                self.group_layout.add(row)
                row = Row()
        self.group_layout.add(row)

    def set_bounds(self, bounds) -> None:
        self.group_layout.set_bounds(bounds)
        self.group_layout.calc()

    def present(self, ctx, event):
        self.group_layout.present(ctx,event)
    
    def on_message(self, ctx, event):
        self.group_layout.on_message(ctx,event)

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


class LayoutPage(Page):
    def __init__(self) -> None:
        super().__init__()
        self.gui_state = 'repaint'
        self.layout = Layout()
        

    def present(self, ctx, event):
        """ Present the gui """

        sz = ctx.aspect_ratio
        if sz is not None and sz.y != 0:
            aspect_ratio = ctx.aspect_ratio
            if self.layout.aspect_ratio != aspect_ratio:
                self.layout.aspect_ratio = aspect_ratio
                self.layout.calc()
                self.gui_state = 'repaint'

        
        match self.gui_state:
            case  "repaint":
                ctx.sbs.send_gui_clear(event.client_id)
                # Setting this to a state we don't process
                # keeps the existing GUI displayed
                self.gui_state = "presenting"
                self.layout.present(ctx,event)
                


