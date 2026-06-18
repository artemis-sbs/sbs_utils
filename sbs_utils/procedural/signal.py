from ..helpers import FrameContext

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
