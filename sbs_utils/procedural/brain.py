""" Manage all brains
"""
from sbs_utils.helpers import FrameContext
from sbs_utils.procedural.inventory import get_inventory_value, set_inventory_value
from sbs_utils.procedural.links import linked_to,unlink, has_link_to, link
from sbs_utils.agent import Agent, get_story_id
from sbs_utils.procedural.query import to_set, to_object
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.mast.pollresults import PollResults
from sbs_utils.mast.mastscheduler import MastAsyncTask


__brain_tick_task = None
def brain_schedule():
    #
    # Schedule a simple tick task 
    #
    global __brain_tick_task
    if __brain_tick_task is None:
        __brain_tick_task = TickDispatcher.do_interval(brains_run_all, 3)


class Brain:
    ids = 0
    all = {}
    def __init__(self, agent, label, data, client_id):
        super().__init__()
        self.agent = agent
        self.label = label #Label could have metadata
        self.data = data
        self._done = False
        self._started = False
        self._result = PollResults.OK_IDLE
        # Ability to have console/client based brains
        self.client_id = client_id
        self.scratch = {}

        brains = Brain.all.get(agent, [])
        brains.append(self)
        Brain.all[agent] = brains

    @property
    def done(self):
        return self._done
    
    @done.setter
    def done(self, _done):
        self._done = _done
    
    @property
    def result(self):
        return self._result
    
    @result.setter
    def result(self, res):
        # Don't overwrite when done
        if self._done:
            return
        self._result = res


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
            brains = Brain.all.get(self.agent, [])
            brains = [b for b in brains if b != self]
            Brain.all[self.agent] = brains
        


    def run_sub_label(self, loc):
        task = get_inventory_value(self.client_id, "GUI_TASK", FrameContext.task)
        t : MastAsyncTask
        t = task.start_task(self.label, self.data, defer=True)
        t.jump(self.label, loc)
        t.set_variable("BRAIN", self)
        #t.set_variable("BRAIN_ID", self.id)
        t.set_variable("BRAIN_AGENT", to_object(self.agent))
        t.set_variable("BRAIN_AGENT_ID", self.agent)
        t.tick_in_context()
        return t.tick_result
            


def brain_add(agent_id_or_set, label, data=None, client_id=0):

    # Make sure a tick task is running
    brain_schedule()

    
    agent_id_or_set = to_set(agent_id_or_set)
    for agent in agent_id_or_set:
        # Added to __all in init
        Brain(agent, label, data, client_id)



__brains_is_running = False
def brains_run_all(tick_task):
    global __brains_is_running
    if __brains_is_running:
        return
    __brains_is_running = True


    try:
        remove_obj = []
        # Don't care about the key here
        for agent in Brain.all:
            brains = list(Brain.all[agent])
            for brain in brains:
                # Verify the agent is valid
                agent = brain.agent
                agent_obj = Agent.get(agent)
                if agent_obj is None:
                    remove_obj.append(agent)
                    break
                brain.run()
                if brain.result == PollResults.OK_SUCCESS:
                    break
            if len(Brain.all[agent])==0:
                remove_obj.append(agent)

        for agent in remove_obj:        
            Brain.all.pop(agent, None)


            
        
    except Exception as e:
        msg = e
        print(f"Exception in brain processing {msg}")
    __brains_is_running = False





