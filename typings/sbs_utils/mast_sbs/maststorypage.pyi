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
    """Apply a named control style and optional overrides to a layout item.
    
    ``extra_style`` may be a raw CSS-style string (``"key:value;..."``) or
    a style name. It is applied on top of the base ``control_name`` style.
    
    Args:
        control_name (str): Base control style name.
        extra_style (str | dict | None): Additional style string, name, or
            parsed dict applied after the base style.
        layout_item (LayoutItem): Layout item to receive the style.
        task (MastAsyncTask): GUI task used for string formatting."""
def get_inventory_value (id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.
    
    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
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
    """Jump a specific client's GUI task to a new label immediately.
    
    Finds the client's active page, optionally sets variables from ``data``,
    then jumps the page's GUI task to ``label`` and ticks it in the current
    frame context.
    
    Args:
        client_id (int): The client to reroute.
        label: MAST label to jump to.
        data (dict | None, optional): Variables to set on the task before
            jumping. Defaults to None.
    
    Example:
        gui_reroute_client(CLIENT_ID, briefing_screen)"""
def has_inventory_value (key: str, value):
    """Return the set of agent IDs whose inventory value for ``key`` equals ``value``.
    
    Args:
        key (str): The inventory key to look for.
        value: The exact value to match.
    
    Returns:
        set[int]: IDs of agents whose ``key`` inventory entry equals ``value``."""
def is_dev_build ():
    """Check if the current mission is a development build.
    
    Returns True if a .git directory exists in the mission folder.
    
    Returns:
        bool: True if running in development mode, False otherwise."""
def linked_to (link_source, link_name: str):
    """Return the set of IDs that an agent links to under a given name.
    
    Args:
        link_source (Agent | int): The source agent ID or object.
        link_name (str): The link key name.
    
    Returns:
        set[int]: IDs of all linked targets, or an empty set if none."""
def log (message: str, name: str = None, level: str = None, use_mast_scope=False) -> None:
    """Emit a log message using Python's ``logging`` module.
    
    When ``use_mast_scope=True`` the message is formatted through the current
    MAST task's string formatter first (MAST exposes this as ``log``).
    
    Args:
        message (str): The message to log. May contain MAST format strings when
            ``use_mast_scope=True``.
        name (str, optional): Logger name. Defaults to None (``__base_logger__``).
        level (str, optional): Logging level string, e.g. ``"DEBUG"``, ``"INFO"``.
            Defaults to None (``DEBUG``).
        use_mast_scope (bool, optional): Format the message via the current
            MAST task. Defaults to False."""
def set_inventory_value (so, key: str, value):
    """Set an inventory value on one or more agents.
    
    If ``so`` is a set or collection, every member receives the value.
    
    Args:
        so (Agent | int | set[Agent | int]): The agent(s) to update.
        key (str): The inventory key.
        value (any): The value to store."""
def signal_emit (name, data=None):
    """Emit a named signal, running all registered ``//signal/<name>`` routes.
    
    Safe to call when no MAST context is active — returns immediately with no
    side effects.
    
    Args:
        name (str): The signal name.
        data (dict, optional): Arbitrary data passed to each signal handler.
            Defaults to None."""
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
