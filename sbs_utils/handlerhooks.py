from lib.sbs_utils.damagedispatcher import DamageDispatcher
from lib.sbs_utils.consoledispatcher import ConsoleDispatcher
from lib.sbs_utils.tickdispatcher import TickDispatcher

def  HandleSimulationTick(sim):
    TickDispatcher.dispatch_tick(sim)

def HandleClientConnect(sim, clientID):
    pass

def HandleDamageEvent(sim, damage_event):
    DamageDispatcher.dispatch_damage(sim,damage_event)

########################################################################################################
def HandleConsoleObjectSelection(sim, console, obj_selected_id, ship_id):
    ConsoleDispatcher.dispatch_select(sim,ship_id, console,obj_selected_id)
########################################################################################################
def HandleCommsButton(sim, button_tag, ship_id, obj_selected_id):
    ConsoleDispatcher.dispatch_comms_message(sim, button_tag, ship_id, obj_selected_id)

