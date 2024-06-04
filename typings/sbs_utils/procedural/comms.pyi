from sbs_utils.agent import Agent
from sbs_utils.mast.mast import Button
from sbs_utils.procedural.gui import ButtonPromise
from sbs_utils.mast.mastscheduler import ChangeRuntimeNode
from sbs_utils.consoledispatcher import ConsoleDispatcher
from sbs_utils.helpers import FrameContext
from sbs_utils.mast.pollresults import PollResults
def _comms_get_origin_id ():
    ...
def _comms_get_selected_id ():
    ...
def comms (path=None, buttons=None, timeout=None):
    """Present the comms buttons. and wait for a choice.
    The timeout can be any promise, but typically is a made using the timeout function.
    
    Args:
        buttons (dict, optional): An dict of button dat key = button properties value label to process button press
        timeout (Promise, optional): The comms will end if this promise finishes. Defaults to None.
    
    Returns:
        Promise: A Promise that finishes when a comms button is selected"""
def comms_add_button (message, label=None, color=None, data=None, path=None):
    ...
def comms_broadcast (ids_or_obj, msg, color='#fff'):
    """Send text to the text waterfall
    The ids can be player ship ids or client/console ids
    
    Args:
        ids_or_obj (id or objecr): A set or single id or object to send to,
        msg (str): The text to send
        color (str, optional): The Color for the text. Defaults to "#fff"."""
def comms_info (name, face=None, color=None):
    """Set the communication information status in the comms console
    
    Args:
        name (str): The name to present
        face (str, optional): The face string of the face. Defaults to None.
        color (str, optional): The colot of the text. Defaults to None."""
def comms_message (msg, from_ids_or_obj, to_ids_or_obj, title=None, face=None, color='#fff', title_color=None, is_receive=True, from_name=None):
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
def comms_navigate (path):
    ...
def comms_receive (msg, title=None, face=None, color='#fff', title_color=None):
    """Receive a message on a player ship from another ship
    It uses the current context to determine the sender and receiver.
    typically from the event that it being handled provide the context.
    
    Args:
        msg (str): The message to send
        title (str, optional):The title text. Defaults to None.
        face (str, optional): The face string of the face to use. Defaults to None.
        color (str, optional): The body text color. Defaults to "#fff".
        title_color (str, optional): The title text color. Defaults to None."""
def comms_receive_internal (msg, ids_or_obj=None, from_name=None, title=None, face=None, color='#fff', title_color=None):
    """Receiver a message within a player ship
    It uses the current context to determine the sender and receiver.
    typically from the event that it being handled provide the context.
    
    Args:
        msg (str): The message to send
        title (str, optional):The title text. Defaults to None.
        face (str, optional): The face string of the face to use. Defaults to None.
        color (str, optional): The body text color. Defaults to "#fff".
        title_color (str, optional): The title text color. Defaults to None."""
def comms_transmit (msg, title=None, face=None, color='#fff', title_color=None):
    """Transmits a message from a player ship
    It uses the current context to determine the sender and receiver.
    typically from the event that it being handled provide the context.
    
    Args:
        msg (str): The message to send
        title (str, optional):The title text. Defaults to None.
        face (str, optional): The face string of the face to use. Defaults to None.
        color (str, optional): The body text color. Defaults to "#fff".
        title_color (str, optional): The title text color. Defaults to None."""
def comms_transmit_internal (msg, ids_or_obj=None, to_name=None, title=None, face=None, color='#fff', title_color=None):
    """Transmits a message within a player ship
    It uses the current context to determine the sender and receiver.
    typically from the event that it being handled provide the context.
    
    Args:
        msg (str): The message to send
        title (str, optional):The title text. Defaults to None.
        face (str, optional): The face string of the face to use. Defaults to None.
        color (str, optional): The body text color. Defaults to "#fff".
        title_color (str, optional): The title text color. Defaults to None."""
def get_inventory_value (id_or_object, key, default=None):
    """get inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
    
    Args:
        id_or_obj (agent): The agent id or object to check
        key (str): The key/name of the inventory item
        default (any): the default value data"""
def has_role (so, role):
    """check if an agent has a role
    
    Args:
        so (an agent): an agent id or object
        role (str): the role to test for
    
    Returns:
        bool: if the agent has that role"""
class CommsPromise(ButtonPromise):
    """class CommsPromise"""
    def __init__ (self, path, task, timeout=None) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def clear (self):
        ...
    def comms_message (self, event):
        ...
    def comms_selected (self, event):
        ...
    def initial_poll (self):
        ...
    def leave (self):
        ...
    def poll (self):
        ...
    def process_on_change (self):
        ...
    def set_buttons (self, origin_id, selected_id):
        ...
    def set_path (self, path):
        ...
    def show_buttons (self):
        ...
