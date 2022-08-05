from ..gui import Page, Gui
from .. import layout as layout
from ..widgets.shippicker import ShipPicker as WShipPicker
import sbs


class ShipPicker(Page):
    
    def __init__(self) -> None:
        self.gui_state = "blank"
        self.picker1 = WShipPicker(25,25, "pick1:", "Your ship:")
        self.picker2 = WShipPicker(65,25, "pick2:", "Enemy ship:")

    def present(self, sim, CID):
        if self.gui_state == "presenting":
            return

        sbs.send_gui_clear(CID)
        self.picker1.present(sim, CID)
        self.picker2.present(sim, CID)
        sbs.send_gui_button(CID, "Back", "back", 85,95, 99,99)

        self.gui_state = "presenting"


    def on_message(self, sim, message_tag, clientID, data):
        if message_tag == 'back':
            Gui.pop(sim,clientID)
        else:
            self.picker1.on_message(sim,message_tag, clientID, data)
            self.picker2.on_message(sim,message_tag, clientID, data)

    def get_selected(self):
        return [self.picker1.get_selected(), self.picker2.get_selected()]
