from ..mast import MastNode, mast_node, Scope, Mast,  MULTI_LINE_STRING_REGEX
import re


PY_EXP_REGEX = r"""((?P<py>~~)[\s\S]*?(?P=py))"""
    
@mast_node()
class Assign(MastNode):
    EQUALS = 1
    INC=2
    DEC = 3
    MUL = 4
    MOD = 5
    DIV=6
    INT_DIV = 7
    oper_map = {"=": EQUALS, "+=": INC,  "-=": DEC, "*=": MUL, "%=": MOD, "/=": DIV, "//=":INT_DIV }
    # '|'+STRING_REGEX+ddd
    # (.*?)(\+=|-=)(.*)?(#\n)?
    rule = re.compile(
        r'(?P<is_default>(default[ \t]+))?(?P<scope>(shared|assigned|client|temp)\s+)?(?P<lhs>.*?)\s*(?P<oper>=|\+=|-=|\*=|%=|/=|//=)(?P<a_wait>\s*await)?\s*(?P<exp>('+PY_EXP_REGEX+'|'+MULTI_LINE_STRING_REGEX+'|[^\n\r\f]+))')
        
        #r'(?P<scope>(shared|assigned|client|temp)\s+)?(?P<lhs>[\w\.\[\]]+)\s*(?P<oper>=|\+=|-=|\*=|%=|/=|//=)(?P<a_wait>\s*await)?\s*(?P<exp>('+PY_EXP_REGEX+'|'+STRING_REGEX+'|[^\n\r\f]+))')

    """ Note this doesn't support destructuring. To do so isn't worth the effort"""
    def __init__(self, is_default, scope, lhs, oper, exp,a_wait=None,  quote=None, py=None, loc=None, compile_info=None):
        super().__init__()
        self.lhs = lhs
        self.loc = loc
        self.oper = Assign.oper_map.get(oper)
        self.is_default = is_default
        self.scope = None if scope is None else Scope[scope.strip(
        ).upper()]
        
        #print(f"quote: {quote}")
        exp = exp.lstrip()
        if quote:
            exp = 'f'+exp        
        if py:
            exp = exp[2:-2]
            exp = exp.strip()
        self.code = compile(exp, "<string>", "eval")
        self.is_await = a_wait is not None

        if lhs in Mast.globals:
            raise Exception(f"Variable assignment to a keyword {lhs}")



