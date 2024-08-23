from sbs_utils.agent import Agent
from sbs_utils.helpers import FakeEvent
from sbs_utils.helpers import FrameContext
from sbs_utils.vec import Vec3
def get_client_aspect_ratio (cid):
    ...
class Gui(object):
    """class GUI
    Manages the GUI pages for all clients"""
    def add_client (event):
        """add_client
        
        Call when a new client connects.
        handlerhooks.py will call this in HandleClientConnect
        
        :param clientID: called to add a new client
        :type int: client id from the engine"""
    def client_start_page_class (cls_page):
        """client start page
        
        Called in the script.py to set the start page for clients.
        this is called once in the script.py
        
        :param cls_page:  The class of the page to create
        :type class: A python class typically a Page"""
    def dirty (client_id):
        ...
    def on_event (event):
        """on_event
        
        Forward to the appropriate GuiClient/Page
        handlerhooks.py will call this in HandleEvent
        
        :param event: The tag name of the control interacted with
        :type event: event"""
    def on_message (event):
        """on_message
        
        Forward to the appropriate GuiClient/Page
        handlerhooks.py will call this in HandlePresentGUIMessage
        
        :param event: The tag name of the control interacted with
        :type event: event"""
    def pop (client_id):
        ...
    def present (event):
        """present
        
        calls present on all clients
        handlerhooks.py will call this in HandlePresentGUI"""
    def present_dirty ():
        ...
    def push (client_id, page):
        """push
        
        Presents the new Page on the specified client by pushing it on the stack.
        
        :param clientID: called to add a new client
        :type int: client id from the engine
        :param page:
        :type Page: A GUI Page"""
    def send_custom_event (tag, sub_tag=''):
        """on_event
        
        Forward to the appropriate GuiClient/Page
        handlerhooks.py will call this in HandleEvent
        
        :param event: The tag name of the control interacted with
        :type event: event"""
    def server_start_page_class (cls_page):
        """server start page
        
        Called in the script.py to set the start page for the server.
        this is called once in the script.py
        
        :param cls_page:  The class of the page to create
        :type class: A python class typically a Page"""
class GuiClient(Agent):
    """Manages the pages for a client
    
        """
    def __init__ (self, client_id):
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
    def has_inventory_list (collection_name):
        ...
    def has_inventory_set (collection_name):
        ...
    def has_links_list (collection_name):
        ...
    def has_links_set (collection_name):
        ...
    def on_event (self, event):
        """on_event
        
        Calls the on_event on the top page of the specified client by calling on_event
        
        :param event: The event data
        :type event: event"""
    def on_message (self, event):
        """on_message
        
        Calls the on_message on the top page of the specified client by calling on_message
        
        :param event: The event data
        :type event: event"""
    @property
    def page (self):
        ...
    def pop (self):
        """pop
        
        Stops presenting the current page and return to the previous one"""
    def present (self, event):
        """present
        
        Presents the top Page for the specified clientID by calling present on that page
        
        :param CID: Client ID
        :type int: A client ID"""
    def push (self, page):
        """push
        
        Presents the new Page by pushing it on the stack.
        
        :param page:
        :type Page: A GUI Page"""
    def resolve_id (other: 'Agent | CloseData | int'):
        ...
    def resolve_py_object (other: 'Agent | CloseData | int'):
        ...
    def tick_gui_task (self):
        """present
        
        Presents the top Page for the specified clientID by calling present on that page
        
        :param CID: Client ID
        :type int: A client ID"""
class Page(object):
    """A interface class for creating GUI pages
    
        """
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
    def on_pop (self):
        ...
    def present (self, event):
        """present
        
        Called to have the page create and update the gui content it is presenting"""
    @property
    def task (self):
        ...
    def tick_gui_task (self):
        """tick_gui_task
        
        Called to have the page run any tasks they have prior to present"""
class Widget(object):
    """A interface class for creating GUI widgets i.e. composite components.
    
        """
    def __init__ (self, left, top, tag_prefix) -> None:
        """Widget init
        
        Called to have the page create and update the gui content it is presenting
        
        :param left: left coordinate
        :type left: float
        :param top: top coordinate
        :type top: float
        :param tag_prefix: Prefix to use in message tags to mak this component unique
        :type tag_prefix: str"""
    def calc_pixels_y (self, pixels):
        """present
        Called to have the page create and update the gui content it is presenting"""
    def on_message (self, event):
        """on_message
        
        Called when a control on the page has been interacted with
        
        :param message_tag: The tag name of the control interacted with
        :type message_tag: str
        :param clientID: The client ID that had the interactive
        :type clientID: int
        :param data: Any data associated with the control e.g. slider float value of current value
        :type clientID: None or str or float"""
    def present (self, event):
        """present
        
        Called to have the page create and update the gui content it is presenting"""
