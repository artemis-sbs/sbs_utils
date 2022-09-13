from sbs_utils.handlerhooks import *
from sbs_utils.objects import PlayerShip, Npc, Terrain
from sbs_utils.tickdispatcher import TickDispatcher

from sbs_utils.gui import Page, Gui
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
        Npc().spawn(sim, -500, 0, 400,
                      "DS 1", "TSN", "Starbase", "behav_station")
        Terrain().spawn_v(sim, 100,0,1000, None, None, f"Asteroid 1", "behav_asteroid")
        
def scatter(sim):
     for v in scatter.line(10, -2000,0,0, 2200,0, 1000,True):
        Terrain().spawn_v(sim, v, None, None, f"Asteroid 1", "behav_asteroid")


class Caravan(Npc):

    def spawn(self, sim, x, y, z, name, side, art_id, behave_id):
        # call the base
        super().spawn(sim, x, y, z, name, side, art_id, behave_id)
        # call think every 5 seconds
        TickDispatcher.do_interval(sim, self.think, 5)

    def think(self, sim, task):
        self.target_closest(sim,'Station', 
            # obj[0] is the id, obj[1] is the SpaceObject
            # sim=sim is how to pass the sim to the lambda
            lambda obj, sim=sim: obj[1].side(sim) == 'TSN', shoot=False )
    

Gui.server_start_page_class(GuiMain)
#Gui.client_start_page_class(GuiMain)



