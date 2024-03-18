from ..helpers import FrameContext
from ..futures import AwaitBlockPromise, Promise
from ..mast.pollresults import PollResults


class PromiseBehave(AwaitBlockPromise):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fail_label = None
        self.success_label = None
        self.main_task = FrameContext.task

    def initial_poll(self):
        if self._initial_poll:
            return
        # Will Build buttons
        #print("INit pool")
        for inline in self.inlines:
            if inline.inline.startswith("fail"):
                self.fail_label = inline
            if inline.inline.startswith("success"):
                self.success_label = inline
            
        super().initial_poll()
    
    def rewind(self):
        pass

    def run_success_label(self):
        if self.success_label:
            task = self.main_task
            self.main_task.jump(task.active_label,self.success_label.loc+1)

    def run_fail_label(self):
        if self.fail_label:
            task = self.main_task
            self.main_task.jump(task.active_label,self.fail_label.loc+1)
    

class PromiseBehaveSeqSel(PromiseBehave):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__()
        if FrameContext.task is None:
            return
        self.main_task = FrameContext.task
        self.data = None
        self.task_promise = None
        if kwargs is not None:
            self.data = kwargs.get("data", None)
        else:
            self.data = {}

        self.set_variable("BT_PROMISE", self)
        self.set_variable("BT_MAIN", self.main_task)

        self.labels = list(args)
        self.current = None
        if len(self.labels)==0:
            self.set_result(PollResults.BT_FAIL)
        else:
            self.next()

    def rewind(self):
        self.current = None
        self.set_result(None)

    def next(self):
        if self.current is None:
            self.current = 0
        else:
            self.current += 1

        if self.current < len(self.labels):
            label = self.labels[self.current]
            if isinstance(label, Promise):
                self.task_promise = label
                # Need to make sure it is in start state
                # e.g. bt_delay
                label.rewind()
            else:
                self.task_promise = FrameContext.task.start_task(label, self.data)

            

    def poll(self):
        super().poll()

    def set_variable(self, name, value):
        if self.data is None:
            self.data = {}
        self.data[name] = value

    def export_variable(self, name, value):
        self.main_task.set_variable(name, value)

    def get_variable(self, name, defa_value):
        if self.data is None:
            return defa_value
        return self.data.get(name, defa_value)

class PromiseBehaveSeq(PromiseBehaveSeqSel):
    def poll(self):
        super().poll()
        if self.task_promise:
            self.task_promise.poll()

        if self.task_promise and self.task_promise.done():
            if self.task_promise.result() == PollResults.BT_SUCCESS:
                self.next()
            else:
                #
                self.set_result(PollResults.BT_FAIL)
                self.run_fail_label()
                return
        # if nothing is left then everything succeeded
        if self.current >= len(self.labels) :
            self.set_result(PollResults.BT_SUCCESS)   
            self.run_success_label()
        
class PromiseBehaveSel(PromiseBehaveSeqSel):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
                
    def poll(self):
        super().poll()
        if self.task_promise.done():
            if self.task_promise.result() == PollResults.BT_FAIL:
                self.next()
            else:

                if self.success_label:
                    self.run_success_label()
                else:
                    self.set_result(PollResults.BT_SUCCESS)
                return
        # if nothing is left then nothing succeeded
        if self.current >= len(self.labels):
            if self.fail_label:
                self.run_fail_label()
            else:
                self.set_result(PollResults.BT_FAIL)   
            
        

class PromiseBehaveInvert(PromiseBehave):
    def __init__(self, label_or_promise) -> None:
        super().__init__()
        # Expect a promise, assum label otherwise
        self.promise = label_or_promise
        if not isinstance(label_or_promise, AwaitBlockPromise):
            self.promise = bt_sel(label_or_promise)
                
    def poll(self):
        super().poll()
        if self.promise.done():
            if self.promise.result() == PollResults.BT_FAIL:
                self.set_result(PollResults.BT_FAIL)       
            else:
                self.set_result(PollResults.BT_SUCCESS)
                return


class PromiseBehaveUntil(PromiseBehave):
    def __init__(self, label_or_promise, until_result=PollResults.BT_SUCCESS) -> None:
        super().__init__()
        # Expect a promise, assum label otherwise
        self.promise = label_or_promise
        self.until_result = until_result
        if not isinstance(label_or_promise, AwaitBlockPromise):
            self.promise = bt_sel(label_or_promise)
                
    def poll(self):
        super().poll()
        if self.promise.done():
            if self.promise.result() == self.until_result:
                self.set_result(self.until_result)       
            # Will fail on non-bt
            self.promise.rewind()
                

def bt_seq(*args, **kwargs):
    """behavior tree sequence only returns success if the whole sequence has success

    Args:
        args (labels): The arguments are labels
        kwargs (any): data = will pass data the the behavior tasks.

    Returns:
        Promise: A Promise that runs until failure or success
    """    
    return PromiseBehaveSeq(*args, **kwargs)

def bt_sel(*args, **kwargs):
    """behavior tree select returns success if any task has success

    Args:
        args (labels): The arguments are labels
        kwargs (any): data = will pass data the the behavior tasks.

    Returns:
        Promise: A Promise that runs until failure or success
    """        
    return PromiseBehaveSel(*args, **kwargs)

def bt_invert(a_bt_promise):
    """behavior tree invert

    Args:
        a_bt_promise (promise): Invert the success or failure of a behavior promise

    Returns:
        Promise: A Promise that runs until failure or success
    """        
    return PromiseBehaveInvert(a_bt_promise)


def bt_until_success(a_bt_promise):
    """reruns behavior tree until success 
    Behavior promise has a reset() to rerun

    Args:
        a_bt_promise (promise): The promise to run

    Returns:
        Promise: A Promise that runs until success
    """        
    return PromiseBehaveUntil(a_bt_promise, PollResults.BT_SUCCESS)

def bt_until_fail(a_bt_promise):
    """reruns behavior tree until failure
    Behavior promise has a reset() to rerun

    Args:
        a_bt_promise (promise): The promise to run

    Returns:
        Promise: A Promise that runs until failure
    """            
    return PromiseBehaveUntil(a_bt_promise, PollResults.BT_FAIL)

def bt_set_variable(name, value):
    """sets a variable on the blackboard data of a behavior tree

    Args:
        name (str): The variable name to set
        value (any): The value to set
    """            
    task = FrameContext.task
    if task is None:
        return
    main = task.get_variable("BT_PROMISE")
    if main:
        main.set_variable(name, value)

def bt_export_variable(name, value):
    """sets a variable on the main task of a behavior tree

    Args:
        name (str): The variable name to set
        value (any): The value to set
    """            
    task = FrameContext.task
    if task is None:
        return
    main = task.get_variable("BT_TASK")
    if main:
        main.set_variable(name, value)

def bt_get_variable(name, defa_value):
    """sets a variable on the blackboard data of a behavior tree

    Args:
        name (str): The variable name to set
        defa_value (any): The value if the name is not found
    """                
    task = FrameContext.task
    if task is None:
        return None
    main = task.get_variable("BT_PROMISE")
    if main:
        return main.get_variable(name, defa_value)
    return None