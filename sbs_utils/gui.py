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
        :param clientID: The client ID that had the interactive
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
        self.page_stack.append(page)
        self.present(event)

    def pop(self):
        """ pop

        Stops presenting the current page and return to the previous one

        """
        ret = None
        FrameContext.context.sbs.send_gui_clear(self.client_id, "")
        if len(self.page_stack) > 0:
            ret = self.page_stack.pop()
            if ret:
                ret.on_pop()



        event = FakeEvent(self.client_id, "gui_pop")
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
        

        if len(self.page_stack) > 0:
            self.page_stack[-1].on_event(event)




class Gui:
    """ class GUI
    Manages the GUI pages for all clients
    """
    clients = {}
    # Set that accumulates client ids whose widgets went dirty this frame.
    # Populated fresh each Gui.present, but dirty() can fire during an
    # immediate present (e.g. Gui.web_page_open -> push -> present) before the
    # first Gui.present of the frame, so give it a class-level default.
    represent = set()
    represent_throttle = 0
    _server_start_page = None
    _client_start_page = None
    # Client ids that are web-page sessions (browsers served a //web/<path>
    # route), not engine consoles. Tracked so Gui.present does not purge them
    # against the engine client list and does not auto-add them as consoles.
    web_client_ids = set()
    # Optional callable web_render_sink(client_id, real_sbs) -> sbs-like shim.
    # When set, a web client's present is rendered through the returned shim
    # (installed as FrameContext.context.sbs for that client only) instead of
    # the real engine transport. This lets a host-side proxy capture a web
    # client's send_gui_* output in pure Python - the basis for serving MAST
    # web pages from the REAL engine with no engine changes (the mock leaves
    # this None and renders web clients straight to the browser as usual).
    web_render_sink = None

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
    def _find_web_label(story, path):
        """Resolve a web path (e.g. "scores" or "web/scores") to its
        //web/<path> route label name within ``story``, or None if no such
        route exists. Resolving against the story that will actually run the
        page keeps the label name and the scheduler in sync."""
        path = str(path).strip("/")
        if not path.startswith("web/"):
            path = "web/" + path
        labels = getattr(story, "labels", None)
        if not labels:
            return None
        for name in labels:
            lbl = labels.get(name)
            if lbl is not None and getattr(lbl, "path", None) == path:
                return name
        return None

    @staticmethod
    def web_page_open(client_id, path, data=None):
        """Open a MAST //web/<path> route as a GUI session for a web client.

        Web clients are browsers connected to a web transport rather than the
        engine console list. They get a normal StoryPage/GuiClient (so widget
        events and rendering flow through the usual path), but the GUI task is
        started at the matched //web/<path> route label and the session is
        exempt from the engine-console purge in Gui.present.

        Returns True if a matching web route was found and opened.
        """
        if Gui._client_start_page is None:
            return False
        page = Gui._client_start_page()
        label = Gui._find_web_label(page.story, path)
        if label is None:
            return False
        page.start_label = label
        page.start_data = data
        Gui.web_client_ids.add(client_id)
        # The push triggers the first (full-frame) present; later presents send
        # only dirty deltas. So this initial present must go through the render
        # sink too, or a host proxy would miss the page layout.
        if Gui.web_render_sink is not None:
            ctx = FrameContext.context
            sbs_restore = ctx.sbs
            ctx.sbs = Gui.web_render_sink(client_id, sbs_restore)
            try:
                Gui.push(client_id, page)
            finally:
                ctx.sbs = sbs_restore
        else:
            Gui.push(client_id, page)
        # Tag the session so mission code can find/target web viewers, e.g.
        # role("__web__") to push updates to everyone watching a web page.
        gui = Gui.clients.get(client_id)
        if gui is not None:
            gui.add_role("__web__")
        return True

    @staticmethod
    def web_page_navigate(client_id, path, data=None):
        """Send an existing web session to a different //web/<path> in-session.

        Returns True if the target web route exists. Unlike opening a new
        browser URL, this reuses the same web client/session.
        """
        gui = Gui.clients.get(client_id)
        if gui is None or client_id not in Gui.web_client_ids:
            return False
        page = gui.page
        if page is None:
            return False
        label = Gui._find_web_label(page.story, path)
        if label is None:
            return False
        from .procedural.gui.navigation import gui_reroute_client
        gui_reroute_client(client_id, label, data)
        return True

    @staticmethod
    def web_page_close(client_id):
        """Tear down a web-page session (browser disconnected)."""
        Gui.web_client_ids.discard(client_id)
        gui = Gui.clients.get(client_id)
        if gui is not None:
            event = FakeEvent(client_id, "mast:client_disconnect")
            gui.on_event(event)
            gui.destroyed()
            Gui.clients.pop(client_id, None)
            FrameContext.aspect_ratios.pop(client_id, None)

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
            if client_id == 0 or client_id in client_list or client_id in Gui.web_client_ids:
                # Remove this from the client list/set
                # since we know about it
                client_list.discard(client_id)
                event = FakeEvent(client_id, "gui_present")
                e_restore = FrameContext.context.event
                FrameContext.context.event = event
                # Web clients can be redirected through a capture shim so their
                # render output can be forwarded to a browser by a host proxy
                # (real-engine web pages). Inert unless web_render_sink is set.
                sbs_restore = None
                if (Gui.web_render_sink is not None
                        and client_id in Gui.web_client_ids):
                    sbs_restore = FrameContext.context.sbs
                    FrameContext.context.sbs = Gui.web_render_sink(
                        client_id, sbs_restore)
                try:
                    gui.tick_gui_task()
                    gui.present(event)
                finally:
                    if sbs_restore is not None:
                        FrameContext.context.sbs = sbs_restore
                    FrameContext.context.event = e_restore
            else:
                disconnect.append(client_id)
        for cid in disconnect:
            gui = Gui.clients.get(cid)
            if gui is not None:
                e_restore = FrameContext.context.event
                FrameContext.context.event = event
                event = FakeEvent(cid,"mast:client_disconnect")
                gui.on_event(event)
                FrameContext.context.event = e_restore
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
                e_restore = FrameContext.context.event
                FrameContext.context.event = event
                # Dirty widgets emit here (not in the main present loop), so web
                # clients must go through the render sink here too.
                sbs_restore = None
                if (Gui.web_render_sink is not None
                        and client_id in Gui.web_client_ids):
                    sbs_restore = FrameContext.context.sbs
                    FrameContext.context.sbs = Gui.web_render_sink(
                        client_id, sbs_restore)
                try:
                    gui.present(event)
                finally:
                    if sbs_restore is not None:
                        FrameContext.context.sbs = sbs_restore
                    FrameContext.context.event = e_restore
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
    """
    Get the aspect ratio of the specified client's screen.
    Args:
        cid (int): The client ID.
    Returns:
        Vec3: The aspect ratio. If Vec3.z is 99, then the client hasn't set the aspect ratio.
    """
    ar = FrameContext.aspect_ratios.get(cid)
    if ar is not None:
        ar = Vec3(ar)
        if ar.x == 0 or ar.y == 0:
            ar = Vec3(1024,768,99)
            
        # if cid == 0 and Agent.SHARED.get_inventory_value("SIM_STATE",None) != "sim_running":
        #     ar.x -= 300

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
#     return Vec3(rect.right-rect.left, rect.bottom-rect.top, 88)
