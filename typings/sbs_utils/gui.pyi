class FakeEvent(object):
    """class FakeEvent"""
    def __init__ (self, client_id):
        """Initialize self.  See help(type(self)) for accurate signature."""
class Gui(object):
    """class GUI
    Manages the GUI pages for all clients"""
    def add_client (sim, event):
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
    def on_message (sim, event):
        """on_message
        
        Forward to the appropriate GuiClient/Page
        handlerhooks.py will call this in HandlePresentGUIMessage
        
        :param sim:
        :type sim: Artemis Cosmos simulation
        :param message_tag: The tag name of the control interacted with
        :type message_tag: str
        :param clientID: The client ID that had the interaction
        :type clientID: int
        :param data: Any data associated with the control e.g. slider float value of current value
        :type clientID: None or str or float"""
    def pop (sim, client_id):
        ...
    def present (sim, event):
        """present
        
        calls present on all clients
        handlerhooks.py will call this in HandlePresentGUI
        
        :param sim:
        :type sim: Artemis Cosmos simulation"""
    def push (sim, client_id, page):
        """push
        
        Presents the new Page on the specified client by pushing it on the stack.
        
        :param sim:
        :type sim: Artemis Cosmos simulation
        :param clientID: called to add a new client
        :type int: client id from the engine
        :param page:
        :type Page: A GUI Page"""
    def server_start_page_class (cls_page):
        """server start page
        
        Called in the script.py to set the start page for the server.
        this is called once in the script.py
        
        :param cls_page:  The class of the page to create
        :type class: A python class typically a Page"""
class GuiClient(object):
    """Manages the pages for a client
    
        """
    def __init__ (self, client_id):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def on_message (self, sim, event):
        """on_message
        
        Calls the on_message on the top page of the specified client by calling on_message
        
        :param sim:
        :type sim: Artemis Cosmos simulation
        :param message_tag: The tag name of the control interacted with
        :type message_tag: str
        :param clientID: The client ID that had the interaction
        :type clientID: int
        :param data: Any data associated with the control e.g. slider float value of current value
        :type clientID: None or str or float"""
    def on_pop (self, sim):
        ...
    def pop (self, sim):
        """pop
        
        Stops presenting the current page and return to the previous one
        
        :param sim:
        :type sim: Artemis Cosmos simulation"""
    def present (self, sim, event):
        """present
        
        Presents the top Page for the specified clientID by calling present on that page
        
        :param sim:
        :type sim: Artemis Cosmos simulation
        :param CID: Client ID
        :type int: A client ID"""
    def push (self, sim, page):
        """push
        
        Presents the new Page by pushing it on the stack.
        
        :param sim:
        :type sim: Artemis Cosmos simulation
        :param page:
        :type Page: A GUI Page"""
class Page(object):
    """A interface class for creating GUI pages
    
        """
    def on_message (self, sim, event):
        """on_message
        
        Called when a control on the page has been interacted with
        
        :param sim:
        :type sim: Artemis Cosmos simulation
        :param message_tag: The tag name of the control interacted with
        :type message_tag: str
        :param clientID: The client ID that had the interaction
        :type clientID: int
        :param data: Any data associated with the control e.g. slider float value of current value
        :type clientID: None or str or float"""
    def present (self, sim, event):
        """present
        
        Called to have the page create and update the gui content it is presenting
        
        :param sim:
        :type sim: Artemis Cosmos simulation"""
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
    def on_message (self, sim, event):
        """on_message
        
        Called when a control on the page has been interacted with
        
        :param sim:
        :type sim: Artemis Cosmos simulation
        :param message_tag: The tag name of the control interacted with
        :type message_tag: str
        :param clientID: The client ID that had the interaction
        :type clientID: int
        :param data: Any data associated with the control e.g. slider float value of current value
        :type clientID: None or str or float"""
    def present (self, sim, event):
        """present
        
        Called to have the page create and update the gui content it is presenting
        
        :param sim:
        :type sim: Artemis Cosmos simulation"""
