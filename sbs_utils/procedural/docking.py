import sbs
from sbs_utils.procedural.query import to_id, to_set, to_object
from sbs_utils.procedural.roles import role
from sbs_utils.procedural.inventory import set_inventory_value
from sbs_utils.procedural.space_objects import closest
from sbs_utils.tickdispatcher import TickDispatcher, TickTask
from sbs_utils.mast.pollresults import PollResults
from sbs_utils.procedural.signal import signal_emit
from sbs_utils.helpers import FrameContext
from sbs_utils.agent import Agent

class _DockingBrain:
    def __init__(self, label, data):
        self.label = label
        self.data = data

__docking_pairs = {}
def docking_set_docking_logic(player_set, npc_set, label, data=None):
    docking_schedule()
    player_ids = to_set(player_set)
    npc_ids = to_set(npc_set)
    for player_id in player_ids:
        for npc_id in npc_ids:
            docks = __docking_pairs.get(player_id, {})
            docks[npc_id] = _DockingBrain(label, data)
            __docking_pairs[player_id] = docks
            

__docking_tick_task = None
def docking_schedule():
    #
    # Schedule a simple tick task 
    #
    global __docking_tick_task
    if __docking_tick_task is None:
        __docking_tick_task = TickDispatcher.do_interval(docking_run_all, 1)


__docking_is_running = False
def docking_run_all(tick_task):
    global __docking_is_running
    if __docking_is_running:
        return
    __docking_is_running = True

    undocking_id = None
    if not isinstance(tick_task, TickTask):
        if tick_task.sub_tag == "undocked":
            undocking_id = tick_task.origin_id 



    try:
        # Don't care about the key here
        docking_pairs_remove = []
        for player_id in __docking_pairs:
            player = Agent.get(player_id)

            # Verify the player is valid
            if player is None:
                docking_pairs_remove.append(player_id)
                continue
            pairs = __docking_pairs.get(player_id, None)
            if pairs is None:
                docking_pairs_remove.append(player_id)
                continue
            
            # anything left to dock with
            if len(pairs) ==0:
                docking_pairs_remove.append(player_id)
                continue
            

            dock_state_string = player.data_set.get("dock_state", 0)
            if undocking_id == player_id:
                brain = pairs.get(tick_task.selected_id)
                npc = to_object(tick_task.selected_id)
                if brain is not None and npc is not None:
                    _docking_handle_undocking(player, npc, brain)

            if "undocked" == dock_state_string:
                _docking_handle_undocked(player_id, player, pairs)
                # Let any state change be processed next go
                continue
            #
            # 
            #
            set_inventory_value(player_id, "dock_state", dock_state_string)

            
            npc_id = player.data_set.get("dock_base_id", 0)
            if npc_id==0:
                continue
            # check if NPC no longer supports docking
            if pairs.get(npc_id) is None:
                continue

            npc = to_object(npc_id)
            # if npc no longer exists continue
            if npc is None:
                pairs.pop(npc_id, None)
                continue
            #
            # Check if NPC is valid
            #
            brain = pairs.get(npc_id)
            if brain is None:
                pairs.pop(npc_id, None)
                continue

            if "docking" == dock_state_string:
                _docking_handle_docking(player, npc, brain)
                continue

            if "dock_start" == dock_state_string:
                _docking_handle_dock_start(player, npc, brain)
                continue


            if "docked" == dock_state_string:
                _docking_handle_docked(player, npc, brain)
                continue

            print(f"Invalid dock state {dock_state_string}")
        
        for id in docking_pairs_remove:
            __docking_pairs.pop(id)
    except Exception as e:
        msg = e
        print(f"Exception in objective processing {msg}")
        import sys, traceback
        error_type, error, tb = sys.exc_info()
        lines = traceback.extract_tb(tb)
        if len(lines)>0:
            filename, lineno, func_name, line = lines[-1]
            print(f"{msg}\n{error}\n{line}\nfunction: {func_name}\nline: {lineno}\nFile: {filename}")
        
    __docking_is_running = False

def _docking_run_task(player, npc, brain, inner_label):
    inline = brain.label.labels.get(inner_label)
    if inline is None:
        return PollResults.OK_SUCCESS
    task = FrameContext.task
    t = task.start_task(brain.label, brain.data, defer=True)
    t.jump(brain.label, inline.loc+1)
    t.set_variable("DOCKING_PLAYER", player)
    t.set_variable("DOCKING_PLAYER_ID", player.id)
    t.set_variable("DOCKING_NPC", npc)
    t.set_variable("DOCKING_NPC_ID", npc.id)
    t.tick_in_context()

    res = t.tick_result
    if res == PollResults.OK_IDLE:
        t.end()
    elif res != PollResults.OK_SUCCESS and res != PollResults.FAIL_END:
        print(f"Objective did not complete properly")

    return res




def _docking_handle_undocked(player_id, player, pairs):
    # Find the closest thing the player can dock with
    paired_ids = set(list(pairs.keys()))
    npc_id = to_id(closest(player_id, paired_ids, 2000))
    player.data_set.set("dock_base_id", 0)
    if npc_id==0:
        return
    # check if NPC no longer supports docking
    if pairs.get(npc_id) is None:
        return

    npc = to_object(npc_id)
    # if npc no longer exists continue
    if npc is None:
        pairs.pop(npc_id, None)
        return

    brain = pairs.get(npc_id)
    if brain is None:
        pairs.pop(npc_id, None)
        return 
    
    #
    # If label has a distance, try it
    test = brain.label.get_inventory_value("distance", 600)
    distanceValue = sbs.distance_id(player.id, npc.id)
    if distanceValue > test:
        return
    
    result = _docking_run_task(player, npc, brain, "enable")
    # If 
    if result == PollResults.FAIL_END:
        return
    #REFACTOR: This is where enable is tested
    player.data_set.set("dock_base_id", npc_id)
    #player.data_set.set("dock_state", "docking", 0)



def _docking_handle_docking(player, npc, brain):
    result = _docking_run_task(player, npc, brain, "docking")

    if result == PollResults.FAIL_END:
        # Reset
        player.data_set.set("dock_base_id", 0, 0)
        player.data_set.set("dock_state", "undocked", 0)

    distanceValue = sbs.distance_id(player.id, npc.id)

    closeEnough = npc.engine_object.exclusion_radius + player.engine_object.exclusion_radius
    closeEnough = closeEnough * 1.1
    if distanceValue <= closeEnough:
        player.data_set.set("dock_state", "dock_start",0)


def _docking_handle_undocking(player, npc, brain):
    result = _docking_run_task(player, npc, brain, "undocking")


    
    
def _docking_handle_dock_start(player, npc, brain):
    result = _docking_run_task(player, npc, brain, "docked")
    if result != PollResults.FAIL_END:
        player.data_set.set("dock_state", "docked", 0)
        player.data_set.set("playerThrottle", 0, 0)
        data = {}
        data["ORIGIN_ID"] = player.id
        data["SELECTED_ID"] = npc.id
        signal_emit("docked", data)
        return
    # Reset
    player.data_set.set("dock_base_id", 0, 0)
    player.data_set.set("dock_state", "undocked", 0)

def _docking_handle_docked(player, npc, brain):
    throttle = player.data_set.get("playerThrottle", 0)
    if throttle >0.6:
        result = _docking_run_task(player, npc, brain, "throttle")
        # Success means undock 2.8 behavior
        if result == PollResults.OK_SUCCESS:
            player.data_set.set("dock_base_id", 0, 0)
            player.data_set.set("dock_state", "undocked", 0)
            return

    result = _docking_run_task(player, npc, brain, "refit")
    if result != PollResults.FAIL_END:
        return
    # Reset
    player.data_set.set("dock_base_id", 0, 0)
    player.data_set.set("dock_state", "undocked", 0)

