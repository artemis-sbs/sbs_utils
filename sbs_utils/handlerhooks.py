from .damagedispatcher import DamageDispatcher
from .consoledispatcher import ConsoleDispatcher
from .tickdispatcher import TickDispatcher
from .gui import Gui

# https://drive.google.com/file/d/1JS6KvN-4ahvI4WJsoJq-6Vq_MWl8H812/view?usp=sharing


def HandlePresentGUI(sim):
    Gui.present(sim)

def HandlePresentGUIMessage(sim, message_tag, clientID, data):
    Gui.on_message(sim, message_tag, clientID, data)


def  HandleSimulationTick(sim):
    TickDispatcher.dispatch_tick(sim)

def HandleClientConnect(sim, clientID):
    Gui.add_client(sim,clientID)

def HandleDamageEvent(sim, damage_event):
    DamageDispatcher.dispatch_damage(sim,damage_event)

########################################################################################################
def HandleConsoleObjectSelection(sim, console, obj_selected_id, ship_id):
    ConsoleDispatcher.dispatch_select(sim,ship_id, console,obj_selected_id)
########################################################################################################
def HandleCommsButton(sim, button_tag, ship_id, obj_selected_id):
    ConsoleDispatcher.dispatch_comms_message(sim, button_tag, ship_id, obj_selected_id)

