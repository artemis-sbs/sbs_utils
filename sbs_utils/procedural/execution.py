from ..helpers import FrameContext
import logging as logging
from ..agent import Agent
from io import StringIO
from ..futures import Promise, PromiseAllAny, PromiseWaiter
from ..mast.pollresults import PollResults

def jump(label):
    """reset the program flow to a label

    Args:
        label (str or label): The label to jump to

    Returns:
        PollResults: The poll results of the jump. used by the task.
    """    
    task = FrameContext.task

    if task is not None:
        return task.jump(label)
    return PollResults.OK_JUMP

def END():
    """ End the current task
    Returns:
        PollResults: The poll results of the jump. used by the task.
    """    
    task = FrameContext.task

    if task is not None:
        return task.end()
    return PollResults.OK_END


def log(message, name=None, level=None):
    """ generate a log message

    Args:
        message (str): The message to log
        name (str, optional): Name of the logger to log to. Defaults to None.
        level (str, optional): The logging level to use. Defaults to None.
    """    
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
    """create or retreive a looger

    Args:
        name (str, optional): The name of the logger. Defaults to None.
        file (str, optional): The file to log to. Defaults to None.
        var (str, optional): The name of a string variable to log to. Defaults to None.
    """    
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
    """create an new task and start running at the specified label

    Args:
        label (str or label): The label to run
        data (duct, optional): Data to initialie task variables. Defaults to None.
        var (str, optional): Set the variable to the task created. Defaults to None.

    Returns:
        MastAsyncTask : The MAST task created
    """    
    task = FrameContext.task
    page = FrameContext.page
    print(f"Task Before: {task} {page}")
    if task is not None:
        t = task.start_task(label, data, var)
        #print(f"Task After: {FrameContext.task}")
        return t
    return None


def task_cancel(task):
    """ends the specified task

    Args:
        task (MastAsyncTAsk): The task to end
    """    
    if FrameContext.task is None:
        FrameContext.task.main.cancel_task(task)



#
# Args are labels or task
#
# Doesn't return until all success, or any fail
#
def task_all(*args, **kwargs):
    """Creates a task for each argument that is a label. Also supports a data named argument to pass the data to all the tasks.

    Args:
        args (0..n labels): the labels to schedule.
        data (dict): keyword arg to pass data to the tasks.
    Returns:
        Promise: A promise that is finished when all tasks are completed.
    """    
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
    """Creates a task for each argument that is a label. Also supports a data named argument to pass the data to all the tasks.

    Args:
        args (0..n labels): the labels to schedule.
        data (dict): keyword arg to pass data to the tasks.
    Returns:
        Promise: A promise that is finished when any of the tasks completes.
    """    
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
    """set the value of a variable at task scope. Or returns the passed default if it doesn't exist.

    Args:
        key (str): the variable name
        value (any): The value to set the variable to
    """    
 
    if FrameContext.task is None:
        return
    FrameContext.task.set_variable(key,value)

def get_variable(key, default=None):
    """get the value of a variable at task scope. Or returns the passed default if it doesn't exist.

    Args:
        key (str): the variable name
        default (optional): What to return if the variable doesn't exist. Defaults to None.

    Returns:
        any: The value of the variable, or default value
    """    
    if FrameContext.task is None:
        return None
    return FrameContext.task.get_variable(key,default)


def get_shared_variable(key, default=None):
    """get the value of a variable at shared scope. Or returns the passed default if it doesn't exist.

    Args:
        key (str): the variable name
        default (optional): What to return if the variable doesn't exist. Defaults to None.

    Returns:
        any: The value of the variable, or default value
    """    
    return Agent.SHARED.get_inventory_value(key, default)
    

def set_shared_variable(key, value):
    """set the value of a variable at shared scope. Or returns the passed default if it doesn't exist.

    Args:
        key (str): the variable name
        value (any): The value to set the variable to
    """    
    Agent.SHARED.set_inventory_value(key, value)



def AWAIT(promise: Promise):
    """ Creates a entity to wait (non-blocking) for a promise to complete

    Args:
        Promise: A promise 
    """    
    return PromiseWaiter(promise)
    
