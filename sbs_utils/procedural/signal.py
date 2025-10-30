from ..helpers import FrameContext
from ..mast.mast import Mast

class SignalLabelInfo:
    def __init__(self, is_jump, label, loc, server) -> None:
        self.is_jump = is_jump
        self.label = label
        self.loc = loc
        self.server = server
        

def signal_emit(name, data=None):
    """
    Emit a signal to trigger all instances of the signal route to run.
    Args:
        name (str): The name of the signal.
        data (dict): The data to provide to the signal route.
    """
    mast = FrameContext.mast
    task = FrameContext.task
    if mast is None:
        return
    mast.signal_emit(name, task, data)

def signal_register(name, label, server=False, task=None, loc=0, is_jump=True):
    """
    Register a new signal route, linking the signal name with the specified label.
    Args:
        name (str): The name of the signal.
        label (str | Label): The label to run when the signal is emitted.
        server (bool, optional): Should the label run only for the server (as a shared signal)? Default is False.
        loc (int, optional): The index of the sublabel to run. Default is 0.
        is_jump (bool, optional): Should the signal trigger a jump to the signal's label, continuing the current task? Default is True.
    """
    mast = FrameContext.mast
    if task is None:
        task = FrameContext.task
    if task is None:
        return
    if task.is_sub_task:
        task = task.root_task
    if task is None:
        return

    if mast is None:
        return
    info = SignalLabelInfo(is_jump, label, loc, server)
    mast.signal_register(name, task, info)
