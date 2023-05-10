from ..consoledispatcher import ConsoleDispatcher
import sbs
import inspect
from .pollresults import PollResults

class PyMastScience:
    def __init__(self, task, scans, player_id, npc_id_or_filter ) -> None:
        self.scans = scans
        # if the npc is None or a filter function it is a more general scan
        if inspect.isfunction(npc_id_or_filter) or inspect.ismethod(npc_id_or_filter) or npc_id_or_filter is None:
            self.filter_npc = npc_id_or_filter
            ConsoleDispatcher.add_select(player_id, "science_target_UID", self.selected)
            ConsoleDispatcher.add_message(player_id, "science_target_UID", self.message)
        else:
            ConsoleDispatcher.add_select_pair(player_id, npc_id_or_filter, "science_target_UID", self.selected)
            ConsoleDispatcher.add_message(player_id, npc_id_or_filter, "science_target_UID", self.message)
        self.task = task
        self.done = False

        
    def selected(self, sim, player_id, event):
        # If there is a fliter function use it to filter out 
        # what is passed here
        if self.filter_npc and not self.filter_npc(event.selected_id):
            return
        
        selected_obj = sim.get_space_object(event.selected_id)
        my_ship  = sim.get_space_object(event.origin_id)
        if selected_obj is None or my_ship is None:
            return
        blob = my_ship.data_set
        # blob.set("science_target_UID", event.selected_id,0)
        # temp_id = blob.get("science_target_UID",0)
        # print (f"science_target_UID now:  {event.selected_id}  {temp_id}")

        #what type of scan is it?
        scan_type = event.extra_tag
        side_tag = my_ship.side
        scan_string = side_tag + scan_type

        #is this space object already scanned, for my side and for that scan type?
        target_blob = selected_obj.data_set
        last_scan_string = target_blob.get(scan_string,0)
        if None == last_scan_string:
            # unscanned, so let's scan it now!
            # cur_scan_speed_coeff is normally already set 
            blob.set("cur_scan_ID",event.selected_id,0)
            blob.set("cur_scan_type",event.extra_tag,0)
            blob.set("cur_scan_percent",0.0,0)

            if my_ship.side == selected_obj.side: # if this target is already on my side
                blob.set("cur_scan_percent",0.999,0)

    def message(self, sim, message, player_id, event):
        # This event is sent from the c++ code, once, when a space object scan is completed
        selected = sim.get_space_object(event.selected_id)
        my_ship  = sim.get_space_object(event.origin_id)
        if selected == None or my_ship == None:
            # self.done = True
            return
        # concentate the scanner's side and the scan type
        scan_type = event.extra_tag
        side_tag = my_ship.side
        scan_string = side_tag + scan_type

        #change the text of the side/scan for the target
        target_blob = selected.data_set
        scan_tabs = ""
        for scan in self.scans:
            if scan != "scan":
                scan_tabs += f"{scan} "
            if scan == scan_type:
                scan_func = self.scans.get(scan)
                if inspect.isfunction(scan_func):
                    scan_text = scan_func(self.task.story, event)
                elif inspect.ismethod(scan_func):
                    scan_text = scan_func(event)
                target_blob.set(scan_string,scan_text,0)
            

        target_blob.set("scan_type_list",scan_tabs, 0)

    def run(self):    
        while self.done == False:
            yield PollResults.OK_RUN_AGAIN
