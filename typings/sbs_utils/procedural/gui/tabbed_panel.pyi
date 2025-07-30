from sbs_utils.helpers import FrameContext
from sbs_utils.futures import Promise
from sbs_utils.pages.widgets.tabbed_panel import TabbedPanel
def apply_control_styles (control_name, extra_style, layout_item, task):
    ...
def awaitable (func):
    ...
def delay_sim (*args, **kwargs):
    ...
def gui_blank (count=1, style=None):
    """adds an empty column to the current gui ow
    
    Args:
        style (_type_, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_button (props, style=None, data=None, on_press=None, is_sub_task=False):
    """Add a gui button
    
    Args:
        count (int): The number of columns to use
        style (_type_, optional): Style. Defaults to None.
        data (object): The data to pass to the button's label
        on_press (label, callable, Promise): Handle a button press, label is jumped to, callable is called, Promise has results set
    
    Returns:
        layout object: The Layout object created"""
def gui_face (face, style=None):
    """queue a gui face element
    
    Args:
        face (str): _description_
        style (str, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_icon (props, style=None):
    """queue a gui icon element
    
    Args:
        props (str): _description_
        style (str, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_info_panel (tab=0, tab_location=0, icon_size=0, var=None):
    ...
def gui_info_panel_add (path, icon_index, show, hide=None, tick=None, var=None):
    ...
def gui_info_panel_remove (path, var=None):
    ...
def gui_info_panel_send_message (*args, **kwargs):
    ...
def gui_list_box (items, style, item_template=None, title_template=None, section_style=None, title_section_style=None, select=False, multi=False, carousel=False, collapsible=False, read_only=False):
    ...
def gui_message (layout_item, label=None):
    """Trigger to watch when the specified layout element has a message
    
    Args:
        layout_item (layout object): The object to watch
    
    Returns:
        trigger: A trigger watches something and runs something when the trigger is reached"""
def gui_panel_console_message (cid, left, top, width, height):
    ...
def gui_panel_console_message_list (cid, left, top, width, height):
    ...
def gui_panel_console_message_list_item (message_obj):
    ...
def gui_panel_console_message_tick (info_panel):
    ...
def gui_panel_ship_data_hide (cid, left, top, width, height):
    ...
def gui_panel_ship_data_show (cid, left, top, width, height):
    ...
def gui_panel_upgrade_list (cid, left, top, width, height):
    ...
def gui_panel_widget_hide (cid, left, top, width, height, widget):
    ...
def gui_panel_widget_show (cid, left, top, width, height, widget):
    ...
def gui_percent_from_pixels (client_id, pixels):
    ...
def gui_represent (layout_item):
    """redraw an item
    
    ??? Note
        For sections it will recalculate the layout and redraw all items
    
    Args:
        layout_item (layout_item): """
def gui_row (style=None):
    """queue a gui row
    
    Args:
        style (str, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_sub_section (style=None):
    """Create a new gui section that uses the area specified in the style
    
    Args:
        style (style, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_tabbed_panel (items=None, style=None, tab=0, tab_location=0, icon_size=0):
    ...
def gui_task_for_client (client_id):
    ...
def gui_text (props, style=None):
    """Add a gui text object
    
    valid properties
        text
        color
        font
    
    
    props (str): property string
    style (style, optional): The style"""
def panel_upgrade_item (message_obj):
    ...
def to_set (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """converts a single object/id, set ot list of things to a set of ids
    
    Args:
        the_set (set): set, list or single item
    
    Returns:
        set of things"""
class InfoButtonPromise(Promise):
    """class InfoButtonPromise"""
    def __init__ (self, message_data) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def set_result (self, result):
        ...
