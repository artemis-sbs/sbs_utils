class Context(object):
    """class Context"""
    def __init__ (self, sim, _sbs, aspect_ratio):
        """Initialize self.  See help(type(self)) for accurate signature."""
class FakeEvent(object):
    """class FakeEvent"""
    def __init__ (self, client_id, tag, sub_tag=''):
        """Initialize self.  See help(type(self)) for accurate signature."""
class Gui(object):
    """class GUI
    Manages the GUI pages for all clients"""
    def add_client (ctx, event):
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
    def on_event (ctx, event):
        """on_event
        
        Forward to the appropriate GuiClient/Page
        handlerhooks.py will call this in HandleEvent
        
        :param ctx:
        :type ctx: Artemis Cosmos simulation
        :param event: The tag name of the control interacted with
        :type event: event"""
    def on_message (ctx, event):
        """on_message
        
        Forward to the appropriate GuiClient/Page
        handlerhooks.py will call this in HandlePresentGUIMessage
        
        :param ctx:
        :type ctx: Artemis Cosmos simulation
        :param event: The tag name of the control interacted with
        :type event: event"""
    def pop (ctx, client_id):
        ...
    def present (ctx, event):
        """present
        
        calls present on all clients
        handlerhooks.py will call this in HandlePresentGUI
        
        :param ctx:
        :type ctx: Artemis Cosmos simulation"""
    def present_dirty (ctx):
        ...
    def push (ctx, client_id, page):
        """push
        
        Presents the new Page on the specified client by pushing it on the stack.
        
        :param ctx:
        :type ctx: Artemis Cosmos simulation
        :param clientID: called to add a new client
        :type int: client id from the engine
        :param page:
        :type Page: A GUI Page"""
    def send_custom_event (ctx, tag, sub_tag=''):
        """on_event
        
        Forward to the appropriate GuiClient/Page
        handlerhooks.py will call this in HandleEvent
        
        :param ctx:
        :type ctx: Artemis Cosmos simulation
        :param event: The tag name of the control interacted with
        :type event: event"""
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
    def on_event (self, ctx, event):
        """on_event
        
        Calls the on_event on the top page of the specified client by calling on_event
        
        :param ctx:
        :type sim: Artemis Cosmos simulation
        :param event: The event data
        :type event: event"""
    def on_message (self, ctx, event):
        """on_message
        
        Calls the on_message on the top page of the specified client by calling on_message
        
        :param ctx:
        :type ctx: Artemis Cosmos simulation
        :param event: The event data
        :type event: event"""
    def pop (self, ctx):
        """pop
        
        Stops presenting the current page and return to the previous one
        
        :param ctx:
        :type ctx: Artemis Cosmos simulation"""
    def present (self, ctx, event):
        """present
        
        Presents the top Page for the specified clientID by calling present on that page
        
        :param ctx:
        :type ctx: Artemis Cosmos simulation
        :param CID: Client ID
        :type int: A client ID"""
    def push (self, ctx, page):
        """push
        
        Presents the new Page by pushing it on the stack.
        
        :param ctx:
        :type ctx: Artemis Cosmos simulation
        :param page:
        :type Page: A GUI Page"""
class Page(object):
    """A interface class for creating GUI pages
    
        """
    def on_event (self, ctx, event):
        """on_event
        
        Called when the option pages page has been interacted with
        
        :param ctx:
        :type ctx: Artemis Cosmos simulation
        :param event: The event data
        :type event: event"""
    def on_message (self, ctx, event):
        """on_message
        
        Called when the option pages page has been interacted with
        
        :param ctx:
        :type ctx: Artemis Cosmos simulation
        :param event: The event data
        :type event: event"""
    def on_pop (self, ctx):
        ...
    def present (self, ctx, event):
        """present
        
        Called to have the page create and update the gui content it is presenting
        
        :param ctx:
        :type ctx: Artemis Cosmos simulation"""
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
    def on_message (self, ctx, event):
        """on_message
        
        Called when a control on the page has been interacted with
        
        :param ctx:
        :type ctx: Artemis Cosmos simulation
        :param message_tag: The tag name of the control interacted with
        :type message_tag: str
        :param clientID: The client ID that had the interaction
        :type clientID: int
        :param data: Any data associated with the control e.g. slider float value of current value
        :type clientID: None or str or float"""
    def present (self, ctx, event):
        """present
        
        Called to have the page create and update the gui content it is presenting
        
        :param ctx:
        :type ctx: Artemis Cosmos simulation"""
