from ..mast import MastNode, mast_node, ParseData
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
        



