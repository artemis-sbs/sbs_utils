from ..helpers import FrameContext
from ..mast.mast import Mast

class SignalLabelInfo:
    def __init__(self, is_jump, label, loc) -> None:
        self.is_jump = is_jump
        self.label = label
        self.loc = loc
        

def signal_emit(name, data):
    mast = FrameContext.mast
    task = FrameContext.task
    if mast is None:
        print("Signal emitted with non MAST")
        return
    mast.signal_emit(name, task, data)

def signal_register(name, label):
    mast = FrameContext.mast
    task = FrameContext.task
    if mast is None:
        print("Signal emitted with non MAST")
        return
    info = SignalLabelInfo(True, label, 0)
    mast.signal_register(name, task, info)
