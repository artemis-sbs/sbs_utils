from sbs_utils.futures import AwaitBlockPromise
from sbs_utils.futures import Promise
from sbs_utils.helpers import FrameContext
from sbs_utils.mast.pollresults import PollResults
def bt_export_variable (name, value):
    """sets a variable on the main task of a behavior tree
    
    Args:
        name (str): The variable name to set
        value (any): The value to set"""
def bt_get_variable (name, defa_value=None):
    """sets a variable on the blackboard data of a behavior tree
    
    Args:
        name (str): The variable name to set
        defa_value (any): The value if the name is not found"""
def bt_invert (a_bt_promise):
    """behavior tree invert
    
    Args:
        a_bt_promise (promise): Invert the success or failure of a behavior promise
    
    Returns:
        Promise: A Promise that runs until failure or success"""
def bt_repeat (a_bt_promise, count):
    """reruns behavior tree a number of times
    Behavior promise has a reset() to rerun
    
    Args:
        a_bt_promise (promise): The promise to run
    
    Returns:
        Promise: A Promise that runs until success"""
def bt_sel (*args, **kwargs):
    """behavior tree select returns success if any task has success
    
    Args:
        args (labels): The arguments are labels
        kwargs (any): data = will pass data the the behavior tasks.
    
    Returns:
        Promise: A Promise that runs until failure or success"""
def bt_seq (*args, **kwargs):
    """behavior tree sequence only returns success if the whole sequence has success
    
    Args:
        args (labels): The arguments are labels
        kwargs (any): data = will pass data the the behavior tasks.
    
    Returns:
        Promise: A Promise that runs until failure or success"""
def bt_set_variable (name, value):
    """sets a variable on the blackboard data of a behavior tree
    
    Args:
        name (str): The variable name to set
        value (any): The value to set"""
def bt_until_fail (a_bt_promise):
    """reruns behavior tree until failure
    Behavior promise has a reset() to rerun
    
    Args:
        a_bt_promise (promise): The promise to run
    
    Returns:
        Promise: A Promise that runs until failure"""
def bt_until_success (a_bt_promise):
    """reruns behavior tree until success
    Behavior promise has a reset() to rerun
    
    Args:
        a_bt_promise (promise): The promise to run
    
    Returns:
        Promise: A Promise that runs until success"""
class PromiseBehave(AwaitBlockPromise):
    """class PromiseBehave"""
    def __init__ (self, *args, **kwargs) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def initial_poll (self):
        ...
    def rewind (self):
        ...
    def run_fail_label (self):
        ...
    def run_success_label (self):
        ...
class PromiseBehaveInvert(PromiseBehave):
    """class PromiseBehaveInvert"""
    def __init__ (self, label_or_promise) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def poll (self):
        ...
class PromiseBehaveRepeat(PromiseBehave):
    """class PromiseBehaveRepeat"""
    def __init__ (self, label_or_promise, count) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def poll (self):
        ...
class PromiseBehaveSel(PromiseBehaveSeqSel):
    """class PromiseBehaveSel"""
    def __init__ (self, *args, **kwargs) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def poll (self):
        ...
class PromiseBehaveSeq(PromiseBehaveSeqSel):
    """class PromiseBehaveSeq"""
    def poll (self):
        ...
class PromiseBehaveSeqSel(PromiseBehave):
    """class PromiseBehaveSeqSel"""
    def __init__ (self, *args, **kwargs) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def export_variable (self, name, value):
        ...
    def get_variable (self, name, defa_value):
        ...
    def next (self):
        ...
    def poll (self):
        ...
    def rewind (self):
        ...
    def set_variable (self, name, value):
        ...
class PromiseBehaveUntil(PromiseBehave):
    """class PromiseBehaveUntil"""
    def __init__ (self, label_or_promise, until_result=<PollResults.OK_END: 99>) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def poll (self):
        ...
