from ..helpers import FrameContext
from ..mast.mast import Mast

class SignalLabelInfo:
    def __init__(self, is_jump, label, loc) -> None:
        self.is_jump = is_jump
        self.label = label
        self.loc = loc
        

def signal_emit(name, data):
    task = FrameContext.task 
    task.main.mast.signal_emit(name, task, data)

def signal_register(name, label):
    task = FrameContext.task 
    info = SignalLabelInfo(True, label, 0)
    task.main.mast.signal_register(name, task, info)
