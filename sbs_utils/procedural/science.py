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
        so.update_engine_data({
            "cur_scan_ID": selected_id,
            "cur_scan_type": tab,
            "cur_scan_percent": percent
        })

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
        so.update_engine_data({
            scan.tab: msg,
        })
        so.set_inventory_value("SCANNED", True)

    # Rerun the scan (until all scans are done)
    if scan.node:
        task.jump(task.active_label,scan.node.loc)
