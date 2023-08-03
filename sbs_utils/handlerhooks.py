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
                ctx.sbs.send_gui_complete(event.client_id)

            case  "show":
                ctx.sbs.send_gui_clear(event.client_id)
                # Setting this to a state we don't process
                # keeps the existing GUI displayed
                self.gui_state = "presenting"
                #print(self.message)
                self.message = self.message.replace(",", ".")
                ctx.sbs.send_gui_text(
                    event.client_id, "text", f"text:scripting error^{self.message}", 0, 0, 80, 95)
                ctx.sbs.send_gui_button(event.client_id, "back", "text:back", 80, 90, 99, 94)
                ctx.sbs.send_gui_button(event.client_id, "resume", "text:Resume Mission", 80, 95, 99, 99)
                ctx.sbs.send_gui_complete(event.client_id)

    def on_message(self, ctx, event):
        match event.sub_tag:
            case "back":
                Gui.pop(ctx, event.client_id)

            case "resume":
                Gui.pop(ctx, event.client_id)
                ctx.sbs.resume_sim()

def cosmos_event_handler(sim, event):
    try:
        t = time.process_time()
        # Allow guis more direct access to events
        # e.g. Mast Story Page, Clients change
        ctx = Context(sim, sbs, None)
        

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
                Gui.present(ctx, event)

            case "screen_size":
                # print(f"{event.client_id}")
                # #print(f"Point {event.source_point.x}  {event.source_point.y} {event.source_point.z}")
                # gui = Gui.clients.get(event.client_id)
                # if gui is not None:
                #     gui.present(Context(sim, sbs, None), event)
                Gui.on_event(ctx, event)
            case "client_change":
                if event.sub_tag == "change_console":
                    Gui.on_event(ctx, event)
            
            case "mission_tick":
                # Run Guis, tick task
                Gui.present(ctx, event)
                TickDispatcher.dispatch_tick(ctx)
                # after tick task handle any lifetime events
                LifetimeDispatcher.dispatch_spawn(ctx)
 
            case "damage":
                DamageDispatcher.dispatch_damage(ctx,event)
                LifetimeDispatcher.dispatch_damage(ctx, event)

            case "player_internal_damage":
                DamageDispatcher.dispatch_internal(ctx,event)
                

            case "client_connect":
                Gui.add_client(ctx, event)

            case "select_space_object":
                # print(f"Parent ID{event.parent_id}")
                #print(f"Origin ID {event.origin_id}")
                #print(f"Selected ID {event.selected_id}")
                #print(f"Sub Tag {event.sub_tag}")
                # print(f"Sub Float {event.sub_float}")
                #print(f"Value Tag {event.value_tag}")
                # print(f"Point {event.source_point.x}  {event.source_point.y} {event.source_point.z}")

                handled = ConsoleDispatcher.dispatch_select(ctx, event)
                if not handled and "comm" in event.sub_tag:
                    face = faces.get_face(event.selected_id)
                    so = SpaceObject.get(event.selected_id)
                    comms_id = "static"
                    if so:
                        comms_id = so.comms_id#(sim)
                    sbs.send_comms_selection_info(event.origin_id, face, "green", comms_id)

            case "press_comms_button":
                ConsoleDispatcher.dispatch_message(ctx, event, "comms_target_UID")

            case "science_scan_complete":
                ConsoleDispatcher.dispatch_message(ctx, event, "science_target_UID")

            case "gui_message":
                Gui.on_message(ctx, event)

            case "grid_object":
                GridDispatcher.dispatch_grid_event(ctx,event)
            case "grid_object_selection":
                ConsoleDispatcher.dispatch_select(ctx, event)
            case "press_grid_button":
                ConsoleDispatcher.dispatch_message(ctx, event, "grid_selected_UID")
                
            case "grid_point_selection":
                GridDispatcher.dispatch_grid_event(ctx,event)

            case "sim_paused":
                Gui.send_custom_event(ctx, "x_sim_paused")
            case "sim_unpaused":
                Gui.send_custom_event(ctx, "x_sim_resume")
        
            case _:
                print (f"Unhandled event {event.client_id} {event.tag} {event.sub_tag}")

    except BaseException as err:
        sbs.pause_sim()

        text_err = traceback.format_exc()
        text_err = text_err.replace(chr(94), "")
        Gui.push(ctx, 0, ErrorPage(text_err))
    et = time.process_time() - t
    if et > 0.03:
        print(f"Elapsed time: {et} {event.tag}-{event.sub_tag}")


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

