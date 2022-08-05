

class Page:
    """ A interface class for creating GUI pages

    """

    def present(self, sim):
        """ present

        Called to have the page create and update the gui content it is presenting

        :param sim: 
        :type sim: Artemis Cosmos simulation
        """
        pass

    def on_message(self, sim, message_tag, clientID, data):
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


    def __init__(self, clientID):
        self.page_stack = []
        self.clientID = clientID

    def push(self, sim, page):
        """ push

        Presents the new Page by pushing it on the stack. 

        :param sim: 
        :type sim: Artemis Cosmos simulation
        :param page: 
        :type Page: A GUI Page
        """
        
        self.page_stack.append(page)
        self.present(sim, self.clientID)

    def pop(self, sim):
        """ pop

        Stops presenting the current page and return to the previous one

        :param sim: 
        :type sim: Artemis Cosmos simulation
        """
        ret = self.page_stack.pop()
        self.present(sim, self.clientID)
        return ret

    def present(self, sim, CID):
        """ present

        Presents the top Page for the specified clientID by calling present on that page

        :param sim: 
        :type sim: Artemis Cosmos simulation
        :param CID: Client ID
        :type int: A client ID
        """
        if len(self.page_stack) > 0:
            self.page_stack[-1].present(sim, CID)

    def on_message(self, sim, message_tag, clientID, data):
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
            self.page_stack[-1].on_message(sim, message_tag, clientID, data)


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
    def add_client(sim, clientID):
        """ add_client

        Call when a new client connects.
        handlerhooks.py will call this in HandleClientConnect

        :param clientID: called to add a new client
        :type int: client id from the engine
        """
        if Gui._client_start_page is not None:
            Gui.push(sim, clientID, Gui._client_start_page())

    @staticmethod
    def push(sim, clientID, page):
        """ push

        Presents the new Page on the specified client by pushing it on the stack. 

        :param sim: 
        :type sim: Artemis Cosmos simulation
        :param clientID: called to add a new client
        :type int: client id from the engine
        :param page: 
        :type Page: A GUI Page
        
        """
        gui = Gui.clients.get(clientID)
        if gui is not None:
            gui.push(sim, page)
        else:
            gui = GuiClient(clientID)
            Gui.clients[clientID] = gui
            gui.push(sim, page)

    @staticmethod
    def pop(sim, clientID):
        gui = Gui.clients.get(clientID)
        if gui is not None:
            return gui.pop(sim)
        return None

    @staticmethod
    def present(sim):
        """ present

        calls present on all clients
        handlerhooks.py will call this in HandlePresentGUI

        :param sim: 
        :type sim: Artemis Cosmos simulation
        """
        for clientId, gui in Gui.clients.items():
            gui.present(sim, clientId)

    @staticmethod
    def on_message(sim, message_tag, clientID, data):
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
        gui = Gui.clients.get(clientID)
        if gui is not None:
            gui.on_message(sim, message_tag, clientID, data)
