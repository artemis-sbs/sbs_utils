from ..helpers import FrameContext
from ..mast.mast import Mast

class SignalLabelInfo:
    def __init__(self, is_jump, label, loc, server) -> None:
        self.is_jump = is_jump
        self.label = label
        self.loc = loc
        self.server = server
        

def signal_emit(name, data=None):
    mast = FrameContext.mast
    task = FrameContext.task
    if mast is None:
        return
    mast.signal_emit(name, task, data)

def signal_register(name, label, server=False, task=None, loc=0, is_jump=True):
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
