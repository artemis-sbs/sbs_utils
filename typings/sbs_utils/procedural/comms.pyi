from sbs_utils.agent import Agent
from sbs_utils.mast_sbs.story_nodes.button import Button
from sbs_utils.procedural.gui.gui import ButtonPromise
from sbs_utils.mast.mastscheduler import ChangeRuntimeNode
from sbs_utils.consoledispatcher import ConsoleDispatcher
from sbs_utils.helpers import FakeEvent
from sbs_utils.helpers import FrameContext
from sbs_utils.garbagecollector import GarbageCollector
from sbs_utils.mast.mast_node import MastDataObject
from sbs_utils.mast.pollresults import PollResults
from sbs_utils.futures import Promise
from sbs_utils.vec import Vec3
def AWAIT (promise: sbs_utils.futures.Promise) -> sbs_utils.futures.PromiseWaiter:
    """Creates a entity to wait (non-blocking) for a promise to complete
    
    Args:
        Promise: A promise """
def _comms_get_colors (to_obj, from_obj, is_receive, title_color, color):
    ...
def _comms_get_origin_id () -> int:
    ...
def _comms_get_selected_id () -> int:
    ...
def awaitable (func):
    ...
def comms (path=None, buttons=None, timeout=None) -> sbs_utils.procedural.comms.CommsPromise:
    """Present the comms buttons. and wait for a choice.
    The timeout can be any promise, but typically is a made using the timeout function.
    
    Args:
        buttons (dict, optional): An dict of button dat key = button properties value label to process button press
        timeout (Promise, optional): The comms will end if this promise finishes. Defaults to None.
    
    Returns:
        Promise: A Promise that finishes when a comms button is selected"""
def comms_add_button (message, label=None, color=None, data=None, path=None) -> None:
    ...
def comms_broadcast (ids_or_obj, msg, color=None) -> None:
    """Send text to the text waterfall
    The ids can be player ship ids or client/console ids
    
    Args:
        ids_or_obj (id or objecr): A set or single id or object to send to,
        msg (str): The text to send
        color (str, optional): The Color for the text. Defaults to "#fff"."""
def comms_info (name, face=None, color=None) -> None:
    """Set the communication information status in the comms console
    
    Args:
        name (str): The name to present
        face (str, optional): The face string of the face. Defaults to None.
        color (str, optional): The colot of the text. Defaults to None."""
def comms_info_face_override (face=None) -> None:
    ...
def comms_message (msg, from_ids_or_obj, to_ids_or_obj, title=None, face=None, color=None, title_color=None, is_receive=True, from_name=None) -> None:
    """Send a Comms message
    This is a lower level function that lets you have more control the sender and receiver
    
    Args:
        msg (str): The message to send
        from_ids_or_obj (idset): The senders of the message
        to_ids_or_obj (idset): The set or receivers
        title (str, optional): The title text. Defaults to None.
        face (str, optional): The face string to use. Defaults to None.
        color (str, optional): The color of the body text. Defaults to "#fff".
        title_color (str, optional): The color of the title text. Defaults to None."""
def comms_navigate (path, face=None, comms_badge=None) -> None:
    """Change the comms path for what buttons to present
    
    Args:
        path (str): _description_
        face (str, optional): _description_. Defaults to None."""
def comms_navigate_override (ids_or_obj, sel_ids_or_obj, path=None, path_must_match=True) -> None:
    """Change the comms path for what buttons to present for specific comms
    pair. You need the two things in the relationship.
    If the things are selected in comms, this is a way to refresh the buttons.
    If the code is in the comms for the things involved, just use comms_navigate
    This is for a non comms task
    
    Args:
        ids_or_obj(id| set| list): The id, set of ids, or list of objects of player ships
        sel_ids_or_obj(id| set| list): The id, set of ids, or list of objects of other ship
        path (str): if none it will use the current path
        path_must_match (bool): Typically the path must match to avoid player confusion"""
def comms_override (origin_id=None, selected_id=None, face=None, from_name=None):
    ...
def comms_receive (msg, title=None, face=None, color=None, title_color=None) -> None:
    """Receive a message on a player ship from another ship
    It uses the current context to determine the sender and receiver.
    typically from the event that it being handled provide the context.
    
    Args:
        msg (str): The message to send
        title (str, optional):The title text. Defaults to None.
        face (str, optional): The face string of the face to use. Defaults to None.
        color (str, optional): The body text color. Defaults to "#fff".
        title_color (str, optional): The title text color. Defaults to None."""
def comms_receive_internal (msg, ids_or_obj=None, from_name=None, title=None, face=None, color=None, title_color=None) -> None:
    """Receiver a message within a player ship
    It uses the current context to determine the sender and receiver.
    typically from the event that it being handled provide the context.
    
    Args:
        msg (str): The message to send
        title (str, optional):The title text. Defaults to None.
        face (str, optional): The face string of the face to use. Defaults to None.
        color (str, optional): The body text color. Defaults to "#fff".
        title_color (str, optional): The title text color. Defaults to None."""
def comms_set_2dview_focus (client_id, focus_id=0, EVENT=None):
    ...
def comms_speech_bubble (msg, seconds=3, color=None, client_id=None, selected_id=None) -> None:
    """Transmits a message from a player ship
    It uses the current context to determine the sender and receiver.
    typically from the event that it being handled provide the context.
    
    Args:
        msg (str): The message to send
        title (str, optional):The title text. Defaults to None.
        face (str, optional): The face string of the face to use. Defaults to None.
        color (str, optional): The body text color. Defaults to "#fff".
        title_color (str, optional): The title text color. Defaults to None."""
def comms_story_buttons (ids, sel_ids, buttons, path, nav_button=None) -> sbs_utils.procedural.comms.CommsChoiceButtonPromise:
    ...
def comms_transmit (msg, title=None, face=None, color=None, title_color=None) -> None:
    """Transmits a message from a player ship
    It uses the current context to determine the sender and receiver.
    typically from the event that it being handled provide the context.
    
    Args:
        msg (str): The message to send
        title (str, optional):The title text. Defaults to None.
        face (str, optional): The face string of the face to use. Defaults to None.
        color (str, optional): The body text color. Defaults to "#fff".
        title_color (str, optional): The title text color. Defaults to None."""
def comms_transmit_internal (msg, ids_or_obj=None, to_name=None, title=None, face=None, color=None, title_color=None) -> None:
    """Transmits a message within a player ship
    It uses the current context to determine the sender and receiver.
    typically from the event that it being handled provide the context.
    
    Args:
        msg (str): The message to send
        title (str, optional):The title text. Defaults to None.
        face (str, optional): The face string of the face to use. Defaults to None.
        color (str, optional): The body text color. Defaults to "#fff".
        title_color (str, optional): The title text color. Defaults to None."""
def create_comms_label ():
    ...
def create_grid_comms_label ():
    ...
def get_comms_selection (id_or_not):
    """Gets the id of the comms selection
    Args:
        id_or_not (Agent | int): agent id or object
    Returns:
        int | None: The agent id or None"""
def get_inventory_value (id_or_object, key: str, default=None):
    """get inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
    
    Args:
        id_or_obj (Agent | int): The agent id or object to check
        key (str): The key/name of the inventory item
        default (any): the default value data
    Returns:
        any: The inventory value associated with the provided key, or the default value if it doesn't exist."""
def gui_properties_set (p=None, tag=None):
    ...
def has_role (so, role):
    """Check if an agent has the specified role.
    
    Args:
        so (Agent | int): An agent or id.
        role (str): The role to test for
    
    Returns:
        bool: True if the agent has that role"""
def labels_get_type (label_type):
    ...
def role_are_allies (id_or_obj, other_id_or_obj):
    """Check if the two objects are allied.
    
    Args:
        id_or_obj (Agent | int): The first object.
        other_id_or_obj (Agent | int): The second object.
    Returns:
        bool: True if they are allied."""
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
def start_comms_common_selected (event, is_grid):
    ...
def start_comms_selected (event):
    ...
def start_grid_comms_selected (event):
    ...
def task_all (*args, **kwargs) -> sbs_utils.procedural.execution.TaskPromiseAllAny:
    """Creates a task for each argument that is a label. Also supports a data named argument to pass the data to all the tasks.
    
    Args:
        args (0..n labels): the labels to schedule.
        data (dict): keyword arg to pass data to the tasks.
    Returns:
        Promise: A promise that is finished when all tasks are completed."""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Converts the item passed to an agent
    ??? note
    * Return of None could mean the agent no longer exists
    Args:
        other (Agent | CloseData | int): The agent ID or other agent like data
    Returns:
        Agent | None: The agent or None"""
def to_object_list (the_set):
    """Converts a set to a list of objects
    Args:
        the_set (set[Agent | int] | list[Agent | int]): a set or list of agents or ids
    Returns:
        list[Agent]: A list of Agent objects"""
class CommsChoiceButtonPromise(Promise):
    """class CommsChoiceButtonPromise"""
    def __init__ (self, buttons, path, nav_button):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def get_buttons (self, path):
        ...
    def set_result (self, result):
        ...
class CommsOverride(object):
    """class CommsOverride"""
    def __enter__ (self):
        ...
    def __exit__ (self, ex_type=None, ex_val=None, ex_tb=None):
        ...
    def __init__ (self, origin_id=None, selected_id=None, face=None, from_name=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def active ():
        ...
class CommsPromise(ButtonPromise):
    """class CommsPromise"""
    def __init__ (self, path, task, timeout=None) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def build_promise_buttons (self):
        ...
    def clear (self) -> None:
        ...
    def collect (self) -> bool:
        ...
    def handle_button_sub_task (self, sub_task):
        ...
    def initial_poll (self) -> None:
        ...
    def leave (self) -> None:
        ...
    def message (self, event) -> None:
        ...
    def poll (self):
        ...
    def post_button_run (self, button):
        ...
    def pre_button_run (self, button):
        ...
    def pressed_set_values (self, task) -> None:
        ...
    def pressed_test (self) -> bool:
        ...
    def process_on_change (self) -> None:
        ...
    def selected (self, event) -> None:
        ...
    def set_buttons (self, origin_id, selected_id) -> None:
        ...
    def set_comms_badge (self, comms_badge):
        ...
    def set_face_override (self, face):
        ...
    def set_path (self, path) -> None:
        ...
    def show_buttons (self) -> None:
        ...
