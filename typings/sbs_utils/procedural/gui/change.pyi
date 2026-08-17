from sbs_utils.helpers import FrameContext
from sbs_utils.futures import Trigger
def gui_change (code, label):
    """Register a per-tick change watch on a Python expression.
    
    Evaluates ``code`` each tick and executes ``label`` when its value differs
    from the previous tick. Python equivalent of the MAST ``on change``
    construct. The trigger is attached to the current task and runs for as long
    as the task is active.
    
    Args:
        code (str): Python expression to evaluate each tick, e.g.
            ``"ship_speed > 100"``.
        label: MAST label or inline block to execute when the value changes.
    
    Example:
        gui_change("shield_level", shield_warning)
        ///shield_warning
            gui_text("Shields changed!")"""
def mast_compile (source, mode='eval', filename=None):
    """``compile()`` for MAST expressions, with the source kept for tracebacks.
    
    Compiling against the shared ``"<string>"`` filename leaves Python with no
    source for the frame, so ``traceback.extract_tb`` reports the offending line
    as ``None`` - which is exactly the useless report a MAST author sees today.
    Compiling against a unique pseudo-filename and registering the text in
    ``linecache`` makes every traceback (eval and ``~~`` exec alike) print the
    real expression, and lets eval_code quote the WHOLE expression even when the
    deepest frame is inside some library function.
    
    An ``mtime`` of ``None`` in the linecache tuple is the documented "loaded by
    a __loader__" form: ``linecache.checkcache`` skips those, so the entry is
    never invalidated out from under us."""
class ChangeTrigger(Trigger):
    """class ChangeTrigger"""
    def __init__ (self, task, node, label=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def run (self):
        ...
    def test (self):
        ...
