from ..mast_node import MastNode, mast_node, BLOCK_START, mast_compile, EVAL_ERROR
import re


@mast_node()
class Await(MastNode):
    """
    waits for an existing or a new 'task' to run in parallel
    this needs to be a rule before Parallel
    """
    # if_exp is lazy (`+?`) and allows colons so a `:` inside a quoted string
    # isn't mistaken for the block-start colon (BLOCK_START requires the colon be
    # at end-of-line). Matches the `if`/`on` rules. e.g. await foo("x:y"):
    rule = re.compile(r"""await[ \t]+(until[ \t]+(?P<until>\w+)[ \t]+)?(?P<if_exp>[ \t\S]+?)"""+BLOCK_START)
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
        await_stack = compile_info.ctx.await_stack
        if self.is_end is None:
            self.inlines = []
            self.buttons = []
            await_stack.append(self)
        else:
            # The end node is only ever built by create_end_node on an await that
            # IS on the stack, so an empty stack here means the stack was corrupted
            # -- historically by an unbalanced block earlier in the file. Say that,
            # rather than letting a bare IndexError surface as "list index out of
            # range" against a line that is not the cause (LM #124).
            if not await_stack:
                raise Exception(
                    "'await' block end with no matching open 'await'. The await "
                    "stack is unbalanced -- check the indentation of the "
                    "'await ...:' block this line is meant to close.")
            await_stack[-1].end_await_node = self
            await_stack.pop()


        if if_exp:
            if_exp = if_exp.lstrip()
            self.code = mast_compile(if_exp, "eval")
        else:
            self.code = None

    def add_inline(self, inline_data):
        self.inlines.append(inline_data)

    def is_indentable(self):
        return True
    
    def create_end_node(self, loc, dedent_obj, compile_info):
        self.dedent_loc = loc
        end = Await(is_end=True, loc = loc, compile_info=compile_info)
        end.dedent_loc = loc+1
        return end

@mast_node()
class AwaitInlineLabel(MastNode):
    # val is lazy + allows colons so a `:` in a quoted string isn't taken for
    # the block-start colon (see Await above).
    rule = re.compile(r"\=(?P<val>[ \t\S]+?)"+BLOCK_START)
    def __init__(self, val=None, loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        self.inline = val
        await_stack = compile_info.ctx.await_stack
        # An '=' inline label only means something inside an await block -- it is
        # how `await` names a branch to resume at. Written outside one (or after a
        # block whose indentation left the stack unbalanced) this used to raise a
        # bare IndexError, reported against THIS line with no hint that the real
        # fault is the await above it (LM #124).
        if not await_stack:
            raise Exception(
                f"'={val}:' inline label has no open 'await' block. An '=' inline "
                "label must be indented inside an 'await ...:' block; an await "
                "block left unbalanced earlier in the label is the usual cause.")
        self.await_node = await_stack[-1]
        await_stack[-1].add_inline(self)

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
        value = task.eval_code_checked(node.code)
        if value is EVAL_ERROR:
            return
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
        
        value = task.eval_code_checked(node.code)
        if value is EVAL_ERROR:
            return PollResults.OK_END
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
