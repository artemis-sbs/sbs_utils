from .griddispatcher import GridDispatcher
from .damagedispatcher import DamageDispatcher
from .consoledispatcher import ConsoleDispatcher
from .tickdispatcher import TickDispatcher
from .gui import Gui, Page
import sbs
import traceback


class ErrorPage(Page):
    def __init__(self, msg) -> None:
        self.gui_state = 'show'
        self.message = msg

    def present(self, sim, event):
        match self.gui_state:
            case  "sim_on":
                self.gui_state = "blank"
                sbs.send_gui_clear(event.client_id)

            case  "show":
                sbs.send_gui_clear(event.client_id)
                # Setting this to a state we don't process
                # keeps the existing GUI displayed
                self.gui_state = "presenting"
                sbs.send_gui_text(
                    event.client_id, f"scripting error^{self.message}", "text", 25, 30, 99, 90)
                sbs.send_gui_button(event.client_id, "back", "back", 80, 90, 99, 94)
                sbs.send_gui_button(event.client_id, "Resume Mission", "resume", 80, 95, 99, 99)

    def on_message(self, sim, event):
        match event.sub_tag:
            case "back":
                Gui.pop(sim, event.client_id)

            case "resume":
                Gui.pop(sim, event.client_id)
                sbs.resume_sim()

def HandleEvent(sim, event):
    try:
        match(event.tag):



            #	value_tag"
            #	source_point"
            #	event_time"
            #    print(f"{event.parent_id}")
            #     print(f"{event.origin_id}")
            #     print(f"{event.selected_id}")
            #     print(f"{event.sub_tag}")
            #     print(f"{event.sub_float}")
 
            case "damage":
                DamageDispatcher.dispatch_damage(sim,event)

            case "client_connect":
                Gui.add_client(sim, event)

            case "client_change":
                Gui.on_client_change(sim, event)

            case "select_space_object":
                print(f"{event.parent_id}")
                print(f"{event.origin_id}")
                print(f"{event.selected_id}")
                print(f"{event.sub_tag}")
                print(f"{event.sub_float}")

                ConsoleDispatcher.dispatch_select(sim, event)

            case "press_comms_button":
                ConsoleDispatcher.dispatch_message(sim, event, "comms_targetUID")

            case "gui_message":
                Gui.on_message(sim, event)

            case "grid_object":
                GridDispatcher.dispatch_grid_event(sim,event)
            case "grid_object_selection":
                GridDispatcher.dispatch_grid_event(sim,event)

            case "grid_point_selection":
                GridDispatcher.dispatch_grid_event(sim,event)
        
            case _:
                print (f"Unhandled event {event.tag}")
  
    except BaseException as err:
        sbs.pause_sim()

        text_err = traceback.format_exc()
        Gui.push(sim, 0, ErrorPage(text_err))


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
    try:
        Gui.present(sim, None)
    except BaseException as err:
        sbs.pause_sim()
        text_err = traceback.format_exc()
        Gui.push(sim, 0, ErrorPage(text_err))

def  HandleSimulationTick(sim):
    try:
        TickDispatcher.dispatch_tick(sim)
    except BaseException as err:
        sbs.pause_sim()
        text_err = traceback.format_exc()
        Gui.push(sim, 0, ErrorPage(text_err))



