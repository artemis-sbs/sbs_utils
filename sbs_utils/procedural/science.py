from . import query 
from .inventory import get_inventory_value
from .roles import has_role
from .. import faces
from ..agent import Agent
from ..helpers import FrameContext
import sbs




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

