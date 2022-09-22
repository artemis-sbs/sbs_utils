from ..gui import Page
import sbs
from ctypes import byref, windll
from ctypes import wintypes, Structure, windll, byref, c_int16, \
            c_int, c_long, WINFUNCTYPE


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

    def present(self, sim, client_id):
        col:Column
        for col in self.columns:
            col.present(sim,client_id)

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

    def present(self, sim, client_id):
        sbs.send_gui_text(client_id, 
            self.message, self.tag, 
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

    def present(self, sim, client_id):
        sbs.send_gui_face(client_id, 
            self.face, self.tag,
            self.left, self.top, self.right, self.bottom)
            #self.left, self.top, self.left+(self.right-self.left)*.60, 100)
            #self.left, self.top, self.left+w, self.top+w)

class Ship(Column):
    def __init__(self, ship, tag) -> None:
        super().__init__()
        self.ship = ship
        self.tag = tag
        self.square = True

    def present(self, sim, client_id):
        sbs.send_gui_3dship(client_id, 
            self.ship, self.tag, 
            self.left, self.top, self.right, self.bottom)



class Layout:
    def __init__(self, rows = None, left=0, top=0, width=100, height=100) -> None:
        self.rows = rows if rows else []
        self.left = left
        self.top = top
        self.width = width
        self.height = height


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

                screen_width  = 1920 #1029
                screen_height = 1010 #800-30
                screen_width  = 1029
                screen_height = 800-30

                col: Column
                for col in row.columns:
                    squares += 1 if col.square else 0
                # Set width 
                square_width = (screen_height/screen_width)*row.width/len(row.columns) 
                if row.height < square_width:
                    square_width = row.height
                rect_col_width = (row.width-(squares*square_width))/(len(row.columns)-squares)

                col_left = left
                for col in row.columns:
                    col.left = col_left
                    col.top = top
                    col.bottom = top+row_height
                    if col.square:
                        col.right = col_left + square_width
                        col.bottom = top+square_width
                    else:
                        col.right = col_left+rect_col_width
                    col_left = col.right

                top += row_height

    def present(self, sim, client_id):
        row:Row
        for row in self.rows:
            row.present(sim,client_id)
        


class LayoutPage(Page):
    def __init__(self) -> None:
        super().__init__()
        self.gui_state = 'repaint'
        self.layout = Layout()

    def present(self, sim, event):
        match self.gui_state:
            case  "repaint":
                sbs.send_gui_clear(event.client_id)
                # Setting this to a state we don't process
                # keeps the existing GUI displayed
                self.gui_state = "presenting"
                self.layout.present(sim,event.client_id)
                


