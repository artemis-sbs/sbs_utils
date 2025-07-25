from ..mast_node import MastNode, mast_node, BLOCK_START
import re



@mast_node()
class OnSignal(MastNode):
    rule = re.compile(r"on[ \t]+signal[ \t]+(?P<signal>\w+)"+BLOCK_START)
    stack = []
    def __init__(self, end=None, signal=None, loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        self.is_end = False
        self.signal = signal
        self.label = None
        if compile_info is not None:
            self.label = compile_info.label
        self.end_node = None

        if end is not None:
            OnSignal.stack[-1].end_node = self
            self.is_end = True
            OnSignal.stack.pop()
        else:
            OnSignal.stack.append(self)

    def is_indentable(self):
        return True
    
    def mus_indent(self):
        return True

    def create_end_node(self, loc, dedent_obj, compile_info):
        """ cascade the dedent up to the start"""
        self.dedent_loc = loc
        end = OnSignal("on_end", loc = loc)
        end.dedent_loc = loc+1
        return end
    
    @classmethod
    def parse(cls, lines):
        return super().parse(lines)
    
from ..pollresults import PollResults
from ..mast_runtime_node import MastRuntimeNode, mast_runtime_node
from ..mast import Scope
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..mast import Mast
    from ..mastscheduler import MastAsyncTask



@mast_runtime_node(OnSignal)
class OnSignalRuntimeNode(MastRuntimeNode):
    #
    # TODO: This needs to be gui transient
    # needs to also register on the task not any subtasks
    #
    def enter(self, mast:'Mast', task:'MastAsyncTask', node: OnSignal):
        from ...procedural.signal import signal_register
        if not node.is_end:
            signal_register(node.signal, node.label, False, task, node.loc+1, False)


    def poll(self, mast:'Mast', task:'MastAsyncTask', node: OnSignal):
        if node.end_node:
            task.jump(node.label, node.dedent_loc+1)
            return PollResults.OK_JUMP
        return PollResults.OK_RUN_AGAIN


