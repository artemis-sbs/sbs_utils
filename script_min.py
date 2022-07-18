from sbs_utils.handlerhooks import *
from sbs_utils.playership import PlayerShip
from sbs_utils.gui import Page
import sbs


class GuiMain(Page):
    def present(self, sim, CID):
        sbs.send_gui_clear(CID)
        sbs.send_gui_text(0, f"Mission start", "text", 25, 30, 99, 90)
        sbs.send_gui_button(CID, "Start", "start", 80,90,99,99)

    def on_message(self, sim, message_tag, clientID):
        if message_tag == 'start':
            Mission.start(sim)

class Mission:
    def start(sim):
        sbs.create_new_sim()
        sbs.resume_sim()

        PlayerShip().spawn(sim, 0,0,0, "Artemis", "tsn", "Battle Cruiser")
    

Gui.server_start_page_class(GuiMain)
#Gui.client_start_page_class(GuiMain)



