from ..gui import Page
import sbs


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
                    CID, self.desc, "text", 25, 30, 99, 90)
        
        sbs.send_gui_button(CID, "Start", "start", 80,90, 99,99)
        

    def on_message(self, sim, event):
        if event.sub_tag == 'start':
            self.callback(sim, event)
        

class ClientSelectPage(Page):
    count = 0
    def __init__(self) -> None:
        self.state = "choose"

    def present(self, sim, event):
        CID = event.client_id

        if self.state == "choose":
            sbs.send_gui_clear(CID)
            sbs.send_gui_clear(event.client_id)
            sbs.send_client_widget_list(event.client_id, "","")
            i = 0
            for console in ["Helm", "Weapons", "Science", "Engineering", "Comms", "Main Screen"]:
                sbs.send_gui_button(CID, console, console, 80,95-i*5, 99,99-i*5)
                i+=1
        

    def on_message(self, sim, event):
        console_name = ""
        widget_list = ""
        match event.sub_tag:
            case "Helm":
                console_name = "normal_helm" 
                widget_list =  "3dview^2dview^helm_movement^throttle^request_dock^shield_control^ship_data^text_waterfall^main_screen_control"
            case "Weapons":
                console_name = "normal_weap"
                widget_list = "2dview^weapon_control^ship_data^shield_control^text_waterfall^main_screen_control"
            case "Science":
                console_name = "normal_sci" 
                widget_list = "science_2d_view^ship_data^text_waterfall^science_data^object_sorted_list"
            case "Engineering":
                console_name = "normal_engi" 
                widget_list = "ship_internal_view^grid_object_list^text_waterfall^eng_heat_controls^eng_power_controls^ship_data"
            case "Comms":
                console_name = "normal_comm" 
                widget_list = "text_waterfall^comms_waterfall^comms_control^comms_face^object_sorted_list^ship_data"
            case "Main Screen":
                console_name = "normal_main" 
                widget_list = "3dview^ship_data^text_waterfall"
            # This is the client_change event being handled
            case "change_console":
                self.state = "choose"
                self.present(sim, event)
                

        if event.tag == "gui_message":
            sbs.send_gui_clear(event.client_id)
            sbs.send_client_widget_list(event.client_id, console_name, widget_list)
            self.state = "main"

    def on_event(self, sim, event):
        match event.sub_tag:
            # This is the client_change event being handled
            case "change_console":
                self.state = "choose"
                self.present(sim, event)
                

        

