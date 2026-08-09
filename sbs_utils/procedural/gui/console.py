from ..inventory import get_inventory_value
from ...helpers import FrameContext
from ..roles import role, all_roles
from ..query import to_set
from ..links import linked_to


def gui_console_clients(path, for_ships=None):
    """Return the set of client IDs that have a specific console type.

    Searches all player ships (or the given ship set) for linked console
    clients whose role matches ``console,{path}``.

    Args:
        path (str): Console path to match, e.g. ``"helm"`` or ``"science"``.
        for_ships (object | None, optional): Agent ID, object, or set of ships
            to search. Defaults to all ``__player__`` ships.

    Returns:
        set: Client IDs that have a console matching ``path``.

    Example:
        helm_clients = gui_console_clients("helm")
    """
    if for_ships is None:
        for_ships = role("__player__")
    else:
        for_ships = to_set(for_ships)
    ret = set()
    for _ship in for_ships:
        ret.update(linked_to(_ship, "consoles") & all_roles(f"console,{path}"))
    return ret



def gui_activate_console(console):
    """Set the current page's active console name.

    Marks the page as running a specific console type, which affects which
    console-specific routes and widgets respond to this client.

    Args:
        console (str): Console name, e.g. ``"helm"``, ``"weapons"``,
            ``"science"``.

    Example:
        gui_activate_console("helm")
    """    
    page = FrameContext.page
    if page is None:
        return None
    page.activate_console(console)


def gui_console(console, is_jump=False):
    """Activate a standard console with its default engine widget layout.

    Sets the engine widget list for the named console using the built-in
    configuration. Supported values: ``"helm"``, ``"weapons"``,
    ``"science"``, ``"engineering"``, ``"comms"``, ``"cinematic"``,
    ``"mainscreen"``, ``"cockpit"``.

    Args:
        console (str): Console name (case-insensitive).
        is_jump (bool, optional): For ``"helm"`` only — include jump-drive
            controls in the widget list. Defaults to ``False``.

    Example:
        gui_console("helm")
        gui_console("helm", is_jump=True)
    """    
    page = FrameContext.page
    if page is None:
        return None
    # NOTE: no console declares `text_waterfall` any more. The engine widget could not
    # be styled from script - its background is fixed and too dark - so it is replaced
    # by gui_log_tail(), a text area the console owns showing the same traffic. See
    # LOG_PANEL_PLAN.md. Removed HERE rather than hidden per console: this is where it
    # was declared, and an engine widget cannot be un-declared once it has been sent.
    widgets = ""
    match console.lower():
        case "helm":
            console =  "normal_helm"
            if is_jump:
                widgets = "2dview^radar_zoom_ctrl^helm_movement^helm_jump^quick_jump^throttle^request_dock^shield_control^ship_data^main_screen_control"
            else:
                widgets = "2dview^radar_zoom_ctrl^helm_movement^throttle^request_dock^shield_control^ship_data^main_screen_control"
        case "weapons":
            console =  "normal_weap"
            widgets = "weapon_2d_view^radar_zoom_ctrl^weapon_control^weap_beam_freq^weap_beam_speed^weap_torp_conversion^ship_data^shield_control^main_screen_control"
        case "science":
            console =  "normal_sci"
            widgets = "science_2d_view^radar_zoom_ctrl^ship_data^science_data_freq^science_data_tabs^science_data^science_sorted_list"
        case "engineering":
            console =  "normal_engi"
            widgets = "ship_internal_view^eng_presets^grid_object_list^grid_face^grid_control^eng_heat_controls^eng_power_controls^ship_data"
        case "comms":
            console =  "normal_comm"
            widgets = "comms_2d_view^radar_zoom_ctrl^comms_waterfall^comms_control^comms_face^comms_sorted_list^ship_data^red_alert"
            #widgets = "2dview^comms_waterfall^comms_control^comms_face^comms_sorted_list^red_alert"
        case "cinematic":
            console =  "cinematic"
            widgets = "3dview"
        case "mainscreen":
            console =  "normal_main"
            # view = page.gui_task.get_variable("MAIN_SCREEN_VIEW", "3d_view")
            # NOT get_ship_of_client: while a console is driving this screen ("on
            # screen", VIEWSCREEN_PLAN.md) the client is ASSIGNED to the SUBJECT - the
            # engine only honors a camera change when the console and the lens ride the
            # same object - so that call answers with the enemy being filmed, and this
            # would pick its widget list from the enemy's main-screen state. Local
            # import: viewscreen reaches back into this package.
            from .viewscreen import viewscreen_home_ship
            ship_id = viewscreen_home_ship(FrameContext.client_id)
            view = get_inventory_value(ship_id, "MAIN_SCREEN_VIEW", "3d_view")
            if view == "lrs":
                #console =  "normal_main_lrs"
                widgets = "2dview^ship_data"
            elif view == "tactical":
                #console =  "normal_main_tact"
                widgets = "2dview^ship_data"
            elif view == "data":
                #console =  "normal_main_data"
                widgets = "ship_internal_view^ship_data"
            else:
                widgets = "3dview^ship_data"
        case "cockpit":
            widgets = "3dview^2dview^radar_zoom_ctrl^helm_free_3d^fighter_control^ship_data^grid_face^grid_control"
        

    page.set_widget_list(console, widgets)
