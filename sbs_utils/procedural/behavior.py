from ..helpers import FrameContext
from ..futures import Promise
from ..mast.pollresults import PollResults


class PromiseBehaveSeq(Promise):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__()
        if FrameContext.task is None:
            return
        self.main_task = FrameContext.task
        self.data = None
        self.task = None
        if kwargs is not None:
            self.data = kwargs.get("data", None)
        self.labels = list(args)
        if len(self.labels)==0:
            self.set_result(PollResults.BT_FAIL)
        else:
            self.next()

    def next(self):
        if len(self.labels) != 0:
            label = self.labels.pop(0)
            self.task = FrameContext.task.start_task(label, self.data)

    def poll(self):
        if self.task and self.task.done():
            if self.task.result() == PollResults.BT_SUCCESS:
                self.next()
            else:
                self.set_result(PollResults.BT_FAIL)
                return
        # if nothing is left then everything succeeded
        if len(self.labels) == 0:
            self.set_result(PollResults.BT_SUCCESS)   
        
class PromiseBehaveSel(PromiseBehaveSeq):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
                
    def poll(self):
        if self.task.done():
            if self.task.result() == PollResults.BT_FAIL:
                self.next()
            else:
                self.set_result(PollResults.BT_SUCCESS)
                return
        # if nothing is left then nothing succeeded
        if len(self.labels) == 0:
            self.set_result(PollResults.BT_FAIL)   
        
    


def bt_seq(*args, **kwargs):
    return PromiseBehaveSeq(*args, **kwargs)

def bt_sel(*args, **kwargs):
    return PromiseBehaveSel(*args, **kwargs)