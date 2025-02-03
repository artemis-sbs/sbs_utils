from sbs_utils.mast_sbs.story_nodes.define_format import DefineFormat
from sbs_utils.mast.mast_node import DescribableNode
from sbs_utils.helpers import FrameContext
from sbs_utils.mast.mast_runtime_node import MastRuntimeNode
def STRING_REGEX_NAMED (name):
    ...
def comms_broadcast (ids_or_obj, msg, color='#fff'):
    """Send text to the text waterfall
    The ids can be player ship ids or client/console ids
    
    Args:
        ids_or_obj (id or objecr): A set or single id or object to send to,
        msg (str): The text to send
        color (str, optional): The Color for the text. Defaults to "#fff"."""
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
def comms_speech_bubble (msg, seconds=3, color='#fff', client_id=None, selected_id=None):
    """Transmits a message from a player ship
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
def mast_node (append=True):
    ...
def mast_runtime_node (parser_node):
    ...
def role (role: str):
    """returns a set of all the agents with a given role.
    
    Args:
        role (str): The role
    
    Returns:
        agent id set: a set of agent IDs"""
def scan_results (message, target=None, tab=None):
    """Set the scan results for the current scan. This should be called when the scan is completed.
       This is typically called as part of a scan()
       This could also be called in response to a routed science message.
       When pair with a scan() the target and tab are not need.
       Tab is the variable __SCAN_TAB__, target is track
    
    Args:
        message (str): scan text for a scan the is in progress
        tab (str): scan tab for a scan the is in progress"""
class CommsMessageStart(DescribableNode):
    """class CommsMessageStart"""
    def __init__ (self, mtype, title, q=None, format=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def create_end_node (self, loc, dedent_obj, compile_info):
        ...
    def is_indentable (self):
        ...
    def parse (lines):
        ...
    def post_dedent (self, compile_info):
        ...
class CommsMessageStartRuntimeNode(MastRuntimeNode):
    """class CommsMessageStartRuntimeNode"""
    def enter (self, mast: 'Mast', task: 'MastAsyncTask', node: sbs_utils.mast_sbs.story_nodes.comms_message.CommsMessageStart):
        ...
