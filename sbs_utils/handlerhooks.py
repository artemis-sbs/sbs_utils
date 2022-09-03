from .damagedispatcher import DamageDispatcher
from .consoledispatcher import ConsoleDispatcher
from .tickdispatcher import TickDispatcher
from .gui import Gui


########################################################################################################
def  HandleEvent(sim, event):
    # print(f"""tag: {event.tag}
    #     sub_tag: {event.sub_tag}
    #     par: {event.parent_id}
    #     origin: {event.origin_id} 
    #     sel: {event.selected_id} 
    #     client_id: {event.parent_id}

    #     """)

    match(event.tag):
        
        case "damage":
            DamageDispatcher.dispatch_damage(sim,event)

        case "client_connect":
            Gui.add_client(sim, event)

        case "select_space_object":
            ConsoleDispatcher.dispatch_select(sim, event)

        case "press_comms_button":
            ConsoleDispatcher.dispatch_message(sim, event, "comms_targetUID")

        case "gui_message":
            Gui.on_message(sim, event)

        case "grid_object":
            pass

        case _:
            print (f"Unhandled event {event.tag}")
        

#	client_id"
#	parent_id"
#	origin_id"
#	selected_id"
#	tag"
#	sub_tag"
#	value_tag"
#	source_point"
#	event_time"
#	sub_float"


def HandlePresentGUI(sim):
    Gui.present(sim, None)

def  HandleSimulationTick(sim):
    TickDispatcher.dispatch_tick(sim)


