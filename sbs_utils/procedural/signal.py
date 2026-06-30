from ..helpers import FrameContext
from ..futures import Promise, awaitable
from ..mast.pollresults import PollResults

class SignalLabelInfo:
    def __init__(self, is_jump, label, loc, server) -> None:
        self.is_jump = is_jump
        self.label = label
        self.loc = loc
        self.server = server
        

def signal_emit(name, data=None):
    """Emit a named signal, running all registered ``//signal/<name>`` routes.

    Safe to call when no MAST context is active — returns immediately with no
    side effects.

    Args:
        name (str): The signal name.
        data (dict, optional): Arbitrary data passed to each signal handler.
            Defaults to None.
    """
    # Resolve any one-shot awaiters first (signal_next); independent of MAST
    # context so a wait still resolves even if no //signal routes are active.
    _resolve_signal_waiters(name, data)

    mast = FrameContext.mast
    task = FrameContext.task
    if mast is None:
        return
    mast.signal_emit(name, task, data)


    

def signal_register(name, label, server=False, task=None, loc=0, is_jump=True, is_temporary=False):
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
            Defaults to False.
    """
    mast = FrameContext.mast
    if task is None:
        task = FrameContext.task
    if task is None:
        return
    # Temporary signals use a new idle task
    # On the GUI task
    if is_temporary:
        from .execution import gui_sub_task_schedule, LABEL_ALWAYS_IDLE
        task = gui_sub_task_schedule(LABEL_ALWAYS_IDLE)
    #  NOTE: on Signal will NOT use is temporary and uses the main gui task on change
    #  
    elif task.is_sub_task:
        task = task.root_task
        
    if task is None:
        return

    if mast is None:
        return
    info = SignalLabelInfo(is_jump, label, loc, server)
    mast.signal_register(name, task, info)


# --- one-shot await of a signal ----------------------------------------------
# signal_next(name) suspends the current task until the NEXT emit of `name`,
# resolving with that emit's data. It is a Future (one-shot): loop it to react
# repeatedly; for persistent, never-miss reaction use a //signal route instead.
# Multiple tasks may await the same signal at once - all resolve on the emit.

_signal_waiters = {}   # name -> [SignalPromise, ...]


class SignalPromise(Promise):
    """Resolves the next time ``name`` is emitted (one-shot).

    ``result()`` is the emitted data dict (which may be ``None``). With a
    ``timeout`` (application seconds, so it advances even while the sim is
    paused) it resolves with ``None`` and sets ``timed_out = True`` if the
    signal does not arrive in time.
    """
    def __init__(self, name, timeout=None):
        super().__init__()
        self.name = name
        self._fired = False
        self.timed_out = False
        self._timeout = None
        if timeout is not None:
            from .timers import Delay
            self._timeout = Delay(timeout, 0, False)  # app-time

    def _fire(self, data):
        self._fired = True
        self._result = data           # may be None; done() uses _fired, not _result

    def poll(self):
        if not self._fired and self._timeout is not None and self._timeout.done():
            self.timed_out = True
            self._fired = True
            _signal_waiter_remove(self.name, self)
        return PollResults.OK_RUN_AGAIN

    def done(self):
        return self._fired or self._canceled is not None or self._exception is not None

    def cancel(self, msg=None):
        _signal_waiter_remove(self.name, self)
        return super().cancel(msg)


def _signal_waiter_remove(name, prom):
    lst = _signal_waiters.get(name)
    if lst and prom in lst:
        lst.remove(prom)
        if not lst:
            del _signal_waiters[name]


def _resolve_signal_waiters(name, data):
    """Fire all tasks currently awaiting ``name`` (one-shot) and clear them."""
    waiters = _signal_waiters.pop(name, None)
    if not waiters:
        return
    for prom in waiters:
        if not prom.done():
            prom._fire(data)


def signal_waiters_clear():
    """Drop all pending signal_next waiters (call on mission reset)."""
    _signal_waiters.clear()


@awaitable
def signal_next(name, timeout=None) -> SignalPromise:
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
        result = await promise_any(signal_next("docked"), delay_sim(30))
    """
    prom = SignalPromise(name, timeout)
    _signal_waiters.setdefault(name, []).append(prom)
    return prom
