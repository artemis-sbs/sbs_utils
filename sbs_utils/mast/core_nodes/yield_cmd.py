from ..mast_node import MastNode, mast_node, ParseData
from ..mast_runtime_node import MastRuntimeNode, mast_runtime_node
from ..pollresults import PollResults
import re


    


@mast_node()
class Yield(MastNode):
    rule = re.compile(r'(->|yield[ \t])[ \t]*(?P<res>(FAIL|fail|SUCCESS|success|END|end|IDLE|idle|RESULT|result))(?P<exp>[^\n\r\f]+)?')
    def __init__(self, res= None, exp=None, if_exp=None, loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        self.result = res.lower()
        self.code = exp
        if exp is not None:
            exp = exp.lstrip()
            self.code = compile(exp, "<string>", "eval")
            #self.result  = "code"

        if if_exp:
            if_exp = if_exp.lstrip()
            self.if_code = compile(if_exp, "<string>", "eval")
        else:
            self.if_code = None

    @classmethod
    def parse(cls, lines):
        mo = cls.rule.match(lines)
        if not mo:
            return None
        span = mo.span()
        data = mo.groupdict()
        # res= data.get("res")
        obj= data.get("exp")
        if obj is not None:
            obj = obj.lstrip()
            is_if = obj.startswith("if ")

            has_if = obj.rsplit(" if ")
            if len(has_if)==2:
                data["if_exp"] = has_if[1]
                data["exp"] = has_if[0]
            elif is_if:
                data["exp"] = None
                data["if_exp"] = obj[3:]

        return ParseData(span[0], span[1], data)
        


@mast_runtime_node(Yield)
class YieldRuntimeNode(MastRuntimeNode):
    def poll(self, mast, task, node:Yield):
        if node.if_code:
            value = task.eval_code(node.if_code)
            if not value:
                return PollResults.OK_ADVANCE_TRUE
        if node.code is not None:
            value = task.eval_code(node.code)
            task.yield_results = value
        if node.result.lower() == 'fail':
            return PollResults.FAIL_END
        if node.result.lower() == 'success':
            return PollResults.OK_END
        if node.result.lower() == 'end':
            return PollResults.OK_END
        if node.result.lower() == 'idle':
            return PollResults.OK_IDLE
        if node.result.lower() == 'result':
            return PollResults.OK_YIELD
        print("GONE ASTRAY")
        return PollResults.OK_RUN_AGAIN
