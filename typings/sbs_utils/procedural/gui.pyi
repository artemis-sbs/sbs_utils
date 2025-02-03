from sbs_utils.agent import Agent
from sbs_utils.futures import AwaitBlockPromise
from sbs_utils.futures import Trigger
from sbs_utils.extra_dispatcher import ClientStringDispatcher
from sbs_utils.helpers import DictionaryToObject
from sbs_utils.helpers import FakeEvent
from sbs_utils.helpers import FrameContext
from sbs_utils.gui import Gui
from sbs_utils.pages.widgets.layout_listbox import LayoutListbox
from sbs_utils.mast.pollresults import PollResults
from sbs_utils.mast.mast_node import Scope
from sbs_utils.mast.parsers import StyleDefinition
from sbs_utils.pages.layout.text_area import TextArea
from builtins import unicode_type
def AWAIT (promise: sbs_utils.futures.Promise):
    """Creates a entity to wait (non-blocking) for a promise to complete
    
    Args:
        Promise: A promise """
def _gui_reroute_main (label, server):
    ...
def apply_control_styles (control_name, extra_style, layout_item, task):
    ...
def get_client_aspect_ratio (cid):
    ...
def get_inventory_value (id_or_object, key, default=None):
    """get inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
    
    Args:
        id_or_obj (agent): The agent id or object to check
        key (str): The key/name of the inventory item
        default (any): the default value data"""
def gui (buttons=None, timeout=None):
    """present the gui that has been queued up
    
    Args:
        buttons (dict, optional): _description_. Defaults to None.
        timeout (promise, optional): A promise that ends the gui. Typically a timeout. Defaults to None.
    
    Returns:
        Promise: The promise for the gui, promise is done when a button is selected"""
def gui_activate_console (console):
    """set the console name for the client
    
    Args:
        console (str): The console name"""
def gui_add_console_tab (id_or_obj, console, tab_name, label):
    """adds a tab definition
    
    Args:
        id_or_obj (agent): agent id or object
        console (str): Console name
        tab_name (str): Tab name
        label (label): Label to run when tab selected"""
def gui_add_console_type (path, display_name, description, label):
    """adds a tab definition
    
    Args:
        id_or_obj (agent): agent id or object
        console (str): Console name
        tab_name (str): Tab name
        label (label): Label to run when tab selected"""
def gui_blank (count=1, style=None):
    """adds an empty column to the current gui ow
    
    Args:
        style (_type_, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_button (props, style=None, data=None, on_message=None, jump=None):
    """Add a gui button
    
    Args:
        count (int): The number of columns to use
        style (_type_, optional): Style. Defaults to None.
        data (object): The data to pass to the button's label
        on_message (label): A label to handle a button press
        jump (label): A label to jump to a button press, ending the Await gui
    
    Returns:
        layout object: The Layout object created"""
def gui_change (code, label):
    """Trigger to watch when the specified value changes
    This is the python version of the mast on change construct
    
    Args:
        code (str): Code to evaluate
        label (label): The label to jump to run when the value changes
    
    Returns:
        trigger: A trigger watches something and runs something when the element is clicked"""
def gui_checkbox (msg, style=None, var=None, data=None):
    """Draw a checkbox
    
    Args:
        props (str):
        style (style, optional): Style. Defaults to None.
        var (str, optional): Variable name to set the value to. Defaults to None.
        data (object, optional): data to pass the handler. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_cinematic_auto (client_id):
    """Will automatically track the consoles assigned ship
    
    ??? Note:
        The tracked ship needs to have excitement values
        player ships automatically have that set
    
    Args:
        client_id (id): the console's client ID"""
def gui_cinematic_full_control (client_id, camera_id, camera_offset, tracked_id, tracked_offset):
    ...
def gui_click (name_or_layout_item=None):
    """Trigger to watch when the specified layout element is clicked
    
    Args:
        layout_item (layout object): The object to watch
    
    Returns:
        trigger: A trigger watches something and runs something when the element is clicked"""
def gui_clipboard_copy (s):
    ...
def gui_clipboard_get ():
    ...
def gui_clipboard_put (s):
    ...
def gui_console (console, is_jump=False):
    """Activates a console using the default set of widgets
    
    Args:
        console (str): The console name"""
def gui_content (content, style=None, var=None):
    """Place a python code widget e.g. list box using the layout system
    
    Args:
        content (widget): A gui widget code in python
        style (str, optional): Style. Defaults to None.
        var (str, optional): The variable to set the widget's value to. Defaults to None.
    
    Returns:
        layout object: The layout object"""
def gui_drop_down (props, style=None, var=None, data=None):
    """Draw a gui drop down list
    
    Args:
        props (str):
        style (style, optional): Style. Defaults to None.
        var (str, optional): Variable name to set the selection to. Defaults to None.
        data (object, optional): data to pass the handler. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_face (face, style=None):
    """queue a gui face element
    
    Args:
        face (str): _description_
        style (str, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_get_console_type (key):
    """Get the list of consoles defined by @console decorator labels
    
        """
def gui_get_console_type_list ():
    """Get the list of consoles defined by @console decorator labels
    path is added as a value"""
def gui_get_console_types ():
    """Get the list of consoles defined by @console decorator labels
    
        """
def gui_hide (layout_item):
    """If the item is visible it will make it hidden
    
    ??? Note
        For sections it will recalculate the layout.
        For individual item or row, it will hide, but not layout.
        so you may also need to pair this with a gui_represent of a section
    
    Args:
        layout_item (layout_item): """
def gui_hide_choice ():
    ...
def gui_history_back ():
    """Jump back in history
    
        """
def gui_history_clear ():
    """Clears the history for the given page
        """
def gui_history_forward ():
    """Jump forward in history
        """
def gui_history_jump (to_label, back_name=None, back_label=None, back_data=None):
    """Jump to a new gui label, but remember how to return to the current state
    
    Args:
        to_label (label): Where to jump to
        back_name (str): A name to use if displayed
        back_label (label, optional): The label to return to defaults to the label active when called
        back_data (dict, optional): A set of value to set when returning back
    
    ??? Note:
        If there is forward history it will be cleared
    
    Returns:
        results (PollResults): PollResults of the jump"""
def gui_history_redirect (back_name=None, back_label=None, back_data=None):
    ...
def gui_history_store (back_text, back_label=None):
    """store the current
    
    Args:
        label (label): A mast label"""
def gui_hole (count=1, style=None):
    """adds an empty column that is used by the next item
    
    Args:
        count (int): The number of columns to use
        style (_type_, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_icon (props, style=None):
    """queue a gui icon element
    
    Args:
        props (str): _description_
        style (str, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_icon_button (props, style=None):
    """queue a gui icon element
    
    Args:
        props (str): _description_
        style (str, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_image (props, style=None, fit=0):
    """queue a gui image element that draw based on the fit argument. Default is stretch
    
    Args:
        props (str): _description_
        style (str, optional): Style. Defaults to None.
        fit (int): The type of fill,
    
    Returns:
        layout object: The Layout object created"""
def gui_image_absolute (props, style=None):
    """queue a gui image element that draw the absolute pixels dimensions
    
    Args:
        props (str): _description_
        style (str, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_image_keep_aspect_ratio (props, style=None):
    """queue a gui image element that draw keeping the same aspect ratio, left top justified
    
    Args:
        props (str): _description_
        style (str, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_image_keep_aspect_ratio_center (props, style=None):
    """queue a gui image element that keeps the aspect ratio and centers when there is extra
    
    Args:
        props (str): _description_
        style (str, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_image_stretch (props, style=None):
    """queue a gui image element that stretches to fit
    
    Args:
        props (str): _description_
        style (str, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_input (props, style=None, var=None, data=None):
    """Draw a text type in
    
    Args:
        props (str): hi, low etc.
        style (style, optional): Style. Defaults to None.
        var (str, optional): Variable name to set the selection to. Defaults to None.
        data (object, optional): data to pass the handler. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_int_slider (msg, style=None, var=None, data=None):
    """Draw an integer slider control
    
    Args:
        props (str): hi, low etc.
        style (style, optional): Style. Defaults to None.
        var (str, optional): Variable name to set the selection to. Defaults to None.
        data (object, optional): data to pass the handler. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_layout_widget (widget):
    """Places a specific console widget in the a layout section. Placing it at a specific location
    
    Args:
        widget (str): The gui widget
    
    Returns:
        layout element: The layout element"""
def gui_list_box (items, style, item_template=None, title_template=None, section_style=None, title_section_style=None, select=False, multi=False, carousel=False, read_only=False):
    ...
def gui_message (layout_item):
    """Trigger to watch when the specified layout element has a message
    
    Args:
        layout_item (layout object): The object to watch
    
    Returns:
        trigger: A trigger watches something and runs something when the trigger is reached"""
def gui_radio (msg, style=None, var=None, data=None, vertical=False):
    """Draw a radio button list
    
    Args:
        props (str): List of buttons to use
        style (style, optional): Style. Defaults to None.
        var (str, optional): Variable name to set the selection to. Defaults to None.
        data (object, optional): data to pass the handler. Defaults to None.
        vertical (bool): Layout vertical if True, default False means horizontal
    
    Returns:
        layout object: The Layout object created"""
def gui_rebuild (region):
    """prepares a section/region to be build a new layout
    
    Args:
        region (layout_item): a layout/Layout item
    
    Returns:
        layout object: The Layout object created"""
def gui_refresh (label):
    """refresh any gui running the specified label
    
    Args:
        label (label): A mast label"""
def gui_region (style=None):
    """Create a new gui section that uses the area specified in the style
    
    Args:
        style (style, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_remove_console_tab (id_or_obj, console, tab_name):
    """removes a tab definition
    
    Args:
        id_or_obj (agent): agent id or object
        console (str): Console name
        tab_name (str): Tab name"""
def gui_remove_console_type (path, display_name, label):
    """adds a tab definition
    
    Args:
        path (str): Console path
        display_name (str): Display name
        label (label): Label to run when tab selected"""
def gui_represent (layout_item):
    """redraw an item
    
    ??? Note
        For sections it will recalculate the layout and redraw all items
    
    Args:
        layout_item (layout_item): """
def gui_request_client_string (client_id, key, timeout=None):
    ...
def gui_reroute_client (client_id, label, data=None):
    ...
def gui_reroute_clients (label, data=None, exclude=None):
    """reroute client guis to run the specified label
    
    Args:
        label (label): Label to jump to
        exclude (set, optional): set client_id values to exclude. Defaults to None."""
def gui_reroute_server (label, data=None):
    """reroute server gui to run the specified label
    
    Args:
        label (label): Label to jump to"""
def gui_row (style=None):
    """queue a gui row
    
    Args:
        style (str, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_screenshot (image_path):
    ...
def gui_section (style=None):
    """Create a new gui section that uses the area specified in the style
    
    Args:
        style (style, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_set_style_def (name, style):
    ...
def gui_ship (props, style=None):
    """renders a 3d image of the ship
    
    Args:
        props (str): The ship key
        style (str, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_show (layout_item):
    """gui show. If the item is hidden it will make it visible again
    
    ??? Note
        For sections it will recalculate the layout.
        For individual item or row, it will hide, but not layout.
        so you may also need to pair this with a gui_represent of a section
    
    Args:
        layout_item (layout_item): """
def gui_slider (msg, style=None, var=None, data=None, is_int=False):
    """Draw a slider control
    
    Args:
        props (str): hi, low etc.
        style (style, optional): Style. Defaults to None.
        var (str, optional): Variable name to set the selection to. Defaults to None.
        data (object, optional): data to pass the handler. Defaults to None.
        is_int (bool): Use only integers values
    
    Returns:
        layout object: The Layout object created"""
def gui_style_def (style):
    ...
def gui_sub_section (style=None):
    """Create a new gui section that uses the area specified in the style
    
    Args:
        style (style, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_text (props, style=None):
    """Add a gui text object
    
    valid properties
        text
        color
        font
    
    
    props (str): property string
    style (style, optional): The style"""
def gui_text_area (props, style=None):
    """Add a gui text object
    
    valid properties
        text
        color
        font
    
    
    props (str): property string
    style (style, optional): The style"""
def gui_update (tag, props, shared=False, test=None):
    """Update the properties of a current gui element
    
    Args:
        tag (str):
        props (str): The new properties to use
        shared (bool, optional): Update all gui screen if true. Defaults to False.
        test (dict, optional): Check the variable (key) update if any value is different than the test. Defaults to None."""
def gui_update_shared (tag, props, test=None):
    ...
def gui_update_widget_list (add_widgets=None, remove_widgets=None):
    """Set the engine widget list. i.e. controls engine controls
    
    Args:
        console (str): The console type name
        widgets (str): The list of widgets"""
def gui_update_widgets (add_widgets, remove_widgets):
    """Set the engine widget list. i.e. controls engine controls
    
    Args:
        console (str): The console type name
        widgets (str): The list of widgets"""
def gui_vradio (msg, style=None, var=None, data=None):
    """Draw a vertical radio button list
    
    Args:
        props (str): List of buttons to use
        style (style, optional): Style. Defaults to None.
        var (str, optional): Variable name to set the selection to. Defaults to None.
        data (object, optional): data to pass the handler. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_widget_list (console, widgets):
    """Set the engine widget list. i.e. controls engine controls
    
    Args:
        console (str): The console type name
        widgets (str): The list of widgets"""
def gui_widget_list_clear ():
    """clear the widet list on the client
        """
def set_inventory_value (so, key, value):
    """set inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
    
    Args:
        id_or_obj (agent): The agent id or object to check
        key (str): The key/name of the inventory item
        value (any): the value"""
def task_all (*args, **kwargs):
    """Creates a task for each argument that is a label. Also supports a data named argument to pass the data to all the tasks.
    
    Args:
        args (0..n labels): the labels to schedule.
        data (dict): keyword arg to pass data to the tasks.
    Returns:
        Promise: A promise that is finished when all tasks are completed."""
def text_sanitize (text):
    ...
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """converts item passed to an agent id
    
    Args:
        other (Agent | CloseData | int): The agent
    
    Returns:
        id: The agent id"""
class ButtonPromise(AwaitBlockPromise):
    """class ButtonPromise"""
    def __init__ (self, path, task, timeout=None) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def add_nav_button (self, button):
        ...
    def build_navigation_buttons (self):
        ...
    def cancel (self, msg=None):
        ...
    def check_for_button_done (self):
        ...
    def expand_button (self, button):
        ...
    def expand_inline (self, inline):
        ...
    def expand_inlines (self):
        ...
    def get_expanded_buttons (self):
        ...
    def initial_poll (self):
        ...
    def poll (self):
        ...
    def press_button (self, button):
        ...
    def pressed_set_values (self):
        ...
    def pressed_test (self):
        ...
    def set_path (self, path):
        ...
class ChangeTrigger(Trigger):
    """class ChangeTrigger"""
    def __init__ (self, task, node, label=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def run (self):
        ...
    def test (self):
        ...
class ChoiceButtonRuntimeNode(object):
    """class ChoiceButtonRuntimeNode"""
    def __init__ (self, promise, button, tag):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def on_message (self, event):
        ...
class ClickableTrigger(Trigger):
    """class ClickableTrigger"""
    def __init__ (self, task, name):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def click (self, click_tag):
        ...
class ClientStringPromise(AwaitBlockPromise):
    """class ClientStringPromise"""
    def __init__ (self, client_id, key, timeout=None) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def on_event (self, event):
        ...
class GuiPromise(ButtonPromise):
    """class GuiPromise"""
    def __init__ (self, page, timeout=None) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def initial_poll (self):
        ...
    def show_buttons (self):
        ...
class MessageHandler(object):
    """class MessageHandler"""
    def __init__ (self, layout_item, task, label, jump=False) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def on_message (self, event):
        ...
class MessageTrigger(Trigger):
    """class MessageTrigger"""
    def __init__ (self, task, layout_item, label=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def on_message (self, event):
        ...
class PageRegion(object):
    """class PageRegion"""
    def __enter__ (self):
        ...
    def __exit__ (self, ex=None, value=None, tb=None):
        ...
    def __init__ (self, style) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    @property
    def is_hidden (self):
        ...
    def rebuild (self):
        ...
    def represent (self, e):
        ...
    def show (self, _show):
        ...
class PageSubSection(object):
    """class PageSubSection"""
    def __enter__ (self):
        ...
    def __exit__ (self, ex=None, value=None, tb=None):
        ...
    def __init__ (self, style) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
