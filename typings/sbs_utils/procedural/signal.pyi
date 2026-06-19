from sbs_utils.helpers import FrameContext
def signal_emit (name, data=None):
    """Emit a named signal, running all registered ``//signal/<name>`` routes.
    
    Safe to call when no MAST context is active — returns immediately with no
    side effects.
    
    Args:
        name (str): The signal name.
        data (dict, optional): Arbitrary data passed to each signal handler.
            Defaults to None."""
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
class SignalLabelInfo(object):
    """class SignalLabelInfo"""
    def __init__ (self, is_jump, label, loc, server) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
