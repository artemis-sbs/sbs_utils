from ..gui import Page
import sbs

class Row:
    def __init__(self, cols=None, width=0, height=0) -> None:
        self.height = height
        self.width = width
        self.columns = cols if cols else []
        self.left=0
        self.top=0

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

class Column:
    def __init__(self, left=0, top=0, right=0, bottom=0) -> None:
        self.left=left
        self.top=top
        self.right=right
        self.bottom=bottom
        self.square = False

    def layout(self, height=0, left=0, top=0, right=0, bottom=0) -> None:
        self.left=left
        self.top=top
        self.right=right
        self.bottom=bottom

    
class Text(Column):
    def __init__(self, message, tag) -> None:
        super().__init__()
        self.message = message
        self.tag = tag
        #self.color = color

    def present(self, sim, event):
        sbs.send_gui_text(event.client_id, 
            self.message, self.tag, 
            self.left, self.top, self.right, self.bottom)

class Button(Column):
    def __init__(self, message, tag) -> None:
        super().__init__()
        self.message = message
        self.tag = tag
        #self.color = color

    def present(self, sim, event):
        sbs.send_gui_button(event.client_id, 
            self.message, self.tag, 
            self.left, self.top, self.right, self.bottom)

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
            self.left, self.top, self.right, self.bottom)

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
            self.left, self.top, self.right, self.bottom)


class Separate(Column):
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
            self.left, self.top, self.right, self.bottom)
            #self.left, self.top, self.left+(self.right-self.left)*.60, 100)
            #self.left, self.top, self.left+w, self.top+w)

class Ship(Column):
    def __init__(self, ship, tag) -> None:
        super().__init__()
        self.ship = ship
        self.tag = tag

    def present(self, sim, event):
        sbs.send_gui_3dship(event.client_id, 
            self.ship, self.tag, 
            self.left, self.top, self.right, self.bottom)


class Layout:
    def __init__(self, rows = None, left=0, top=0, right=100, bottom=100) -> None:
        self.rows = rows if rows else []
        self.aspect_ratio = sbs.get_screen_size()
        self.set_size(left,top,right,bottom)

    def set_size(self, left=0, top=0, right=100, bottom=100):
        self.left = left
        self.top = top
        self.width = right-left
        self.height = bottom-top
        



    def add(self, row:Row):
        self.rows.append(row)

    def calc(self):
        if len(self.rows):
            row_height = self.height / len(self.rows)
            row : Row
            left = self.left
            top = self.top
            for row in self.rows:
                row.height = row_height
                row.width = self.width
                row.left = left
                row.top = top
                squares = 0

                col: Column
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

                if len(row.columns) != squares:
                    rect_col_width = (row.width-(squares*square_width))/(len(row.columns)-squares)
                    if square_width> rect_col_width:
                        square_width= rect_col_width
                        rect_col_width = (row.width-(squares*square_width))/(len(row.columns)-squares)
                else:
                    rect_col_width = square_width

                # bit of a hack to make sure face aren't the biggest things
                

                col_left = left
                for col in row.columns:
                    col.left = col_left
                    col.top = top
                    col.bottom = top+row_height
                    if col.square:
                        col.right = col_left + square_width
                        col.bottom = top+square_height
                    else:
                        col.right = col_left+rect_col_width
                    col_left = col.right

                top += row_height

    def present(self, sim, event):
        row:Row
        for row in self.rows:
            row.present(sim,event)
        


class LayoutPage(Page):
    def __init__(self) -> None:
        super().__init__()
        self.gui_state = 'repaint'
        self.layout = Layout()
        

    def present(self, sim, event):
        """ Present the gui """

        sz = sbs.get_screen_size()
        if sz is not None and sz.y != 0:
            aspect_ratio = sz.x/sz.y
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
                


