from ...helpers import FrameContext
from ...futures import Trigger
import re

class ChangeTrigger(Trigger):
    rule = re.compile(r"change[ \t]+(?P<val>.+)")
    def __init__(self, task, node, label=None):
        self.task = task
        if isinstance(node, str):
            val = node
            node = None
        else:
            match_obj = ChangeTrigger.rule.match(node.inline)
            val = None
            if match_obj:
                data = match_obj.groupdict()
                val = data['val']

        if val is None:
            self.value = False
            self.code = compile("True", "<string>", "eval")
        else:
            self.code = compile(val, "<string>", "eval")
            self.value = self.task.eval_code(self.code) 

        # What to jump to one past the inline node
        self.node = node
        
        if label is None:
            self.label = task.active_label
        else:
            self.label = label

    def test(self):
        prev = self.value
        self.value = self.task.eval_code(self.code) 
        return prev!=self.value
    
    def run(self):
        loc = 0
        if self.node:
            loc = self.node.loc + 1
        self.task.push_inline_block(self.label, loc)
        self.task.tick_in_context()

def gui_change(code, label):
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
            gui_text("Shields changed!")
    """

    task = FrameContext.task
    page = FrameContext.page
    if task is None:
        return
    if page is None:
        return

    handler = ChangeTrigger(task, code, label)
    task.queue_on_change(handler)


