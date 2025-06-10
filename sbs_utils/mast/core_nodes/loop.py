from ..mast_node import MastNode, mast_node, BLOCK_START, IF_EXP_REGEX
import re


class LoopEnd(MastNode):
    """
    LoopEnd is a node that is injected to allow loops to know where the end is
    """
    #rule = re.compile(r'((?P<loop>next)[ \t]*(?P<name>\w+))')
    def __init__(self, start=None, name=None,loc=None, compile_info=None):
        super().__init__()
        self.start = start
        self.loc = loc
        self.start.end = self
        

@mast_node()
class LoopStart(MastNode):
    rule = re.compile(r'(for[ \t]*(?P<name>\w+)[ \t]*)(?P<while_in>in|while)((?P<cond>[^\n\r\f]+))'+BLOCK_START)
    loop_stack = {}
    def __init__(self, while_in=None, cond=None, name=None, loc=None, compile_info=None):
        super().__init__()
        if cond:
            cond = cond.lstrip()
            self.code = compile(cond, "<string>", "eval")
        else:
            self.code = None
        self.name = name
        self.is_while = while_in == "while"
        self.loc = loc
        self.end = None
        self.indent = compile_info.indent

    def post_dedent(self,compile_info):
        #
        # This needs to happen after the dedent, indents are all processed
        #
        LoopStart.loop_stack[compile_info.indent] =self
        
        
    def is_indentable(self):
        return True
    
    def must_indent(self):
        return True

    def create_end_node(self, loc, dedent_obj, compile_info):
        end =  LoopEnd(self, loc=loc, compile_info=compile_info)

        # if dedent_obj.__class__ == LoopStart:
        #     LoopStart.loop_stack.pop()
        #     LoopStart.loop_stack.pop()
        #     LoopStart.loop_stack.append(dedent_obj)
        # else:
        #     LoopStart.loop_stack.pop()
        if LoopStart.loop_stack[self.indent] != self:
            raise Exception("For loop indention issue")
        
        LoopStart.loop_stack[self.indent] = None


        # Dedent is one passed the end node
        self.dedent_loc = loc+1
        return end
        
@mast_node()
class LoopBreak(MastNode):

    #rule = re.compile(r'(?P<op>break|continue)\s*(?P<name>\w+)')
    rule = re.compile(r'(?P<op>break|continue)'+IF_EXP_REGEX)
    def __init__(self, op=None, name=None, if_exp=None, loc=None, compile_info=None):
        super().__init__()
        self.name = name
        self.op = op

        # Find the right for loop
        prev_indent = -1
        for (i, obj) in LoopStart.loop_stack.items():
            # Skip anything th
            if i >= compile_info.indent or obj is None:
                continue

            if i > prev_indent:
                prev_indent = i
        if prev_indent >-1:
            self.start = LoopStart.loop_stack.get(prev_indent, None)

        if self.start is None:
            raise Exception("MAST break/continue indention error") 

        self.loc = loc
        if if_exp:
            if_exp = if_exp.lstrip()
            self.if_code = compile(if_exp, "<string>", "eval")
        else:
            self.if_code = None

from ..pollresults import PollResults
from ..mast_runtime_node import MastRuntimeNode, mast_runtime_node
from ..mast import Scope
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..mast import Mast
    from ..mastscheduler import MastAsyncTask

@mast_runtime_node(LoopStart)
class LoopStartRuntimeNode(MastRuntimeNode):
    def enter(self, mast, task:'MastAsyncTask', node:LoopStart):
        #scoped_val = task.get_scoped_value(node.name, Scope.TEMP, None)
        scoped_cond = task.get_scoped_value(node.name+"__iter", None, Scope.TEMP)
        # The loop is running if cond
        if scoped_cond is None:
            # set cond to true to show we have initialized
            # setting to -1 to start it will be made 0 in poll
            if node.is_while:
                task.set_value(node.name, -1, Scope.TEMP)
                task.set_value(node.name+"__iter", True, Scope.TEMP)
            else:
                value = task.eval_code(node.code)
                try:
                    _iter = iter(value)
                    task.set_value(node.name+"__iter", _iter, Scope.TEMP)
                except TypeError:
                    task.set_value(node.name+"__iter", False, Scope.TEMP)

    def poll(self, mast, task, node:LoopStart):
        # All the time if iterable
        # Value is an index
        current = task.get_scoped_value(node.name, None, Scope.TEMP)
        scoped_cond = task.get_scoped_value(node.name+"__iter", None, Scope.TEMP)
        if node.is_while:
            current += 1
            task.set_value(node.name, current, Scope.TEMP)
            if node.code:
                value = task.eval_code(node.code)
                if value == False:
                    inline_label = f"{task.active_label}:{node.name}"
                    # End loop clear value
                    task.set_value(node.name, None, Scope.TEMP)
                    task.set_value(node.name+"__iter", None, Scope.TEMP)
                    task.jump(task.active_label, node.dedent_loc)
                    return PollResults.OK_JUMP

            
        elif scoped_cond == False:
            print("Possible badly formed for")
            # End loop clear value
            task.set_value(node.name, None, Scope.TEMP)
            task.set_value(node.name+"__iter", None, Scope.TEMP)
            task.jump(task.active_label, node.dedent_loc)
            #task.jump_inline_end(inline_label, False)
            return PollResults.OK_JUMP
        else:
            try:
                current = next(scoped_cond)
                task.set_value(node.name, current, Scope.TEMP)
            except StopIteration:
                # done iterating jump to end
                task.set_value(node.name, None, Scope.TEMP)
                task.set_value(node.name+"__iter", None, Scope.TEMP)
                task.jump(task.active_label, node.dedent_loc)
                return PollResults.OK_JUMP
        return PollResults.OK_ADVANCE_TRUE

@mast_runtime_node(LoopEnd)
class LoopEndRuntimeNode(MastRuntimeNode):
    def poll(self, mast, task, node:LoopEnd):
        task.jump(task.active_label, node.start.loc)
        return PollResults.OK_JUMP
        # return PollResults.OK_ADVANCE_TRUE

@mast_runtime_node(LoopBreak)
class LoopBreakRuntimeNode(MastRuntimeNode):
    def enter(self, mast, task:'MastAsyncTask', node:LoopBreak):
        scoped_val = task.get_value(node.start.name, None)
        index = scoped_val[0]
        scope = scoped_val[1]
        if index is None:
            scope = Scope.TEMP
        self.scope = scope

    def poll(self, mast, task, node:LoopBreak):
        if node.if_code:
            value = task.eval_code(node.if_code)
            if not value:
                return PollResults.OK_ADVANCE_TRUE
            
        if node.op == 'break':
            #task.jump_inline_end(inline_label, True)
            task.set_value(node.start.name, None, self.scope)
            task.set_value(node.start.name+"__iter", None, Scope.TEMP)
            task.jump(task.active_label, node.start.dedent_loc)
            # End loop clear value
            
            return PollResults.OK_JUMP
        elif node.op == 'continue':
            task.jump(task.active_label, node.start.loc)
            #task.jump_inline_start(inline_label)
            return PollResults.OK_JUMP
        return PollResults.OK_ADVANCE_TRUE
