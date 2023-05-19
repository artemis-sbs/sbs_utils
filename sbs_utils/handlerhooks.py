from .griddispatcher import GridDispatcher
from .damagedispatcher import DamageDispatcher
from .consoledispatcher import ConsoleDispatcher
from .tickdispatcher import TickDispatcher
from .lifetimedispatcher import LifetimeDispatcher

from .gui import Gui, Page, Context
import sbs
import traceback
from . import faces
from .spaceobject import SpaceObject
import time


class ErrorPage(Page):
    def __init__(self, msg) -> None:
        self.gui_state = 'show'
        self.message = msg

    def present(self, ctx, event):
        match self.gui_state:
            case  "sim_on":
                self.gui_state = "blank"
                ctx.sbs.send_gui_clear(event.client_id)

            case  "show":
                ctx.sbs.send_gui_clear(event.client_id)
                # Setting this to a state we don't process
                # keeps the existing GUI displayed
                self.gui_state = "presenting"
                print(self.message)
                self.message = self.message.replace(",", ".")
                ctx.sbs.send_gui_text(
                    event.client_id, "text", f"text:scripting error^{self.message}", 0, 0, 80, 95)
                ctx.sbs.send_gui_button(event.client_id, "back", "text:back", 80, 90, 99, 94)
                ctx.sbs.send_gui_button(event.client_id, "resume", "text:Resume Mission", 80, 95, 99, 99)

    def on_message(self, ctx, event):
        match event.sub_tag:
            case "back":
                Gui.pop(ctx, event.client_id)

            case "resume":
                Gui.pop(ctx, event.client_id)
                ctx.sbs.resume_sim()

def cosmos_event_handler(sim, event):
    try:
        #t = time.process_time()
        # Allow guis more direct access to events
        # e.g. Mast Story Page, Clients change
        Gui.on_event(Context(sim, sbs, None), event)

        match(event.tag):
            #	value_tag"
            #	source_point"
            #	event_time"
            #    print(f"{event.parent_id}")
            #     print(f"{event.origin_id}")
            #     print(f"{event.selected_id}")
            #     print(f"{event.sub_tag}")
            #     print(f"{event.sub_float}")
            case "present_gui":
                Gui.present(Context(sim, sbs, None), event)
            
            case "mission_tick":
                TickDispatcher.dispatch_tick(Context(sim, sbs, None))
                LifetimeDispatcher.dispatch_spawn(Context(sim, sbs, None))
 
            case "damage":
                DamageDispatcher.dispatch_damage(Context(sim, sbs, None),event)
                LifetimeDispatcher.dispatch_damage(Context(sim, sbs, None), event)

            case "player_internal_damage":
                DamageDispatcher.dispatch_internal(Context(sim, sbs, None),event)
                

            case "client_connect":
                Gui.add_client(Context(sim, sbs, None), event)

            case "select_space_object":
                # print(f"{event.parent_id}")
                # print(f"{event.origin_id}")
                # print(f"{event.selected_id}")
                # print(f"{event.sub_tag}")
                # print(f"{event.sub_float}")
                # print(f"{event.value_tag}")
                handled = ConsoleDispatcher.dispatch_select(Context(sim, sbs, None), event)
                if not handled and "comm" in event.sub_tag:
                    face = faces.get_face(event.selected_id)
                    so = SpaceObject.get(event.selected_id)
                    comms_id = "static"
                    if so:
                        comms_id = so.comms_id#(sim)
                    sbs.send_comms_selection_info(event.origin_id, face, "green", comms_id)

            case "press_comms_button":
                ConsoleDispatcher.dispatch_message(Context(sim, sbs, None), event, "comms_target_UID")

            case "science_scan_complete":
                ConsoleDispatcher.dispatch_message(Context(sim, sbs, None), event, "science_target_UID")

            case "gui_message":
                Gui.on_message(Context(sim, sbs, None), event)

            case "grid_object":
                GridDispatcher.dispatch_grid_event(Context(sim, sbs, None),event)
            case "grid_object_selection":
                ConsoleDispatcher.dispatch_select(Context(sim, sbs, None), event)
            case "press_grid_button":
                ConsoleDispatcher.dispatch_message(Context(sim, sbs, None), event, "grid_selected_UID")
                

            case "grid_point_selection":
                GridDispatcher.dispatch_grid_event(Context(sim, sbs, None),event)

            case "sim_paused":
                Gui.send_custom_event(Context(sim, sbs, None), "x_sim_paused")
            case "sim_unpaused":
                Gui.send_custom_event(Context(sim, sbs, None), "x_sim_resume")
        
            case _:
                print (f"Unhandled event {event.client_id} {event.tag} {event.sub_tag}")
  
    except BaseException as err:
        sbs.pause_sim()

        text_err = traceback.format_exc()
        text_err = text_err.replace(chr(94), "")
        Gui.push(Context(sim, sbs, None), 0, ErrorPage(text_err))
    #et = time.process_time() - t
    #print(f"Elapsed time: {et}")


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

