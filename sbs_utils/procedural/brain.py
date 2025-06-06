""" Manage all brains
"""
from sbs_utils.helpers import FrameContext
from sbs_utils.procedural.inventory import get_inventory_value, set_inventory_value, has_inventory
from sbs_utils.agent import Agent
from sbs_utils.procedural.query import to_set, to_object
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.mast.pollresults import PollResults
from sbs_utils.mast.mastscheduler import MastAsyncTask
from sbs_utils.mast.mast_node import MastNode

from enum import IntFlag


#__brain_tick_task = None
def brain_schedule():
    from .objective import objective_schedule
    objective_schedule()
    # This is handled in Objectives NOW
    #
    # Schedule a simple tick task 
    #
    # global __brain_tick_task
    # if __brain_tick_task is None:
    #     __brain_tick_task = TickDispatcher.do_interval(brains_run_all, 3)

class BrainType(IntFlag):
    # Alters result
    Invert = 0x02
    AlwayFail = 0x04
    AlwaySuccess = 0x08
    #
    Simple = 0x100
    Sequence = 0x200
    Select = 0x400


class Brain:
    def __init__(self, agent, label, data, client_id, brain_type=BrainType.Simple):
        super().__init__()
        self.agent = agent
        self.label = label #Label could have metadata
        self.data = data
        self._started = False
        self._result = PollResults.OK_IDLE
        self._active = None
        # Ability to have console/client based brains
        self.client_id = client_id
        self.brain_type = brain_type
        self.children = []

    def add_child(self, child):
        self.children.append(child)

    
    @property
    def active(self):
        if self.brain_type & BrainType.Simple:
            if self.label is not None:
                return self.label.name
        elif self._active is not None:
            return self._active.active
        return "idle"

    ### Brains are never Done
    # @property
    # def done(self):
    #     #return self._done
    #     return False
    
    # @done.setter
    # def done(self, _done):
    #     self._done = _done
    
    @property
    def result(self):
        return self._result
    
    @result.setter
    def result(self, res):
        if self.brain_type & BrainType.AlwayFail:
            res = PollResults.BT_FAIL
        elif self.brain_type & BrainType.AlwaySuccess:
            res = PollResults.BT_SUCCESS
        elif self.brain_type & BrainType.Invert:
            if res == PollResults.BT_FAIL:
                res  = PollResults.BT_SUCCESS
            elif res == PollResults.BT_SUCCESS:
                res  = PollResults.BT_FAIL

        self._result = res

    def run(self):
        match self.brain_type&0xFF00:
            case BrainType.Simple:
                self.run_simple()
            case BrainType.Sequence:
                self.run_sequence()
            case BrainType.Select:
                self.run_select()

    def run_select(self):
        # Select runs until a success
        # Otherwise it fails
        self._active = None
        self.result =  PollResults.BT_FAIL
        for child in self.children:
            child.result = PollResults.OK_IDLE
        for child in self.children:
            child.run()
            if child.result == PollResults.BT_SUCCESS:
                self.result =  PollResults.BT_SUCCESS
                self._active = child
                set_inventory_value(self.agent, "brain_active", child.active)
                return
        self.result =  PollResults.BT_FAIL

    def run_sequence(self):
        # Sequence needs all to succeed
        # Otherwise it fails
        for child in self.children:
            child.result = PollResults.OK_IDLE
        for child in self.children:
            child.run()
            if child.result == PollResults.BT_FAIL:
                self.result =  PollResults.BT_FAIL
                return
        
        self.result =  PollResults.BT_SUCCESS



    def run_simple(self):
        # Convert label string to label object
        if isinstance(self.label, str):
            task = get_inventory_value(self.client_id, "GUI_TASK", FrameContext.task)    
            self.label = task.main.mast.labels.get(self.label, None)
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


    def run_sub_label(self, loc):
        task = get_inventory_value(self.client_id, "GUI_TASK", FrameContext.task)
        t : MastAsyncTask
        t = task.start_task(self.label, self.data, defer=True, inherit=False)
        t.jump(self.label, loc)
        t.set_variable("BRAIN", self)
        #t.set_variable("BRAIN_ID", self.id)
        t.set_variable("BRAIN_AGENT", to_object(self.agent))
        t.set_variable("BRAIN_AGENT_ID", self.agent)
        t.tick_in_context()
        return t.tick_result
        


            

def brain_clear(agent_id_or_set):
    agent_id_or_set = to_set(agent_id_or_set)
    for agent in agent_id_or_set:
        set_inventory_value(agent, "__BRAIN__", None)
        

def brain_add_parent(parent, agent, label, data=None, client_id=0):
    if isinstance(label, str):
        label = label.strip()

    if isinstance(label, str):
        task = FrameContext.task
        l = label
        label = task.main.mast.labels.get(label, None)
        if label is None:
            print(f"Ignoring objective configured with invalid label {l}")
            return
        
        child = Brain(agent, label, data, client_id, BrainType.Simple)
        parent.add_child(child)
        return
        
    if isinstance(label, MastNode):
        child = Brain(agent, label, data, client_id, BrainType.Simple)
        parent.add_child(child)
        return
        
        
    if isinstance(label, list):
        for l in label:
            brain_add_parent(parent, agent, l, None)

    if isinstance(label, dict):
        seq = label.get("SEQ")
        sel = label.get("SEL")

        data = label.get("data")
        # Car
        the_label = label.get("label")
        
        if the_label is not None:
            brain_add_parent(parent, agent, the_label, data, client_id)
        elif sel is not None:
            child = Brain(agent, None, None, client_id, BrainType.Select)
            parent.add_child(child)
            brain_add_parent(child, agent, sel, None, client_id)
        elif seq is not None:
            child = Brain(agent, None, None, client_id, BrainType.Sequence)
            parent.add_child(child)
            brain_add_parent(child, agent, seq, None, client_id)


def brain_add(agent_id_or_set, label, data=None, client_id=0, parent=None):
    brain_schedule()
    agent_id_or_set = to_set(agent_id_or_set)
    for agent in agent_id_or_set:
        if parent is None:
            parent = get_inventory_value(agent, "__BRAIN__", None)
            if parent is None:
                # Default brain is Select
                parent = Brain(agent, None, None, client_id, BrainType.Select)
                set_inventory_value(agent, "__BRAIN__", parent)
        brain_add_parent(parent, agent, label, data, client_id)


__brains_is_running = False
def brains_run_all(tick_task):
    global __brains_is_running
    if __brains_is_running:
        return
    __brains_is_running = True

    all = has_inventory("__BRAIN__")
    for agent in all:
        try:
            agent_root = get_inventory_value(agent, "__BRAIN__")
            # Verify the agent is valid
            agent_obj = Agent.get(agent)
            if agent_obj is None:
                continue
            agent_root.run()
        
        except Exception as e:
            msg = e
            print(f"Exception in brain processing {msg}")
    __brains_is_running = False
    

