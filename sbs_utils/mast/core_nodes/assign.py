from ..mast_node import MastNode, mast_node, Scope, MULTI_LINE_STRING_REGEX
from ..mast_runtime_node import MastRuntimeNode, mast_runtime_node
from ..pollresults import PollResults
from ...futures import Promise
from ..mast_globals import MastGlobals
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

        if lhs in MastGlobals.globals:
            raise Exception(f"Variable assignment to a keyword {lhs}")

class MastAsyncTask:
    pass

@mast_runtime_node(Assign)
class AssignRuntimeNode(MastRuntimeNode):
    def __init__(self) -> None:
        super().__init__()
        self.promise = None

    def poll(self, mast, task:MastAsyncTask, node:Assign):
        #try:
        if not self.promise:
            value = task.eval_code(node.code)
            if node.is_await and isinstance(value, Promise):
                self.promise = value
            elif isinstance(value, str):
                value = task.compile_and_format_string(value)
            
        if self.promise:
            self.promise.poll()
            # The assumes the promise is a task
            if self.promise.done():
                value = self.promise.result()
            else:
                return PollResults.OK_RUN_AGAIN
            
        start = None
        if node.oper != Assign.EQUALS or node.is_default:
            # Value should be set by here
            if "." in node.lhs or "[" in node.lhs:
                start = task.eval_code(f"""{node.lhs}""")
            else:
                start = task.get_variable(node.lhs, (None,))
                if node.is_default and start!= (None,): 
                    return PollResults.OK_ADVANCE_TRUE     

        match node.oper:
            case Assign.EQUALS:
                pass
            case Assign.INC:
                value = start + value
            case Assign.DEC:
                value = start - value
            case Assign.MUL:
                value = start * value
            case Assign.MOD:
                value = start % value
            case Assign.DIV:
                value = start / value
            case Assign.INT_DIV:
                value = start // value

        if "." in node.lhs or "[" in node.lhs:
            task.exec_code(f"""{node.lhs} = __mast_value""",{"__mast_value": value}, None )
            
        elif node.scope: 
            task.set_value(node.lhs, value, node.scope)
        else:
            task.set_value_keep_scope(node.lhs, value)
            
        # except:
        #     task.main.runtime_error(f"assignment error {node.lhs}")
        #     return PollResults.OK_END

        return PollResults.OK_ADVANCE_TRUE
