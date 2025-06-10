from ..mast_node import MastNode, mast_node, BLOCK_START
from .await_cmd import Await
import re



@mast_node()
class OnChange(MastNode):
    rule = re.compile(r"on[ \t]+(change[ \t]+)?(?P<val>[^:]+)"+BLOCK_START)
    stack = []
    def __init__(self, end=None, val=None, loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        self.value = val
        if val:
            self.value = compile(val, "<string>", "eval")

        self.is_end = False
        #
        # Check to see if this is embedded in an await
        #
        self.await_node = None
        if len(Await.stack) >0:
            self.await_node = Await.stack[-1]
        self.end_node = None

        if end is not None:
            OnChange.stack[-1].end_node = self
            self.is_end = True
            OnChange.stack.pop()
        else:
            OnChange.stack.append(self)

    def is_indentable(self):
        return True
    
    def mus_indent(self):
        return True

    def create_end_node(self, loc, dedent_obj, compile_info):
        """ cascade the dedent up to the start"""
        self.dedent_loc = loc
        end = OnChange("on_end", loc = loc)
        end.dedent_loc = loc+1
        return end

   
from ..pollresults import PollResults
from ..mast_runtime_node import MastRuntimeNode, mast_runtime_node
from ..mast import Scope
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..mast import Mast
    from ..mastscheduler import MastAsyncTask

from ...futures import Trigger

@mast_runtime_node(OnChange)
class OnChangeRuntimeNode(MastRuntimeNode):
    def enter(self, mast:'Mast', task:'MastAsyncTask', node: OnChange):
        self.task = task
        self.node = node
        self.is_running = False
        self.node_label = self.task.active_label
        if not node.is_end:
            self.value = task.eval_code(node.value)
            # Triggers handle things themselves
            if not isinstance(self.value, Trigger):  
                task.queue_on_change(self)
            # If the label is set don't override it
            # Python must have set it
            else:
                self.value.loc = node.loc+1
                self.value.label = task.active_label

            # TODO
            # Hmmm A little leakage that it uses PAGE
            # Move this to Task>
            #

    def test(self):
        prev = self.value
        self.is_running = False
        self.value = self.task.eval_code(self.node.value) 
        return prev!=self.value
    
    def run(self):
        self.is_running = True
        self.task.push_inline_block(self.node_label, self.node.loc+1)
        self.task.tick_in_context()

    def dequeue(self):
        pass

    def poll(self, mast:'Mast', task:'MastAsyncTask', node: OnChange):
        if node.is_end and self.is_running:
            self.task.pop_label(False)
            self.is_running = False
            # This is run again intentionally
            # The change aspect is done, no need to run anything 
            # again for this fork of the task 
            #
            return PollResults.OK_RUN_AGAIN
        if node.end_node:
            self.task.jump(self.node_label, node.dedent_loc+1)
            return PollResults.OK_JUMP
        return PollResults.OK_RUN_AGAIN


