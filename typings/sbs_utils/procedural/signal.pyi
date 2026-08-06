from sbs_utils.helpers import FrameContext
from sbs_utils.mast.pollresults import PollResults
from sbs_utils.futures import Promise
def _resolve_signal_waiters (name, data):
    """Fire all tasks currently awaiting ``name`` (one-shot) and clear them."""
def _signal_once_fired ():
    """The label -> path map of `once` routes that have already run."""
def _signal_waiter_remove (name, prom):
    ...
def awaitable (func):
    ...
def signal_emit (name, data=None):
    """Emit a named signal, running all registered ``//signal/<name>`` routes.
    
    Safe to call when no MAST context is active — returns immediately with no
    side effects.
    
    Args:
        name (str): The signal name.
        data (dict, optional): Arbitrary data passed to each signal handler.
            Defaults to None."""
def signal_next (name, timeout=None) -> sbs_utils.procedural.signal.SignalPromise:
    """Suspend the current task until the next ``signal_emit(name)``.
    
    Resolves with that emit's data (may be ``None``). One-shot - loop it to
    react to each occurrence; for persistent reaction use a ``//signal/<name>``
    route. Composes with ``promise_any`` for event-or-timeout, or pass
    ``timeout`` (application seconds) to resolve with ``None`` on expiry.
    
    Args:
        name (str): Signal name to wait for.
        timeout (float, optional): Seconds to wait before resolving with
            ``None`` (``timed_out`` set). Defaults to None (wait forever).
    
    Returns:
        SignalPromise: Await it; the value is the emitted data.
    
    Example:
        data = await signal_next("wave_cleared")
        result = await promise_any(signal_next("docked"), delay_sim(30))"""
def signal_once_enter (label, path=None):
    """Test-and-set the one-shot flag for a ``once`` route body.
    
    Compiled into the route by ``SignalRouteDecoratorLabel`` - scripts do not call
    this directly. Keyed on the generated LABEL name, not the signal path, so two
    routes handling the same signal each get their own shot.
    
    Args:
        label (str): The route's generated label name.
        path (str, optional): The signal name, so ``signal_once_reset`` can find it.
    
    Returns:
        bool: True the first time (run the body), False afterwards."""
def signal_once_reset (name=None):
    """Re-arm ``once`` routes so they will run again.
    
    The explicit path for an INTENTIONAL re-initialization - resetting scenario
    conditions without reloading the mission. A mission reload needs no call: the
    flags live in Agent.SHARED and ``reset_mission_state`` clears it.
    
    Args:
        name (str, optional): Signal name to re-arm. Defaults to all of them.
    
    Returns:
        int: How many routes were re-armed."""
def signal_register (name, label, server=False, task=None, loc=0, is_jump=True, is_temporary=False):
    """Register a label as a handler for a named signal.
    
    When ``signal_emit(name)`` is called, each handler registered under that
    name will run. Temporary handlers are attached to a short-lived idle task
    and are cleaned up when a new GUI is loaded.
    
    Args:
        name (str): The signal name to listen for.
        label (str | Label): The label to execute when the signal fires.
        server (bool, optional): If ``True``, run only on the server (shared
            signal). Defaults to False.
        task (Task, optional): The task to attach the handler to. Defaults to
            the current ``FrameContext.task``.
        loc (int, optional): Sub-label index to run. Defaults to 0.
        is_jump (bool, optional): If ``True``, jump to the label in the current
            task rather than spawning a new one. Defaults to True.
        is_temporary (bool, optional): If ``True``, attach the handler to a
            transient idle task that is cleaned up on the next GUI load.
            Defaults to False."""
def signal_waiters_clear ():
    """Drop all pending signal_next waiters (call on mission reset)."""
class SignalLabelInfo(object):
    """class SignalLabelInfo"""
    def __init__ (self, is_jump, label, loc, server) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
class SignalPromise(Promise):
    """Resolves the next time ``name`` is emitted (one-shot).
    
    ``result()`` is the emitted data dict (which may be ``None``). With a
    ``timeout`` (application seconds, so it advances even while the sim is
    paused) it resolves with ``None`` and sets ``timed_out = True`` if the
    signal does not arrive in time."""
    def __init__ (self, name, timeout=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _fire (self, data):
        ...
    def cancel (self, msg=None):
        ...
    def done (self):
        ...
    def poll (self):
        ...
