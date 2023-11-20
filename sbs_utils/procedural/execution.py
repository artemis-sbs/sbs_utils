from ..helpers import FrameContext

def jump(label):
    task = FrameContext.task

    if task is not None:
        return task.jump(label)
    return None
