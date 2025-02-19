""" Manage all objective
"""
from sbs_utils.helpers import FrameContext
from sbs_utils.procedural.inventory import get_inventory_value, set_inventory_value
from sbs_utils.agent import Agent
from sbs_utils.procedural.query import to_set
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.mast.pollresults import PollResults
from sbs_utils.mast.mastscheduler import MastAsyncTask



__upgrades_tick_task = None
def upgrade_schedule():
    #
    # Schedule a simple tick task 
    #
    global __upgrades_tick_task
    if __upgrades_tick_task is None:
        __upgrades_tick_task = TickDispatcher.do_interval(objectives_run_all, 5)


class Upgrade:
    ids = 0
    # Just by ID
    all = {}
    # Set algebra will be used to 
    # get the subset
    active = set()
    timed = set()
    # These are run when it changes
    available = {}
    # these need to run via task
    # These will be set by agent
    by_agent ={}
    # 
    changed_agents = set()
    
    def __init__(self, agent, label, data, client_id):
        self.agent = agent
        self.label = label #Label could have meta_data
        self.data = data
        self._done = False
        self._result = PollResults.OK_IDLE
        # Ability to have console/client based objectives
        self.client_id = client_id
        self.scratch = {}
        self.id = Upgrade.ids+1
        Upgrade.ids = self.id

        Upgrade.all[self.id] = self
        # Not active by default
        Upgrade.available.add(self.id)
        # Add quick look up by agent
        ba = Upgrade.by_agent.get(agent, set())
        ba.add(self.id)
        Upgrade.by_agent[agent]=ba

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
        if self.done:
            self.discard()

    def discard(self):
        Upgrade.changed_agents.add(self)
        self.remove()

    def remove(self):
        del Upgrade.all[self.id]
        # Not active by default
        Upgrade.available.discard(self.id)
        Upgrade.timed.discard(self.id)
        # Add quick look up by agent
        ba = Upgrade.by_agent.get(self.agent, None)
        if ba is not  None:
            ba.discard(self.id)
            Upgrade.by_agent[self.agent]=ba

    def activate(self):
        Upgrade.active.add(self.id)
        # If timed add it
        Upgrade.changed_agents.add(self.agent)


    def deactivate(self):
        Upgrade.active.discard(self.id)
        # If timed add it
        #....
        # Schedule agent to recalculate
        Upgrade.changed_agents.add(self.agent)



def upgrade_add(agent_id_or_set, label, data=None, client_id=0, activate=False):
    # Make sure a tick task is running
    upgrade_schedule()

    agent_id_or_set = to_set(agent_id_or_set)
    for agent in agent_id_or_set:
        up = Upgrade(agent, label, data, client_id)
        if activate:
            up.activate()

def upgrade_remove_for_agent(agent):
    by_agent = Upgrade.by_agent.get(agent)
    if by_agent is None:
        return 
    for ob_id in by_agent:
        obj : Upgrade
        obj = Upgrade.all.get(ob_id)
        if obj is None:
            continue
        obj.remove()

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
        
        for agent in Upgrade.changed_agents:
            
            # Reset set the important value
            # ??
            by_agent = Upgrade.by_agent.get(agent, set())
            agent = Agent.get(agent)
            if agent is None:
                upgrade_remove_for_agent(agent)
                continue
            # This should be a list of upgrades by agent and active
            active = Upgrade.activate & by_agent
            for up_id in active:
                obj = Upgrade.all.get(up_id)
                if obj is None:
                    continue

                task = get_inventory_value(obj.client_id, "GUI_TASK", FrameContext.task)
                t : MastAsyncTask
                t = task.start_task(obj.label, obj.data, defer=True)
                t.set_variable("__OBJECTIVE__", obj)
                t.set_variable("OBJECTIVE_AGENT_ID", agent)
                t.tick_in_context()
                obj.result = t.tick_result
            
        
    except Exception as e:
        msg = e
        print(f"Exception in objective processing {msg}")

    Upgrade.changed_agents = set()
    __upgrades_is_running = False





