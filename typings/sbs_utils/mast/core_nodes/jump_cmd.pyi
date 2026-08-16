from sbs_utils.mast.mast_node import MastNode
from sbs_utils.mast.mast_runtime_node import MastRuntimeNode
from sbs_utils.mast.pollresults import PollResults
def mast_compile (source, mode='eval', filename=None):
    """``compile()`` for MAST expressions, with the source kept for tracebacks.
    
    Compiling against the shared ``"<string>"`` filename leaves Python with no
    source for the frame, so ``traceback.extract_tb`` reports the offending line
    as ``None`` - which is exactly the useless report a MAST author sees today.
    Compiling against a unique pseudo-filename and registering the text in
    ``linecache`` makes every traceback (eval and ``~~`` exec alike) print the
    real expression, and lets eval_code quote the WHOLE expression even when the
    deepest frame is inside some library function.
    
    An ``mtime`` of ``None`` in the linecache tuple is the documented "loaded by
    a __loader__" form: ``linecache.checkcache`` skips those, so the entry is
    never invalidated out from under us."""
def mast_node (append=True):
    ...
def mast_runtime_node (parser_node):
    ...
class Jump(MastNode):
    """class Jump"""
    def __init__ (self, pop=None, jump=None, jump_name=None, if_exp=None, data=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (src, pos=0):
        ...
class JumpRuntimeNode(MastRuntimeNode):
    """class JumpRuntimeNode"""
    def poll (self, mast: 'Mast', task: 'MastAsyncTask', node: sbs_utils.mast.core_nodes.jump_cmd.Jump):
        ...
