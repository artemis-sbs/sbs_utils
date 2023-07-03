from ..gui import Page
import sbs
from ..spaceobject import SpaceObject
from ..tickdispatcher import TickDispatcher


class StartPage(Page):
    count = 0
    def __init__(self, description, callback) -> None:
        self.gui_state = 'options'
        self.desc = description
        self.callback = callback

    def present(self, sim, event):
        CID = event.client_id

        sbs.send_gui_clear(CID)
        sbs.send_gui_text(
                    CID,  "text", self.desc, 25, 30, 99, 90)
        
        sbs.send_gui_button(CID, "start", "text: Start", 80,90, 99,99)
        

    def on_message(self, sim, event):
        if event.sub_tag == 'start':
            self.callback(sim, event)
        

class ClientSelectPage(Page):
    count = 0
    def __init__(self) -> None:
        self.state = "choose"
        self.console = "Helm"
        self.player_id = None
        self.console_name = "normal_helm" 
        self.widget_list =  "3dview^2dview^helm_movement^throttle^request_dock^shield_control^ship_data^text_waterfall^main_screen_control"
        self.player_count = 0

    def present(self, sim, event):
        CID = event.client_id

        players = SpaceObject.get_role_objects("__PLAYER__")
        if self.player_count != len(players):
           self.state == "choose"
           self.player_count == len(players)

        if self.state == "choose":
            sbs.send_gui_clear(CID)
            sbs.send_gui_clear(event.client_id)
            sbs.send_client_widget_list(event.client_id, "","")
            i = 0
            for console in ["Helm", "Weapons", "Science", "Engineering", "Comms", "Main Screen"]:
                sbs.send_gui_checkbox(CID, console, f"text: {console};state:{'on' if console==self.console else 'off'}", 80,75-i*5, 99,79-i*5)
                i+=1

            i = 0
            for player in players:
                name = player.name
                if self.player_id is None:
                    self.player_id = player.id
                sbs.send_gui_checkbox(CID, str(player.id), f"text:{name};state:{'on' if self.player_id == player.id else 'off'}", 20,75-i*5, 39,79-i*5)
                i+=1

            if self.player_id is not None:
                sbs.send_gui_button(CID, "select", "text:Select", 80,95-i*5, 99,99-i*5)
            self.state = "skip"
            
        

    def on_message(self, sim, event):

        match event.sub_tag:
            case "Helm":
                self.console_name = "normal_helm" 
                self.console = event.sub_tag
                self.widget_list =  "2dview^helm_movement^throttle^request_dock^shield_control^ship_data^text_waterfall^main_screen_control"
            case "Weapons":
                self.console_name = "normal_weap"
                self.console = event.sub_tag
                self.widget_list = "2dview^weapon_control^weap_beam_freq^ship_data^shield_control^text_waterfall^main_screen_control"
            case "Science":
                self.console_name = "normal_sci" 
                self.console = event.sub_tag
                self.widget_list = "science_2d_view^ship_data^text_waterfall^science_data^science_sorted_list"
            case "Engineering":
                self.console_name = "normal_engi" 
                self.console = event.sub_tag
                self.widget_list = "ship_internal_view^grid_object_list^grid_face^grid_control^text_waterfall^eng_heat_controls^eng_power_controls^ship_data"
            case "Comms":
                self.console_name = "normal_comm" 
                self.console = event.sub_tag
                self.widget_list = "text_waterfall^comms_waterfall^comms_control^comms_face^comms_sorted_list^ship_data^red_alert"
            case "Main Screen":
                self.console_name = "normal_main" 
                self.console = event.sub_tag
                self.widget_list = "3dview^ship_data^text_waterfall"
            # This is the client_change event being handled
            case "change_console":
                self.state = "choose"
                self.present(sim, event)
            case "select":
                sbs.send_gui_clear(event.client_id)
                sbs.send_client_widget_list(event.client_id, self.console_name, self.widget_list)
                self.state = "main"
                self.present(sim, event)
                sbs.assign_client_to_ship(event.client_id, self.player_id)
                return
            case _:
                self.player_id = int(event.sub_tag)

        self.state = "choose"
        self.present(sim, event)

    def on_event(self, sim, event):
        if event.tag == "client_change":
            if event.sub_tag == "change_console":
                self.state = "choose"
                self.present(sim, event)
        elif event.tag == "x_sim_resume":
            self.state = "choose"
            self.present(sim, event)


