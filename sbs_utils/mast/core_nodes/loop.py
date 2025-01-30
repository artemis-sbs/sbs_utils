from ..mast import MastNode, mast_node, BLOCK_START, IF_EXP_REGEX
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

