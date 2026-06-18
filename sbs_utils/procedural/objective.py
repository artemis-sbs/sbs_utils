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
    """Ensure the background tick task that drives objectives is running."""
    global __objective_tick_task
    if __objective_tick_task is None:
        __objective_tick_task = TickDispatcher.do_interval(objectives_run_everything, 1)
        __objective_tick_task.state = 0

from .brain import brains_run_all
from .extra_scan_sources import extra_scan_sources_run_all
import time




__end_game_promise = []
__end_game_ids = 100
def game_end_condition_add(promise, message, is_win, music=None, signal=None) -> int:
    """Register a promise that ends the game when it resolves.

    Args:
        promise (Promise): Resolving this promise triggers the end condition.
        message (str): Message displayed on the results screen.
        is_win (bool): ``True`` for a victory, ``False`` for a defeat.
        music (str, optional): Music file to play at end. Defaults to None
            (uses the default victory/failure track).
        signal (str, optional): Signal to emit instead of
            ``"show_game_results"``. Defaults to None.

    Returns:
        int: Handle ID that can be passed to ``game_end_condition_remove``.
    """
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
    """Remove a registered game end condition.

    Args:
        id (int): Handle returned by ``game_end_condition_add``.
    """
    global __end_game_promise
    new_cond = [cond for cond in __end_game_promise if cond[0]!=id]
    __end_game_promise = new_cond


def game_end_run_all(tt):
    """Poll all registered game end conditions and trigger the end screen if any resolve.

    Args:
        tt (Task): Tick task (unused).
    """
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

from .modifiers import ModifierHandler
def objectives_run_everything(tick_task):
    """Run one slice of the per-tick work: objectives, brains, scan sources, or game-end checks.

    Work is spread across three alternating states to avoid all processing
    happening in the same tick. ``tick_task.state`` selects which slice runs.

    Args:
        tick_task (Task): The repeating tick task — ``state`` is read and
            updated each call.
    """
    state = tick_task.state % 3
    tick_task.state += 1
    #t = time.perf_counter()
    if state == 0:
        objectives_run_all(tick_task)
        ModifierHandler.remove_expired_modifiers()
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
        """
        Create an Objective.
        Args:
            agent (Agent | int): The agent or id for this objective
            label (str | Label): The objective label to run
            data (dict): Data to associate with this objective. May not be used.
            client_id (int): The client ID for this objective. May not be used.
        """
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
    def done(self) -> bool:
        """
        Is the objective completed?
        Returns:
            bool: True if the objective is complete.
        """
        return self._done
    
    @property
    def result(self) -> PollResults:
        """
        Get the result of the objective.
        Returns:
            PollResults: The result.
        """
        return self._result
    
    @result.setter
    def result(self, res):
        """
        Set the result of the objective. If the objective is done, then does nothing (to prevent overwriting the result of a completed objective).
        If the result is not `PollResults.OK_IDLE`, then sets the value of the objective's `done` field to True.
        """
        # Don't overwrite when done
        if self._done:
            return
        self._result = res
        self._done = self._result != PollResults.OK_IDLE
        if self._done:
            self.force_clear()

    def force_clear(self):
        """
        Clear this objective from its agent and undesignates it as an objective.
        """
        self.remove_role("OBJECTIVE")
        unlink(self.agent, "OBJECTIVE", self.id)
        self.remove_role("OBJECTIVE_RUN")
        unlink(self.agent, "OBJECTIVE_RUN", self.id)



    def run(self):
        """
        Run the objective label.
        """
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
        """
        Stop the label run with a result.
        Args:
            result (PollResults): The result of the objective label.
        """
        leave = self.label.labels.get("leave", None)
        self.result = result
        if leave is not None:
            self.run_sub_label(leave.loc+1)
        self.force_clear()

    def run_sub_label(self, loc):
        """
        Run the sublabel with the specified index.
        Args:
            loc (int): The index of the sublabel.
        Returns:
            PollResults: The result of the sublabel task.
        """
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
        res = t.tick_result
        if res == PollResults.OK_IDLE:
            t.end()
        elif res != PollResults.OK_SUCCESS and res != PollResults.FAIL_END:
            print(f"Objective did not complete properly")

        return res

def objective_clear(agent_id_or_set):
    """Remove all active objectives from one or more agents.

    Args:
        agent_id_or_set (Agent | int | set[Agent | int]): Agent(s) whose
            objectives should be cleared.
    """
    agent_id_or_set = to_set(agent_id_or_set)
    for agent in agent_id_or_set:
        for obj in to_object_list(linked_to(agent, "OBJECTIVE")):
            if obj is not None:
                obj.stop_and_leave()
                obj.force_clear()

        

def objective_add(agent_id_or_set, label, data=None, client_id=0):
    """Add an objective label to one or more agents.

    ``label`` may be a label name, a Label object, a dict with ``"label"`` and
    ``"data"`` keys, or a list of any of these. One ``Objective`` is created
    per (agent, label) pair.

    Args:
        agent_id_or_set (Agent | int | set[Agent | int]): Agent(s) to attach
            the objective to.
        label (str | Label | dict | list): The objective label(s) to run.
        data (dict, optional): Variables passed into the objective label.
            Defaults to None.
        client_id (int, optional): Console client ID (reserved for future use).
            Defaults to 0.

    Returns:
        Objective | list[Objective]: A single Objective when exactly one is
            created, otherwise a list.
    """
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
    """Poll every active ``OBJECTIVE_RUN`` objective, removing any whose agent no longer exists.

    Args:
        tick_task (Task): Tick task (unused).
    """
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


from .execution import sub_task_schedule
from ..futures import awaitable
from ..helpers import FrameContext

@awaitable
def objective_extends(label, data=None):
    """Run an objective label as a sub-task of the current task.

    Args:
        label (str | Label): The label to execute.
        data (dict, optional): Variables to pass into the sub-task. Defaults to
            None.

    Returns:
        MastAsyncTask: The scheduled sub-task.
    """
    prefab = FrameContext.task
    if data is None:
        data = {}
# Need to set the self and prefab properly
    data["self"] = prefab
    data["prefab"] = prefab
    t = sub_task_schedule(label, data=data)
    t.tick_in_context()
    return t




