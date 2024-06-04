from sbs_utils.agent import Agent
from sbs_utils.helpers import FrameContext
def get_inventory_value (id_or_object, key, default=None):
    """get inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
    
    Args:
        id_or_obj (agent): The agent id or object to check
        key (str): The key/name of the inventory item
        default (any): the default value data"""
class ConsoleDispatcher(object):
    """class ConsoleDispatcher"""
    def add_always_select (console: str, cb: callable):
        """add a target for console selection
        :param console: The consoles unique ID
        :type console: string
        :param cb: call back function
        :type cb:  should have arguments of other ctx and object's id"""
    def add_default_message (console: str, cb: callable):
        """add a target for console message
        
        :param console: The consoles unique ID
        :type console: string
        :param cb: call back function
        :type cb:  should have arguments of other ctx, message and object's id"""
    def add_default_select (console: str, cb: callable):
        """add a target for console selection
        :param console: The consoles unique ID
        :type console: string
        :param cb: call back function
        :type cb:  should have arguments of other ctx and object's id"""
    def add_message (an_id: int, console: str, cb: callable):
        """add a target for console message
        
        :param an_id: A ships ID player or non-player
        :type an_id: int
        :param console: The consoles unique ID
        :type console: string
        :param cb: call back function
        :type cb:  should have arguments of other ctx, message and object's id"""
    def add_message_pair (an_id: int, another, console: str, cb: callable):
        """add a target for console message
        
        :param an_id: A ships ID player or non-player
        :type an_id: int
        :param console: The consoles unique ID
        :type console: string
        :param cb: call back function
        :type cb:  should have arguments of other ctx, message and object's id"""
    def add_select (an_id: int, console: str, cb: callable):
        """add a target for console selection
        
        :param an_id: A ships ID player or non-player
        :type an_id: int
        :param console: The consoles unique ID
        :type console: string
        :param cb: call back function
        :type cb:  should have arguments of other ctx and object's id"""
    def add_select_pair (an_id: int, another_id: int, console: str, cb: callable):
        """add a target for console selection
        
        :param an_id: A ships ID player or non-player
        :type an_id: int
        :param console: The consoles unique ID
        :type console: string
        :param cb: call back function
        :type cb:  should have arguments of other ctx and object's id"""
    def convert (event):
        ...
    def convert_to_console_id (event):
        ...
    def dispatch_message (event, console):
        """dispatches a console message
        
        :param message_tag: The message
        :type message_tag: string
        :param player_id: A player ship ID
        :type player_id: int
        :param console: The consoles unique ID
        :type console: string
        :param other_id: A non player ship ID player
        :type other_id: int"""
    def dispatch_select (event):
        """dispatches a console selection
        
        :param player_id: A player ship ID
        :type player_id: int
        :param console: The consoles unique ID
        :type console: string
        :param other_id: A non player ship ID player
        :type other_id: int"""
    def do_select (event, console):
        ...
    def remove_message (an_id: int, console: str, cb=None):
        """remove a target for console messages
        
        :param an_id: A ships ID player or non-player
        :type an_id: int
        :param console: The consoles unique ID
        :type console: string"""
    def remove_message_pair (an_id: int, another_id: int, console: str):
        """remove a target for console messages
        
        :param an_id: A ships ID player or non-player
        :type an_id: int
        :param console: The consoles unique ID
        :type console: string"""
    def remove_select (an_id: int, console: str, cb=None):
        """remove a target for console selection
        
        :param an_id: A ships ID player or non-player
        :type an_id: int
        :param console: The consoles unique ID
        :type console: string"""
    def remove_select_pair (an_id: int, another_id: int, console: str):
        """remove a target for console selection
        
        :param an_id: A ships ID player or non-player
        :type an_id: int
        :param console: The consoles unique ID
        :type console: string"""
class MCommunications(object):
    """class MCommunications"""
    def comms_message (self, message, an_id, event):
        """handle a comms message
        
        :param message_tag: The message
        :type message_tag: string
        :param an_id: The other ship involved
        :type an_id: int"""
    def comms_selected (self, an_id, event):
        """handle a comms selection
        :param an_id: The other ship involved
        :type an_id: int"""
    def enable_comms (self, face_desc=None):
        """includes in ConsoleDispatch system
        
        :param face_desc: Face Description
        :type face_desc: string"""
