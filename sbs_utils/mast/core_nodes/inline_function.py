from ..mast import MastNode, mast_node
import re


from ..pollresults import PollResults
from ..mast_runtime_node import MastRuntimeNode, mast_runtime_node
from ...futures import Promise
class MastAsyncTask:
    pass    



CLOSE_FUNC = r"\)[ \t]*(?=\r\n|\n|\#)"
@mast_node()
class FuncCommand(MastNode):
    rule = re.compile(r'(?P<is_await>await\s+)?(?P<py_cmds>[\w\.]+\s*\([^\n\r\f]+[ \t]*(?=\r\n|\n|\#))')
    def __init__(self, is_await=None, py_cmds=None, loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        self.is_await = is_await != None
        if py_cmds:
            py_cmds= py_cmds.lstrip()
            self.code = compile(py_cmds, "<string>", "eval")

@mast_runtime_node(FuncCommand)
class FuncCommandRuntimeNode(MastRuntimeNode):
    def enter(self, mast, task:MastAsyncTask, node:FuncCommand):
        self.is_await = node.is_await
        value = task.eval_code(node.code)
        self.promise = None
        if isinstance(value, Promise):
            self.promise = value

    def poll(self, mast, task:MastAsyncTask, node:FuncCommand):
        if not node.is_await:
            return PollResults.OK_ADVANCE_TRUE
    
        if self.promise:
            res = self.promise.poll()
            if res == PollResults.OK_JUMP:
                return PollResults.OK_JUMP

            if self.promise.done():
                return PollResults.OK_ADVANCE_TRUE
            else:
                return PollResults.OK_RUN_AGAIN

        value = task.eval_code(node.code)
        if value:
            return PollResults.OK_ADVANCE_TRUE

        return PollResults.OK_RUN_AGAIN    
