from sbs_utils.agent import Agent
from sbs_utils.mast.maststory import AppendText
from sbs_utils.mast.maststory import CommsMessageStart
from sbs_utils.mast.maststory import Text
from sbs_utils.helpers import FakeEvent
from sbs_utils.helpers import FrameContext
from sbs_utils.gui import Gui
from sbs_utils.mast.mast import Mast
from sbs_utils.mast.mast import Scope
from sbs_utils.mast.mastscheduler import MastAsyncTask
from sbs_utils.mast.mastscheduler import MastRuntimeNode
from sbs_utils.mast.mastscheduler import MastScheduler
from sbs_utils.mast.pollresults import PollResults
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
def format_exception (message, source):
    ...
def gui_text_area (props, style=None):
    """Add a gui text object
    
    valid properties
        text
        color
        font
    
    
    props (str): property string
    style (style, optional): The style"""
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
class AppendTextRuntimeNode(MastRuntimeNode):
    """class AppendTextRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.AppendText):
        ...
class CommsMessageStartRuntimeNode(MastRuntimeNode):
    """class CommsMessageStartRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.CommsMessageStart):
        ...
class SkipBlockRuntimeNode(MastRuntimeNode):
    """class SkipBlockRuntimeNode"""
    def poll (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node):
        ...
class StoryScheduler(MastScheduler):
    """class StoryScheduler"""
    def __init__ (self, mast: sbs_utils.mast.mast.Mast, overrides=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _add (id, obj):
        ...
    def _remove (id):
        ...
    def clear ():
        ...
    def get (id):
        ...
    def get_as (id, as_cls):
        ...
    def get_objects_from_set (the_set):
        ...
    def get_role_object (link_name):
        ...
    def get_role_objects (role):
        ...
    def get_role_set (role):
        ...
    def get_symbols (self):
        ...
    def get_value (self, key, defa=None):
        """_summary_
        
        Args:
            key (_type_): _description_
            defa (_type_, optional): _description_. Defaults to None.
        
        Returns:
            _type_: _description_"""
    def has_inventory_list (collection_name):
        ...
    def has_inventory_set (collection_name):
        ...
    def has_links_list (collection_name):
        ...
    def has_links_set (collection_name):
        ...
    def is_server (self):
        ...
    def refresh (self, label):
        ...
    def resolve_id (other: 'Agent | CloseData | int'):
        ...
    def resolve_py_object (other: 'Agent | CloseData | int'):
        ...
    def run (self, client_id, page, label='main', inputs=None, task_name=None, defer=False):
        ...
    def runtime_error (self, message):
        ...
    def set_value (self, key, value, scope):
        ...
    def story_tick_tasks (self, client_id):
        ...
class TextRuntimeNode(MastRuntimeNode):
    """class TextRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.Text):
        ...
