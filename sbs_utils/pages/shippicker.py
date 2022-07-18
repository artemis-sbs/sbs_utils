from ..gui import Page, Gui
from .. import layout as layout
import sbs
from .. import faces as faces
import json
from .. import fs

class ShipPicker(Page):
    
    def __init__(self) -> None:
        self.gui_state = "blank"
        self.cur = 0
        data = fs.get_ship_data()
        
        self.test = fs.get_artemis_data_dir()

        if data is None:
            self.ships = None
        else:
            self.ships = data["#ship-list"]
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
                    0, f"{self.test}", "error", 25, 25, 99, 29)
            return

        ship = self.ships[self.cur]

        sbs.send_gui_clear(CID)
        sbs.send_gui_text(
                    0, f"{ship['name']}", "title", 25, 25, 99, 29)
        l1 = layout.wrap(25, 20, 19, 4,col=3)
        
        sbs.send_gui_button(CID, "prev", "prev", *next(l1))
        sbs.send_gui_button(CID, "next", "next", *next(l1))

        w = layout.wrap(99, 99, 19, 4,col=1, v_dir=-1, h_dir=-1)
        sbs.send_gui_button(CID, "Back", "back", *next(w))
        

        self.gui_state = "presenting"


    def on_message(self, sim, message_tag, clientID):
        if message_tag == 'back':
            Gui.pop(sim,clientID)
        match message_tag:
            case "prev":
                if self.cur > 0:
                    self.cur -= 1

            case "next":
                if self.cur < len(self.ships):
                    self.cur += 1
            # catch all for switching race
            case _:
                self.gui_state = message_tag
                self.present(sim, clientID)
