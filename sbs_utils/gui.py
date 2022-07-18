

class Page:
    def present(self, sim):
        pass
    def on_message(self, sim, message_tag, clientID):
        pass


class GuiClient:
    def __init__(self, clientID):
        self.page_stack= []
        self.clientID = clientID


    def push(self, sim, page):
        self.page_stack.append(page)
        self.present(sim, self.clientID)

    def pop(self,sim):
        self.page_stack.pop()
        self.present(sim, self.clientID)

    def present(self, sim, CID):
        if len(self.page_stack)>0:
            self.page_stack[-1].present(sim, CID)

    def on_message(self, sim, message_tag, clientID):
        if len(self.page_stack)>0:
            self.page_stack[-1].on_message(sim, message_tag, clientID)

class Gui:
    clients = {0: GuiClient(0)}
    _server_start_page = None
    _client_start_page = None



    @staticmethod
    def server_start_page_class(cls_page):
        Gui._server_start_page = cls_page
        Gui.push(None, 0, cls_page())

    @staticmethod
    def client_start_page_class(cls_page):
        Gui._client_start_page = cls_page

    @staticmethod
    def add_client(sim, clientID):
        if Gui._client_start_page is not None:
            Gui.push(sim, clientID, Gui._client_start_page())


    @staticmethod
    def push(sim, clientID, page):
        gui = Gui.clients.get(clientID)
        if gui is not None:
            gui.push(sim,page)
        else:
            gui = GuiClient(clientID)
            Gui.clients[clientID] = gui
            gui.push(sim,page)

    @staticmethod
    def pop(sim, clientID):
        gui = Gui.clients.get(clientID)
        if gui is not None:
            gui.pop(sim)


    @staticmethod
    def present(sim):
        for clientId, gui in Gui.clients.items():
            gui.present(sim, clientId)

    @staticmethod
    def on_message(sim, message_tag, clientID):
        gui = Gui.clients.get(clientID)
        if gui is not None:
            gui.on_message(sim, message_tag, clientID)

    