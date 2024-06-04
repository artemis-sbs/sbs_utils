from sbs_utils.agent import Agent
from sbs_utils.helpers import FakeEvent
from sbs_utils.helpers import FrameContext
from sbs_utils.gui import Gui
from sbs_utils.gui import Page
from sbs_utils.mast.maststory import MastStory
from sbs_utils.mast.maststoryscheduler import StoryScheduler
def apply_control_styles (control_name, extra_style, layout_item, task):
    ...
def get_inventory_value (id_or_object, key, default=None):
    """get inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
    
    Args:
        id_or_obj (agent): The agent id or object to check
        key (str): The key/name of the inventory item
        default (any): the default value data"""
def get_mission_name ():
    ...
def get_startup_mission_name ():
    ...
def gui_reroute_client (client_id, label, data=None):
    ...
def has_inventory_value (key: str, value):
    """get the object that have a inventory item with the given key
    
    Args:
        key (str): The key/name of the inventory item
    
    Returns:
        set: set of ids"""
def linked_to (link_source, link_name: str):
    """get the set that inventor the source is linked to for the given key
    
    Args:
        link_source(id): The id object to check
        link_name (str): The key/name of the inventory item
        set | None: set of ids"""
def log (message, name=None, level=None):
    """generate a log message
    
    Args:
        message (str): The message to log
        name (str, optional): Name of the logger to log to. Defaults to None.
        level (str, optional): The logging level to use. Defaults to None."""
def set_inventory_value (so, key, value):
    """set inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
    
    Args:
        id_or_obj (agent): The agent id or object to check
        key (str): The key/name of the inventory item
        value (any): the value"""
class StoryPage(Page):
    """A interface class for creating GUI pages
    
        """
    def __init__ (self) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def activate_console (self, console):
        ...
    def add_console_widget (self, widget):
        ...
    def add_content (self, layout_item, runtime_node):
        ...
    def add_on_click (self, runtime_node):
        ...
    def add_row (self):
        ...
    def add_section (self, tag=None):
        ...
    def add_tag (self, layout_item, runtime_node):
        ...
    def get_path (self):
        ...
    def get_pending_layout (self):
        ...
    def get_pending_row (self):
        ...
    def get_tag (self):
        ...
    def gui_queue_console_tabs (self):
        ...
    def on_event (self, event):
        """on_event
        
        Called when the option pages page has been interacted with
        
        :param event: The event data
        :type event: event"""
    def on_message (self, event):
        """on_message
        
        Called when the option pages page has been interacted with
        
        :param event: The event data
        :type event: event"""
    def pop_sub_section (self, add_content, is_rebuild):
        ...
    def present (self, event):
        """Present the gui """
    def push_sub_section (self, style, layout_item, is_rebuild):
        ...
    def set_button_layout (self, layout, gui_promise):
        ...
    def set_widget_list (self, console, widgets):
        ...
    def start_story (self, client_id):
        ...
    def swap_layout (self):
        ...
    def tick_gui_task (self):
        """tick_gui_task
        
        Called to have the page run any tasks they have prior to present"""
    def update_props_by_tag (self, tag, props, test):
        ...
class TabControl(Text):
    """class TabControl"""
    def __init__ (self, tag, message, label, page) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def on_message (self, event):
        ...
