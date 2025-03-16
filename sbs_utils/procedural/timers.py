from .inventory import get_inventory_value, set_inventory_value
from ..helpers import FrameContext
from ..futures import Promise
from ..mast.pollresults import PollResults

TICK_PER_SECONDS = 30
def set_timer(id_or_obj, name, seconds=0, minutes =0):
    """set up a timer

    Args:
        id_or_obj (agent): The agent to set the timer for
        name (str): The name of the timer
        seconds (int, optional): The number of seconds. Defaults to 0.
        minutes (int, optional): The number of minutes. Defaults to 0.
    """    
    seconds += minutes*60
    seconds *= TICK_PER_SECONDS
    seconds += FrameContext.context.sim.time_tick_counter
    set_inventory_value(id_or_obj, f"__timer__{name}", seconds)

def is_timer_set(id_or_obj, name):
    """check to see if a timer is running

    Args:
        id_or_obj (agent): The id or object of the agent that has the timer
        name (str): Timer name

    Returns:
        bool: True if a timer exists
    """    
    return get_inventory_value(id_or_obj, f"__timer__{name}", None) is not None


def is_timer_finished(id_or_obj, name):
    """check to see if a timer is finished

    Note: 
        if the timer is not set. this function returns true.

    Args:
        id_or_obj (agent): The id or object of the agent that has the timer
        name (str): Timer name

    Returns:
        bool: True if a timer finished
    """    
    target = get_inventory_value(id_or_obj, f"__timer__{name}")
    if target is None or target == 0:
        return True
    now = FrameContext.context.sim.time_tick_counter
    if now > target:
        return True
    return False

def format_time_remaining(id_or_obj, name):
    """Get the remaining time on a timer and return a formatted string

    Args:
        id_or_obj (agent): The agent id or object
        name (str): The timer name

    Returns:
        str: A formatted string with the minutes and seconds left on the timer
    """    
    time = get_time_remaining(id_or_obj, name)
    if time is None:
        return ""
    if time <=0:
        return ""
    minutes = time // 60
    seconds = str(time % 60).zfill(2)
    return f"{minutes}:{seconds}"
    

def get_time_remaining(id_or_obj, name):
    """The number of seconds remaining for a timer

    Args:
        id_or_obj (agent): The agent id or object
        name (str): The timer name

    Returns:
        int: The number of seconds remaining
    """    
    target = get_inventory_value(id_or_obj, f"__timer__{name}")
    if target is None or target == 0:
        return 0
    now = FrameContext.context.sim.time_tick_counter
    return (target - now) // TICK_PER_SECONDS
    


def is_timer_set_and_finished(id_or_obj, name):
    """check to see if a timer was set and is finished

    Args:
        id_or_obj (agent): The id or object of the agent that has the timer
        name (str): Timer name

    Returns:
        bool: True if a timer finished and was set
    """    

    target = get_inventory_value(id_or_obj, f"__timer__{name}")
    if target is None or target == 0:
        return False
    now = FrameContext.context.sim.time_tick_counter
    if now > target:
        return True
    return False


def clear_timer(id_or_obj, name):
    """deactivated a timer

    Args:
        id_or_obj (agent): The id or object of the agent that has the timer
        name (str): Timer name
    """    

    set_inventory_value(id_or_obj, f"__timer__{name}", None)

def start_counter(id_or_obj, name):
    """starts counting seconds

    Args:
        id_or_obj (agent): The agent to set the timer for
        name (str): The name of the timer
    """    

    set_inventory_value(id_or_obj, f"__counter__{name}", FrameContext.context.sim.time_tick_counter)

def get_counter_elapsed_seconds(id_or_obj, name, default_value= None):
    """returns the number of seconds since the counter started

    Args:
        id_or_obj (agent): The agent id or object 
        name (str): The counter name

    Returns:
        int: The number of seconds since the counter started
    """    
    start = get_inventory_value(id_or_obj, f"__counter__{name}")
    now =  FrameContext.context.sim.time_tick_counter
    if start is None:
        return default_value
    return int((now-start) / TICK_PER_SECONDS)
    

def clear_counter(id_or_obj, name):
    """removes a counter
    Args:
        id_or_obj (agent): The agent id or object
        name (str): The name of the counter
    """    
    set_inventory_value(id_or_obj, f"__counter__{name}", None)


class Delay(Promise):
    def __init__(self,  seconds, minutes, sim) -> None:
        super().__init__()

        self.is_sim = sim
        self.seconds = seconds
        self.minutes = minutes
        self.rewind()

    def rewind(self):
        # this enables the standard delay to work with behavior tree
        if self.is_sim:
            self.timeout = FrameContext.sim_seconds + (self.minutes*60+self.seconds) 
        else:
            self.timeout = FrameContext.app_seconds + (self.minutes*60+self.seconds)
        self.set_result(None)

    def done(self):
        #
        # Tiny hack to just do the work in done
        #
        if self.is_sim: 
            if self.timeout < FrameContext.sim_seconds:
                self.set_result(PollResults.BT_SUCCESS)
        else:
            if self.timeout < FrameContext.app_seconds:
                self.set_result(PollResults.BT_SUCCESS)
        return super().done()
    
    def poll(self):
        if self.done():
            return None
        return PollResults.OK_RUN_AGAIN
    
def delay_sim(seconds=0, minutes=0):
    """creates a Promise that waits for the specified time to elapse
    this is in simulation time (i.e. it could get paused)

    Args:
        seconds (int, optional): The number of seconds. Defaults to 0.
        minutes (int, optional): The number of minutes. Defaults to 0.

    Returns:
        Promise: A promise that is done when time has elapsed
    """    
    return Delay(seconds, minutes, True)

def delay_app(seconds=0, minutes=0):
    """creates a Promise that waits for the specified time to elapse
    this is in app time (i.e. it could NOT get paused)

    Args:
        seconds (int, optional): The number of seconds. Defaults to 0.
        minutes (int, optional): The number of minutes. Defaults to 0.

    Returns:
        Promise: A promise that is done when time has elapsed
    """
    return Delay(seconds, minutes, False)

def timeout(seconds=0, minutes=0):
    """creates a Promise that waits for the specified time to elapse
    this is in simulation time (i.e. it could NOT get paused)

    Args:
        seconds (int, optional): The number of seconds. Defaults to 0.
        minutes (int, optional): The number of minutes. Defaults to 0.

    Returns:
        Promise: A promise that is done when time has elapsed
    """    
    return Delay(seconds, minutes, False)

def timeout_sim(seconds=0, minutes=0):
    """creates a Promise that waits for the specified time to elapse
    this is in simulation time (i.e. it could get paused)

    Args:
        seconds (int, optional): The number of seconds. Defaults to 0.
        minutes (int, optional): The number of minutes. Defaults to 0.

    Returns:
        Promise: A promise that is done when time has elapsed
    """    
    return Delay(seconds, minutes, True)



class DelayForTests(Promise):
    def __init__(self,  seconds, minutes) -> None:
        super().__init__()
        self.count = seconds+minutes*60 
        self.count *= 20 # Poll calls done and poll is called a bunch 
        # caused hangs if the delay was too short
        
    def done(self):
        #
        # Tiny hack to just do the work in done
        #
        self.count -= 1
        if self.count <=0:
            self.set_result(True)
        return super().done()
    
    def poll(self):
        if self.done():
            return PollResults.OK_ADVANCE_TRUE
        return PollResults.OK_RUN_AGAIN
    
    
def delay_test(seconds=0, minutes=0):
    """creates a Promise that waits for the specified time to elapse
    this is for unit testing and not realtime

    Args:
        seconds (int, optional): The number of seconds. Defaults to 0.
        minutes (int, optional): The number of minutes. Defaults to 0.

    Returns:
        Promise: A promise that is done when time has elapsed
    """    
    return DelayForTests(seconds, minutes)