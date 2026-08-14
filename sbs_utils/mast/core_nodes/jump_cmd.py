from ..mast_node import MastNode, mast_node, BLOCK_START, OPT_DATA_REGEX, IF_EXP_REGEX, mast_compile, EVAL_ERROR
import re


    
@mast_node()
class Jump(MastNode):
    #rule = re.compile(r"""(((?P<jump>jump|->|push|->>|popjump|<<->|poppush|<<->>)[ \t]*(?P<jump_name>\w+))|(?P<pop>pop|<<-))"""+OPT_ARGS_REGEX+IF_EXP_REGEX)
    # The `jump` keyword MUST be followed by whitespace before the label, so an
    # identifier that merely starts with the letters "jump" (e.g. `jump_ship = ...`)
    # is NOT swallowed as a jump statement. `->` keeps zero-or-more space so `->END`
    # (and `-> main`) still parse. (Old `(jump|->)[ \t]*` used `*` for both, which let
    # `jump` eat any `jump`-prefixed identifier - an engine-only misparse the mock
    # never flagged.) No valid script breaks: `jump foo` is always written with a space.
    rule = re.compile(r"""(?P<jump>jump[ \t]+|->[ \t]*)(?P<jump_name>\w+)"""+OPT_DATA_REGEX+IF_EXP_REGEX)
    def __init__(self, pop=None, jump=None, jump_name=None, if_exp=None, data=None, loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        self.label = jump_name
        if if_exp:
            if_exp = if_exp.lstrip()
            self.if_code = mast_compile(if_exp, "eval")
        else:
            self.if_code = None
        self.data = data
        if data is not None:
            data = data.lstrip()
            self.data = mast_compile(data, "eval")

from ..pollresults import PollResults
from ..mast_runtime_node import MastRuntimeNode, mast_runtime_node
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..mast import Mast
    from ..mastscheduler import MastAsyncTask
   

@mast_runtime_node(Jump)
class JumpRuntimeNode(MastRuntimeNode):
    def poll(self, mast:'Mast', task:'MastAsyncTask', node:Jump):
        if node.if_code:
            value = task.eval_code_checked(node.if_code)
            # A test that raised is not a test that said "don't jump".
            if value is EVAL_ERROR:
                return PollResults.OK_END
            if not value:
                return PollResults.OK_ADVANCE_TRUE
        
        task.jump(node.label)
        return PollResults.OK_JUMP



