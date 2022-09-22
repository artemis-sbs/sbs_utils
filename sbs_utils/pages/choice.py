from gui import Gui, Page
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

    def add(self, col):
        self.columns.append(col)

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
                col: Column
                for col in row.columns:
                    squares += 1 if col.square else 0
                # Set width 
                rect_col_width = (row.width-(squares*row.height))/(len(row.columns)-squares)
                col_left = left
                for col in row.columns:
                    col.left = col_left
                    col.top = top
                    col.bottom = top+row_height
                    if col.square:
                        col.right = left + row_height
                    else:
                        col.right = left+rect_col_width
                    col_left = col.right
                top += row_height

    def present(self, sim, client_id):
        row:Row
        for row in self.rows:
            row.present(sim,client_id)






class LayoutPage(Page):
    def __init__(self) -> None:
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


class ChoicePage(LayoutPage):
    def __init__(self) -> None:
        super().__init__()

    def choices(self, choices, prev=None, next=None, exit=None):
        self.choices = choices
        self.prev=prev
        self.next=next
        self.exit=exit
        self.layout()
        self.gui_state = 'repaint'

    def countdown(self, time_seconds:int):
        self.countdown = time_seconds
        self.gui_state = 'repaint'

    def on_tick(self, sim):
        pass

    def on_choice(self, sim, choice:str):
        pass

    def present(self, sim, event):
        self.on_tick(sim)
        match self.gui_state:
            case  "repaint":
                sbs.send_gui_clear(event.client_id)
                # Setting this to a state we don't process
                # keeps the existing GUI displayed
                self.gui_state = "presenting"
                sbs.send_gui_text(
                    event.client_id, f"{self.message}", "text", 25, 20, 99, 90)
                sbs.send_gui_button(event.client_id, "back", "back", 80, 90, 99, 94)
                sbs.send_gui_button(event.client_id, "Resume Mission", "resume", 80, 95, 99, 99)

    def on_message(self, sim, event):
        match event.sub_tag:
            case "exit":
                Gui.pop(sim, event.client_id)

            case _:
                self.on_choice(sim, event.sub_tag)


