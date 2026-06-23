from ..mast_node import MastNode, mast_node, BLOCK_START
import re



@mast_node()
class OnSignal(MastNode):
    rule = re.compile(r"on[ \t]+signal[ \t]+(?P<signal>\w+)"+BLOCK_START)
    def __init__(self, end=None, signal=None, loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        self.is_end = False
        self.signal = signal
        self.label = None
        if compile_info is not None:
            self.label = compile_info.label
        self.end_node = None

        on_signal_stack = compile_info.ctx.on_signal_stack
        if end is not None:
            on_signal_stack[-1].end_node = self
            self.is_end = True
            on_signal_stack.pop()
        else:
            on_signal_stack.append(self)

    def is_indentable(self):
        return True
    
    def mus_indent(self):
        return True

    def create_end_node(self, loc, dedent_obj, compile_info):
        """ cascade the dedent up to the start"""
        self.dedent_loc = loc
        end = OnSignal("on_end", loc = loc, compile_info=compile_info)
        end.dedent_loc = loc+1
        return end
    
    @classmethod
    def parse(cls, src, pos=0):
        return super().parse(src, pos)
    
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


