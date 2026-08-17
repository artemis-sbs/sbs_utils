from sbs_utils.helpers import FrameContext
from sbs_utils.mast.pollresults import PollResults
from sbs_utils.futures import Promise
def _signal_arm (agent_id, inv_key, name, due, signal, every, anchor):
    ...
def _signal_disarm (id_or_obj, inv_key):
    ...
def _signal_reanchor (id_or_obj, inv_key, anchor):
    """Follow an anchor value that was rewritten (start_counter restarting)."""
def _signal_recompute ():
    """Re-cache the earliest deadline; park the tick task when nothing is armed."""
def _signal_retime (id_or_obj, inv_key, target):
    """Follow a deadline that moved under an armed entry (timer_add_time)."""
def _signal_stop_task ():
    ...
def _signals_tick (t=None):
    ...
def awaitable (func):
    ...
def clear_counter (id_or_obj, name):
    """Remove a named counter from an agent.
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
        name (str): Counter name.
    
    Example:
        clear_counter(SHIP_ID, "docked")"""
def clear_interval (id_or_obj, name):
    """Stop an interval started by ``set_interval``.
    
    Identical to ``clear_counter`` - an interval IS a counter - and named for
    symmetry so a script that starts one can stop it by the same word.
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
        name (str): Interval name.
    
    Example:
        clear_interval(SHIP_ID, "patrol")"""
def clear_timer (id_or_obj, name):
    """Clear a named timer so it is no longer set.
    
    After clearing, ``is_timer_set`` returns ``False`` and
    ``is_timer_finished`` returns ``True``.
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
        name (str): Timer name.
    
    Example:
        clear_timer(SHIP_ID, "cooldown")"""
def delay_app (seconds=0, minutes=0) -> sbs_utils.procedural.timers.Delay:
    """Suspend the current task for a duration measured in real application time.
    
    Application time is not affected by game pause.
    
    Args:
        seconds (int, optional): Duration in seconds. Defaults to 0.
        minutes (int, optional): Additional duration in minutes. Defaults to 0.
    
    Returns:
        Delay: A promise that resolves when the time has elapsed.
    
    Example:
        await delay_app(seconds=3)
        "Three real seconds have passed (even if paused).""""
def delay_sim (seconds=0, minutes=0) -> sbs_utils.procedural.timers.Delay:
    """Suspend the current task for a duration measured in simulation time.
    
    Simulation time can be paused (e.g. when the game is paused).
    
    Args:
        seconds (int, optional): Duration in seconds. Defaults to 0.
        minutes (int, optional): Additional duration in minutes. Defaults to 0.
    
    Returns:
        Delay: A promise that resolves when the time has elapsed.
    
    Example:
        await delay_sim(seconds=5)
        "Five simulation seconds have passed.""""
def delay_test (seconds=0, minutes=0):
    """Suspend a task for use in unit tests (not real-time).
    
    Uses ``DelayForTests`` which counts poll iterations rather than wall or sim
    time, so tests run fast without sleeping.
    
    Args:
        seconds (int, optional): Simulated duration in seconds. Defaults to 0.
        minutes (int, optional): Additional simulated minutes. Defaults to 0.
    
    Returns:
        DelayForTests: A promise that resolves after enough poll ticks."""
def format_time_remaining (id_or_obj, name):
    """Return the time remaining on a timer as a ``M:SS`` string.
    
    Returns an empty string when the timer has expired or is not set.
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
        name (str): Timer name.
    
    Returns:
        str: Formatted remaining time, e.g. ``"1:30"``, or ``""`` if expired.
    
    Example:
        gui_text("Time: {format_time_remaining(SHIP_ID, 'mission')}")"""
def get_counter_elapsed_seconds (id_or_obj, name, default_value=None):
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
            "Docking complete.""""
def get_inventory_value (id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.
    
    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
def get_time_remaining (id_or_obj, name):
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
            "Less than a minute remaining!""""
def is_timer_finished (id_or_obj, name):
    """Return whether a timer has expired. Returns ``True`` if the timer is not set.
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
        name (str): Timer name.
    
    Returns:
        bool: ``True`` if the timer has expired or was never set.
    
    Example:
        if is_timer_finished(SHIP_ID, "repair"):
            "Repair bay ready.""""
def is_timer_set (id_or_obj, name):
    """Return whether a named timer exists on an agent.
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
        name (str): Timer name.
    
    Returns:
        bool: ``True`` if the timer has been set (even if already expired).
    
    Example:
        if not is_timer_set(SHIP_ID, "cooldown"):
            set_timer(SHIP_ID, "cooldown", seconds=10)"""
def is_timer_set_and_finished (id_or_obj, name):
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
            "Weapons ready!""""
def set_interval (id_or_obj, name, signal, seconds=0, minutes=0):
    """Emit a signal on an agent every ``seconds``, until it is cleared.
    
    The repeating sibling of ``set_timer``. Beats are scheduled from the start,
    not from when the last one fired, so the period does not drift. Each emit
    carries ``TIMER_AGENT_ID``, ``TIMER_NAME`` and ``TIMER_COUNT`` (1 for the
    first beat). Handle it with ``//shared/signal/<name>`` for anything with a
    side effect - a plain ``//signal/<name>`` runs once per console, so a beat
    becomes one per console per beat (see SIGNAL_ROUTING.md).
    
    Runs on a counter, so ``get_counter_elapsed_seconds(id, name)`` reads the
    time since it started and ``clear_interval`` (or ``clear_counter``) stops it.
    Stops on its own if the agent is deleted. A paused sim does not advance the
    beat, and beats missed while paused are skipped rather than caught up on.
    
    Args:
        id_or_obj (Agent | int): The agent to run the interval on.
        name (str): Unique interval name for this agent.
        signal (str): Signal to emit on every beat.
        seconds (int, optional): Seconds between beats. Defaults to 0.
        minutes (int, optional): Additional minutes between beats. Defaults to 0.
    
    Example:
        set_interval(SHIP_ID, "patrol", "patrol_beat", seconds=30)
        # //shared/signal/patrol_beat runs on the server every 30 seconds
        clear_interval(SHIP_ID, "patrol")"""
def set_inventory_value (so, key: str, value):
    """Set an inventory value on one or more agents.
    
    If ``so`` is a set or collection, every member receives the value.
    
    Args:
        so (Agent | int | set[Agent | int]): The agent(s) to update.
        key (str): The inventory key.
        value (any): The value to store."""
def set_timer (id_or_obj, name, seconds=0, minutes=0, signal=None):
    """Start a named countdown timer on an agent.
    
    Records the expiry tick in the agent's inventory. Use ``is_timer_finished``
    or ``get_time_remaining`` to check progress.
    
    Pass ``signal`` to have the library emit that signal once, when the timer
    expires, instead of polling for it. The emit carries ``TIMER_AGENT_ID`` and
    ``TIMER_NAME``. It is purely additive - the timer is still an ordinary timer
    afterwards, so ``is_timer_set_and_finished`` and ``format_time_remaining``
    behave exactly as they do without it. Handle it with
    ``//shared/signal/<name>`` for anything with a side effect; a plain
    ``//signal/<name>`` runs once per console (see SIGNAL_ROUTING.md).
    
    No signal is emitted if the timer is cleared, re-set without ``signal``, or
    its agent is deleted before it expires. A paused sim does not advance the
    timer, so it does not expire while paused.
    
    Args:
        id_or_obj (Agent | int): The agent to set the timer on.
        name (str): Unique timer name for this agent.
        seconds (int, optional): Duration in seconds. Defaults to 0.
        minutes (int, optional): Additional duration in minutes. Defaults to 0.
        signal (str, optional): Signal to emit once when the timer expires.
            Defaults to None (no signal - poll it instead).
    
    Example:
        set_timer(SHIP_ID, "repair", seconds=30)
        if is_timer_finished(SHIP_ID, "repair"):
            "Repairs complete!"
    
        set_timer(SHIP_ID, "repair", seconds=30, signal="repair_done")
        # //shared/signal/repair_done runs on the server when it expires"""
def start_counter (id_or_obj, name):
    """Record the current sim tick as the start of a named counter.
    
    Use ``get_counter_elapsed_seconds`` to read how many seconds have passed
    since the counter was started. Use ``set_interval`` for a counter that emits
    a signal every so often instead of being read.
    
    Restarting a counter that ``set_interval`` armed restarts its beat too - the
    next one lands a full interval from now.
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
        name (str): Counter name.
    
    Example:
        start_counter(SHIP_ID, "docked")
        # later...
        secs = get_counter_elapsed_seconds(SHIP_ID, "docked")"""
def timeout (seconds=0, minutes=0) -> sbs_utils.procedural.timers.Delay:
    """Create a timeout promise measured in real application time.
    
    Identical to ``delay_app``. Typically passed to ``await comms(timeout=…)``
    or similar constructs that accept a timeout promise.
    
    Args:
        seconds (int, optional): Duration in seconds. Defaults to 0.
        minutes (int, optional): Additional duration in minutes. Defaults to 0.
    
    Returns:
        Delay: A promise that resolves when the time has elapsed.
    
    Example:
        await comms(timeout=timeout(seconds=30))"""
def timeout_sim (seconds=0, minutes=0) -> sbs_utils.procedural.timers.Delay:
    """Create a timeout promise measured in simulation time.
    
    Identical to ``delay_sim``. Simulation time can be paused.
    
    Args:
        seconds (int, optional): Duration in seconds. Defaults to 0.
        minutes (int, optional): Additional duration in minutes. Defaults to 0.
    
    Returns:
        Delay: A promise that resolves when the time has elapsed.
    
    Example:
        await comms(timeout=timeout_sim(minutes=2))"""
def timer_add_time (id_or_obj, name, seconds=0, minutes=0):
    """Add (or subtract) time on a timer that is currently running.
    
    A no-op when the timer was never set or has already expired - use ``set_timer``
    to start a fresh one. Times may be negative, which shortens the timer and can
    expire it outright.
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
        name (str): Timer name.
        seconds (int, optional): Seconds to add. Negative shortens. Defaults to 0.
        minutes (int, optional): Additional minutes to add. Defaults to 0.
    
    Returns:
        bool: ``True`` if a running timer was adjusted.
    
    Example:
        set_timer(SHIP_ID, "repair", seconds=30)
        timer_add_time(SHIP_ID, "repair", seconds=15)   # damaged mid-repair"""
def timer_signals_clear ():
    """Drop every armed timer/counter signal (mission reset)."""
def timer_signals_count ():
    """How many timers/counters are armed to emit a signal (reset audit)."""
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
