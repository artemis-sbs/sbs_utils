""" Manage all objective
"""
from sbs_utils.procedural.links import linked_to,unlink, has_link_to, link
from sbs_utils.procedural.inventory import get_inventory_value, set_inventory_value
from sbs_utils.procedural.roles import role
from sbs_utils.procedural.query import to_data_set, to_object
from sbs_utils.tickdispatcher import TickDispatcher, TickTask
from sbs_utils.procedural.routes import follow_route_select_science
from sbs_utils.helpers import FrameContext
import random


__extra_scan_sources_tick_task = None
def extra_scan_sources_schedule():
    #
    # Schedule a simple tick task 
    #
    global __extra_scan_sources_tick_task
    if __extra_scan_sources_tick_task is None:
        __extra_scan_sources_tick_task = TickDispatcher.do_interval(extra_scan_sources_run_all, 5)




__extra_scan_sourcess_is_running = False
def extra_scan_sources_run_all(tick_task:TickTask):
    global __extra_scan_sourcess_is_running

    if __extra_scan_sourcess_is_running:
        return
    __extra_scan_sourcess_is_running = True
    

    # Give it some variability of when run
    tick_task.delay = 5*(1+random.randrange(4))

    player_and_others = role("__player__") | role("has_science_scan")
    l = len(player_and_others)
    #print(f"extra_scan_sources {l}")

    for  scanner_id in player_and_others:
        scanner = to_object(scanner_id)
        if scanner is None:
            continue
        name = scanner.name
        
        last_crc = get_inventory_value(scanner_id, "scan_source_crc", 0)

        #print(f"extra_scan_sources {name} {last_crc}")
        # copy so it can be modified
        friends = set(linked_to(scanner_id, "extra_scan_source"))
        crc = 0
        for v in friends:
            crc += v & 0x00FF_FFFF_FFFF_FFFF
        # if no change don't do anything
        # Reduce network traffic
        if crc == last_crc:
            continue

        set_inventory_value(scanner_id, "scan_source_crc", crc)
        data_set = to_data_set(scanner_id)
        side = scanner.side
        num_ids = 0
        for friend in friends:
            # Remove if friend is no more
            f_data = to_data_set(friend)
            if  f_data is None:
                unlink(scanner_id, "extra_scan_source", friend)
                continue

            data_set.set("extra_scan_source", friend, num_ids)
            num_ids += 1

            has_initial = f_data.get(f"{side}scan", 0)

            if not has_initial:
                follow_route_select_science(scanner_id, friend)
        data_set.set("num_extra_scan_sources",num_ids,0)

        #print(f"extra_scan_sources {num_ids}")
        
    __extra_scan_sourcess_is_running = False





