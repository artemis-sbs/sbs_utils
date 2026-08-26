from .inventory import get_inventory_value, set_inventory_value
from ..helpers import FrameContext
from ..futures import Promise, awaitable
from ..mast.pollresults import PollResults

TICK_PER_SECONDS = 30
def set_timer(id_or_obj, name, seconds=0, minutes=0, signal=None):
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
        # //shared/signal/repair_done runs on the server when it expires
    """    
    seconds += minutes*60
    seconds *= TICK_PER_SECONDS
    seconds += FrameContext.context.sim.time_tick_counter
    set_inventory_value(id_or_obj, f"__timer__{name}", seconds)
    if signal is not None:
        from .query import to_id
        _signal_arm(to_id(id_or_obj), f"__timer__{name}", name,
                    due=seconds, signal=signal, every=None, anchor=seconds)
    else:
        # Re-setting a timer WITHOUT a signal disarms the previous one. Otherwise
        # the old entry would sit on a deadline the inventory no longer holds, and
        # the re-validation in the tick would drop it silently - which reads as
        # "the signal randomly stopped firing" rather than as a deliberate cancel.
        _signal_disarm(id_or_obj, f"__timer__{name}")

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

def timer_add_time(id_or_obj, name, seconds=0, minutes=0):
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
        timer_add_time(SHIP_ID, "repair", seconds=15)   # damaged mid-repair
    """
    # Timers store an ABSOLUTE sim tick (see set_timer), so the adjustment is made
    # against that tick in ticks. Going via get_time_remaining would both drop the
    # `now` offset and truncate to whole seconds, shedding up to a second per call.
    target = get_inventory_value(id_or_obj, f"__timer__{name}")
    if target is None or target == 0:
        return False
    now = FrameContext.context.sim.time_tick_counter
    if now > target:
        # Already finished. Extending an expired timer would silently resurrect it.
        return False
    target += (seconds + minutes*60) * TICK_PER_SECONDS
    # A stored 0 reads as "never set" to every other function here, so a large
    # negative adjustment has to leave the timer FINISHED, never UNSET.
    target = max(target, 1)
    set_inventory_value(id_or_obj, f"__timer__{name}", target)
    _signal_retime(id_or_obj, f"__timer__{name}", target)
    # Imported here, not at module scope: signal.py already lazy-imports Delay from
    # this module, and both stub.py and MastGlobals.import_python_module re-export
    # whatever sits in this namespace - a top-level import would publish a second
    # signal_emit into the stubs and the MAST global table.
    from .signal import signal_emit
    from .query import to_id
    signal_emit("timer_updated", {"TIMER_AGENT_ID": to_id(id_or_obj), "TIMER_NAME": name})
    return True


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
    _signal_disarm(id_or_obj, f"__timer__{name}")

def start_counter(id_or_obj, name):
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
        secs = get_counter_elapsed_seconds(SHIP_ID, "docked")
    """

    now = FrameContext.context.sim.time_tick_counter
    set_inventory_value(id_or_obj, f"__counter__{name}", now)
    # An armed interval is anchored to the counter's start value, so moving the
    # start has to move the anchor with it or the next beat would find a value it
    # did not recognize and silently disarm.
    _signal_reanchor(id_or_obj, f"__counter__{name}", now)


def set_interval(id_or_obj, name, signal, seconds=0, minutes=0):
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
        clear_interval(SHIP_ID, "patrol")
    """
    every = (seconds + minutes*60) * TICK_PER_SECONDS
    if every <= 0:
        # A zero period would emit on every single tick forever. That is never what
        # the caller meant, and it would be found as a frame-rate bug, not as a
        # scripting one - so refuse it here where the message names the interval.
        # Local import for the same reason signal_emit is imported locally below.
        from .execution import log
        log(f"set_interval('{name}') needs a period greater than 0 - not started",
            "timers", "warning")
        return False
    now = FrameContext.context.sim.time_tick_counter
    set_inventory_value(id_or_obj, f"__counter__{name}", now)
    from .query import to_id
    _signal_arm(to_id(id_or_obj), f"__counter__{name}", name,
                due=now + every, signal=signal, every=every, anchor=now)
    return True


def clear_interval(id_or_obj, name):
    """Stop an interval started by ``set_interval``.

    Identical to ``clear_counter`` - an interval IS a counter - and named for
    symmetry so a script that starts one can stop it by the same word.

    Args:
        id_or_obj (Agent | int): Agent ID or object.
        name (str): Interval name.

    Example:
        clear_interval(SHIP_ID, "patrol")
    """
    clear_counter(id_or_obj, name)


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

def format_counter_elapsed_seconds(id_or_obj, name, display="hh:mm:ss"):
    """
    Return a formatted string of the elapsed time for the counter, rounded to the second.
    The format can be customized by specifying the `display` argument.

    Args:
        id_or_obj (int | Agent): Agent ID or object
        name (str): The name of the counter
        format (str): The format the string should take. Use `hh` for hours, `mm` for minutes, and `ss` for seconds. Default is `hh:mm:ss`.
    Returns:
        str: The formatted time, in the specified format.
    """
    elapsed = get_counter_elapsed_seconds(id_or_obj, name, 0)
    seconds = round(elapsed)
    minutes, sec = divmod(seconds, 60) # Get total minutes and remaining seconds
    hours, minutes = divmod(minutes, 60) # Get total hours and remaining
    # Here we replace the times.
    ret = display.replace("hh",f"{hours}".zfill(2)).replace("mm", f"{minutes}".zfill(2)).replace("ss",f"{seconds}".zfill(2))#.replace("h",f"{hours}").replace("m",f"{minutes}").replace("s",f"{seconds}") 
    # TODO: I'd like to support single digits, but not sure how best to handle displays like "Mission time is h hours, m minutes, and s seconds" due to the possibility of single characters being in the string.
    return ret

def clear_counter(id_or_obj, name):
    """Remove a named counter from an agent.

    Args:
        id_or_obj (Agent | int): Agent ID or object.
        name (str): Counter name.

    Example:
        clear_counter(SHIP_ID, "docked")
    """    
    set_inventory_value(id_or_obj, f"__counter__{name}", None)
    _signal_disarm(id_or_obj, f"__counter__{name}")


# ---------------------------------------------------------------------------
# Opt-in signals for timers and counters
#
# A timer is an int in an agent's inventory and nothing ever runs - which is what
# makes timers free: a mission with 500 of them costs the same per frame as one
# with none. Sweeping every timer looking for expired ones would spend that on
# behalf of every GUI countdown nobody listens to, so signals are OPT-IN: only
# set_timer(signal=) and set_interval() register here.
#
# Armed entries are still nearly free, because the deadline is a known integer at
# arm time. `_NEXT_DUE` caches the earliest one, so a tick costs one integer
# compare and the dict is only walked on a frame where something is actually due.
# That is cheaper than the pattern this replaces: a watcher task per timer costs a
# generator resume through task.tick() PLUS a run_on_change pass, each, every tick.
#
# The tick task is created with the first armed entry and stopped when the last one
# leaves (the DripQueue pattern), so a mission that never uses this schedules
# nothing at all. Deliberately not an "already scheduled" latch - those survive
# TickDispatcher.clear() and are why brains stopped ticking on every run after the
# first.
#
# entry: (agent_id, inv_key) ->
#     [due_tick, signal, every_ticks_or_None, anchor, name, beats_so_far]
# `anchor` is the inventory value the entry was armed against, re-read at fire
# time: it is how a cleared timer, a deleted agent, a value rewritten behind our
# back, and a RECYCLED agent id all fail to emit. `every` is None for a one-shot
# timer completion and the beat period for a counter heartbeat.
# ---------------------------------------------------------------------------
_SIGNALS = {}
_NEXT_DUE = None
_TICK_TASK = None


def _signal_stop_task():
    global _TICK_TASK
    if _TICK_TASK is not None:
        try:
            _TICK_TASK.stop()
        except Exception:
            pass
        _TICK_TASK = None


def _signal_recompute():
    """Re-cache the earliest deadline; park the tick task when nothing is armed."""
    global _NEXT_DUE
    if _SIGNALS:
        _NEXT_DUE = min(entry[0] for entry in _SIGNALS.values())
    else:
        _NEXT_DUE = None
        _signal_stop_task()


def _signal_arm(agent_id, inv_key, name, due, signal, every, anchor):
    global _TICK_TASK
    _SIGNALS[(agent_id, inv_key)] = [due, signal, every, anchor, name, 0]
    _signal_recompute()
    if _TICK_TASK is None:
        # Local import: tickdispatcher pulls in the agent layer, and this module is
        # imported early and re-exported wholesale into the MAST global table.
        from ..tickdispatcher import TickDispatcher
        _TICK_TASK = TickDispatcher.do_interval(_signals_tick, 0)


def _signal_disarm(id_or_obj, inv_key):
    # Cheap guard first: a mission using no signals never resolves an id here.
    if not _SIGNALS:
        return
    from .query import to_id
    if _SIGNALS.pop((to_id(id_or_obj), inv_key), None) is not None:
        _signal_recompute()


def _signal_retime(id_or_obj, inv_key, target):
    """Follow a deadline that moved under an armed entry (timer_add_time)."""
    if not _SIGNALS:
        return
    from .query import to_id
    entry = _SIGNALS.get((to_id(id_or_obj), inv_key))
    if entry is None:
        return
    entry[0] = target
    entry[3] = target
    _signal_recompute()


def _signal_reanchor(id_or_obj, inv_key, anchor):
    """Follow an anchor value that was rewritten (start_counter restarting)."""
    if not _SIGNALS:
        return
    from .query import to_id
    entry = _SIGNALS.get((to_id(id_or_obj), inv_key))
    if entry is None:
        return
    entry[3] = anchor
    entry[0] = anchor + entry[2]
    _signal_recompute()


def _signals_tick(t=None):
    if not _SIGNALS:
        _signal_stop_task()
        return
    now = FrameContext.context.sim.time_tick_counter
    if _NEXT_DUE is not None and now <= _NEXT_DUE:
        return
    # `now > due` is the same test is_timer_finished uses. A signal must not claim
    # a timer is done on a tick where polling it would still say it is running.
    due = [key for key, entry in _SIGNALS.items() if now > entry[0]]
    for key in due:
        entry = _SIGNALS.get(key)
        if entry is None:
            continue
        deadline, signal, every, anchor, name, count = entry
        agent_id, inv_key = key
        stored = get_inventory_value(agent_id, inv_key)
        if stored is None or stored != anchor:
            # Cleared, re-set, or its agent was deleted. No signal, and stop
            # watching - whoever rewrote it re-armed if they wanted one.
            del _SIGNALS[key]
            continue
        count += 1
        if every is None:
            del _SIGNALS[key]
        else:
            # Schedule from the previous deadline, not from `now`, so a heartbeat
            # keeps its period instead of drifting by a tick every beat. A beat
            # missed while the sim was paused is skipped, not caught up on.
            while deadline <= now:
                deadline += every
            entry[0] = deadline
            entry[5] = count
        # signal_emit needs FrameContext.mast, which the MastScheduler sets on its
        # own tick and never restores - so the live story is still there during the
        # dispatch_tick phase this runs in. game_end_run_all's "show_game_results"
        # emit rides the same thing. Do not "fix" this by requiring a task.
        #
        # ...but the scheduler leaves FrameContext.TASK behind too, and by the time
        # this runs that task is usually FINISHED. signal_emit passes it as the
        # sender, and MastAsyncTask.emit_signal drops any emit whose sender is done
        # - so the signal was emitted and every //signal route silently did nothing.
        # A timer is not speaking on behalf of a task; say so, and the routes run.
        # Only the TASK is overridden: the page and event still belong to the frame.
        from .signal import signal_emit
        held = FrameContext._task
        FrameContext._task = None
        try:
            signal_emit(signal, {"TIMER_AGENT_ID": agent_id,
                                 "TIMER_NAME": name,
                                 "TIMER_COUNT": count})
        finally:
            FrameContext._task = held
    _signal_recompute()


def timer_signals_clear():
    """Drop every armed timer/counter signal (mission reset)."""
    _SIGNALS.clear()
    _signal_recompute()


def timer_signals_count():
    """How many timers/counters are armed to emit a signal (reset audit)."""
    return len(_SIGNALS)


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