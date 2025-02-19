""" Manage all objective
"""
from sbs_utils.helpers import FrameContext
from sbs_utils.procedural.inventory import get_inventory_value, set_inventory_value
from sbs_utils.procedural.links import linked_to,unlink, has_link_to, link
from sbs_utils.agent import Agent, get_story_id
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


    def run(self):
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
            leave = self.label.labels.get("leave", None)
            if leave is not None:
                self.run_sub_label(leave.loc+1)
        
            self.remove_role("OBJECTIVE_RUN")
            unlink(self.agent, "OBJECTIVE_RUN", self.id)
        


    def run_sub_label(self, loc):
        task = get_inventory_value(self.client_id, "GUI_TASK", FrameContext.task)
        t : MastAsyncTask
        t = task.start_task(self.label, self.data, defer=True)
        t.jump(self.label, loc)
        t.set_variable("OBJECTIVE", self)
        t.set_variable("OBJECTIVE_ID", self.id)
        t.set_variable("OBJECTIVE_AGENT_ID", self.agent)
        t.tick_in_context()
        return t.tick_result
            


def objective_add(agent_id_or_set, label, data=None, client_id=0):
    # Make sure a tick task is running
    objective_schedule()

    
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
        for obj_id in Agent.get_role_set("OBJECTIVE_RUN"):
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





