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
        #else:
        #    self.next()
        

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
                data = getattr(label, "data", None)
                if data is not None:
                    label.data = label.data | self.data

                # Need to make sure it is in start state
                # e.g. bt_delay
                label.rewind()
            else:
                self.task_promise = FrameContext.task.start_task(label, self.data)

    def poll(self):
        super().poll()
        if self.current is None:
            self.next()

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
        if self.task_promise and not self.task_promise.done():
            self.task_promise.poll()

        if self.task_promise and self.task_promise.done():
            if self.task_promise.result() == PollResults.BT_SUCCESS:
                self.next()
            else:
                #
                self.set_result(PollResults.BT_FAIL)
                self.run_fail_label()
                return PollResults.OK_RUN_AGAIN
        # if nothing is left then everything succeeded
        if self.current is not None and self.current >= len(self.labels) :
            self.set_result(PollResults.BT_SUCCESS)   
            self.run_success_label()
        return PollResults.OK_RUN_AGAIN
        
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
        self.promise.poll()
        if self.promise.done():
            if self.promise.result() == PollResults.BT_FAIL:
                self.set_result(PollResults.BT_FAIL)       
                return PollResults.BT_FAIL
            else:
                self.set_result(PollResults.BT_SUCCESS)
                return PollResults.BT_SUCCESS


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
        self.promise.poll()
        if self.promise.done():
            if self.promise.result() == self.until_result:
                self.set_result(self.until_result)       
                return self.until_result
            # Will fail on non-bt
            self.promise.rewind()
        return PollResults.OK_RUN_AGAIN


class PromiseBehaveRepeat(PromiseBehave):
    def __init__(self, label_or_promise, count) -> None:
        super().__init__()
        # Expect a promise, assum label otherwise
        self.promise = label_or_promise
        self.count = count
        if not isinstance(label_or_promise, AwaitBlockPromise):
            self.promise = bt_sel(label_or_promise)
                
    def poll(self):
        super().poll()
        if not self.promise.done():
            self.promise.poll()
        if self.promise.done():
            if self.promise.result() != PollResults.BT_SUCCESS:
                self.set_result(self.promise.result())
                return self.promise.result()
            self.count -= 1
            if self.count <=0:
                self.set_result(self.promise.result())
                return self.promise.result()
            # Will fail on non-bt
            self.promise.rewind()
        return PollResults.OK_RUN_AGAIN


def bt_seq(*args, **kwargs):
    """Behavior tree sequence — succeeds only if every child succeeds in order.

    Args:
        *args (label): Labels to run as sequential children.
        data (dict, optional): Keyword argument passed as variables to each
            child task. Defaults to None.

    Returns:
        PromiseBehaveSeq: A promise that resolves when all children succeed,
            or fails as soon as any child fails.
    """
    return PromiseBehaveSeq(*args, **kwargs)

def bt_sel(*args, **kwargs):
    """Behavior tree selector — succeeds as soon as any child succeeds.

    Args:
        *args (label): Labels to run as selector children.
        data (dict, optional): Keyword argument passed as variables to each
            child task. Defaults to None.

    Returns:
        PromiseBehaveSel: A promise that resolves on the first child success,
            or fails if all children fail.
    """
    return PromiseBehaveSel(*args, **kwargs)

def bt_invert(a_bt_promise):
    """Behavior tree inverter — flips the success/failure result of a promise.

    Args:
        a_bt_promise (PromiseBehave | label): Promise or label whose result
            should be inverted.

    Returns:
        PromiseBehaveInvert: A promise that inverts the child result.
    """
    return PromiseBehaveInvert(a_bt_promise)


def bt_until_success(a_bt_promise):
    """Repeat a behavior tree promise until it succeeds.

    Args:
        a_bt_promise (PromiseBehave | label): Promise or label to repeat.

    Returns:
        PromiseBehaveUntil: A promise that keeps rewinding the child until it
            returns ``BT_SUCCESS``.
    """
    return PromiseBehaveUntil(a_bt_promise, PollResults.BT_SUCCESS)

def bt_until_fail(a_bt_promise):
    """Repeat a behavior tree promise until it fails.

    Args:
        a_bt_promise (PromiseBehave | label): Promise or label to repeat.

    Returns:
        PromiseBehaveUntil: A promise that keeps rewinding the child until it
            returns ``BT_FAIL``.
    """
    return PromiseBehaveUntil(a_bt_promise, PollResults.BT_FAIL)

def bt_repeat(a_bt_promise, count):
    """Repeat a behavior tree promise a fixed number of times.

    Args:
        a_bt_promise (PromiseBehave | label): Promise or label to repeat.
        count (int): Maximum number of repetitions.

    Returns:
        PromiseBehaveRepeat: A promise that resolves after ``count`` successful
            iterations or fails if the child fails.
    """
    return PromiseBehaveRepeat(a_bt_promise, count)


def bt_set_variable(name, value):
    """Set a variable on the current behavior tree's blackboard data.

    Args:
        name (str): Variable name.
        value (any): Value to assign.
    """
    task = FrameContext.task
    if task is None:
        return
    main = task.get_variable("BT_PROMISE")
    if main:
        main.set_variable(name, value)

def bt_export_variable(name, value):
    """Export a variable from the behavior tree to the main (root) task's scope.

    Args:
        name (str): Variable name.
        value (any): Value to assign.
    """
    task = FrameContext.task
    if task is None:
        return
    main = task.get_variable("BT_TASK")
    if main:
        main.set_variable(name, value)

def bt_get_variable(name, defa_value=None):
    """Get a variable from the current behavior tree's blackboard data.

    Args:
        name (str): Variable name.
        defa_value (any, optional): Value returned when the variable is absent.
            Defaults to None.

    Returns:
        any: The variable value, or ``defa_value``.
    """
    task = FrameContext.task
    if task is None:
        return None
    main = task.get_variable("BT_PROMISE")
    if main:
        return main.get_variable(name, defa_value)
    return None