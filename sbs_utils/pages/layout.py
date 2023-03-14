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

    def set_col_width(self, width):
        self.default_width = width

    def clear(self):
        self.columns = []
        return self

    def add(self, col):
        self.columns.append(col)
        return self

    def present(self, sim, event):
        col:Column
        for col in self.columns:
            col.present(sim,event)

    def on_message(self, sim, event):
        col:Column
        for col in self.columns:
            col.on_message(sim,event)

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
        else:
            self.bounds.left=bounds.left+self.padding.left
            self.bounds.top=bounds.top+self.padding.top
            self.bounds.right=bounds.right-self.padding.right
            self.bounds.bottom=bounds.bottom-self.padding.bottom

    def set_row_height(self, height):
        self.default_height = height

    def set_col_width(self, width):
        self.default_width = width

    def set_padding(self, padding):
        self.padding = padding

    def on_message(self, sim, event):
        pass


    
class Text(Column):
    def __init__(self, message, tag) -> None:
        super().__init__()
        self.message = message
        self.tag = tag
        #self.color = color

    def present(self, sim, event):
        sbs.send_gui_text(event.client_id, 
            self.message, self.tag, 
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)

class Button(Column):
    def __init__(self, message, tag) -> None:
        super().__init__()
        self.message = message
        self.tag = tag
        #self.color = color

    def present(self, sim, event):
        sbs.send_gui_button(event.client_id, 
            self.message, self.tag, 
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)

class Slider(Column):
    def __init__(self,  value=0.5, low=0.0, high=1.0, tag=None) -> None:
        super().__init__()
        self.tag = tag
        self.value = value
        self.low = low
        self.high = high

    def present(self, sim, event):
        sbs.send_gui_slider(event.client_id, 
            self.tag, 
            self.low, self.high, self.value,
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)

class Checkbox(Column):
    def __init__(self, message, tag, value=False) -> None:
        super().__init__()
        self.message = message
        self.tag = tag
        self.value = value
        
    def present(self, sim, event):
        sbs.send_gui_checkbox(event.client_id, 
            self.message, self.tag, 
            1 if self.value else 0,
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)

class Image(Column):
    def __init__(self, file, color, tag) -> None:
        super().__init__()
        fs.get_artemis_data_dir()
        self.file = os.path.abspath(file)
        self.rel_file = os.path.relpath(file, fs.get_artemis_data_dir()+"\graphics")
        print(f"{self.file} >> {self.rel_file}")
        self.color = color
        self.tag = tag
        self.width = -1
        self.height = -1
        self.get_image_size()
        
    def present(self, sim, event):
        if self.width == -1:
            message = f"IMAGE NOT FOUND: {self.file}"
            sbs.send_gui_text(event.client_id, 
                message, self.tag, 
                self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)
        else:
            sbs.send_gui_image(event.client_id, 
                self.rel_file, self.color, self.tag, 
                0,0,self.width, self.height,
                self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)

    # Get image width and height of image
    def get_image_size(self):
        try:
            with open(self.file+".png", 'rb') as f:
                data = f.read(26)
                print("Opened")
                # Chck if is png
                #if (data[:8] == '\211PNG\r\n\032\n'and (data[12:16] == 'IHDR')):
                w, h = struct.unpack('>LL', data[16:24])
                self.width = int(w)
                self.height = int(h)
                print(f"Images size {w} {h}")
        except Exception:
            self.width = -1
            self.height = -1

class Dropdown(Column):
    def __init__(self, value, values, tag) -> None:
        super().__init__()
        self.value = value
        self.values = values
        self.tag = tag
        
    def present(self, sim, event):
        sbs.send_gui_dropdown(event.client_id, 
            self.value, self.tag, self.values,
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)

class TextInput(Column):
    def __init__(self, value, label, tag) -> None:
        super().__init__()
        self.value = value
        self.tag = tag
        self.label = label
        
    def present(self, sim, event):
        sbs.send_gui_typein(event.client_id, 
            self.value, self.label,self.tag,
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)


class Blank(Column):
    def __init__(self) -> None:
        super().__init__()
    def present(self, sim, client_id):
        pass

class Hole(Column):
    def __init__(self) -> None:
        super().__init__()
    def present(self, sim, client_id):
        pass


class Face(Column):
    def __init__(self, face, tag) -> None:
        super().__init__()
        self.face = face
        self.tag = tag
        self.square = True

    def present(self, sim, event):
        sbs.send_gui_face(event.client_id, 
            self.face, self.tag,
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)
            #self.left, self.top, self.left+(self.right-self.left)*.60, 100)
            #self.left, self.top, self.left+w, self.top+w)

class Ship(Column):
    def __init__(self, ship, tag) -> None:
        super().__init__()
        self.ship = ship
        self.tag = tag
        #self.square = False

    def present(self, sim, event):
        sbs.send_gui_3dship(event.client_id, 
            self.ship, self.tag, 
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)

class GuiControl(Column):
    def __init__(self, content, tag) -> None:
        super().__init__()
        self.tag = tag
        self.content = content
        self.content.tag_prefix = tag
        self.value=""

    def present(self, sim, event):
        self.content.present(sim, event)
        #sbs.send_gui_3dship(event.client_id, 
        #    self.ship, self.tag, 
        #    self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)
    def on_message(self, sim, event):
        self.content.on_message(sim,event)
        self.value = self.content.get_value()
        #return super().on_message(sim, event)

    def set_bounds(self, bounds) -> None:
        super().set_bounds(bounds)
        self.content.left = self.bounds.left
        self.content.top = self.bounds.top
        self.content.right = self.bounds.right
        self.content.bottom = self.bounds.bottom
        self.content.gui_state = ""



class Layout:
    def __init__(self, rows = None, 
                left=0, top=0, right=100, bottom=100,
                left_pixels=False, top_pixels=False, right_pixels=False, bottom_pixels=False) -> None:
        self.rows = rows if rows else []
        self.aspect_ratio = sbs.get_screen_size()
        self.set_bounds(Bounds(left,top,right,bottom))
        self.default_height = None
        self.default_width = None
        self.padding = None

    def set_bounds(self, bounds):
        self.bounds = bounds

       
    def set_row_height(self, height):
        self.default_height = height

    def set_col_width(self, width):
        self.default_width = width

    def add(self, row:Row):
        self.rows.append(row)

    def calc(self):
        
        if len(self.rows):
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
                    bounds = Bounds(col_left,0,0,0)
                    bounds.top = top
                    bounds.bottom = top+row_height
                    if col.square:
                        bounds.right = bounds.left + square_width
                        print(f"SW {square_width} SH {square_height}")
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
                    col.set_bounds(bounds)
                top += row_height

    def present(self, sim, event):
        row:Row
        for row in self.rows:
            row.present(sim,event)
    
    def on_message(self, sim, event):
        row:Row
        for row in self.rows:
            row.on_message(sim,event)
        


class LayoutPage(Page):
    def __init__(self) -> None:
        super().__init__()
        self.gui_state = 'repaint'
        self.layout = Layout()
        

    def present(self, sim, event):
        """ Present the gui """

        sz = sbs.get_screen_size()
        if sz is not None and sz.y != 0:
            aspect_ratio = sbs.get_screen_size()
            if self.layout.aspect_ratio != aspect_ratio:
                self.layout.aspect_ratio = aspect_ratio
                self.layout.calc()
                self.gui_state = 'repaint'

        
        match self.gui_state:
            case  "repaint":
                sbs.send_gui_clear(event.client_id)
                # Setting this to a state we don't process
                # keeps the existing GUI displayed
                self.gui_state = "presenting"
                self.layout.present(sim,event)
                


