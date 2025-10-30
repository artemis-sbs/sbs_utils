from sbs_utils.helpers import FrameContext
from sbs_utils.mast.pollresults import PollResults
from sbs_utils.futures import Promise
def awaitable (func):
    ...
def clear_counter (id_or_obj, name):
    """Removes a counter.
    Args:
        id_or_obj (Agent | int): The agent id or object.
        name (str): The name of the counter."""
def clear_timer (id_or_obj, name):
    """Deactivate a timer.
    
    Args:
        id_or_obj (Agent | int): The id or object of the agent that has the timer.
        name (str): Timer name."""
def delay_app (*args, **kwargs):
    ...
def delay_sim (*args, **kwargs):
    ...
def delay_test (*args, **kwargs):
    ...
def format_time_remaining (id_or_obj, name):
    """Get the remaining time on a timer and return a formatted string.
    
    Args:
        id_or_obj (Agent | int): The agent id or object.
        name (str): The timer name.
    
    Returns:
        str: A formatted string with the minutes and seconds left on the timer."""
def get_counter_elapsed_seconds (id_or_obj, name, default_value=None):
    """Returns the number of seconds since the counter started.
    
    Args:
        id_or_obj (Agent | int): The agent id or object.
        name (str): The counter name.
    
    Returns:
        int: The number of seconds since the counter started."""
def get_inventory_value (id_or_object, key: str, default=None):
    """get inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
    
    Args:
        id_or_obj (Agent | int): The agent id or object to check
        key (str): The key/name of the inventory item
        default (any): the default value data
    Returns:
        any: The inventory value associated with the provided key, or the default value if it doesn't exist."""
def get_time_remaining (id_or_obj, name):
    """The number of seconds remaining for a timer.
    
    Args:
        id_or_obj (agent): The agent id or object.
        name (str): The timer name.
    
    Returns:
        int: The number of seconds remaining."""
def is_timer_finished (id_or_obj, name):
    """Check to see if a timer is finished.
    
    Note:
        * If the timer is not set, this function returns true.
    
    Args:
        id_or_obj (Agent | int): The id or object of the agent that has the timer.
        name (str): Timer name
    
    Returns:
        bool: True if a timer finished, or if it is not set."""
def is_timer_set (id_or_obj, name):
    """Check to see if a timer is running.
    
    Args:
        id_or_obj (Agent | int): The id or object of the agent that has the timer
        name (str): Timer name
    
    Returns:
        bool: True if a timer exists"""
def is_timer_set_and_finished (id_or_obj, name):
    """Check to see if a timer was set and is finished.
    
    Args:
        id_or_obj (Agent | int): The id or object of the agent that has the timer.
        name (str): Timer name.
    
    Returns:
        bool: True if a timer finished and was set."""
def set_inventory_value (so, key: str, value):
    """Set inventory value with the given key the the agent has.
    This is the way to create a collection in inventory.
    `so` can be a set. If it is, the inventory value is set for each member in the set.
    
    Args:
        id_or_obj (Agent | int | set[Agent | int]): The agent id or object or set to check
        key (str): The key/name of the inventory item
        value (any): the value"""
def set_timer (id_or_obj, name, seconds=0, minutes=0):
    """Set up a timer
    
    Args:
        id_or_obj (Agent | int): The agent to set the timer for
        name (str): The name of the timer
        seconds (int, optional): The number of seconds. Defaults to 0.
        minutes (int, optional): The number of minutes. Defaults to 0."""
def start_counter (id_or_obj, name):
    """Starts counting seconds.
    
    Args:
        id_or_obj (Agent | int): The agent for which to set the timer.
        name (str): The name of the counter."""
def timeout (*args, **kwargs):
    ...
def timeout_sim (*args, **kwargs):
    ...
class Delay(Promise):
    """class Delay"""
    def __init__ (self, seconds, minutes, sim) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def done (self):
        ...
    def poll (self):
        ...
    def rewind (self):
        ...
class DelayForTests(Promise):
    """class DelayForTests"""
    def __init__ (self, seconds, minutes) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def done (self):
        ...
    def poll (self):
        ...
