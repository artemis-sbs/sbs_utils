from ..mast_node import MastNode, mast_node, BLOCK_START, IF_EXP_REGEX, mast_compile, EVAL_ERROR
import re

# Compile-time counter giving every `for` in every story a distinct pair of runtime keys.
# Only has to be unique within one interpreter; a story reload makes new nodes, and the
# task scopes that would have held old keys are gone with the tasks.
_LOOP_SITE_SEQ = 0


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
    # `name` accepts a comma-separated target list, so `for a, b in enumerate(xs):`
    # unpacks each iteration (see the runtime below). A single name is the common case.
    rule = re.compile(r'(for[ \t]*(?P<name>\w+(?:[ \t]*,[ \t]*\w+)*)[ \t]*)(?P<while_in>in|while)((?P<cond>[^\n\r\f]+))'+BLOCK_START)
    def __init__(self, while_in=None, cond=None, name=None, loc=None, compile_info=None):
        super().__init__()
        if cond:
            cond = cond.lstrip()
            self.code = mast_compile(cond, "eval")
        else:
            self.code = None
        self.name = name
        # Per-loop-SITE keys for the runtime bookkeeping, instead of the bare
        # `<name>__iter` this used to use. Two things went wrong with a name-derived key:
        #
        #  - It is inherited. `task_schedule` copies the caller's scope by default, so a
        #    child running `for p in players:` found the PARENT's `p__iter` already set,
        #    concluded the loop was already running, and kept pulling from the parent's
        #    iterator. Measured in LM: the console leaves `for p in presets:` early via
        #    `jump game_code_reload`, and a map label's `for p in players:` then iterated
        #    game-code PRESETS - `p` came out a dict while `o`, iterating the very same
        #    list one line above, came out a correct id.
        #  - Two loops in one task that happen to share a variable name would collide the
        #    same way. `p`, `i`, `s` and `x` are the most common loop names in the tree.
        #
        # A site-unique key cannot be confused with any other loop's. See the runtime
        # node for `cont_key`, which is what tells a re-entry from a continuation.
        global _LOOP_SITE_SEQ
        _LOOP_SITE_SEQ += 1
        self.iter_key = f"__loop{_LOOP_SITE_SEQ}_{name}__iter"
        self.cont_key = f"__loop{_LOOP_SITE_SEQ}_{name}__cont"
        # Comma target list -> tuple-unpack each iteration; single name -> [name].
        self.targets = [t.strip() for t in name.split(",")] if name else []
        self.is_while = while_in == "while"
        self.loc = loc
        self.end = None
        self.indent = compile_info.indent

    def post_dedent(self,compile_info):
        #
        # This needs to happen after the dedent, indents are all processed
        #
        compile_info.ctx.loop_stack[compile_info.indent] = self
        
        
    def is_indentable(self):
        return True
    
    def must_indent(self):
        return True

    def create_end_node(self, loc, dedent_obj, compile_info):
        end =  LoopEnd(self, loc=loc, compile_info=compile_info)

        loop_stack = compile_info.ctx.loop_stack
        if loop_stack[self.indent] != self:
            raise Exception("For loop indention issue")

        loop_stack[self.indent] = None


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
        loop_stack = compile_info.ctx.loop_stack
        prev_indent = -1
        for (i, obj) in loop_stack.items():
            # Skip anything th
            if i >= compile_info.indent or obj is None:
                continue

            if i > prev_indent:
                prev_indent = i
        if prev_indent >-1:
            self.start = loop_stack.get(prev_indent, None)

        if self.start is None:
            raise Exception("MAST break/continue indention error") 

        self.loc = loc
        if if_exp:
            if_exp = if_exp.lstrip()
            self.if_code = mast_compile(if_exp, "eval")
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
        scoped_cond = task.get_scoped_value(node.iter_key, None, Scope.TEMP)
        # "Am I already running?" used to be inferred from the latch existing, which
        # cannot tell a CONTINUATION from a fresh entry - and a latch outlives a loop
        # that was left early (`jump` out of the body never reaches LoopEnd, so nothing
        # clears it). LoopEnd now says so explicitly: it sets cont_key immediately before
        # jumping back here, and this consumes it. Anything else reaching this node - a
        # first entry, a re-entry after jumping out, a task that merely INHERITED the
        # latch from whoever scheduled it - finds no token and starts the loop over,
        # which is what every one of those cases means.
        continuing = task.get_scoped_value(node.cont_key, None, Scope.TEMP)
        if continuing:
            task.set_value(node.cont_key, None, Scope.TEMP)
        else:
            scoped_cond = None
        # The loop is running if cond
        if scoped_cond is None:
            # set cond to true to show we have initialized
            # setting to -1 to start it will be made 0 in poll
            if node.is_while:
                task.set_value(node.name, -1, Scope.TEMP)
                task.set_value(node.iter_key, True, Scope.TEMP)
            else:
                value = task.eval_code_checked(node.code)
                # The iterable expression raised (already reported). Falling
                # through would do iter(None) and report a second, unrelated
                # TypeError against the same line. The task is already ending.
                if value is EVAL_ERROR:
                    return
                try:
                    _iter = iter(value)
                    task.set_value(node.iter_key, _iter, Scope.TEMP)
                except TypeError:
                    task.set_value(node.iter_key, False, Scope.TEMP)

    def poll(self, mast, task, node:LoopStart):
        # All the time if iterable
        # Value is an index
        current = task.get_scoped_value(node.name, None, Scope.TEMP)
        scoped_cond = task.get_scoped_value(node.iter_key, None, Scope.TEMP)
        if node.is_while:
            current += 1
            task.set_value(node.name, current, Scope.TEMP)
            if node.code:
                value = task.eval_code_checked(node.code)
                if value is EVAL_ERROR:
                    return PollResults.OK_END
                if value == False:
                    inline_label = f"{task.active_label}:{node.name}"
                    # End loop clear value
                    task.set_value(node.name, None, Scope.TEMP)
                    task.set_value(node.iter_key, None, Scope.TEMP)
                    task.jump_in_label(task.active_label, node.dedent_loc)
                    return PollResults.OK_JUMP

            
        elif scoped_cond == False:
            print("Possible badly formed for")
            # End loop clear value
            task.set_value(node.name, None, Scope.TEMP)
            task.set_value(node.iter_key, None, Scope.TEMP)
            task.jump_in_label(task.active_label, node.dedent_loc)
            #task.jump_inline_end(inline_label, False)
            return PollResults.OK_JUMP
        else:
            try:
                current = next(scoped_cond)
                if len(node.targets) > 1:
                    # `for a, b in ...`: unpack this iteration into each target name.
                    _vals = list(current)
                    for _t, _v in zip(node.targets, _vals):
                        task.set_value(_t, _v, Scope.TEMP)
                else:
                    task.set_value(node.name, current, Scope.TEMP)
            except StopIteration:
                # done iterating jump to end
                task.set_value(node.name, None, Scope.TEMP)
                task.set_value(node.iter_key, None, Scope.TEMP)
                task.jump_in_label(task.active_label, node.dedent_loc)
                return PollResults.OK_JUMP
        return PollResults.OK_ADVANCE_TRUE

@mast_runtime_node(LoopEnd)
class LoopEndRuntimeNode(MastRuntimeNode):
    def poll(self, mast, task, node:LoopEnd):
        # Reaching the end of the body is the ONLY thing that means "keep iterating".
        # LoopStart consumes this token; without it, it starts the loop over. That is
        # what makes a `jump` out of the body safe: it never gets here, so the abandoned
        # iterator cannot be resumed later - or inherited by a scheduled task.
        task.set_value(node.start.cont_key, True, Scope.TEMP)
        task.jump_in_label(task.active_label, node.start.loc)
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
            value = task.eval_code_checked(node.if_code)
            if value is EVAL_ERROR:
                return PollResults.OK_END
            if not value:
                return PollResults.OK_ADVANCE_TRUE
            
        if node.op == 'break':
            #task.jump_inline_end(inline_label, True)
            task.set_value(node.start.name, None, self.scope)
            task.set_value(node.start.iter_key, None, Scope.TEMP)
            task.set_value(node.start.cont_key, None, Scope.TEMP)
            task.jump_in_label(task.active_label, node.start.dedent_loc)
            # End loop clear value

            return PollResults.OK_JUMP
        elif node.op == 'continue':
            # `continue` is the other way back to LoopStart, so it owes the same token
            # LoopEnd sets - without it the loop would restart from the top of the
            # iterable instead of advancing, which is an infinite loop, not a slow one.
            task.set_value(node.start.cont_key, True, Scope.TEMP)
            task.jump_in_label(task.active_label, node.start.loc)
            #task.jump_inline_start(inline_label)
            return PollResults.OK_JUMP
        return PollResults.OK_ADVANCE_TRUE
