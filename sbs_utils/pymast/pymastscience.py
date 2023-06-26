from ..consoledispatcher import ConsoleDispatcher
import sbs
import inspect
from .pollresults import PollResults

class PyMastScience:
    def __init__(self, task, scans, origin_id, selected_id ) -> None:
        self.scans = scans
        self.selected_id = selected_id
        self.origin_id = origin_id
        # if the npc is None or a filter function it is a more general scan
        if  selected_id is None:
            ConsoleDispatcher.add_select(origin_id, "science_target_UID", self.selected)
            ConsoleDispatcher.add_message(origin_id, "science_target_UID", self.message)
        else:
            ConsoleDispatcher.add_select_pair(origin_id, selected_id, "science_target_UID", self.selected)
            ConsoleDispatcher.add_message_pair(origin_id, selected_id, "science_target_UID", self.message)
        self.task = task
        self.done = False
        self.event = None
        

    def selected(self, ctx, origin_id, event):
        if self.selected_id != event.selected_id or \
            self.origin_id != event.origin_id:
            return
        
        self.event = event
        self.handle_selected(ctx.sim, event.origin_id, event.selected_id, event.extra_tag)
        self.event = None

    def handle_selected(self, sim, origin_id, selected_id, scan_type):
        
        selected_obj = sim.get_space_object(selected_id)
        my_ship  = sim.get_space_object(origin_id)
        if selected_obj is None or my_ship is None:
            self.done = True
            return
        blob = my_ship.data_set
        # blob.set("science_target_UID", event.selected_id,0)
        # temp_id = blob.get("science_target_UID",0)
        # print (f"science_target_UID now:  {event.selected_id}  {temp_id}")

        #what type of scan is it?
        
        side_tag = my_ship.side
        scan_string = side_tag + scan_type

        #is this space object already scanned, for my side and for that scan type?
        target_blob = selected_obj.data_set
        last_scan_string = target_blob.get(scan_string,0)
        if None == last_scan_string:
            # unscanned, so let's scan it now!
            # cur_scan_speed_coeff is normally already set 
            blob.set("cur_scan_ID",selected_id,0)
            blob.set("cur_scan_type",scan_type,0)
            blob.set("cur_scan_percent",0.99,0)

            if my_ship.side == selected_obj.side: # if this target is already on my side
                blob.set("cur_scan_percent",0.999,0)

    def message(self, ctx, message, player_id, event):
        if self.selected_id != event.selected_id or \
            self.origin_id != event.origin_id:
            return
        sim = ctx.sim
        # This event is sent from the c++ code, once, 
        # when a space object scan is completed
        selected = sim.get_space_object(event.selected_id)
        my_ship  = sim.get_space_object(event.origin_id)
        if selected == None or my_ship == None:
            print("Science: Missing id")
            self.done = True
            return
        # concentate the scanner's side and the scan type
        scan_type = event.extra_tag
        side_tag = my_ship.side
        scan_string = side_tag + scan_type

        #change the text of the side/scan for the target
        target_blob = selected.data_set
        scan_tabs = ""
        scans_needed = 0
        scans_completed = 0
        for scan in self.scans:
            # Check to see if things have been scanned
            scans_needed += 1
            test_scan_string = side_tag + scan
            has_text = target_blob.get(test_scan_string,0)
            if has_text is not None and len(has_text)>0:
                scans_completed += 1
            if scan != "scan":
                scan_tabs += f"{scan} "
            if scan == scan_type:
                scan_func = self.scans.get(scan)
                self.event = event
                if inspect.isfunction(scan_func):
                    scan_text = scan_func(self.task.story, self)
                elif inspect.ismethod(scan_func):
                    scan_text = scan_func(self)
                self.event = None
                target_blob.set(scan_string,scan_text,0)
                scans_completed += 1
        self.done = scans_needed == scans_completed
        if self.done:
            print(f"scans finished?{scans_needed} == {scans_completed}")

        target_blob.set("scan_type_list",scan_tabs, 0)

    def run(self):    
        while self.done == False:
            yield PollResults.OK_RUN_AGAIN
