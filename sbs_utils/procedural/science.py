from . import query 
from .inventory import to_object
from .roles import has_role
from .. import faces
from ..agent import Agent
from ..helpers import FrameContext
from ..mast.mast import Button
from ..garbagecollector import GarbageCollector
import sbs

def show_warning(t):
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
#         so = query.to_object(origin_id_or_side)
#         player_side = so.side

#     so_sel = query.to_object(selected_id)
#     percent = 0.0

#     if player_side == so_sel.side:
#         percent = 0.90
#     if so:
#         so.data_set.set("cur_scan_ID", selected_id,0)
#         so.data_set.set("cur_scan_type", tab,0)
#         so.data_set.set("cur_scan_percent", percent,)
        

def science_set_scan_data(player_id_or_obj, scan_target_id_or_obj, tabs):
    """Immediately set the science scan data for a scan target
       use this for things that you do not want to have scan delayed.

    Args:
        player_id_or_obj (agent): The player ship agent id or object
        scan_target_id_or_obj (agent): The target ship agent id or object
        tabs (dict): A dictionary to key = tab, value = scan string
    """    
    player_id = query.to_id(player_id_or_obj)
    scan_target_id = query.to_id(scan_target_id_or_obj)
    player_obj = query.to_object(player_id)
    target_blob = query.to_blob(scan_target_id)
    

    if player_obj is None: return
    if target_blob is None: return
    scan_tabs = ""
    if isinstance(tabs, str):
        tabs = {"scan": tabs}

    for tab in tabs:
        if tab != "scan":
            scan_tabs += f"{tab},"
        message = tabs.get(tab)
        #print(f"sci scan {tab} {message}")
        target_blob.set(f"{player_obj.side}{tab}", message, 0)
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



def scan_results(message, target=None, tab = None):
    """Set the scan results for the current scan. This should be called when the scan is completed.
       This is typically called as part of a scan()
       This could also be called in response to a routed science message.
       When pair with a scan() the target and tab are not need.
       Tab is the variable __SCAN_TAB__, target is track 

    Args:
        message (str): scan text for a scan the is in progress
        tab (str): scan tab for a scan the is in progress
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
    #print(f"{scan.tab} scan {msg}")
    
    p = task.get_variable("BUTTON_PROMISE")
    p.set_scan_results(msg) 
    # Rerun the scan (until all scans are done)
    #if scan.node:
    

from .gui import ButtonPromise
from ..consoledispatcher import ConsoleDispatcher
class ScanPromise(ButtonPromise):
    def __init__(self, path, task, timeout=None, auto_side=True) -> None:
        path = path if path is not None else ""
        path = f"science"
        super().__init__(path, task, timeout)
        self.path_root = "science"
        
        self.expanded_buttons = None

        self.origin_id = task.get_variable("SCIENCE_ORIGIN_ID")
        self.selected_id = task.get_variable("SCIENCE_SELECTED_ID")
        self.auto_side = auto_side
        self.scan_is_done = False
        # The stuff to start the scan is now in initial_poll / show_buttons

    def set_path(self, path):
        super().set_path(path)

    def initial_poll(self):
        if self._initial_poll:
            return
        self.show_buttons()
        super().initial_poll()

    def poll(self):
        super().poll()

    def set_scan_results(self, msg):
        selected_id = self.selected_id
        so = query.to_object(selected_id)
        if so:
            so.data_set.set(self.tab, msg,0)
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



    def science_message(self, event):
        # makes sure this was for us
        if event.selected_id != self.selected_id or self.origin_id != event.origin_id:
            return
        self.tab = event.extra_tag
        self.event = event
        self.cancel_if_no_longer_exists()
        #print(f"SCIENCE MESSAGE {event.extra_tag} {event.tag} {event.sub_tag} ")
        if not self.done():
            self.process_tab()
        else:
            #print(f"SKIPPED SCIENCE MESSAGE {event.extra_tag}")
            pass

    def process_tab(self):
        if self.tab is not None:
            self.button = None
            for i, button in enumerate(self.expanded_buttons):
                if self.task.format_string(button.message) == self.tab:
                    self.button = button
                    #self.button = None # Don't let default process the button
            # if self.button is None:
            #     print(f"No button for {self.tab} {len(self.expanded_buttons)}")
            so_player = query.to_object(self.origin_id)
            if so_player:
                self.tab = so_player.side+self.tab
            self.task.set_variable("__SCAN_TAB__", self)
        
    def science_selected(self, event):
        #
        # avoid if this isn't for us
        #
        if self.origin_id != event.origin_id or \
            self.selected_id != event.selected_id:
            return
        self.run_focus = True
        self.show_buttons()
        self.cancel_if_no_longer_exists()

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

            
        so = query.to_object(origin_id)
        so_sel = query.to_object(selected_id)
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
        oo = query.to_object(self.origin_id)
        selected_so = query.to_object(self.selected_id)
        if oo is not None and selected_so is not None:
            return False
        # print("GARBAGE COLLECTION science promise")
        self.leave()
        self.task.end()
        return True

    def leave(self):
        GarbageCollector.remove_garbage_collect(self.collect)
        ConsoleDispatcher.remove_select_pair(self.origin_id, self.selected_id, 'science_target_UID')
        ConsoleDispatcher.remove_message_pair(self.origin_id, self.selected_id, 'science_target_UID')
     
    def show_buttons(self):
        sel_so = query.to_object(self.selected_id)
        origin_so = query.to_object(self.origin_id)
        if sel_so is None or origin_so is None:
            return


        scan_tab = origin_so.side+"scan"
        #
        # Have scans ever occurred
        # If so just do the scan tab
        #
        has_scan = sel_so.data_set.get(scan_tab,0)
        self.expanded_buttons = self.get_expanded_buttons()

        if has_scan is None:
            scan_tabs = "scan"
            self.scan_is_done = False
        elif has_scan == "no data":
            scan_tabs = "scan"
            self.tab = "scan"
            self.process_tab()
        else:
            #print(f"has scan else {has_scan}")
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
                    has_scan = sel_so.data_set.get(origin_so.side+msg, 0)
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

        #print(f"Science tabs {scan_tabs}")
        sel_so.data_set.set("scan_type_list", scan_tabs, 0)
        
        ConsoleDispatcher.add_select_pair(self.origin_id, self.selected_id, 'science_target_UID', self.science_selected)
        ConsoleDispatcher.add_message_pair(self.origin_id, self.selected_id,  'science_target_UID', self.science_message)
        GarbageCollector.add_garbage_collect(self.collect)
        
        

def scan(path=None, buttons=None, timeout=None, auto_side=True):
    """Start a science scan

    Args:
        buttons (dict, optional): dictionary key = button, value = label. Defaults to None.
        timeout (_type_, optional): A promise typically by calling timeout(). Defaults to None.
        auto_side (bool, optional): If true quickly scans thing on the same side. Defaults to True.

    Returns:
        Promise: A promise to wait. Typically passed to an await/AWAIT
    """    
    task = FrameContext.task
    ret = ScanPromise(path, task, timeout, auto_side)
    if buttons is not None:
        for k in buttons:
            ret .buttons.append(Button(k,button="+", label=buttons[k],loc=0))
    #origin_id = task.get_variable("SCIENCE_ORIGIN_ID")
    #selected_id = task.get_variable("SCIENCE_SELECTED_ID")
    #print(f"scan() {origin_id} {selected_id}")
    return ret

def science_add_scan(message, label=None, data=None, path=None):
    p = ButtonPromise.navigating_promise
    if p is None:
        return
    p.add_nav_button(Button(message, "+", label=label, data=data, new_task=True, path=path, loc=0))


def science_navigate(path):
    task = FrameContext.task
    p = task.get_variable("BUTTON_PROMISE")
    if p is None:
        return
    p.set_path(path)
