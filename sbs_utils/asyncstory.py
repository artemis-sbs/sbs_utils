from enum import IntEnum
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.consoledispatcher import ConsoleDispatcher
from sbs_utils.engineobject import EngineObject
from sbs_utils import faces
import sbs
import inspect

class PollResults(IntEnum):
    OK_RUN_AGAIN=1
    OK_ADVANCE_TRUE =2
    OK_ADVANCE_FALSE=3
    OK_JUMP= 4
    OK_END = 99
    FAIL_END = 100



class AsyncScience:
    def __init__(self, task, player_id, npc_id_or_filter, scans ) -> None:
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
        

class AsyncComms:
    def __init__(self, task, player_id, npc_id_or_filter, buttons ) -> None:
        self.buttons = buttons
        # if the npc is None or a filter function it is a more general scan
        if inspect.isfunction(npc_id_or_filter) or inspect.ismethod(npc_id_or_filter) or npc_id_or_filter is None:
            self.filter_npc = npc_id_or_filter
            ConsoleDispatcher.add_select(player_id, "comms_target_UID", self.selected)
            ConsoleDispatcher.add_message(player_id, "comms_target_UID", self.message)
        else:
            ConsoleDispatcher.add_select_pair(player_id, npc_id_or_filter, "comms_target_UID", self.selected)
            ConsoleDispatcher.add_message(player_id, npc_id_or_filter, "comms_target_UID", self.message)
        self.task = task
        self.event = None
        self.done = False

        
    def selected(self, sim, _ , event):
        if self.filter_npc and not self.filter_npc(event.selected_id):
            return
        
        player_so = EngineObject.get(event.origin_id)
        npc_so = EngineObject.get(event.selected_id)

        if player_so is None or npc_so is None:
            return
        npc_comms_id = npc_so.comms_id
        face_text = faces.get_face(event.selected_id)
        sbs.send_comms_selection_info(event.origin_id, face_text, "white", npc_comms_id)
        i = 0
        for button, data in self.buttons.items():
            color = "white"
            if isinstance(data, tuple):
                color = data[0]
            sbs.send_comms_button_info(event.origin_id, color, button, f"comms:{i}")
            i+=1

    
    def message(self, sim, message, player_id, event):
        if not message.startswith("comms:") or len(message)<7:
            return
        self.event = event
        button = int(message[6:])
        if button<len(self.buttons):
            button_func = list(self.buttons.values())[button]
            if isinstance(button_func, tuple):
                button_func = button_func[1]
            if button_func:
                if inspect.isfunction(button_func):
                    def pusher(story):
                        gen = button_func(self.task.story, self)
                        if gen is not None:
                            for res in gen:
                                yield res
                        yield story.pop()
                    self.story.push(pusher)
                elif inspect.ismethod(button_func):
                    ##############
                    ## This is some wild code
                    ## Schedule a inner function 
                    ## to automatically pop()
                    def pusher(story):
                        gen = button_func(self)
                        if gen is not None:
                            for res in gen:
                                yield res
                        yield story.pop()
                    self.task.story.push(pusher)
        self.done = True

    def have_other_tell_player(self, text, color=None, face=None, comms_id=None):
        # Messge from NPC
        if face is None:
            face = faces.get_face(self.event.selected_id)
        if comms_id is None:
            npc_so = EngineObject.get(self.event.selected_id)
            comms_id = npc_so.comms_id
        if color is None:
            color = "gray"
        sbs.send_comms_message_to_player_ship(self.event.origin_id, self.event.selected_id, color, face, 
                comms_id,  text)
        
    def have_player_tell_other(self, text, color=None, face=None, comms_id=None):
        # Messge from player
        if face is None:
            face = faces.get_face(self.event.origin_id)
        if comms_id is None:
            so = EngineObject.get(self.event.origin_id)
            comms_id = so.comms_id
        if color is None:
            color = "gray"
        sbs.send_comms_message_to_player_ship(self.event.origin_id, self.event.selected_id, 
                color, face, 
                comms_id,  text)

    def run(self):    
        while self.done == False:
            yield PollResults.OK_RUN_AGAIN
        

###
##
## Runs a set of generator functions
##
class AsyncTask:
    def __init__(self, story, scheduler, label) -> None:
        super().__init__()
        self.stack=[]
        self.delay_time = None
        self.scheduler = scheduler
        self.story = story
        self.pending_jump = label
        self.await_gen = None
        #self.jump(label)
        
        self.last_poll_result = None
            

    def tick(self, sim):
        self.sim = sim    
        # Keep running until told to defer or you've jump 100 time
        # Arbitrary number
        throttle = 0
        while throttle < 100:
            throttle += 1
            if self.pending_jump:
                self.do_jump()
            
            gen = self.await_gen if self.await_gen else self.current_gen
            # It is possible that the label
            # did not Yield, which is OK just End 
            if gen is None:
                self.last_poll_result = PollResults.OK_END
                return self.last_poll_result

            for res in gen:
                self.last_poll_result = res
                if res == PollResults.OK_RUN_AGAIN:
                    return
                if res == PollResults.OK_JUMP:
                    break

        # don't hold pointer
        self.sim = None
        return self.last_poll_result

    def do_jump(self):
        label = self.pending_jump
        self.pending_jump = None
        if isinstance(label, str):
            if getattr(self.story, label):
                self.current_gen = getattr(self.story, label)()
                return PollResults.OK_JUMP
        elif inspect.isfunction(label):
            self.current_gen = label(self.story)
            return PollResults.OK_JUMP
        elif inspect.ismethod(label):
            self.current_gen = label()
            return PollResults.OK_JUMP
        return PollResults.FAIL_END
    
    def jump(self, label):
        self.pending_jump = label
        return PollResults.OK_JUMP

    def push(self, label):
        self.stack.append(self.current_gen)
        return self.jump(label)

    def pop(self):
        if len(self.stack) > 0:
            self.current_gen = self.stack.pop()
            return PollResults.OK_JUMP
        return PollResults.FAIL_END
    
    def delay(self,  delay):
        self.stack.append(self.current_gen)
        self.current_gen = self._delay(delay)
        return PollResults.OK_RUN_AGAIN
  
    def _delay(self, delay):
        delay_time = self.sim.time_tick_counter + 30 * delay
        while delay_time > self.sim.time_tick_counter:
            #print ("tick")
            yield PollResults.OK_RUN_AGAIN
        yield self.pop()

    def await_science(self, player, npc, scans):
        self.await_gen = self.run_science(player, npc, scans)
        return PollResults.OK_RUN_AGAIN

    def run_science(self, player, npc, scans):
        science = AsyncScience(self, player, npc, scans)
        while science.done == False:
            yield PollResults.OK_RUN_AGAIN
        self.await_gen = None

    def await_comms(self, player, npc, buttons):
        self.await_gen = self.run_comms(player, npc, buttons)
        return PollResults.OK_RUN_AGAIN

    def run_comms(self, player, npc, buttons):
        comms = AsyncScience(self, player, npc, buttons)
        while comms.done == False:
            yield PollResults.OK_RUN_AGAIN
        self.await_gen = None


class AsyncScheduler:
    def __init__(self, story, label) -> None:
        self.tick_task = None
        #self.current_gen = self.start()
        self.tasks = []
        self.remove_tasks = set()
        self.new_tasks = []
        self.scheduler = self #Alais for scoping
        self.shared = story
        self.story = story
        self.task = None
        # Initial tasks
        self.tasks.append(AsyncTask(story, self, label))

    def schedule_task(self, label):
        self.schedule_a_task(AsyncTask(self.story, self, label))
        return PollResults.OK_RUN_AGAIN
    
    def schedule_a_task(self, task):
        self.new_tasks.append(task)
        return PollResults.OK_RUN_AGAIN

    def tick(self, sim):
        self.story.scheduler = self.scheduler
        for task in self.tasks:
            self.story.task = task
            self.task = task            
            task.tick(sim)
            if task.last_poll_result == PollResults.OK_END:
                self.remove_tasks.add(task)
        for finished in self.remove_tasks:
            self.tasks.remove(finished)
        self.remove_tasks.clear()
        self.tasks.extend(self.new_tasks)




class AsyncStory:
    def __init__(self) -> None:
        self.schedulers = []
        self.remove_scheduler = []
        self.shared = self #Alias for scoping


    def enable(self, sim, delay=0, count=None):
        self.tick_task = TickDispatcher.do_interval(sim, self, delay, count)
        self.schedulers.append(AsyncScheduler(self, "start"))

    def delay(self,  delay):
        return self.task.delay(delay)
    
    def await_science(self, player, npc, scans):
        return self.task.await_science(player, npc, scans)
    
    def schedule_science(self, player, npc, scans):
        task = AsyncTask(self,self.scheduler, None)
        science = AsyncScience(task, player, npc, scans)
        task.current_gen = science.run()
        return self.scheduler.schedule_a_task(task)

    def await_comms(self, player, npc, buttons):
        return self.task.await_comms(player, npc, buttons)
    
    def schedule_comms(self, player, npc, buttons):
        task = AsyncTask(self,self.scheduler, None)
        comms = AsyncComms(task, player, npc, buttons)
        task.current_gen = comms.run()
        return self.scheduler.schedule_a_task(task)


    def schedule_task(self, label):
        return self.scheduler.schedule_task(label)


    def jump(self, label):
        return self.task.jump(label)
    def push(self, label):
        return self.task.push(label)
    def pop(self):
        return self.task.pop()

    def disable(self):
        if self.tick_task is not None:
            self.tick_task.stop()
            self.tick_task = None

    def __call__(self, sim, sched=None):
        self.sim = sim
        for sched in self.schedulers:
            self.scheduler = sched
            sched.tick(sim)
            if len(sched.tasks) == 0:
                self.remove_scheduler.append(sched)
        for finished in self.remove_scheduler:
            self.schedulers.remove(finished)
        self.remove_scheduler.clear()
        if len(self.schedulers)==0:
            self.disable()
        self.sim = None


    def END(self):
        self.remove_tasks.add(self.task)

    def start(self):
        pass


