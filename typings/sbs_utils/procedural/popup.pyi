from sbs_utils.mast_sbs.story_nodes.button import Button
from sbs_utils.procedural.gui.gui import ButtonPromise
from sbs_utils.consoledispatcher import ConsoleDispatcher
from sbs_utils.helpers import FakeEvent
from sbs_utils.helpers import FrameContext
from sbs_utils.garbagecollector import GarbageCollector
from sbs_utils.vec import Vec3
def get_comms_selection (id_or_not):
    """gets the id of the comms selection
    
    Args:
        id_or_not (agent): agent id or object
    
    Returns:
        agent id | None: The agent id or None"""
def get_science_selection (id_or_not):
    """gets the id of the science selection
    
    Args:
        id_or_not (agent): agent id or object
    
    Returns:
        agent id | None: The agent id or None"""
def get_weapons_selection (id_or_not):
    """gets the id of the weapons selection
    
    Args:
        id_or_not (agent): agent id or object
    
    Returns:
        agent id | None: The agent id or None"""
def popup_navigate (path):
    ...
def start_popup_selected (event):
    ...
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """converts the item passed to an agent
    
    ??? note
        Retrun of None could mean the agent no longer exists
    
    Args:
        other (Agent | CloseData | int): The agent ID or other agent like data
    
    Returns:
        agent | None: The agent or None"""
class PopupPromise(ButtonPromise):
    """class PopupPromise"""
    def __init__ (self, event) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def collect (self):
        ...
    def handle_button_sub_task (self, sub_task):
        ...
    def initial_poll (self):
        ...
    def leave (self):
        ...
    def message (self, event):
        ...
    def poll (self):
        ...
    def pressed_set_values (self, task) -> None:
        ...
    def selected (self, event):
        ...
    def set_path (self, path):
        ...
    def set_variables (self, event):
        ...
    def show_buttons (self):
        ...
