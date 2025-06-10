from .query  import to_object, get_comms_selection, get_science_selection, get_weapons_selection
from ..helpers import FrameContext, FakeEvent
from ..mast_sbs.story_nodes.button import Button
from ..garbagecollector import GarbageCollector
from .gui import ButtonPromise
from ..consoledispatcher import ConsoleDispatcher
from ..vec import Vec3
#from ..futures import awaitable



class PopupPromise(ButtonPromise):
    popup_promises = {}

    def __init__(self, event) -> None:

        path = f"popup/{event.sub_tag}"
        #
        # Small stub task to hold scope variables
        # 
        task = FrameContext.server_task.start_task("$NOOP$", defer=True, inherit=False, unscheduled=True)


        super().__init__(path, task, None)
        self.path_root = path
        self.uid = f"{event.sub_tag}_popup"

        self.expanded_buttons = None
        self.origin_id = event.origin_id
        self.selected_id = event.selected_id
        self.title = "options"

        # Add this as the thing to call 
        # for this pair of IDs
        ConsoleDispatcher.add_select_pair(self.origin_id, self.selected_id, self.uid, self.selected)
        ConsoleDispatcher.add_message_pair(self.origin_id, self.selected_id,  self.uid, self.message)
        GarbageCollector.add_garbage_collect(self.collect)

    def set_path(self, path):
        super().set_path(path)

    def initial_poll(self):
        if self._initial_poll:
            return
        self.show_buttons()
        super().initial_poll()

    def poll(self):
        # This is in case a gui is used in the can
        # But it won't
        event = FrameContext.context.event
        FrameContext.context.event = self.event
        ret = super().poll()
        FrameContext.context.event = event
        return ret

   
    

    def pressed_set_values(self, task) -> None:
        event = self.event
        console = event.sub_tag.upper()

        self.task.set_variable("EVENT", event)
        self.task.set_variable("client_id", event.client_id)
        # 
        task.set_variable(f"{console}_POPUP_ID", event.selected_id)
        task.set_variable(f"{console}_SELECTED_ID", event.origin_id)
        # Set focus id
        ship_id = FrameContext.context.sbs.get_ship_of_client(event.client_id)
        task.set_variable(f"{console}_ORIGIN_ID", ship_id)
        #
        task.set_variable(f"{console}_POPUP_POINT", Vec3(event.source_point))
        task.set_variable("client_id", event.client_id)

        # 
        # console selected is popup origin
        # console origin is the ship the client is on
        # popup selected is the things click on
        cs = None if self.origin_id == 0 else to_object(event.origin_id)
        ps = None if self.selected_id == 0 else to_object(event.selected_id)
        co = None if ship_id == 0 else to_object(ship_id)

        task.set_variable(f"{console}_ORIGIN", co)
        task.set_variable(f"{console}_SELECTED", cs)
        task.set_variable(f"{console}_POPUP", ps)

        self.title = "Location"
        if ps is not None: 
            self.title =  ps.name
        
  
    
    def set_variables(self, event):
        self.event = event
        self.pressed_set_values(self.task)

            

    def message(self, event):
        # makes sure this was for us
        if event.selected_id != self.selected_id or self.origin_id != event.origin_id:
            return
        
        self.set_variables(event)
        self.event = event

        #print(f"POPUP MESSAGE {event.extra_tag}")
        self.button = None
        for i, button in enumerate(self.expanded_buttons):
            if self.task.format_string(button.message) == event.extra_tag:
                self.button = button
                self.set_path(self.path_root+"/hide")
                self.poll()

        #FrameContext.context.sbs.send_hold_menu(event.client_id, self.origin_id, self.selected_id, "")
        
        
    def selected(self, event):
        #
        # avoid if this isn't for us
        #
        if self.origin_id != event.origin_id or \
            self.selected_id != event.selected_id:
            return
        self.run_focus = True
        self.event = event
        self.set_variables(event)
        self.path = self.path_root

        self.show_buttons()
        
        # if not self.done:
        #     self.task.tick()

    def collect(self):
        #
        # Remember Origin is the ALT ship
        # Selection is the popup ID
        #
        oo = to_object(self.origin_id)
        selected_so = to_object(self.selected_id)
        if oo is not None and self.selected_id == 0:
            return False
        if oo is not None and selected_so is not None:
            return False

        self.leave()
        self.task.end()
        return True

    def leave(self):
        #print("POPUP LEAVE")
        GarbageCollector.remove_garbage_collect(self.collect)
        ConsoleDispatcher.remove_select_pair(self.origin_id, self.selected_id, self.uid)
        ConsoleDispatcher.remove_message_pair(self.origin_id, self.selected_id, self.uid)
        test = (self.origin_id, self.selected_id, self.uid)
        PopupPromise.popup_promises.pop(test, None)
     
    def show_buttons(self):
        sel_so = to_object(self.selected_id)
        origin_so = to_object(self.origin_id)
        if (self.selected_id != 0 and sel_so is None) or origin_so is None:
            return
        
        CID = FrameContext.client_id        
        if self.path == self.path_root+"/hide":
            FrameContext.context.sbs.send_hold_menu(CID, self.origin_id, self.selected_id, "")
            return
        #
        # Have scans ever occurred
        # If so just do the scan tab
        #

        self.expanded_buttons = self.get_expanded_buttons()
        button_count = 0
        button_msg = []
        for button in self.expanded_buttons:
            value = True
            if button.code is not None:
                value = self.task.eval_code(button.code)
            if value:
                button_count += 1
                button_msg.append(self.task.format_string(button.message).strip())

        self.button_string = ";".join(button_msg)

        #self.button_string = "Protect;Attack;"
        # Add Title
        if len(self.button_string)>0:
            self.button_string = self.title+";" + self.button_string

        FrameContext.context.sbs.send_hold_menu(CID, self.origin_id, self.selected_id, self.button_string)


def popup_navigate(path):
    task = FrameContext.task
    p = task.get_variable("BUTTON_PROMISE")
    if p is None:
        return
    p.set_path(path)


# ################
# ## This is a PyMAST label used to run comms
# def create_popup_label():
#     c = popup()
#     yield AWAIT(c)


def start_popup_selected(event):
    # Don't run if the selection doesn't exist
    # so = to_object(event.selected_id)
    # if event.selected_id != 0 and so is None:
    #     return
    
    # Don't run if the selection doesn't exist
    if event.origin_id !=0 and to_object(event.origin_id) is None:
        return
    #
    # If we're already running
    #
    #
    uid = f"{event.sub_tag}_popup"
    test = (event.origin_id, event.selected_id, uid)
    promise = PopupPromise.popup_promises.get(test)
    if promise is not None:
        promise.selected(event)
        #print ("__SCIENCE_PROMISE creation already exists")
        return promise
    else:
        promise = PopupPromise(event)
        
        PopupPromise.popup_promises[test] = promise
        promise.selected(event)

    return promise
    
    
ConsoleDispatcher.add_default_select("science_popup", start_popup_selected)
ConsoleDispatcher.add_default_select("comms_popup", start_popup_selected)
ConsoleDispatcher.add_default_select("comms2d_popup", start_popup_selected)
ConsoleDispatcher.add_default_select("weapons_popup", start_popup_selected)


