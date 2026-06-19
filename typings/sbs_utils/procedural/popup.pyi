from sbs_utils.mast_sbs.story_nodes.button import Button
from sbs_utils.procedural.gui.gui import ButtonPromise
from sbs_utils.consoledispatcher import ConsoleDispatcher
from sbs_utils.helpers import FakeEvent
from sbs_utils.helpers import FrameContext
from sbs_utils.garbagecollector import GarbageCollector
from sbs_utils.vec import Vec3
def get_comms_selection (id_or_not):
    """Return the ID of the object currently selected on the comms console.
    
    Args:
        id_or_not (Agent | int): The player ship agent ID or object.
    
    Returns:
        int | None: The selected agent ID, or ``None`` if unavailable."""
def get_science_selection (id_or_not):
    """Return the ID of the object currently selected on the science console.
    
    Args:
        id_or_not (Agent | int): The player ship agent ID or object.
    
    Returns:
        int | None: The selected agent ID, or ``None`` if unavailable."""
def get_weapons_selection (id_or_not):
    """Return the ID of the object currently selected on the weapons console.
    
    Args:
        id_or_not (Agent | int): The player ship agent ID or object.
    
    Returns:
        int | None: The selected agent ID, or ``None`` if unavailable."""
def popup_navigate (path):
    """Set the active path for the current popup, similar to a comms route (e.g. ``//popup/science``).
    
    Args:
        path (str): The new popup path to navigate to."""
def start_popup_selected (event):
    """Start or resume a popup for the given selection event.
    
    Creates a new ``PopupPromise`` for the (origin, selected) pair if one does
    not already exist; otherwise resumes the existing promise. Called
    automatically by ``ConsoleDispatcher`` for ``science_popup``,
    ``comms_popup``, ``comms2d_popup``, and ``weapons_popup`` events.
    
    Args:
        event: The engine selection event that triggered the popup.
    
    Returns:
        PopupPromise: The promise managing this popup, or ``None`` if the
            origin object no longer exists."""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Resolve an ID, ``CloseData``, or ``SpawnData`` to its Agent object.
    
    Returns ``None`` when the agent no longer exists.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to resolve.
    
    Returns:
        Agent | None: The agent, or ``None`` if it could not be resolved."""
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
