from ..helpers import FrameContext
import logging as logging
from ..agent import Agent
from io import StringIO
from ..futures import Promise, PromiseAllAny, PromiseWaiter
from ..mast.pollresults import PollResults

def jump(label):
    task = FrameContext.task

    if task is not None:
        return task.jump(label)
    return PollResults.OK_JUMP

def END():
    task = FrameContext.task

    if task is not None:
        return task.end()
    return PollResults.OK_END


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
        FrameContext.task.main.cancel_task(task)



#
# Args are labels or task
#
# Doesn't return until all success, or any fail
#
def task_all(*args, **kwargs):
    if FrameContext.task is None:
        return
    data = None
    if kwargs is not None:
        data = kwargs.get("data", None)
    tasks = []
    for label in args:
        t = FrameContext.task.start_task(label, data)
        tasks.append(t)
    return PromiseAllAny(tasks, True)




#
# Args are labels or task
#
# Doesn't return until any success, or all fail
#
def task_any(*args, **kwargs):
    if FrameContext.task is None:
        return
    data = None
    if kwargs is not None:
        data = kwargs.get("data", None)
    tasks = []
    for label in args:
        t = FrameContext.task.start_task(label, data)
        tasks.append(t)
    return PromiseAllAny(tasks, False)



def set_variable(key, value):
    if FrameContext.task is None:
        return
    FrameContext.task.set_variable(key,value)

def get_variable(key, default=None):
    if FrameContext.task is None:
        return None
    return FrameContext.task.get_variable(key,default)


def get_shared_variable(self, key, default=None):
    if FrameContext.task is None:
        return None
    return FrameContext.task.get_shared_variable(key,default)

def set_shared_variable(self, key, value):
    if FrameContext.task is None:
        return None
    return FrameContext.task.set_shared_variable(key,value)



def AWAIT(promise: Promise):
    return PromiseWaiter(promise)
    
