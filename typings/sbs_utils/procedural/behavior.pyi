from sbs_utils.futures import AwaitBlockPromise
from sbs_utils.futures import Promise
from sbs_utils.helpers import FrameContext
from sbs_utils.mast.pollresults import PollResults
def bt_export_variable (name, value):
    """Export a variable from the behavior tree to the main (root) task's scope.
    
    Args:
        name (str): Variable name.
        value (any): Value to assign."""
def bt_get_variable (name, defa_value=None):
    """Get a variable from the current behavior tree's blackboard data.
    
    Args:
        name (str): Variable name.
        defa_value (any, optional): Value returned when the variable is absent.
            Defaults to None.
    
    Returns:
        any: The variable value, or ``defa_value``."""
def bt_invert (a_bt_promise):
    """Behavior tree inverter — flips the success/failure result of a promise.
    
    Args:
        a_bt_promise (PromiseBehave | label): Promise or label whose result
            should be inverted.
    
    Returns:
        PromiseBehaveInvert: A promise that inverts the child result."""
def bt_repeat (a_bt_promise, count):
    """Repeat a behavior tree promise a fixed number of times.
    
    Args:
        a_bt_promise (PromiseBehave | label): Promise or label to repeat.
        count (int): Maximum number of repetitions.
    
    Returns:
        PromiseBehaveRepeat: A promise that resolves after ``count`` successful
            iterations or fails if the child fails."""
def bt_sel (*args, **kwargs):
    """Behavior tree selector — succeeds as soon as any child succeeds.
    
    Args:
        *args (label): Labels to run as selector children.
        data (dict, optional): Keyword argument passed as variables to each
            child task. Defaults to None.
    
    Returns:
        PromiseBehaveSel: A promise that resolves on the first child success,
            or fails if all children fail."""
def bt_seq (*args, **kwargs):
    """Behavior tree sequence — succeeds only if every child succeeds in order.
    
    Args:
        *args (label): Labels to run as sequential children.
        data (dict, optional): Keyword argument passed as variables to each
            child task. Defaults to None.
    
    Returns:
        PromiseBehaveSeq: A promise that resolves when all children succeed,
            or fails as soon as any child fails."""
def bt_set_variable (name, value):
    """Set a variable on the current behavior tree's blackboard data.
    
    Args:
        name (str): Variable name.
        value (any): Value to assign."""
def bt_until_fail (a_bt_promise):
    """Repeat a behavior tree promise until it fails.
    
    Args:
        a_bt_promise (PromiseBehave | label): Promise or label to repeat.
    
    Returns:
        PromiseBehaveUntil: A promise that keeps rewinding the child until it
            returns ``BT_FAIL``."""
def bt_until_success (a_bt_promise):
    """Repeat a behavior tree promise until it succeeds.
    
    Args:
        a_bt_promise (PromiseBehave | label): Promise or label to repeat.
    
    Returns:
        PromiseBehaveUntil: A promise that keeps rewinding the child until it
            returns ``BT_SUCCESS``."""
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
