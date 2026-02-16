from sbs_utils.agent import Agent
from sbs_utils.pages.layout.blank import Blank
from sbs_utils.helpers import FakeEvent
from sbs_utils.helpers import FrameContext
from sbs_utils.helpers import FrameContextOverride
from sbs_utils.gui import Gui
from sbs_utils.gui import Page
from sbs_utils.mast_sbs.story_nodes.gui_tab_decorator_label import GuiTabDecoratorLabel
from sbs_utils.pages.layout.layout import Layout
from sbs_utils.mast.maststory import MastStory
from sbs_utils.pages.layout.row import Row
from sbs_utils.mast_sbs.maststoryscheduler import StoryScheduler
from sbs_utils.pages.layout.text import Text
def apply_control_styles (control_name, extra_style, layout_item, task):
    """Apply style information to a layout item based on the type of the layout, and apply the extra styles as needed.
    Args:
        control_name (str): The name of the control style.
        extra_style (str): A CSS-style string containing extra style definitions which override those in the control style.
        layout_item (LayoutItem): The layout item for which the style is to be applied."""
def get_inventory_value (id_or_object, key: str, default=None):
    """get inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
    
    Args:
        id_or_obj (Agent | int): The agent id or object to check
        key (str): The key/name of the inventory item
        default (any): the default value data
    Returns:
        any: The inventory value associated with the provided key, or the default value if it doesn't exist."""
def get_mission_name ():
    """Get the name of the current mission.
    
    Returns the name derived from the script directory basename.
    Cached after first call.
    
    Returns:
        str: The mission folder name."""
def get_startup_mission_name ():
    """Get the default mission name from preferences.
    
    Returns:
        str: The default mission folder name from game preferences."""
def gui_reroute_client (client_id, label, data=None):
    ...
def has_inventory_value (key: str, value):
    """Get the object that have a inventory item with the given key
    
    Args:
        key (str): The key/name of the inventory item
    
    Returns:
        set[int]: set of ids"""
def linked_to (link_source, link_name: str):
    """Get the set of ids that the source is linked to for the given key.
    
    Args:
        link_source (Agent | int): The agent or id to check
        link_name (str): The key/name of the inventory item
    Returns:
        set[int]: The set of linked ids"""
def log (message: str, name: str = None, level: str = None, use_mast_scope=False) -> None:
    """generate a log message
    
        note: MAST exposes mast_log as log so it by default uses MAST scope
    Args:
        message (str): The message to log
        name (str, optional): Name of the logger to log to. Defaults to None.
        level (str, optional): The logging level to use. Defaults to None."""
def set_inventory_value (so, key: str, value):
    """Set inventory value with the given key the the agent has.
    This is the way to create a collection in inventory.
    `so` can be a set. If it is, the inventory value is set for each member in the set.
    
    Args:
        id_or_obj (Agent | int | set[Agent | int]): The agent id or object or set to check
        key (str): The key/name of the inventory item
        value (any): the value"""
def signal_emit (name, data=None):
    """Emit a signal to trigger all instances of the signal route to run.
    Args:
        name (str): The name of the signal.
        data (dict): The data to provide to the signal route."""
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
    def on_begin_presenting (self):
        ...
    def on_end_presenting (self):
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
    def on_new_gui (self):
        ...
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
    def swap_gui_promise (self, pending):
        ...
    def swap_layout (self):
        ...
    @property
    def task (self):
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
