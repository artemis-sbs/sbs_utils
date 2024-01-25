from . import query 
from .inventory import get_inventory_value
from .roles import has_role
from .. import faces
from ..agent import Agent
from ..helpers import FrameContext
import sbs

def show_warning(t):
    print(t)



def science_start_scan(origin_id, selected_id, tab):
    #
    # Check if this was initiated by a "Follow route"
    #
    so = query.to_object(origin_id)
    so_sel = query.to_object(selected_id)
    percent = 0.0

    if so.side == so_sel.side:
        percent = 0.90
    if so:
        so.data_set.set("cur_scan_ID", selected_id,0)
        so.data_set.set("cur_scan_type", tab,0)
        so.data_set.set("cur_scan_percent", percent,)
        

def science_set_scan_data(player_id_or_obj, scan_target_id_or_obj, tab, message):
        player_id = query.to_id(player_id_or_obj)
        scan_target_id = query.to_id(scan_target_id_or_obj)
        player_obj = query.to_object(player_id)
        target_blob = query.to_blob(scan_target_id)

        if player_obj is None: return
        if target_blob is None: return
        target_blob.set(f"{player_obj.side}{tab}", message, 0)


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



def scan_results(message):
    if FrameContext.task is None:
        show_warning("Scan results called in a weird way")
        return
    
    task = FrameContext.task

    scan = task.get_variable("__SCAN_TAB__")
    if scan is None:
        show_warning("Scan results expecting a scan tab")
        return
    
    msg = task.compile_and_format_string(message)
    #print(f"{scan.tab} scan {msg}")
    selected_id = _science_get_selected_id()
    so = query.to_object(selected_id)
    if so:
        so.data_set.set(scan.tab, msg,0)
        so.set_inventory_value("SCANNED", True)
        task.set_inventory_value("__SCAN_DONE__", True)

    # Rerun the scan (until all scans are done)
    #if scan.node:
    task.pop_label(False) #(task.active_label,scan.node.loc)

from .gui import ButtonPromise
from ..consoledispatcher import ConsoleDispatcher
class ScanPromise(ButtonPromise):
    def __init__(self, task, timeout=None, auto_side=True) -> None:
        super().__init__(task, timeout)

        self.expanded_buttons = None

        self.origin_id = task.get_variable("SCIENCE_ORIGIN_ID")
        self.selected_id = task.get_variable("SCIENCE_SELECTED_ID")
        self.auto_side = auto_side
        self.scan_is_done = False
        # The stuff to start the scan is now in initial_poll / show_buttons

    def initial_poll(self):
        if self._initial_poll:
            return
        
        if self.expanded_buttons is None:
            self.expanded_buttons = self.get_expanded_buttons()
        self.show_buttons()
        super().initial_poll()

    def poll(self):
        # if self.task.get_inventory_value("__SCAN_DONE__", None):
        #     self.task.set_inventory_value("__SCAN_DONE__", None)
        #     self.show_buttons()
        #     if self.scan_is_done:
        #         self.set_result(True)
        super().poll()

    def check_for_button_done(self):
        self.show_buttons()
        if not self.scan_is_done:
            return
        #
        # THIS sets the promise to finish 
        # after you let the button process
        # science will override this to 
        # keep going until all scanned
        if self.running_button:
            self.set_result(self.running_button)



    def science_message(self, message, an_id, event):
        # makes sure this was for us
        if event.selected_id != self.selected_id or self.origin_id != event.origin_id:
            return
        self.tab = event.extra_tag
        self.event = event
        #print(f"SCIENCE MESSAGE {event.extra_tag}")
        self.process_tab()

    def process_tab(self):
        if self.tab is not None:
            for i, button in enumerate(self.expanded_buttons):
                if self.task.format_string(button.message) == self.tab:
                    self.button = i

            so_player = query.to_object(self.origin_id)
            if so_player:
                self.tab = so_player.side+self.tab

            self.task.set_variable("__SCAN_TAB__", self)
            if self.button is not None:
                button = self.expanded_buttons[self.button] 
                self.button = None
                self.task.set_variable("EVENT", self.event)
                self.task.push_inline_block(self.task.active_label,button.loc+1)

    def science_selected(self, an_id, event):
        #
        # avoid if this isn't for us
        #
        if self.origin_id != event.origin_id or \
            self.selected_id != event.selected_id:
            return
        self.run_focus = True
        self.start_scan(event.origin_id, event.selected_id, event.extra_tag)

    def start_scan(self, origin_id, selected_id, extra_tag):
        if self.selected_id != selected_id or \
            self.origin_id != origin_id:
            return
        #
        # Check if this was initiated by a "Follow route"
        #
            
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

    def leave(self):
        ConsoleDispatcher.remove_select_pair(self.origin_id, self.selected_id, 'science_target_UID')
        ConsoleDispatcher.remove_message_pair(self.origin_id, self.selected_id, 'science_target_UID')
     
    def show_buttons(self):
        sel_so = query.to_object(self.selected_id)
        origin_so = query.to_object(self.origin_id)

        if sel_so is not None:
            scan_tab = origin_so.side+"scan"
            #
            # Have scans ever occurred
            # If so just do the scan tab
            #
            has_scan = sel_so.data_set.get(scan_tab,0)
            if has_scan is None:
                scan_tabs = "scan"
                self.scan_is_done = False
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
                        if msg != "scan":
                            if len(scan_tabs):
                                scan_tabs += " "
                            scan_tabs += msg
                        # Check if this has been scanned
                        has_scan = sel_so.data_set.get(origin_so.side+msg, 0)
                        if has_scan:
                            scanned_tabs += 1
                self.scan_is_done = scanned_tabs == button_count
                sel_so.data_set.set("scan_type_list", scan_tabs, 0)

        
        ConsoleDispatcher.add_select_pair(self.origin_id, self.selected_id, 'science_target_UID', self.science_selected)
        ConsoleDispatcher.add_message_pair(self.origin_id, self.selected_id,  'science_target_UID', self.science_message)
        
        routed = self.task.get_variable("SCIENCE_ROUTED")
        if routed:
            # Clear routed???
            routed = self.task.set_variable("SCIENCE_ROUTED", False)
            self.event = self.task.get_variable("EVENT")
            if self.event is not None:
                self.start_scan(origin_so.id, sel_so.id, self.event.extra_tag)
            else:
                self.start_scan( origin_so.id, sel_so.id, "__init__")


def scan(timeout=None, auto_side=True):
    task = FrameContext.task
    return ScanPromise(task, timeout, auto_side)