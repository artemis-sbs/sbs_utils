""" Manage all objective
"""
from sbs_utils.helpers import FrameContext
from sbs_utils.agent import Agent, get_story_id
from sbs_utils.procedural.query import to_set, to_object
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.mast.pollresults import PollResults
from sbs_utils.mast.mastscheduler import MastAsyncTask
from sbs_utils.procedural.roles import add_role, role, remove_role
from sbs_utils.procedural.links import linked_to,unlink, has_link_to
from sbs_utils.procedural.inventory import get_inventory_value



__upgrades_tick_task = None
def upgrade_schedule():
    #
    # Schedule a simple tick task 
    #
    global __upgrades_tick_task
    if __upgrades_tick_task is None:
        __upgrades_tick_task = TickDispatcher.do_interval(objectives_run_all, 5)


class Upgrade(Agent):
    def __init__(self, agent_id, label, data, client_id):
        self.agent_id = agent_id
        self.label = label #Label could have metadata
        self.data = data
        self._done = False
        self._result = PollResults.OK_IDLE
        # Ability to have console/client based objectives
        self.client_id = client_id
        self.id = get_story_id()
        self.add()
        self.add_role("__UPGRADE__")
        self.add_link(self.agent_id, "__UPGRADE__", self.id)

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
        if self.done:
            self.discard()

    def discard(self):
        add_role(self.agent_id, "__UPGRADE_CHANGED__")
        unlink(self.agent_id, "__UPGRADE__", self.id)
        self.remove()

    def activate(self):
        self.add_role("__UPGRADE_ACTIVE__")


    def deactivate(self):
        self.remove_role("__UPGRADE_ACTIVE__")
        # If timed add it
        #....
        self.remove_role("__UPGRADE_TIMED__")
        # Schedule agent to recalculate
        add_role(self.agent_id, "__UPGRADE_CHANGED__")



def upgrade_add(agent_id_or_set, label, data=None, client_id=0, activate=False):
    # Make sure a tick task is running
    upgrade_schedule()

    agent_id_or_set = to_set(agent_id_or_set)
    for agent in agent_id_or_set:
        up = Upgrade(agent, label, data, client_id)
        if activate:
            up.activate()

def upgrade_remove_for_agent(agent):
    by_agent = linked_to(agent, "__UPGRADE__")
    for ob_id in by_agent:
        Agent.remove_id(ob_id)

__upgrades_is_running = False
def objectives_run_all(tick_task):
    global __upgrades_is_running
    if __upgrades_is_running:
        return
    __upgrades_is_running = True


    try:
        # Roll through all the timed one
        # to see if they remain active

        # Roll though all changed agents
        # use copy so it can be altered
        changed_agents = set(role("__UPGRADE_CHANGED__"))
        for agent_id in changed_agents:
            #
            agent = Agent.get(agent_id)
            if agent is None:
                upgrade_remove_for_agent(agent_id)
                continue
            # This should be a list of upgrades by agent and active
            active = role("__UPGRADE_ACTIVE__") & linked_to(agent_id, "__UPGRADE__")
            for up_id in active:
                obj = to_object(up_id)
                if obj is None:
                    continue

                task = get_inventory_value(obj.client_id, "GUI_TASK", FrameContext.task)
                t : MastAsyncTask
                t = task.start_task(obj.label, obj.data, defer=True)
                t.set_variable("UPGRADE", obj)
                t.set_variable("UPGRADE_ID", up_id)
                t.set_variable("UPGRADE_AGENT_ID", agent)
                t.tick_in_context()
                obj.result = t.tick_result
            remove_role(agent_id, "__UPGRADE_CHANGED__")
            
        
    except Exception as e:
        msg = e
        print(f"Uncaught exception in upgrades processing {msg}")

        
    __upgrades_is_running = False





