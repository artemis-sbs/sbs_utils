from ...helpers import FrameContext

def gui_activate_console(console):
    """set the console name for the client

    Args:
        console (str): The console name

    """    
    page = FrameContext.page
    if page is None:
        return None
    page.activate_console(console)


def gui_console(console, is_jump=False):
    """Activates a console using the default set of widgets

    Args:
        console (str): The console name

    """    
    page = FrameContext.page
    if page is None:
        return None
    widgets = ""
    match console.lower():
        case "helm":
            console =  "normal_helm"
            if is_jump:
                widgets = "2dview^helm_movement^helm_jump^quick_jump^throttle^request_dock^shield_control^ship_data^text_waterfall^main_screen_control"
            else:
                widgets = "2dview^helm_movement^throttle^request_dock^shield_control^ship_data^text_waterfall^main_screen_control"
        case "weapons":
            console =  "normal_weap"
            widgets = "weapon_2d_view^weapon_control^weap_beam_freq^weap_beam_speed^weap_torp_conversion^ship_data^shield_control^text_waterfall^main_screen_control"
        case "science":
            console =  "normal_sci"
            widgets = "science_2d_view^ship_data^text_waterfall^science_data^science_sorted_list"
        case "engineering":
            console =  "normal_engi"
            widgets = "ship_internal_view^eng_presets^grid_object_list^grid_face^grid_control^text_waterfall^eng_heat_controls^eng_power_controls^ship_data"
        case "comms":
            console =  "normal_comm"
            widgets = "2dview^text_waterfall^comms_waterfall^comms_control^comms_face^comms_sorted_list^ship_data^red_alert"
            #widgets = "2dview^text_waterfall^comms_waterfall^comms_control^comms_face^comms_sorted_list^red_alert"
        case "cinematic":
            console =  "cinematic"
            widgets = "3dview"
        case "mainscreen":
            console =  "normal_main"
            view = page.gui_task.get_variable("MAIN_SCREEN_VIEW", "3d_view")
            if view == "lrs":
                #console =  "normal_main_lrs"
                widgets = "2dview^ship_data^text_waterfall"
            elif view == "tactical":
                #console =  "normal_main_tact"
                widgets = "2dview^ship_data^text_waterfall"
            elif view == "data":
                #console =  "normal_main_data"
                widgets = "ship_internal_view^ship_data^text_waterfall"
            else:
                widgets = "3dview^ship_data^text_waterfall"
        case "cockpit":
            widgets = "3dview^2dview^helm_free_3d^text_waterfall^fighter_control^ship_internal_view^ship_data^grid_face^grid_control"
        

    page.set_widget_list(console, widgets)
