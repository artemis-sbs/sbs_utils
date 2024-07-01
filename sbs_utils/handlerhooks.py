from .griddispatcher import GridDispatcher
from .damagedispatcher import DamageDispatcher, CollisionDispatcher
from .consoledispatcher import ConsoleDispatcher
from .tickdispatcher import TickDispatcher
from .lifetimedispatcher import LifetimeDispatcher
from .procedural.inventory import get_inventory_value, set_inventory_value

from .gui import Gui, Page
import sbs
import traceback
from . import faces
from .fs import get_mission_name, get_startup_mission_name
from .vec import Vec3

from .agent import Agent
from .helpers import FrameContext, Context, format_exception
import time


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
def print_event(event):
    print(f"client ID {event.client_id}")
    print(f"Parent ID {event.parent_id}")
    print(f"Origin ID {event.origin_id}")
    print(f"Selected ID {event.selected_id}")
    print(f"Tag {event.tag}")
    print(f"Sub Tag {event.sub_tag}")
    print(f"Sub Float {event.sub_float}")
    print(f"Value Tag {event.value_tag}")
    print(f"Extra Tag {event.extra_tag}")
    print(f"Extra Extra Tag {event.extra_tag}")
    print(f"Point {event.source_point.x}  {event.source_point.y} {event.source_point.z}")


class ErrorPage(Page):
    def __init__(self, msg) -> None:
        self.gui_state = 'show'
        self.message = msg

    def present(self, event):
        match self.gui_state:
            case  "sim_on":
                self.gui_state = "blank"
                sbs.send_gui_clear(event.client_id, "")
                sbs.send_gui_complete(event.client_id, "")

            case  "show":
                sbs.send_gui_clear(event.client_id, "")
                # Setting this to a state we don't process
                # keeps the existing GUI displayed
                self.gui_state = "presenting"
                print(self.message)
                self.message = self.message.replace(",", ".")
                self.message = self.message.replace(";", ".")
                self.message = self.message.replace(":", ".")
                sbs.send_gui_text(
                    event.client_id,"", "text", f"text:sbs_utils runtime error^{self.message};", 0, 0, 80, 95)
                
                # sbs.send_gui_button(event.client_id, "back", "text:pause mission;", 0, 80, 20, 94)
                sbs.send_gui_button(event.client_id,"", "resume", "text:Resume Mission;", 25, 80, 45, 99)
                sbs.send_gui_button(event.client_id,"", "rerun", "text:Rerun Mission;", 50, 80, 70, 99)
                sbs.send_gui_button(event.client_id,"", "startup", "text:run startup Mission;", 75, 80, 99, 99)
                sbs.send_gui_complete(event.client_id, "")

    def on_message(self, event):
        match event.sub_tag:
            # case "back":
            #     self.gui_state = "sim_on"
            #     self.present(event)

            #     Gui.pop(event.client_id)
            #     FrameContext.context.sbs.pause_sim()

            case "resume":
                self.gui_state = "sim_on"
                self.present(event)

                Gui.pop(event.client_id)
                FrameContext.context.sbs.resume_sim()

            case "rerun":
                self.gui_state = "sim_on"
                self.present(event)

                Gui.pop(event.client_id)
                start_mission = get_mission_name()
                sbs.run_next_mission(start_mission)

            case "startup":
                self.gui_state = "sim_on"
                self.present(event)

                Gui.pop(event.client_id)
                start_mission = get_startup_mission_name()
                if start_mission is not None:
                    sbs.run_next_mission(start_mission)


def cosmos_event_handler(sim, event):
    try:
        t = time.process_time()
        # Allow guis more direct access to events
        # e.g. Mast Story Page, Clients change
        ctx = Context(sim, sbs, event)
        FrameContext.context = ctx
        # gui = Gui.clients.get(event.client_id):
        # if gui is not None:
        #     FrameContext.page = gui.page

        Agent.SHARED.set_inventory_value("sim", sim)
        
        #print(f"{event.sub_tag}")
        #print_event(event)
        match(event.tag):
            #	value_tag"
            #	source_point"
            #	event_time"
            #    print(f"{event.parent_id}")
            #     print(f"{event.origin_id}")
            #     print(f"{event.selected_id}")
            #     print(f"{event.sub_tag}")
            #     print(f"{event.sub_float}")
            # case "present_gui":
            #     Agent.SHARED.set_inventory_value("SIM_STATE", "sim_paused")
            #     Gui.present(event)

            case "screen_size":
                # print(f"{event.client_id}")
                #print(f"Point {event.source_point.x}  {event.source_point.y} {event.source_point.z}")
                # gui = Gui.clients.get(event.client_id)
                # if gui is not None:
                #     gui.present(Context(sim, sbs, None), event)
                ar = Vec3(event.source_point.x, event.source_point.y,event.source_point.z)

                FrameContext.aspect_ratios[event.client_id] = ar
                Gui.on_event(event)
            case "client_change":
                if event.sub_tag == "change_console":
                    Gui.on_event(event)

            case "main_screen_change":
                Gui.on_event(event)
            
            case "mission_tick":
                # Run Guis, tick task
                Gui.present(event)
                #
                # set the simulation state variable
                #
                # either sim_paused, or sim_running
                #
                Agent.SHARED.set_inventory_value("SIM_STATE", event.sub_tag)
                #Agent.SHARED.set_inventory_value("SIM_STATE", "sim_running")
                # Give a few ticks
                for x in range(5):
                    TickDispatcher.dispatch_tick()
                # after tick task handle any lifetime events
                LifetimeDispatcher.dispatch_spawn()
 
            case "damage":
                #print_event(event)
                DamageDispatcher.dispatch_damage(event)
                LifetimeDispatcher.dispatch_damage(event)

            case "red_alert":
                # get_inventory_value(event.client_id, "assigned_ship", None)
                ship_id = sbs.get_ship_of_client(event.client_id) 
                if ship_id is not None:
                    set_inventory_value(ship_id, "red_alert", event.value_tag == "on")
                


            case "player_internal_damage":
                DamageDispatcher.dispatch_internal(event)

            case "heat_critical_damage":
                #print_event(event)
                DamageDispatcher.dispatch_heat(event)

            case "passive_collision":
                print(f"TDO Handler hooks page{event.client_id} {FrameContext.page}")
                print(f"TDO Handler hooks task{event.client_id} {FrameContext.task}")

                CollisionDispatcher.dispatch_collision(event)

            case "client_connect":
                Gui.add_client(event)

            case "select_space_object":
                # print_event(event)
                handled = ConsoleDispatcher.dispatch_select(event)
                if not handled and "comms_sorted_list" == event.value_tag:
                    face = faces.get_face(event.selected_id)
                    so = Agent.get(event.selected_id)
                    comms_id = "static"
                    if so:
                        comms_id = so.comms_id#(sim)
                    sbs.send_comms_selection_info(event.origin_id, face, "green", comms_id)

            case "press_comms_button":
                ConsoleDispatcher.dispatch_message(event, "comms_target_UID")

            case "science_scan_complete":
                #print_event(event)
                ConsoleDispatcher.dispatch_message(event, "science_target_UID")

            case "gui_message":
                #print_event(event)
                Gui.on_message(event)

            case "grid_object":
                GridDispatcher.dispatch_grid_event(event)
            case "grid_object_selection":
                #print_event(event)
                ConsoleDispatcher.dispatch_select(event)
            case "press_grid_button":
                ConsoleDispatcher.dispatch_message(event, "grid_selected_UID")
                
            case "grid_point_selection":
                #print_event(event)
                GridDispatcher.dispatch_grid_event(event)

            case "sim_paused":
                Gui.send_custom_event("x_sim_paused")
            case "sim_unpaused":
                Gui.send_custom_event("x_sim_resume")
            case "fighter_requests_dock":
                LifetimeDispatcher.dispatch_dock(event)
        
            case _:
                print (f"Unhandled event {event.client_id} {event.tag} {event.sub_tag}")
        
    except BaseException as err:
        sbs.pause_sim()

        
        text_err = format_exception("", "SBS Utils Hook level Runtime Error:")
        text_err += traceback.format_exc()
        text_err = text_err.replace(chr(94), "")
        
        Gui.push(0, ErrorPage(text_err))
    
    Agent.SHARED.set_inventory_value("sim", None)
    Agent.context = None
    
    et = time.process_time() - t
    if et > 0.03:
        print(f"Elapsed time: {et} {event.tag}-{event.sub_tag}")


