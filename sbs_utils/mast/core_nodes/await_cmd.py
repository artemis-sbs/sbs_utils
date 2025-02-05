from ..mast_node  import MastNode, mast_node, BLOCK_START
import re


@mast_node()
class Await(MastNode):
    """
    waits for an existing or a new 'task' to run in parallel
    this needs to be a rule before Parallel
    """
    stack = []
    rule = re.compile(r"""await[ \t]+(until[ \t]+(?P<until>\w+)[ \t]+)?(?P<if_exp>[^:\n\r\f]+)"""+BLOCK_START)
    def __init__(self, until=None, if_exp=None, is_end = None, loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        self.end_await_node = None
        self.inlines = None
        self.buttons = None
        self.until = until

        #####self.timeout_label = None
        self.on_change = None
        self.fail_label = None
        self.is_end = is_end
        if self.is_end is None:
            self.inlines = []
            self.buttons = []
            Await.stack.append(self)
        else:
            Await.stack[-1].end_await_node = self

        if if_exp:
            if_exp = if_exp.lstrip()
            self.code = compile(if_exp, "<string>", "eval")
        else:
            self.code = None

    def add_inline(self, inline_data):
        self.inlines.append(inline_data)

    def is_indentable(self):
        return True
    
    def create_end_node(self, loc, dedent_obj, compile_info):
        self.dedent_loc = loc
        end = Await(is_end=True, loc = loc)
        end.dedent_loc = loc+1
        return end

@mast_node()
class AwaitInlineLabel(MastNode):
    rule = re.compile(r"\=(?P<val>[^:\n\r\f]+)"+BLOCK_START)
    def __init__(self, val=None, loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        self.inline = val
        self.await_node = Await.stack[-1]
        Await.stack[-1].add_inline(self)

    def is_indentable(self):
        return True
    def never_indent(self):
        return False


    def create_end_node(self, loc, dedent_obj, compile_info):
        """ cascade the dedent up to the start"""
        self.dedent_loc = loc+1
        
   
from ..pollresults import PollResults
from ..mast_runtime_node import MastRuntimeNode, mast_runtime_node
from ..mast import Scope
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..mast import Mast
    from ..mastscheduler import MastAsyncTask
from ...futures import Promise

@mast_runtime_node(Await)
class AwaitRuntimeNode(MastRuntimeNode):
    def leave(self, mast:'Mast', task:'MastAsyncTask', node: Await):
        if self.promise is not None:
            self.promise.cancel("Canceled by Await leave")
    
    def enter(self, mast:'Mast', task:'MastAsyncTask', node: Await):
        self.promise = None
        if node.is_end:
            return
        value = task.eval_code(node.code)
        if isinstance(value, Promise):
            self.promise = value
            self.promise.inlines = node.inlines
            self.promise.buttons = node.buttons

        
    def poll(self, mast:'Mast', task:'MastAsyncTask', node: Await):
        if node.is_end:
            task.jump(task.active_label, node.dedent_loc)
            return PollResults.OK_JUMP
        
      
        if self.promise:
            res = self.promise.poll()
            if res == PollResults.OK_JUMP:
                return PollResults.OK_JUMP
            
            if self.promise.done():
                task.jump(task.active_label, node.dedent_loc)
                return PollResults.OK_JUMP
            else:
                return PollResults.OK_RUN_AGAIN
        
        value = task.eval_code(node.code)
        if value:
            task.jump(task.active_label, node.dedent_loc)
            return PollResults.OK_JUMP

      

        return PollResults.OK_RUN_AGAIN

@mast_runtime_node(AwaitInlineLabel)
class AwaitInlineLabelRuntimeNode(MastRuntimeNode):
    def leave(self, mast:'Mast', task:'MastAsyncTask', node: AwaitInlineLabel):
        print("INline Await leave")

    def enter(self, mast:'Mast', task:'MastAsyncTask', node: AwaitInlineLabel):
        self.node_label = self.task.active_label
    def poll(self, mast:'Mast', task:'MastAsyncTask', node: AwaitInlineLabel):
        if node.await_node:
            task.jump(self.node_label, node.await_node.end_await_node.dedent_loc)
            #task.jump(task.active_label,node.await_node.loc)
            return PollResults.OK_JUMP
        return PollResults.OK_ADVANCE_TRUE
