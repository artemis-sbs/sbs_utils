from ..helpers import FrameContext
from ..mast.mast import Mast

class SignalLabelInfo:
    def __init__(self, is_jump, label, loc, server) -> None:
        self.is_jump = is_jump
        self.label = label
        self.loc = loc
        self.server = server
        

def signal_emit(name, data):
    mast = FrameContext.mast
    task = FrameContext.task
    if mast is None:
        return
    mast.signal_emit(name, task, data)

def signal_register(name, label, server):
    mast = FrameContext.mast
    task = FrameContext.task
    if mast is None:
        return
    print(f"signal registered {name} {task.get_id() & 0x0000FFFFFFF} {server}")
    info = SignalLabelInfo(True, label, 0, server)
    mast.signal_register(name, task, info)
