from sbs_utils.mast_sbs.story_nodes.button import Button
from sbs_utils.procedural.gui.gui import ButtonPromise
from sbs_utils.consoledispatcher import ConsoleDispatcher
from sbs_utils.helpers import FakeEvent
from sbs_utils.helpers import FrameContext
from sbs_utils.garbagecollector import GarbageCollector
from sbs_utils.vec import Vec3
def get_comms_selection (id_or_not):
    """Gets the id of the comms selection
    Args:
        id_or_not (Agent | int): agent id or object
    Returns:
        int | None: The agent id or None"""
def get_science_selection (id_or_not):
    """Gets the id of the science selection
    Args:
        id_or_not (Agent | int): agent id or object
    Returns:
        int | None: The agent id or None"""
def get_weapons_selection (id_or_not):
    """Gets the id of the weapons selection
    Args:
        id_or_not (Agent | int): agent id or object
    Returns:
        int | None: The agent id or None"""
def popup_navigate (path):
    """Set the path for the popup task. Similar to comms paths, e.g. `//popup/science`
    Args:
        path (str): The path"""
def start_popup_selected (event):
    """Display the popup.
    Args:
        event (event): The event that triggered the popup.
    Returns:
        Promise: The popup's promise """
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Converts the item passed to an agent
    ??? note
    * Return of None could mean the agent no longer exists
    Args:
        other (Agent | CloseData | int): The agent ID or other agent like data
    Returns:
        Agent | None: The agent or None"""
class PopupPromise(ButtonPromise):
    """class PopupPromise"""
    def __init__ (self, event) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def collect (self):
        """Garbage Collect the popup promise.
        Returns:
            bool: Was the GC successfully completed?"""
    def handle_button_sub_task (self, sub_task):
        """Add the sub task to the gui task
        Args:
            sub_task (MastAsyncTask): The task to add"""
    def initial_poll (self):
        ...
    def leave (self):
        """Leave and remove the promise."""
    def message (self, event):
        """Triggered when a button is pressed.
        Args:
            event (event): The button press event."""
    def poll (self):
        """Get the result of the popup.
        Returns:
            PollResults: The result."""
    def pressed_set_values (self, task) -> None:
        """When the popup is pressed, the task variables are set.
        Args:
            task (MastAsyncTask): The task."""
    def selected (self, event):
        """Triggered when an object is selected on the widget.
        Args:
            event (event): The selection event"""
    def set_path (self, path):
        ...
    def set_variables (self, event):
        """Set the variables based on the event that fired.
        Args:
            event (event): The event"""
    def show_buttons (self):
        """Display the popup menu buttons."""
