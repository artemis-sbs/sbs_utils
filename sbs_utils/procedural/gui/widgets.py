from ...helpers import FrameContext


def gui_widget_list(console, widgets):
    """ Set the engine widget list. i.e. controls engine controls

    Args:
        console (str): The console type name
        widgets (str): The list of widgets

    """    
    page = FrameContext.page
    if page is None:
        return None
    page.set_widget_list(console, widgets)

order_first_widgets = ["2dview","3dview", "comms_2d_view", "ship_internal_view", "weapon_2d_view", "science_2d_view"]
def gui_update_widget_list(add_widgets=None, remove_widgets= None):
    """ Set the engine widget list. i.e. controls engine controls

    Args:
        console (str): The console type name
        widgets (str): The list of widgets

    """    
    """ Set the engine widget list. i.e. controls engine controls

    Args:
        console (str): The console type name
        widgets (str): The list of widgets

    """    
    page = FrameContext.page
    if page is None:
        return None
    
    if add_widgets is None and remove_widgets is None:
        return
    if add_widgets is None:
        add_widgets = ""
    if remove_widgets is None:
        remove_widgets = ""

    widgets = set(page.widgets.split("^"))
    add_widgets = set(add_widgets.split("^"))
    remove_widgets = set(remove_widgets.split("^"))
    widgets = (widgets | add_widgets) - remove_widgets
    new_widgets = ""
    delim = ""
    for widget in widgets:
        if widget in order_first_widgets:
            new_widgets = widget + delim + new_widgets
            delim = "^"
        else:
            new_widgets = new_widgets + delim + widget
            delim = "^"
    #print(f"GUI {new_widgets} {widgets} {add_widgets} {remove_widgets}")
    FrameContext.context.sbs.send_client_widget_list(page.client_id, page.console, new_widgets)



def gui_update_widgets(add_widgets, remove_widgets):
    """ Set the engine widget list. i.e. controls engine controls

    Args:
        console (str): The console type name
        widgets (str): The list of widgets

    """    
    page = FrameContext.page
    if page is None:
        return None

    widgets = set(page.pending_widgets.split("^"))
    add_widgets = set(add_widgets.split("^"))
    remove_widgets = set(remove_widgets.split("^"))
    widgets = (widgets | add_widgets) - remove_widgets
    new_widgets = ""
    delim = ""
    for widget in widgets:
        if widget in order_first_widgets:
            new_widgets = widget + delim + new_widgets
            delim = "^"
        else:
            new_widgets = new_widgets + delim + widget
            delim = "^"
    
    page.pending_widgets = new_widgets



def gui_widget_list_clear():
    """clear the widet list on the client
    """    
    gui_widget_list("","")
from ...pages.layout.console_widget import ConsoleWidget
def gui_layout_widget(widget):
    """Places a specific console widget in the a layout section. Placing it at a specific location

    Args:
        widget (str): The gui widget

    Returns:
        layout element: The layout element
    """    
    page = FrameContext.page
    if page is None:
        return None
    
    page.add_console_widget(widget)
    control = ConsoleWidget(widget)
    page.add_content(control, None)
    return control
    
