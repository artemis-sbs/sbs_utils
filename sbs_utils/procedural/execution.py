from ..helpers import FrameContext
import logging as logging
from ..agent import Agent
from io import StringIO
from ..pymast.pollresults import PollResults

def jump(label):
    task = FrameContext.task

    if task is not None:
        return task.jump(label)
    return None


def log(message, name=None, level=None):
    _logger = logging.getLogger()
    if isinstance(name, str):
        _logger = logging.getLogger(name)
    

    task = FrameContext.task
    if task is not None:
        message = task.compile_and_format_string(message)

    if level is None:
        level = logging.DEBUG
    elif isinstance(level, str):
        level = level.upper()
        level = logging.getLevelName(level)
    _logger.log(level, message)

def logger(name=None, file=None, var=None):
    _logger = logging.getLogger(name)
    logging.basicConfig(level=logging.DEBUG)
    _logger.setLevel(logging.DEBUG)

    if var is not None:
        streamer = StringIO()
        handler = logging.StreamHandler(stream=streamer)
        handler.setFormatter(logging.Formatter("%(message)s"))
        handler.setLevel(logging.DEBUG)
        _logger.addHandler(handler)
        #mast.vars[node.var] = streamer
        Agent.SHARED.set_inventory_value(var, streamer)

    task = FrameContext.task
    if file is not None and task is not None:
        file = task.format_string(file)
        handler = logging.FileHandler(file,mode='w')
        handler.setFormatter(logging.Formatter("%(message)s"))
        handler.setLevel(logging.NOTSET)
        _logger.addHandler(handler)


def task_schedule(label, data=None, var=None):
    task = FrameContext.task

    if task is not None:
        return task.start_task(label, data, var)
    return None


def task_cancel(task):
    if FrameContext.task is None:
        return
    FrameContext.task.main.cancel_task(task)


def watch_all(tasks):
    done = False
    tasks = set(tasks)
    while not done:
        finished = set()
        for t in tasks:
            if t.done:
                finished.add(t)
        else:
            done = True
        tasks = tasks - finished
        yield PollResults.OK_RUN_AGAIN
    yield PollResults.OK_END

def watch_any(tasks):
    done = False
    while not done:
        for t in tasks:
            if t.done:
                done = True
                break
        else:
            done = True
        yield PollResults.OK_RUN_AGAIN
    yield PollResults.OK_END

#
# Args are labels or task
#
# Doesn't return until all success, or any fail
#
def task_all(*args, **kwargs):
    if FrameContext.task is None:
        return
    data = kwargs.get("data", None)
    tasks = []
    for label in args:
        t = FrameContext.task.start_task(label, data)
        tasks.append(t)
    return watch_all(tasks)



#
# Args are labels or task
#
# Doesn't return until any success, or all fail
#
def task_all(*args, **kwargs):
    pass

