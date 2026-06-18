from .query  import to_object, to_object_list, to_id, to_blob
from ..helpers import FrameContext, FakeEvent
from ..mast_sbs.story_nodes.button import Button
from ..garbagecollector import GarbageCollector

def show_warning(t):
    """Print a warning message to the F7 debug screen.

    Args:
        t (str): The message to display.
    """
    print(t)



# def science_start_scan(origin_id_or_side, selected_id, tab):
#     """Start the scan for a a science tab

#     Args:
#         origin_id_or_side (agent|str): If a string is passed it used as the player side, otherwise it use this as an agent to determine side
#         selected_id (agent): Agent id or objects
#         tab (str): The tab to start
#     """
#     player_side = origin_id_or_side
#     if not isinstance(origin_id_or_side, str):
#         so = to_object(origin_id_or_side)
#         player_side = so.side

#     so_sel = to_object(selected_id)
#     percent = 0.0

#     if player_side == so_sel.side:
#         percent = 0.90
#     if so:
#         so.data_set.set("cur_scan_ID", selected_id,0)
#         so.data_set.set("cur_scan_type", tab,0)
#         so.data_set.set("cur_scan_percent", percent,)
        

def science_set_scan_data(player_id_or_obj, scan_target_id_or_obj, tabs):
    """Set science scan data for a target immediately, bypassing the normal scan delay.

    Args:
        player_id_or_obj (Agent | int): The scanning player ship.
        scan_target_id_or_obj (Agent | int): The object being scanned.
        tabs (dict | str): Tab-name → scan-text mapping. A bare string is
            treated as ``{"scan": string}``.
    """
    player_id = to_id(player_id_or_obj)
    scan_target_id = to_id(scan_target_id_or_obj)
    player_obj = to_object(player_id)
    target_blob = to_blob(scan_target_id)
    

    if player_obj is None: return
    if target_blob is None: return
    scan_tabs = ""
    if isinstance(tabs, str):
        tabs = {"scan": tabs}

    for tab in tabs:
        if tab != "scan":
            scan_tabs += f"{tab},"
        message = tabs.get(tab)
        target_blob.set(tab, message, player_obj.side)
    target_blob.set("scan_type_list", scan_tabs, 0)

def _science_get_origin_id():
    #
    # Event 
    #
    if FrameContext.context.event is not None:
        if FrameContext.context.event.tag == "science_scan_complete":
            return FrameContext.context.event.origin_id
    #
    # 
    #
    if FrameContext.task is not None:
        return FrameContext.task.get_variable("SCIENCE_ORIGIN_ID")

def _science_get_selected_id():
    #
    # Event 
    #
    if FrameContext.context.event is not None:
        if FrameContext.context.event.tag == "science_scan_complete":
            return FrameContext.context.event.selected_id
    
    if FrameContext.task is not None:
        return FrameContext.task.get_variable("SCIENCE_SELECTED_ID")
    
def science_update_scan_data(origin, target, info, tab="scan"):
    """Update (or forcibly set) the scan text on a specific tab for a scanning ship.

    Use when the target has already been scanned and the text needs to change, or
    to inject scan data without requiring the player to scan first.

    Args:
        origin (int | Agent): The scanning player ship.
        target (int | Agent): The object being scanned.
        info (str): The new scan text.
        tab (str): The science tab to update (e.g. ``"scan"``, ``"intel"``).
            Defaults to ``"scan"``.
    """
    oo = to_object(origin)
    so = to_object(target)
    if not oo or not so:
        return
    #scan_name = oo.side+tab
    # Set the scan data
    so.data_set.set(tab, info, oo.side)
    # Check if the tab is already in the list
    tab_list = so.data_set.get("scan_type_list",0)
    if tab_list != 0:
        # If it's not in the list, add it.
        if tab_list.find(tab) == -1:
            tab_list += f"{tab}"
    else:
        # If the tab list isn't found, we'll make it
        tab_list = tab
    # update the list of tabs used
    so.data_set.set("scan_type_list", tab_list)
    
def science_get_scan_data(origin, target, tab="scan")->str:
    """Return the scan text on a tab as seen by the scanning ship.

    Args:
        origin (int | Agent): The scanning player ship.
        target (int | Agent): The object being scanned.
        tab (str): Science tab to read. Defaults to ``"scan"``.

    Returns:
        str: The scan text, or ``None`` if not yet scanned.
    """
    oo = to_object(origin)
    so = to_object(target)
    if oo is None or so is None:
        return ""
    # scan_name = oo.side+tab
    initial_scan = so.data_set.get(tab,oo.side)
    if initial_scan is not None:
        initial_scan = initial_scan.strip()
    # print(f"SCIENCE {tab} {oo.side} {initial_scan} ")
    return initial_scan

def science_is_unknown(origin, target)->bool:
    """Return ``True`` if the target has not been scanned by the scanning ship.

    Checks the ``"scan"`` tab. Use ``science_has_scan_data`` to check a
    different tab.

    Args:
        origin (int | Agent): The scanning player ship.
        target (int | Agent): The object to check.

    Returns:
        bool: ``True`` if the target is unscanned or shows default/empty data.
    """
    initial_scan = science_get_scan_data(origin, target)
    is_unknown = (initial_scan is None or initial_scan == "" or initial_scan == "no data" or initial_scan == "Default Scan")
    return is_unknown

def science_has_scan_data(origin, target, tab="scan") -> bool:
    """Return ``True`` if the target has real scan data on the given tab.

    Args:
        origin (int | Agent): The scanning player ship.
        target (int | Agent): The object to check.
        tab (str): Science tab to check. Defaults to ``"scan"``.

    Returns:
        bool: ``True`` if scan data exists and is not empty or default.
    """
    initial_scan = science_get_scan_data(origin, target, tab)
    has_scan = (initial_scan is None or initial_scan == "" or initial_scan == "no data" or initial_scan == "Default Scan")
    return not has_scan

def scan_results(message, target=None, tab = None):
    """Set the scan results for the current scan. This should be called when the scan is completed.
       This is typically called as part of a scan()
       This could also be called in response to a routed science message.
       When paired with a scan() the target and tab are not needed.
       Tab is the variable __SCAN_TAB__, target is track 

    Args:
        message (str): Scan text for a scan that is in progress.
        target (Any, optional): Not currently used. Default is None.
        tab (str, optional): Scan tab for a scan that is in progress. Default is None.
    """    
    if FrameContext.task is None:
        show_warning("Scan results called in a weird way")
        return
    
    task = FrameContext.task
    scan = tab
    if tab is None:
        scan = task.get_variable("__SCAN_TAB__")

    if scan is None:
        show_warning("Scan results expecting a scan tab")
        return
    
    msg = task.compile_and_format_string(message)
    msg = msg.strip()
    
    p = task.get_variable("BUTTON_PROMISE")
    p.set_scan_results(msg) 
    # Rerun the scan (until all scans are done)
    #if scan.node:
    

from .gui import ButtonPromise
from ..consoledispatcher import ConsoleDispatcher
from ..futures import awaitable

class ScanPromise(ButtonPromise):
    def __init__(self, path, task, timeout=None, auto_side=True) -> None:
        path = path if path is not None else "" # NOTE: This is never used. WHY?
        path = f"science"
        super().__init__(path, task, timeout)
        self.path_root = "science"
        
        self.expanded_buttons = None

        self.origin_id = task.get_variable("SCIENCE_ORIGIN_ID")
        self.selected_id = task.get_variable("SCIENCE_SELECTED_ID")
        self.auto_side = auto_side
        self.scan_is_done = False
        self.task.set_variable("BUTTON_PROMISE", self)
        # The stuff to start the scan is now in initial_poll / show_buttons
        self.task.main.tasks.remove(self.task)

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


    def set_scan_results(self, msg):
        selected_id = self.selected_id
        so = to_object(selected_id)
        selected_id = self.origin_id
        oo = to_object(self.origin_id)
        if so and oo:
            so.data_set.set(self.tab, msg, oo.side)
            so.set_inventory_value("SCANNED", True)
            self.task.set_inventory_value("__SCAN_DONE__", True)
        self.task.pop_label(False) #(task.active_label,scan.node.loc)


    def check_for_button_done(self):
        pass
        # if not self.scan_is_done:
        #     return
        # #
        # # THIS sets the promise to finish 
        # # after you let the button process
        # # science will override this to 
        # # keep going until all scanned
        # if self.running_button:
        #     self.set_result(self.running_button)

    def cancel_if_no_longer_exists(self):
        oo = to_object(self.origin_id)
        so = to_object(self.selected_id)
        if so is None or oo is None:
            self.cancel("Objects no longer exist")



    def message(self, event):
        # makes sure this was for us
        if event.selected_id != self.selected_id or self.origin_id != event.origin_id:
            return
        self.tab = event.extra_tag
        self.event = event
        self.cancel_if_no_longer_exists()
        
        if not self.done():
            self.process_tab()
        else:
            pass
        self.task.tick()

    def process_tab(self):
        if self.tab is not None:
            self.button = None
            for i, button in enumerate(self.expanded_buttons):
                if self.task.format_string(button.message) == self.tab:
                    self.button = button
                    #self.button = None # Don't let default process the button
            # if self.button is None:
            #     print(f"No button for {self.tab} {len(self.expanded_buttons)}")
            so_player = to_object(self.origin_id)
            # if so_player:
            #     self.tab = self.tab
            
            self.task.set_variable("__SCAN_TAB__", self)
        
    def selected(self, event):
        #
        # avoid if this isn't for us
        #
        if self.origin_id != event.origin_id or \
            self.selected_id != event.selected_id:
            return
        self.run_focus = True
        self.show_buttons()
        self.cancel_if_no_longer_exists()
        if not self.done:
            self.task.tick()

    def start_scan(self, origin_id, selected_id, extra_tag):
        return
    
        if self.selected_id != selected_id or \
            self.origin_id != origin_id:
            return
        #
        # Check if this was initiated by a "Follow route"
        #
        self.cancel_if_no_longer_exists()
        if self.done():
            return

            
        so = to_object(origin_id)
        so_sel = to_object(selected_id)
        percent = 0.0

        if so.side == so_sel.side:
            if self.auto_side:
                percent = 0.99
            else:
                percent = 0.50

        if extra_tag == "__init__":
            self.tab = "scan"
            percent = 0.99
            self.process_tab()
            return 


        if so:
            so.data_set.set("cur_scan_ID", selected_id,0)
            so.data_set.set("cur_scan_type", extra_tag,0)
            so.data_set.set("cur_scan_percent", percent,0)
            

    def set_result(self, result):
        if result is not None:
            self.leave()
        super().set_result(result)

    def collect(self):
        oo = to_object(self.origin_id)
        selected_so = to_object(self.selected_id)
        if oo is not None and selected_so is not None:
            return False
        self.leave()
        self.task.end()
        return True

    def leave(self):
        GarbageCollector.remove_garbage_collect(self.collect)
        ConsoleDispatcher.remove_select_pair(self.origin_id, self.selected_id, 'science_target_UID')
        ConsoleDispatcher.remove_message_pair(self.origin_id, self.selected_id, 'science_target_UID')
     
    def show_buttons(self):
        sel_so = to_object(self.selected_id)
        origin_so = to_object(self.origin_id)
        if sel_so is None or origin_so is None:
            return


        #scan_tab = origin_so.side+"scan"
        #
        # Have scans ever occurred
        # If so just do the scan tab
        #
        has_scan = sel_so.data_set.get("scan",origin_so.side)
        self.expanded_buttons = self.get_expanded_buttons()

        if has_scan is None:
            scan_tabs = "scan"
            self.scan_is_done = False
        elif has_scan == "no data":
            scan_tabs = "scan"
            self.tab = "scan"
            self.process_tab()
        else:
            scan_tabs = ""
            scanned_tabs = 0
            button_count = 0
            for button in self.expanded_buttons:
                value = True
                if button.code is not None:
                    value = self.task.eval_code(button.code)
                if value:
                    button_count += 1
                    msg = self.task.format_string(button.message).strip()
                    # scan always first
                    if  "scan" == msg:
                        if len(scan_tabs) >= 0:
                            scan_tabs = msg +","+scan_tabs
                        else:
                            scan_tabs = "scan"
                    else:
                        if len(scan_tabs) >= 0:
                            scan_tabs +=","
                        scan_tabs += msg

                    # Check if this has been scanned
                    has_scan = sel_so.data_set.get(msg,origin_so.side)
                    # if has_scan is None:
                    #     print("SCAN NOT STARTED")
                    # elif has_scan == "no data":
                    #     print(f"SCAN {msg} FINISHED NO DATA")
                    # else:
                    #     print(f"SCAN {msg} {has_scan}")

                    if has_scan is not None and has_scan != "no data":
                        scanned_tabs += 1
            
                
            self.scan_is_done = scanned_tabs == button_count
            # if self.scan_is_done: 
            #     print(f"Science scan I think I'm done")

        sel_so.data_set.set("scan_type_list", scan_tabs, 0)
        
        ConsoleDispatcher.add_select_pair(self.origin_id, self.selected_id, 'science_target_UID', self.selected)
        ConsoleDispatcher.add_message_pair(self.origin_id, self.selected_id,  'science_target_UID', self.message)
        GarbageCollector.add_garbage_collect(self.collect)
        
        
@awaitable
def scan(path=None, buttons=None, timeout=None, auto_side=True):
    """Start a science scan and return a promise that resolves when scanning is complete.

    Args:
        path (str, optional): Route path prefix for scan button labels. Defaults
            to None.
        buttons (dict, optional): Extra buttons as ``{label_text: label}`` pairs.
            Defaults to None.
        timeout (Promise, optional): A timeout promise (e.g. from
            ``timeout()``). Defaults to None.
        auto_side (bool, optional): Instantly complete scanning for same-side
            objects. Defaults to True.

    Returns:
        ScanPromise: A promise to ``await``; resolves when all tabs are scanned.
    """
    task = FrameContext.task
    ret = ScanPromise(path, task, timeout, auto_side)
    if buttons is not None:
        for k in buttons:
            ret .buttons.append(Button(k,button="+", label=buttons[k],loc=0))
    #origin_id = task.get_variable("SCIENCE_ORIGIN_ID")
    #selected_id = task.get_variable("SCIENCE_SELECTED_ID")
    return ret

def science_add_scan(message, label=None, data=None, path=None):
    """Add a scan button to the current science scan promise.

    Args:
        message (str): Button text shown in the science UI.
        label (str | Label, optional): Label to run when the button is pressed.
        data (dict, optional): Variables passed to the button's label.
        path (str, optional): Route path to navigate to when pressed.
    """
    p = ButtonPromise.navigating_promise
    if p is None:
        return
    p.add_nav_button(Button(message, "+", label=label, data=data, new_task=True, path=path, loc=0))


def science_navigate(path):
    """Navigate the current science GUI task to a new button path.

    Args:
        path (str): The science route path to navigate to.
    """
    task = FrameContext.task
    p = task.get_variable("BUTTON_PROMISE")
    if p is None:
        return
    p.set_path(path)


from ..mast.pollresults import PollResults
from .execution import AWAIT, task_all, labels_get_type
################
## This is a PyMAST label used to run comms
def create_scan_label():
    c = scan()
    yield AWAIT(c)
    print("SCAN ENDED?")


__science_promises = {}
def start_science_selected(event):
    """Start or resume a science scan for the given selection event.

    Creates a new ``ScanPromise`` for the (origin, selected) pair if none
    exists; otherwise returns the existing one. Called automatically by
    ``ConsoleDispatcher`` for ``science_target_UID`` select events.

    Args:
        event: Engine selection event that triggered the scan.

    Returns:
        ScanPromise | None: The active scan promise, or ``None`` if the origin
            or target no longer exists.
    """
    # Don't run if the selection doesn't exist
    so = to_object(event.selected_id)
    if event.selected_id != 0 and so is None:
        return
    
    # Don't run if the selection doesn't exist
    if event.origin_id !=0 and to_object(event.origin_id) is None:
        return
    
    #
    # If we're already running
    #
    #
    test = (event.origin_id, event.selected_id)
    promise = __science_promises.get(test)
    if promise is not None:
        #print ("__SCIENCE_PROMISE creation already exists")
        return promise
    
    

    console = "SCIENCE"
    point = None
    if event.selected_id == 0:
        point = FrameContext.context.sbs.vec3()
        point.x = event.source_point.x
        point.y = event.source_point.y
        point.z = event.source_point.z
    
    data = {
                f"{console}_POINT": event.source_point,
                f"EVENT": event,
                f"{console}_ROUTED": True
    }
    

    if event.origin_id:
        data[f"{console}_ORIGIN_ID"] = event.origin_id
        data[f"{console}_ORIGIN"] = to_object(event.origin_id)
    else:
        data[f"{console}_ORIGIN_ID"] = 0
        data[f"{console}_ORIGIN"] = None

    if event.parent_id:
        data[f"{console}_PARENT_ID"] = event.parent_id
        data[f"{console}_PARENT"] = to_object(event.parent_id)
    else:
        data[f"{console}_PARENT_ID"] = 0
        data[f"{console}_PARENT"] = None

    if event.selected_id:
        data[f"{console}_SELECTED_ID"] = event.selected_id
        data[f"{console}_SELECTED"] = to_object(event.selected_id)
    else:
        data[f"{console}_SELECTED_ID"] = 0
        data[f"{console}_SELECTED"] = None
        # Only point selections can have a NONE
    #
    #
    #
    #
    task = FrameContext.server_task
    #
    # May need a null label
    #
    label = create_scan_label
    t = task.start_task(label, data, defer=True)
    #
    restore_task =  FrameContext.task
    restore_page =  FrameContext.page

    path_labels = []
    path_labels = labels_get_type("enable/science")
    #
    # Run all the valid enables
    #

    FrameContext.task = t
    FrameContext.page= t.main.page
    p = task_all(*path_labels, data=data, sub_tasks=True)

    p.poll()
    #
    # This could get into a lock
    # but the expectation is this runs in one pass
    #
    count = 0
    while not p.done():
        p.poll()

        if p.is_idle:
            break

        if count > 100000:
            print(f"Science enables caused hang build")
            break
        count += 1

    legit = False
    for r in p.result():
        if r != PollResults.FAIL_END:
            legit = True
            break
    if legit == False:
        t.end()
        FrameContext.task = restore_task
        FrameContext.page = restore_page
        return
    
    #
    # After all the sub task have run, NOW the 
    # actual task can run
    #
    
    t.tick_in_context()
    #
    # Kind of a round about way, but the variable
    # BUTTON_PROMISE is set in __init__ of the promise
    #
    promise = t.get_variable("BUTTON_PROMISE")
    if promise is None:
        print("SCIENCE SYSTEM Unexpected missing promise")
    __science_promises[test] = promise

    FrameContext.task = restore_task
    FrameContext.page = restore_page
    return promise
    
def start_science_message(event):
    """Handle a science message event, emitting a ``science_auto_scan`` signal.

    This is the mechanism behind the auto-scan feature. Called automatically
    by ``ConsoleDispatcher`` for ``science_target_UID`` message events.

    Args:
        event: Engine message event carrying the auto-scan trigger.
    """
    if event.sub_tag != "":
        from .signal import signal_emit
        signal_emit("science_auto_scan", {
            "SCIENCE_PARENT_ID": event.parent_id,
            "SCIENCE_ORIGIN_ID": event.origin_id,
            "SCIENCE_SELECTED_ID": event.selected_id,
        })
        
    
ConsoleDispatcher.add_default_select("science_target_UID", start_science_selected)
ConsoleDispatcher.add_default_message("science_target_UID", start_science_message)

def science_ensure_scan(ids_or_objs, target_ids_or_objs, tabs="scan"):
    """Force a completed scan result onto all (scanner, target) pairs.

    Useful for scripted encounters where objects should appear pre-scanned
    without waiting for player interaction. Pass ``tabs="*"`` to populate
    every tab the target exposes.

    Args:
        ids_or_objs (set[Agent | int]): The scanning player ship(s).
        target_ids_or_objs (set[Agent | int]): The object(s) to mark as
            scanned.
        tabs (str): Comma-separated tab names, or ``"*"`` for all tabs.
            Defaults to ``"scan"``.
    """
    players = to_object_list(ids_or_objs)
    targets = to_object_list(target_ids_or_objs)
    

    def do_tab(p, t, tab, promise):
        value_tag = p.side
        extra_tag = tab
        event = FakeEvent(0, "science_scan_complete", "", p.get_id(), t.get_id(), 0,extra_tag, value_tag)
        #print(f"DOING TAB {tab}")
        promise.message(event)

    for p in players:
        if p is None:
            continue
        for t in targets:
            scan_tabs = tabs
            if t is None:
                continue
            event = FakeEvent(0, "science_scan_complete", "", p.get_id(), t.get_id())
            promise = start_science_selected(event)
            if promise is None:
                continue

            skip = False
            if tabs=="*":
                # Have to make sure initial scan occurred
                do_tab(p,t, "scan", promise)
                scan_tabs = t.data_set.get("scan_type_list", 0)
                if scan_tabs is None:
                    continue
                skip = True


            scan_tabs = scan_tabs.split(",")
            for tab in scan_tabs:
                extra_tag = tab.strip()
                if len(extra_tag) == 0:
                    continue
                if skip and extra_tag=="scan":
                    continue
                do_tab(p,t,tab, promise)
                





from sbs_utils.procedural.inventory import get_inventory_value, set_inventory_value
from sbs_utils.helpers import FrameContext
from sbs_utils.procedural.query import to_object


#
# NOTE: These all could be moved to the sbs_utils library
#

def science_set_2dview_focus(client_id, focus_id=0):
    """Focus the science 2D view of a client console on a specific object.

    Args:
        client_id (int): The client console ID.
        focus_id (int, optional): ID of the object to focus on. ``0`` clears
            the focus. Defaults to 0.
    """
    if focus_id is None:
        return
    
    follow = get_inventory_value(client_id, "2d_follow")
    on_ship =  FrameContext.context.sbs.get_ship_of_client(client_id)
    set_inventory_value(client_id, "science_2dview_alt_ship", focus_id)
    set_inventory_value(on_ship, "science_2dview_alt_ship", focus_id)
    set_id = focus_id
    if not follow:
        set_id = 0

    previous = get_inventory_value(client_id, "science_2dview_alt_ship_prev", 0)
    if previous != set_id:
        FrameContext.context.sbs.assign_client_to_alt_ship(client_id, set_id)
        set_inventory_value(client_id, "science_2dview_alt_ship_prev", set_id)

