import sbs
class Widget:
    """ A interface class for creating GUI widgets i.e. composite components.

    """
    def __init__(self, left, top, tag_prefix) -> None:
        """ Widget init

        Called to have the page create and update the gui content it is presenting

        :param left: left coordinate
        :type left: float
        :param top: top coordinate
        :type top: float
        :param tag_prefix: Prefix to use in message tags to mak this component unique
        :type tag_prefix: str
        """
        self.tag_prefix = tag_prefix
        self.left= left
        self.top = top

    def present(self, sim, event):
        """ present

        Called to have the page create and update the gui content it is presenting

        :param sim: 
        :type sim: Artemis Cosmos simulation
        """
        pass

    def on_message(self, sim, event):
        """ on_message

        Called when a control on the page has been interacted with

        :param sim: 
        :type sim: Artemis Cosmos simulation
        :param message_tag: The tag name of the control interacted with
        :type message_tag: str
        :param clientID: The client ID that had the interaction
        :type clientID: int
        :param data: Any data associated with the control e.g. slider float value of current value
        :type clientID: None or str or float
        """
        pass

class Page:
    """ A interface class for creating GUI pages

    """

    def present(self, sim, event):
        """ present

        Called to have the page create and update the gui content it is presenting

        :param sim: 
        :type sim: Artemis Cosmos simulation
        """
        pass

    def on_pop(self, sim):
        pass

    def on_message(self, sim, event):
        """ on_message

        Called when a control on the page has been interacted with

        :param sim: 
        :type sim: Artemis Cosmos simulation
        :param message_tag: The tag name of the control interacted with
        :type message_tag: str
        :param clientID: The client ID that had the interaction
        :type clientID: int
        :param data: Any data associated with the control e.g. slider float value of current value
        :type clientID: None or str or float
        """
        pass


class GuiClient:
    """ Manages the pages for a client

    """
    def __init__(self, client_id):
        self.page_stack = []
        self.client_id = client_id

    def push(self, sim, page):
        """ push

        Presents the new Page by pushing it on the stack. 

        :param sim: 
        :type sim: Artemis Cosmos simulation
        :param page: 
        :type Page: A GUI Page
        """
        event = FakeEvent(self.client_id)
        self.page_stack.append(page)
        self.present(sim, event)

    def pop(self, sim):
        """ pop

        Stops presenting the current page and return to the previous one

        :param sim: 
        :type sim: Artemis Cosmos simulation
        """
        sbs.send_gui_clear(self.client_id)
        if len(self.page_stack) > 0:
            ret = self.page_stack.pop()
            if len(self.page_stack) > 0:
                self.page_stack[-1].on_pop(sim)



        event = FakeEvent(self.client_id)
        self.present(sim, event)
        return ret

    def present(self, sim,  event):
        """ present

        Presents the top Page for the specified clientID by calling present on that page

        :param sim: 
        :type sim: Artemis Cosmos simulation
        :param CID: Client ID
        :type int: A client ID
        """
        if len(self.page_stack) > 0:
            self.page_stack[-1].present(sim, event)

  
    def on_message(self, sim, event):
        """ on_message

        Calls the on_message on the top page of the specified client by calling on_message

        :param sim: 
        :type sim: Artemis Cosmos simulation
        :param message_tag: The tag name of the control interacted with
        :type message_tag: str
        :param clientID: The client ID that had the interaction
        :type clientID: int
        :param data: Any data associated with the control e.g. slider float value of current value
        :type clientID: None or str or float
        """
        if len(self.page_stack) > 0:
            self.page_stack[-1].on_message(sim, event)

class FakeEvent:
    def __init__(self, client_id):
        self.client_id = client_id


class Gui:
    """ class GUI
    Manages the GUI pages for all clients
    """
    clients = {0: GuiClient(0)}
    _server_start_page = None
    _client_start_page = None

    @staticmethod
    def server_start_page_class(cls_page):
        """ server start page

        Called in the script.py to set the start page for the server.
        this is called once in the script.py

        :param cls_page:  The class of the page to create
        :type class: A python class typically a Page
        """
        Gui._server_start_page = cls_page
        Gui.push(None, 0, cls_page())

    @staticmethod
    def client_start_page_class(cls_page):
        """ client start page

        Called in the script.py to set the start page for clients.
        this is called once in the script.py

        :param cls_page:  The class of the page to create
        :type class: A python class typically a Page
        """
        Gui._client_start_page = cls_page

    @staticmethod
    def add_client(sim, event):
        """ add_client

        Call when a new client connects.
        handlerhooks.py will call this in HandleClientConnect

        :param clientID: called to add a new client
        :type int: client id from the engine
        """
        if Gui._client_start_page is not None:
            Gui.push(sim, event.client_id, Gui._client_start_page())

    @staticmethod
    def push(sim, client_id, page):
        """ push

        Presents the new Page on the specified client by pushing it on the stack. 

        :param sim: 
        :type sim: Artemis Cosmos simulation
        :param clientID: called to add a new client
        :type int: client id from the engine
        :param page: 
        :type Page: A GUI Page
        
        """
        gui = Gui.clients.get(client_id)
        if gui is not None:
            gui.push(sim, page)
        else:
            gui = GuiClient(client_id)
            Gui.clients[client_id] = gui
            gui.push(sim, page)

    @staticmethod
    def pop(sim, client_id):
        gui = Gui.clients.get(client_id)
        if gui is not None:
            return gui.pop(sim)
            
        return None

    @staticmethod
    def present(sim, event):
        """ present

        calls present on all clients
        handlerhooks.py will call this in HandlePresentGUI

        :param sim: 
        :type sim: Artemis Cosmos simulation
        """
        Gui.represent = set()
        Gui.represent_throttle = 0
        for client_id, gui in Gui.clients.items():
            event = FakeEvent(client_id)
            gui.present(sim, event)
        # Try to repaint things we can this round
        Gui.present_dirty(sim)

    @staticmethod
    def dirty(client_id):
        Gui.represent.add(client_id)

    @staticmethod
    def present_dirty(sim):
        if len(Gui.represent) <1:
            return

        # Ideally this is only called once per 'tick'
        # but account for cascading repaints, but limit it
        # to avoid infinite loop
        if Gui.represent_throttle > 5:
            return

        Gui.represent_throttle += 1
        dirty = list(Gui.represent)
        Gui.represent = set()
        for client_id in dirty:
            gui = Gui.clients.get(client_id)
            event = FakeEvent(client_id)
            gui.present(sim, event)
        Gui.present_dirty()

        

    @staticmethod
    def on_message(sim, event):
        """ on_message

        Forward to the appropriate GuiClient/Page
        handlerhooks.py will call this in HandlePresentGUIMessage

        :param sim: 
        :type sim: Artemis Cosmos simulation
        :param message_tag: The tag name of the control interacted with
        :type message_tag: str
        :param clientID: The client ID that had the interaction
        :type clientID: int
        :param data: Any data associated with the control e.g. slider float value of current value
        :type clientID: None or str or float
        """
        # message_tag, clientID, data
        gui = Gui.clients.get(event.client_id)
        if gui is not None:
            gui.on_message(sim, event)
            
