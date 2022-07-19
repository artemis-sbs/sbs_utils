from ..gui import Page, Gui
from .. import layout as layout
import sbs
from .. import faces as faces
import json
from .. import fs

def filter_ship(ship):
    if "hullpoints" in ship:
        return True
    else:
        return False

class ShipPicker(Page):
    
    def __init__(self) -> None:
        self.gui_state = "blank"
        self.cur = 0
        self.test = fs.get_artemis_data_dir()

        data = fs.get_ship_data()
        #data = None
        
        self.ships = None
        if data is None:
            self.ships = None
        else:
            self.test = data
            self.ships = [ a for a in filter(filter_ship, data["#ship-list"] )]

            if self.ships is None:
                self.ships = None


    def present(self, sim, CID):
        if self.gui_state == "presenting":
            return
        if self.ships is None:
            sbs.send_gui_clear(CID)
            #sbs.send_gui_text(
            #        0, f"Error reading ship data", "error", 25, 25, 99, 29)
            sbs.send_gui_text(
                    0, f"Error {self.test}", "error", 25, 25, 99, 99)
            return

        ship = self.ships[self.cur]

        sbs.send_gui_clear(CID)
        sbs.send_gui_text(
                    0, f"Ship: {ship['name']}", "title", 25, 25, 99, 29)
        l1 = layout.wrap(25, 60, 19, 4,col=3)
        
        sbs.send_gui_button(CID, "prev", "prev", *next(l1))
        sbs.send_gui_button(CID, "next", "next", *next(l1))
        sbs.send_gui_3dship(CID, ship['name'], "ship", 30, 30, 58, 58)
     
        

        w = layout.wrap(99, 99, 19, 4,col=1, v_dir=-1, h_dir=-1)
        sbs.send_gui_button(CID, "Back", "back", *next(w))
        

        self.gui_state = "presenting"


    def on_message(self, sim, message_tag, clientID):
        if message_tag == 'back':
            Gui.pop(sim,clientID)
        match message_tag:
            case "prev":
                if self.cur >= 0:
                    self.cur -= 1
                    self.gui_state = "redraw"
                    if self.cur <0:
                        self.cur = len(self.ships)-1
                    self.present(sim, clientID)
                
            case "next":
                if self.cur < len(self.ships):
                    self.cur += 1
                    self.gui_state = "redraw"
                    if self.cur >= len(self.ships):
                        self.cur = 0
                    self.present(sim, clientID)
                
                
            # catch all for switching race
            case _:
                self.gui_state = message_tag
                self.present(sim, clientID)

    def get_selected(self):
        ship = self.ships[self.cur]
        if "name" in ship:
            return ship["name"]
        return "Light Cruiser"