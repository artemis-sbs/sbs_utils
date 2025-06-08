""" Manage all objective
"""
from sbs_utils.helpers import FrameContext
from sbs_utils.procedural.inventory import get_inventory_value, set_inventory_value
from sbs_utils.procedural.links import linked_to,unlink, has_link_to, link
from sbs_utils.agent import Agent, get_story_id
from sbs_utils.procedural.query import to_set, to_object_list
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.mast.pollresults import PollResults
from sbs_utils.mast.mastscheduler import MastAsyncTask
from sbs_utils.procedural.signal import signal_emit


__objective_tick_task = None
def objective_schedule():
    #
    # Schedule a simple tick task 
    #
    global __objective_tick_task
    if __objective_tick_task is None:
        __objective_tick_task = TickDispatcher.do_interval(objectives_run_everything, 1)
        __objective_tick_task.state = 0

from .brain import brains_run_all
from .extra_scan_sources import extra_scan_sources_run_all
import time




__end_game_promise = []
__end_game_ids = 100
def game_end_condition_add(promise, message, is_win, music=None, signal=None):
    global __end_game_ids
    global __end_game_promise
# Make sure low level task runner is running
    objective_schedule()

    id = __end_game_ids
    __end_game_ids += 1
    tup = (id, promise, message, is_win, music, signal)
    __end_game_promise.append(tup)
    return id

def game_end_condition_remove(id):
    global __end_game_promise
    new_cond = [cond for cond in __end_game_promise if cond[0]!=id]
    __end_game_promise = new_cond


def game_end_run_all(tt):
    for cond in __end_game_promise:
        id, promise, message, is_win, music, signal = cond
        promise.poll()
        if promise.done():
            ## play music
            if music is not None:
                FrameContext.context.sbs.play_music_file(0,music)
            if is_win:
                FrameContext.context.sbs.play_music_file(0,"music/default/failure")
            else:
                FrameContext.context.sbs.play_music_file(0,"music/default/victory")

            ## show the end screen by notifying the system
            ## with a signal
            Agent.SHARED.set_inventory_value("GAME_STARTED",  False)
            Agent.SHARED.set_inventory_value("GAME_ENDED",  True)
            Agent.SHARED.set_inventory_value("START_TEXT",  message)
            data = {"promise": promise, "message": message, "is_win": is_win}
            if signal is None:
                signal_emit("show_game_results", data)
            else:
                signal_emit(signal, data)


def objectives_run_everything(tick_task):
    state = tick_task.state % 3
    tick_task.state += 1
    #t = time.perf_counter()
    if state == 0:
        objectives_run_all(tick_task)
    elif state == 1:
        brains_run_all(tick_task)
    elif state == 2:
        extra_scan_sources_run_all(tick_task)
        game_end_run_all(tick_task)
        

    # Cycle this every 5 seconds
    tick_task.state = tick_task.state % 5
    

    # et = time.perf_counter() - t
    # if et > 0.033:
    #     print(f"Elapsed time: {et} shared task state {state} ")


class Objective(Agent):
    ids = 0
    def __init__(self, agent, label, data, client_id):
        super().__init__()
        self.agent = agent
        self.label = label #Label could have metadata
        self.data = data
        self._done = False
        self._started = False
        self._result = PollResults.OK_IDLE
        # Ability to have console/client based objectives
        self.client_id = client_id
        self.scratch = {}
        self.id = get_story_id()
        self.add()
        desc = self.label.get_inventory_value("desc")
        if desc is None:
            desc = self.label.name
        self.set_inventory_value("desc", desc)
        self.add_role("OBJECTIVE")
        self.add_role("OBJECTIVE_RUN")
        link(self.agent, "OBJECTIVE", self.id)
        link(self.agent, "OBJECTIVE_RUN", self.id)


    @property
    def done(self):
        return self._done
    
    @property
    def result(self):
        return self._result
    
    @result.setter
    def result(self, res):
        # Don't overwrite when done
        if self._done:
            return
        self._result = res
        self._done = self._result != PollResults.OK_IDLE
        if self._done:
            self.remove_role("OBJECTIVE")
            unlink(self.agent, "OBJECTIVE", self.id)
            self.remove_role("OBJECTIVE_RUN")
            unlink(self.agent, "OBJECTIVE_RUN", self.id)



    def run(self):
        if self.done:
            return
        if not self._started:
            self._started = True
            enter = self.label.labels.get("enter")
            if enter is not None:
                self.run_sub_label(enter.loc+1)
            
        test = self.label.labels.get("test",None)
        if test is not None:
            self.result = self.run_sub_label(test.loc+1)
        else:
            self.result = self.run_sub_label(0)

        if self.done:
            self.stop_and_leave(self.result)

    def stop_and_leave(self, result=PollResults.FAIL_END):
        leave = self.label.labels.get("leave", None)
        self.result = result
        if leave is not None:
            self.run_sub_label(leave.loc+1)

    def run_sub_label(self, loc):
        agent_object = Agent.get(self.agent)
        if agent_object is None:
            return PollResults.FAIL_END
        task = get_inventory_value(self.client_id, "GUI_TASK", FrameContext.task)
        t : MastAsyncTask
        t = task.start_task(self.label, self.data, defer=True)
        t.jump(self.label, loc)
        t.set_variable("OBJECTIVE", self)
        t.set_variable("OBJECTIVE_ID", self.id)
        t.set_variable("OBJECTIVE_AGENT_ID", self.agent)
        t.set_variable("OBJECTIVE_AGENT", agent_object)
        t.tick_in_context()
        return t.tick_result

def objective_clear(agent_id_or_set):
    agent_id_or_set = to_set(agent_id_or_set)
    for agent in agent_id_or_set:
        for obj in to_object_list(linked_to(agent, "OBJECTIVE")):
            if obj is not None:
                obj.stop_and_leave()

        

def objective_add(agent_id_or_set, label, data=None, client_id=0):
    # Make sure a tick task is running
    objective_schedule()

    if isinstance(label, dict):
        data =  label.get("data",data)
        label = label.get("label")
        

    if isinstance(label, str) or label is None:
        task = FrameContext.task
        l = label
        label = task.main.mast.labels.get(label, None)
        if label is None:
            print(f"Ignoring objective configured with invalid label {l}")
            return

    label_list = [(label, data)]
    
    if isinstance(label, list):
        label_list = []
        for l in label:
            if isinstance(l, str):
                this_label = l
                this_data = data
            elif isinstance(l, dict):
                this_label = l.get("label")
                this_data = l.get("data")
            else:
                this_label = l
                this_data = data
            if this_label is None:
                continue # Bad data
            if this_data is not None and data is not None and data != this_data:
                this_data = data | this_data
            elif this_data is None:
                this_data = data

            if isinstance(this_label, str) or label is None:
                task = FrameContext.task
                l = this_label
                this_label = task.main.mast.labels.get(this_label, None)
                if this_label is None:
                    print(f"Ignoring objective configured with invalid label {l}")
                    continue
            
            label_list.append((this_label, this_data))
    ret = []
    for ld in label_list:
        label, data = ld
        agent_id_or_set = to_set(agent_id_or_set)
        for agent in agent_id_or_set:
            # Added to __all in init
            ret.append(Objective(agent, label, data, client_id))
    if len(ret)==1:
        return ret[0]
    return ret

__objectives_is_running = False
def objectives_run_all(tick_task):
    global __objectives_is_running
    if __objectives_is_running:
        return
    __objectives_is_running = True


    try:
        remove_obj = []
        # Don't care about the key here
        for obj_id in list(Agent.get_role_set("OBJECTIVE_RUN")):
            obj = Agent.get(obj_id)
            # Verify the agent is valid
            agent = obj.agent
            agent_obj = Agent.get(agent)
            if agent_obj is None:
                remove_obj.append(obj.id)
                continue
            obj.run()
        
    except Exception as e:
        msg = e
        print(f"Exception in objective processing {msg}")
    __objectives_is_running = False





