from .inventory import get_inventory_value, set_inventory_value
from ..helpers import FrameContext
from ..futures import Promise, awaitable
from ..mast.pollresults import PollResults

TICK_PER_SECONDS = 30
def set_timer(id_or_obj, name, seconds=0, minutes=0):
    """Start a named countdown timer on an agent.

    Records the expiry tick in the agent's inventory. Use ``is_timer_finished``
    or ``get_time_remaining`` to check progress.

    Args:
        id_or_obj (Agent | int): The agent to set the timer on.
        name (str): Unique timer name for this agent.
        seconds (int, optional): Duration in seconds. Defaults to 0.
        minutes (int, optional): Additional duration in minutes. Defaults to 0.

    Example:
        set_timer(SHIP_ID, "repair", seconds=30)
        if is_timer_finished(SHIP_ID, "repair"):
            "Repairs complete!"
    """    
    seconds += minutes*60
    seconds *= TICK_PER_SECONDS
    seconds += FrameContext.context.sim.time_tick_counter
    set_inventory_value(id_or_obj, f"__timer__{name}", seconds)

def is_timer_set(id_or_obj, name):
    """Return whether a named timer exists on an agent.

    Args:
        id_or_obj (Agent | int): Agent ID or object.
        name (str): Timer name.

    Returns:
        bool: ``True`` if the timer has been set (even if already expired).

    Example:
        if not is_timer_set(SHIP_ID, "cooldown"):
            set_timer(SHIP_ID, "cooldown", seconds=10)
    """    
    return get_inventory_value(id_or_obj, f"__timer__{name}", None) is not None


def is_timer_finished(id_or_obj, name):
    """Return whether a timer has expired. Returns ``True`` if the timer is not set.

    Args:
        id_or_obj (Agent | int): Agent ID or object.
        name (str): Timer name.

    Returns:
        bool: ``True`` if the timer has expired or was never set.

    Example:
        if is_timer_finished(SHIP_ID, "repair"):
            "Repair bay ready."
    """    
    target = get_inventory_value(id_or_obj, f"__timer__{name}")
    if target is None or target == 0:
        return True
    now = FrameContext.context.sim.time_tick_counter
    if now > target:
        return True
    return False

def format_time_remaining(id_or_obj, name):
    """Return the time remaining on a timer as a ``M:SS`` string.

    Returns an empty string when the timer has expired or is not set.

    Args:
        id_or_obj (Agent | int): Agent ID or object.
        name (str): Timer name.

    Returns:
        str: Formatted remaining time, e.g. ``"1:30"``, or ``""`` if expired.

    Example:
        gui_text("Time: {format_time_remaining(SHIP_ID, 'mission')}")
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
    """Return the number of whole seconds remaining on a timer.

    Returns ``0`` when the timer has expired or is not set.

    Args:
        id_or_obj (Agent | int): Agent ID or object.
        name (str): Timer name.

    Returns:
        int: Seconds remaining, or ``0`` if expired or not set.

    Example:
        secs = get_time_remaining(SHIP_ID, "mission")
        if secs < 60:
            "Less than a minute remaining!"
    """    
    target = get_inventory_value(id_or_obj, f"__timer__{name}")
    if target is None or target == 0:
        return 0
    now = FrameContext.context.sim.time_tick_counter
    return (target - now) // TICK_PER_SECONDS
    


def is_timer_set_and_finished(id_or_obj, name):
    """Return whether a timer was explicitly set and has since expired.

    Unlike ``is_timer_finished``, returns ``False`` when the timer was never
    set. Use this to distinguish "timer done" from "timer never started".

    Args:
        id_or_obj (Agent | int): Agent ID or object.
        name (str): Timer name.

    Returns:
        bool: ``True`` only if the timer was set and has now expired.

    Example:
        if is_timer_set_and_finished(SHIP_ID, "cooldown"):
            clear_timer(SHIP_ID, "cooldown")
            "Weapons ready!"
    """    

    target = get_inventory_value(id_or_obj, f"__timer__{name}")
    if target is None or target == 0:
        return False
    now = FrameContext.context.sim.time_tick_counter
    if now > target:
        return True
    return False


def clear_timer(id_or_obj, name):
    """Clear a named timer so it is no longer set.

    After clearing, ``is_timer_set`` returns ``False`` and
    ``is_timer_finished`` returns ``True``.

    Args:
        id_or_obj (Agent | int): Agent ID or object.
        name (str): Timer name.

    Example:
        clear_timer(SHIP_ID, "cooldown")
    """    

    set_inventory_value(id_or_obj, f"__timer__{name}", None)

def start_counter(id_or_obj, name):
    """Record the current sim tick as the start of a named counter.

    Use ``get_counter_elapsed_seconds`` to read how many seconds have passed
    since the counter was started.

    Args:
        id_or_obj (Agent | int): Agent ID or object.
        name (str): Counter name.

    Example:
        start_counter(SHIP_ID, "docked")
        # later...
        secs = get_counter_elapsed_seconds(SHIP_ID, "docked")
    """    

    set_inventory_value(id_or_obj, f"__counter__{name}", FrameContext.context.sim.time_tick_counter)

def get_counter_elapsed_seconds(id_or_obj, name, default_value=None):
    """Return the number of seconds elapsed since a counter was started.

    Args:
        id_or_obj (Agent | int): Agent ID or object.
        name (str): Counter name.
        default_value (optional): Value returned if the counter was never
            started. Defaults to None.

    Returns:
        float | None: Seconds elapsed, or ``default_value`` if not set.

    Example:
        elapsed = get_counter_elapsed_seconds(SHIP_ID, "docked", 0)
        if elapsed > 60:
            "Docking complete."
    """    
    start = get_inventory_value(id_or_obj, f"__counter__{name}")
    now =  FrameContext.context.sim.time_tick_counter
    if start is None:
        return default_value
    return (now-start) / TICK_PER_SECONDS
    

def clear_counter(id_or_obj, name):
    """Remove a named counter from an agent.

    Args:
        id_or_obj (Agent | int): Agent ID or object.
        name (str): Counter name.

    Example:
        clear_counter(SHIP_ID, "docked")
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
    
@awaitable
def delay_sim(seconds=0, minutes=0) -> Delay:
    """Suspend the current task for a duration measured in simulation time.

    Simulation time can be paused (e.g. when the game is paused).

    Args:
        seconds (int, optional): Duration in seconds. Defaults to 0.
        minutes (int, optional): Additional duration in minutes. Defaults to 0.

    Returns:
        Delay: A promise that resolves when the time has elapsed.

    Example:
        await delay_sim(seconds=5)
        "Five simulation seconds have passed."
    """    
    return Delay(seconds, minutes, True)

@awaitable
def delay_app(seconds=0, minutes=0) -> Delay:
    """Suspend the current task for a duration measured in real application time.

    Application time is not affected by game pause.

    Args:
        seconds (int, optional): Duration in seconds. Defaults to 0.
        minutes (int, optional): Additional duration in minutes. Defaults to 0.

    Returns:
        Delay: A promise that resolves when the time has elapsed.

    Example:
        await delay_app(seconds=3)
        "Three real seconds have passed (even if paused)."
    """
    return Delay(seconds, minutes, False)

@awaitable
def timeout(seconds=0, minutes=0) -> Delay:
    """Create a timeout promise measured in real application time.

    Identical to ``delay_app``. Typically passed to ``await comms(timeout=…)``
    or similar constructs that accept a timeout promise.

    Args:
        seconds (int, optional): Duration in seconds. Defaults to 0.
        minutes (int, optional): Additional duration in minutes. Defaults to 0.

    Returns:
        Delay: A promise that resolves when the time has elapsed.

    Example:
        await comms(timeout=timeout(seconds=30))
    """
    # NOTE: This is identical to 'delay_app()'.
    return Delay(seconds, minutes, False)

@awaitable
def timeout_sim(seconds=0, minutes=0) -> Delay:
    """Create a timeout promise measured in simulation time.

    Identical to ``delay_sim``. Simulation time can be paused.

    Args:
        seconds (int, optional): Duration in seconds. Defaults to 0.
        minutes (int, optional): Additional duration in minutes. Defaults to 0.

    Returns:
        Delay: A promise that resolves when the time has elapsed.

    Example:
        await comms(timeout=timeout_sim(minutes=2))
    """
    # NOTE: This is identical to 'delay_sim()'.
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
    
@awaitable
def delay_test(seconds=0, minutes=0):
    """Suspend a task for use in unit tests (not real-time).

    Uses ``DelayForTests`` which counts poll iterations rather than wall or sim
    time, so tests run fast without sleeping.

    Args:
        seconds (int, optional): Simulated duration in seconds. Defaults to 0.
        minutes (int, optional): Additional simulated minutes. Defaults to 0.

    Returns:
        DelayForTests: A promise that resolves after enough poll ticks.
    """
    return DelayForTests(seconds, minutes)