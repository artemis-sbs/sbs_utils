import sbs
from .agent import Agent
from .helpers import FakeEvent, FrameContext
from .vec import Vec3

        

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

    def present(self, event):
        """ present

        Called to have the page create and update the gui content it is presenting
        """
        pass

    def calc_pixels_y(self, pixels):
        """ present
        Called to have the page create and update the gui content it is presenting
        """
        aspect_ratio = FrameContext.aspect_ratio 

        

    def on_message(self, event):
        """ on_message

        Called when a control on the page has been interacted with

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

    def present(self, event):
        """ present

        Called to have the page create and update the gui content it is presenting
        """
        pass

    @property
    def task(self):
        return None

    def tick_gui_task(self):
        """ tick_gui_task

        Called to have the page run any tasks they have prior to present


        """
        pass

    def on_pop(self):
        pass

    def on_message(self, event):
        """ on_message

        Called when the option pages page has been interacted with

        :param event: The event data
        :type event: event
        """
        pass
    def on_event(self, event):
        """ on_event

        Called when the option pages page has been interacted with

        :param event: The event data
        :type event: event
        """
        pass


class GuiClient(Agent):
    """ Manages the pages for a client

    """
    def __init__(self, client_id):
        super().__init__()

        self.page_stack = []
        self.client_id = client_id
        self.id = client_id
        self.add()
        self.add_role("__gui__")
        self.aspect_ratio = Vec3(1024,768,1)

    def push(self, page):
        """ push

        Presents the new Page by pushing it on the stack. 

        :param page: 
        :type Page: A GUI Page
        """
        event = FakeEvent(self.client_id, "gui_push")
        #print(f"Pushing {self.client_id}")
        # page.aspect_ratio = sbs.vec3(self.aspect_ratio.x,self.aspect_ratio.y,self.aspect_ratio.z)
        self.page_stack.append(page)
        self.present(event)
        #print(f"After Pushing {self.client_id} {page.task.done()}")

    def pop(self):
        """ pop

        Stops presenting the current page and return to the previous one

        """
        ret = None
        sbs.send_gui_clear(self.client_id, "")
        if len(self.page_stack) > 0:
            ret = self.page_stack.pop()
            if ret:
                ret.on_pop()



        event = FakeEvent(self.client_id, "gui_pop")
        #print(f"popping {self.client_id}")
        self.present(event)
        return ret

    @property
    def page(self):
        if len(self.page_stack) > 0:
            page = self.page_stack[-1]
            return page
        return None


    def present(self, event):
        """ present

        Presents the top Page for the specified clientID by calling present on that page

        :param CID: Client ID
        :type int: A client ID
        """
        if len(self.page_stack) > 0:
            page = self.page_stack[-1]
            page.present(event)

    def tick_gui_task(self):
        """ present

        Presents the top Page for the specified clientID by calling present on that page

        :param CID: Client ID
        :type int: A client ID
        """
        if len(self.page_stack) > 0:
            self.page_stack[-1].tick_gui_task()

  
    def on_message(self, event):
        """ on_message

        Calls the on_message on the top page of the specified client by calling on_message

        :param event: The event data
        :type event: event
        
        """
        if len(self.page_stack) > 0:
            self.page_stack[-1].on_message(event)

    def on_event(self, event):
        """ on_event

        Calls the on_event on the top page of the specified client by calling on_event

        :param event: The event data
        :type event: event
        
        """
        # if event.client_id ==self.client_id and event.tag == "screen_size":
        #     sz = event.source_point
        #     if sz is not None and sz.y != 0:
        #         aspect_ratio = sz
        #         if (self.aspect_ratio.x != aspect_ratio.x or 
        #             self.aspect_ratio.y != aspect_ratio.y):
        #             crap = 0
        #             if self.client_id ==0:
        #                 crap = 300

        #             self.aspect_ratio.x = sz.x - crap
        #             self.aspect_ratio.y = sz.y
        #         #print(f"client told {aspect_ratio.x} {aspect_ratio.y} ")
        

        if len(self.page_stack) > 0:
            self.page_stack[-1].on_event(event)




class Gui:
    """ class GUI
    Manages the GUI pages for all clients
    """
    clients = {}
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
    def add_client(event):
        """ add_client

        Call when a new client connects.
        handlerhooks.py will call this in HandleClientConnect

        :param clientID: called to add a new client
        :type int: client id from the engine
        """
        if Gui._client_start_page is not None:
            Gui.push(event.client_id, Gui._client_start_page())

    @staticmethod
    def push(client_id, page):
        """ push

        Presents the new Page on the specified client by pushing it on the stack. 

        :param clientID: called to add a new client
        :type int: client id from the engine
        :param page: 
        :type Page: A GUI Page
        
        """
        gui = Gui.clients.get(client_id)
        if gui is not None:
            gui.push(page)
        else:
            gui = GuiClient(client_id)
            Gui.clients[client_id] = gui
            gui.push(page)

    @staticmethod
    def pop(client_id):
        gui = Gui.clients.get(client_id)
        if gui is not None:
            return gui.pop()
            
        return None

    @staticmethod
    def present(event):
        """ present

        calls present on all clients
        handlerhooks.py will call this in HandlePresentGUI
        """
        #
        # This is a list of what the engine thinks are clients

        client_list = set(FrameContext.context.sbs.get_client_ID_list())
        disconnect = []
        Gui.represent = set()
        Gui.represent_throttle = 0

        #
        # Create server if needed
        #
        if event.client_id==0 and len(Gui.clients)==0:
            Gui.push(0, Gui._server_start_page ())

        #
        # Present GUI needs to tell all clients to present
        #
        for client_id, gui in Gui.clients.items():
            if client_id == 0 or client_id in client_list:
                # Remove this from the client list/set
                # since we know about it
                client_list.discard(client_id)
                event = FakeEvent(client_id, "gui_present")
                gui.tick_gui_task()
                gui.present(event)
            else:
                disconnect.append(client_id)
        for cid in disconnect:
            gui = Gui.clients.get(cid)
            if gui is not None:
                event = FakeEvent(cid,"mast:client_disconnect")
                gui.on_event(event)
                gui.destroyed()
                Gui.clients.pop(cid, None)
                FrameContext.aspect_ratios.pop(cid, None)
                

        # Anything left is a client not connected to the script
        # So we start the client as if it connected
        for cid in client_list:
            if Gui._client_start_page is not None:
                Gui.push(cid, Gui._client_start_page())

            
        # Try to repaint things we can this round
        Gui.present_dirty()

    @staticmethod
    def dirty(client_id):
        Gui.represent.add(client_id)

    @staticmethod
    def present_dirty():
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
            # Gui could have disconnected
            if gui:
                event = FakeEvent(client_id, "gui_represent")
                gui.present(event)
        #Gui.present_dirty()

        

    @staticmethod
    def on_message(event):
        """ on_message

        Forward to the appropriate GuiClient/Page
        handlerhooks.py will call this in HandlePresentGUIMessage

        :param event: The tag name of the control interacted with
        :type event: event
        """
        # message_tag, clientID, data
        gui = Gui.clients.get(event.client_id)
        if gui is not None:
            gui.on_message(event)
        Gui.present_dirty()
        

    @staticmethod
    def on_event(event):
        """ on_event

        Forward to the appropriate GuiClient/Page
        handlerhooks.py will call this in HandleEvent

        :param event: The tag name of the control interacted with
        :type event: event
        """
        # message_tag, clientID, data
        gui = Gui.clients.get(event.client_id)
        if gui is not None:
            gui.on_event(event)

    @staticmethod
    def send_custom_event(tag, sub_tag=""):
        """ on_event

        Forward to the appropriate GuiClient/Page
        handlerhooks.py will call this in HandleEvent

        :param event: The tag name of the control interacted with
        :type event: event
        """
        # message_tag, clientID, data
        for client_id, gui in Gui.clients.items():
            event = FakeEvent(client_id, tag, sub_tag)
            gui.on_event(event)

            
def get_client_aspect_ratio(cid):
    ar = FrameContext.aspect_ratios.get(cid)
    if ar is not None:
        ar = Vec3(ar)
        if ar.x == 0 or ar.y == 0:
            ar = Vec3(1020,768,99)
            #print("0  0")
            
        if cid == 0 and Agent.SHARED.get_inventory_value("SIM_STATE",None) != "sim_running":
            ar.x -= 300
            #print("AR CALC Paused (gui.py)")
        # print("Found client gui")
        return ar
    # v = get_server_win()
    # if v.x == 0 or v.y==0:
    #     v = Vec3(1020,768,99)
    # FrameContext.aspect_ratios[cid] = v
    # return v # 
    return Vec3(1024,768,99) # 99 Means the client hasn't set the aspect ratio


# import ctypes
# #import os
# from ctypes.wintypes import HWND, DWORD, RECT

# def get_server_win():
#     hwnd = ctypes.windll.user32.GetForegroundWindow()
#     rect = ctypes.wintypes.RECT()
#     ctypes.windll.user32.GetWindowRect(hwnd, ctypes.pointer(rect))
#     # print(hwnd)
#     # print(rect)
#     return Vec3(rect.right-rect.left, rect.bottom-rect.top, 88)
