from .execution import task_schedule, AWAIT, sub_task_schedule
from ..helpers import FrameContext
from ..mast.pollresults import PollResults


def mission_runner(label=None, data=None):
    """Runs a mission this runs the same task multiple times

    Args:
        label (_type_): a Mission Label
        data (_type_, optional): _Data to pass to the mission task. Defaults to None.

    Yields:
        PollResults: Sucess or Failure
    """
    if label is None:
        task = FrameContext.task
        label = task.get_variable("label")
        data = task.get_variable("data")

    # Run the label itself just in case
    abort_cmds = label.cmd_map.get("abort", [])
    init_cmds = label.cmd_map.get("init", [])
    start_cmds = label.cmd_map.get("start", [])
    objectives = label.cmd_map.get("objective", [])
    complete_cmd = label.cmd_map.get("complete", [])

    # run the label, gets any onchange etc.
    # it should skip the cmd block
    task = sub_task_schedule(label, data)
    res = task.result()
    while res == PollResults.OK_RUN_AGAIN:
        res = AWAIT(task)
        yield res
    
    

    for cmd in init_cmds:
        task.jump_restart_task(label, cmd.loc+1)
        res = task.result()
        while res == PollResults.OK_RUN_AGAIN:
            res = AWAIT(task)
            yield res
        if res != PollResults.OK_SUCCESS:
            yield PollResults.OK_END

    # wait for the start     
    # Keep running until start, set else where
    while True:
        start = task.get_variable("__START__")
        if start:
            break
        yield PollResults.OK_RUN_AGAIN

    # Run the start command block
    for cmd in start_cmds:
        task.jump_restart_task(label, cmd.loc+1)
        res = task.result()
        while res == PollResults.OK_RUN_AGAIN:
            res = AWAIT(task)
            yield res
        if res != PollResults.OK_SUCCESS:
            yield PollResults.OK_END

    # Continue to loop until failure or completion

    done = False
    while not done:
        # Success of an abort is end task
        for cmd in abort_cmds:
            task.jump_restart_task(label, cmd.loc+1)
            while True:
                res = task.result()
                if res == PollResults.FAIL_END:
                    yield PollResults.OK_END
                    #
                    # Emit mission aborted
                    #
                    return
                elif res != PollResults.OK_RUN_AGAIN:
                    break 
                yield res
                task.poll()
                
            

        # Fail or success is OK
        # success means it is currently completed
        for cmd in objectives:
            task.jump_restart_task(label, cmd.loc+1)
            while True:
                res = task.result()
                if res == PollResults.OK_SUCCESS:
                    yield PollResults.OK_END
                    #
                    # Emit objective achieved
                    #
                    return
                elif res != PollResults.OK_RUN_AGAIN:
                    break 
                yield res
                task.poll()

        done = True
        # If any fail, we're not done
        for cmd in complete_cmd:
            task.jump_restart_task(label, cmd.loc+1)
            while True:
                res = task.result()
                if res == PollResults.OK_SUCCESS:
                    yield PollResults.OK_END
                    #
                    # Emit mission aborted
                    #
                    return
                elif res != PollResults.OK_SUCCESS:
                    done = False
                if res != PollResults.OK_RUN_AGAIN:
                    break 
                yield res
                task.poll()
            


def mission_find(agent_id):
    pass


def mission_run(label, data= None):
    return task_schedule(mission_runner, {"label": label, "data": data})
