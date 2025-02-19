""" Manage all objective
"""
from sbs_utils.helpers import FrameContext
from sbs_utils.procedural.inventory import get_inventory_value, set_inventory_value
from sbs_utils.agent import Agent
from sbs_utils.procedural.query import to_set
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.mast.pollresults import PollResults
from sbs_utils.mast.mastscheduler import MastAsyncTask



__objective_tick_task = None
def objective_schedule():
    #
    # Schedule a simple tick task 
    #
    global __objective_tick_task
    if __objective_tick_task is None:
        __objective_tick_task = TickDispatcher.do_interval(objectives_run_all, 5)


class Objective:
    ids = 0
    all = {}
    def __init__(self, agent, label, data, client_id):
        self.agent = agent
        self.label = label #Label could have meta_data
        self.data = data
        self._done = False
        self._result = PollResults.OK_IDLE
        # Ability to have console/client based objectives
        self.client_id = client_id
        self.scratch = {}
        self.id = Objective.ids+1
        Objective.ids = self.id
        Objective.all[self.id] = self

    def set_scratch_value(self, key, value):
        self.scratch[key] = value

    def get_scratch_value(self, key, defa):
        return self.scratch.get(key, defa)

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

def objective_add(agent_id_or_set, label, data=None, client_id=0):
    # Make sure a tick task is running
    objective_schedule()

    name = label.meta_data.get("display_name")
    desc = label.desc
    
    agent_id_or_set = to_set(agent_id_or_set)
    for agent in agent_id_or_set:
        Objective(agent, label, data, client_id)


__objectives_is_running = False
def objectives_run_all(tick_task):
    global __objectives_is_running
    if __objectives_is_running:
        return
    __objectives_is_running = True


    try:
        remove_obj = []
        # Don't care about the key here
        for obj in Objective.all.values():
            # Verify the agent is valid
            agent = obj.agent
            agent_obj = Agent.get(agent)
            if agent_obj is None:
                remove_obj.append(obj.id)
                continue
            
            task = get_inventory_value(obj.client_id, "GUI_TASK", FrameContext.task)
            t : MastAsyncTask
            t = task.start_task(obj.label, obj.data, defer=True)
            t.set_variable("__OBJECTIVE__", obj)
            t.set_variable("OBJECTIVE_AGENT_ID", agent)
            t.tick_in_context()
            obj.result = t.tick_result
            if obj.done:
                remove_obj.append(obj.id)

            
        for k in remove_obj: del Objective.all[k]
    except Exception as e:
        msg = e
        print(f"Exception in objective processing {msg}")
    __objectives_is_running = False





