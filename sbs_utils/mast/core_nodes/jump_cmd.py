from ..mast import MastNode, mast_node, BLOCK_START, OPT_DATA_REGEX, IF_EXP_REGEX
import re


    
@mast_node()
class Jump(MastNode):
    #rule = re.compile(r"""(((?P<jump>jump|->|push|->>|popjump|<<->|poppush|<<->>)[ \t]*(?P<jump_name>\w+))|(?P<pop>pop|<<-))"""+OPT_ARGS_REGEX+IF_EXP_REGEX)
    rule = re.compile(r"""(?P<jump>jump|->)[ \t]*(?P<jump_name>\w+)"""+OPT_DATA_REGEX+IF_EXP_REGEX)
    def __init__(self, pop=None, jump=None, jump_name=None, if_exp=None, data=None, loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        self.label = jump_name
        if if_exp:
            if_exp = if_exp.lstrip()
            self.if_code = compile(if_exp, "<string>", "eval")
        else:
            self.if_code = None
        self.data = data
        if data is not None:
            data = data.lstrip()
            self.data = compile(data, "<string>", "eval")

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
            value = task.eval_code(node.if_code)
            if not value:
                return PollResults.OK_ADVANCE_TRUE
        
        task.jump(node.label)
        return PollResults.OK_JUMP



