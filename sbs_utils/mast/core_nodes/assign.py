from ..mast_node import MastNode, mast_node, Scope, MULTI_LINE_STRING_REGEX, mast_compile, EVAL_ERROR
from ..mast_runtime_node import MastRuntimeNode, mast_runtime_node
from ..pollresults import PollResults
from ...futures import Promise
from ..mast_globals import MastGlobals
import re


PY_EXP_REGEX = r"""((?P<py>~~)[\s\S]*?(?P=py))"""
YAML_EXP_REGEX = r"""((?P<yaml>```)\s*yaml\s*[\s\S]*?(?P=yaml))"""
    
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
        r'(?P<is_default>(default[ \t]+))?(?P<scope>(shared|assigned|client|temp)\s+)?(?P<lhs>.*?)\s*(?P<oper>=|\+=|-=|\*=|%=|/=|//=)(?P<a_wait>\s*await)?\s*(?P<exp>('+PY_EXP_REGEX+'|'+MULTI_LINE_STRING_REGEX+'|'+YAML_EXP_REGEX+'|[^\n\r\f]+))')
        
        #r'(?P<scope>(shared|assigned|client|temp)\s+)?(?P<lhs>[\w\.\[\]]+)\s*(?P<oper>=|\+=|-=|\*=|%=|/=|//=)(?P<a_wait>\s*await)?\s*(?P<exp>('+PY_EXP_REGEX+'|'+STRING_REGEX+'|[^\n\r\f]+))')

    """Tuple unpacking (`a, b = expr`) IS supported for plain comma-separated names
    (see AssignRuntimeNode._set_value); a target carrying `.`/`[` in the tuple falls
    through to exec. `for a, b in ...` is handled separately by the Loop node."""
    def __init__(self, is_default, scope, lhs, oper, exp,a_wait=None,  quote=None, py=None, yaml=None,loc=None, compile_info=None):
        super().__init__()
        self.lhs = lhs
        self.loc = loc
        self.oper = Assign.oper_map.get(oper)
        self.is_default = is_default
        self.scope = None if scope is None else Scope[scope.strip().upper()]
        
        exp = exp.lstrip()
        if quote:
            exp = 'f'+exp        
        if py:
            exp = exp[2:-2]
            exp = exp.strip()
        
        self.yaml = None
        if yaml:
            self.yaml = exp.strip('`')
            self.yaml = self.yaml.strip()
            self.yaml = self.yaml[4:]
            self.yaml = self.yaml.strip()
            self.code = None
        else:
            self.code = mast_compile(exp, "eval")
        self.is_await = a_wait is not None
        
                
        # A hard assignment to a global/keyword is an error, but a `default` (set only
        # if unset) to one is a legitimate fallback - e.g. `default elite_get_all_abilities
        # = None` in debug.mast, so the var exists even when that module isn't imported.
        # It also keeps an in-process recompile working: a default that precedes the
        # import which registers the name no longer errors just because the name is still
        # a global from the prior compile.
        if lhs in MastGlobals.globals and not self.is_default:
            raise Exception(f"Variable assignment to a keyword {lhs}")

class MastAsyncTask:
    pass

@mast_runtime_node(Assign)
class AssignRuntimeNode(MastRuntimeNode):
    def __init__(self) -> None:
        super().__init__()
        self.promise = None

    def _set_value(self, value, node, task):
        # Tuple unpacking: `a, b = expr` binds each plain name (mimics Python), using
        # the same per-name write-back as a normal assignment. Only engages when every
        # target is a bare name (no `.`/`[`); a mixed/attr/subscript tuple falls through
        # to the exec path below. MAST vars live in task inventory, so we bind by name -
        # not via exec (whose locals dict is thrown away).
        if "," in node.lhs:
            parts = [p.strip() for p in node.lhs.split(",")]
            if len(parts) > 1 and all(p and "." not in p and "[" not in p for p in parts):
                vals = list(value)
                if len(vals) != len(parts):
                    raise Exception(
                        f"tuple unpack '{node.lhs}': expected {len(parts)} values, got {len(vals)}")
                for name, val in zip(parts, vals):
                    if node.scope:
                        task.set_value(name, val, node.scope)
                    else:
                        task.set_value_keep_scope(name, val)
                return
        if "." in node.lhs or "[" in node.lhs:
            task.exec_code(f"""{node.lhs} = __mast_value""",{"__mast_value": value}, None )
        elif node.scope:
            task.set_value(node.lhs, value, node.scope)
        else:
            task.set_value_keep_scope(node.lhs, value)

    def poll(self, mast, task:MastAsyncTask, node:Assign):
        #try:
        if node.yaml is not None:
            value = task.compile_and_format_string(node.yaml)
            if node.oper != Assign.EQUALS:
                raise Exception(f"Assign for yaml only support = not {node.oper}")

            try:
                from ... import yaml
                value = yaml.safe_load(value)
                self._set_value(value, node, task)

            except Exception as e:
                raise Exception(f"Invalid yaml expression\n{e}")
            return PollResults.OK_ADVANCE_TRUE

        if not self.promise:
            value = task.eval_code_checked(node.code)
            # The expression blew up (already reported). Assigning its "value"
            # would put None in the variable - and a `shared` one is None for
            # every other task from here on, which is how one bad expression
            # turns into a pile of unrelated errors elsewhere.
            if value is EVAL_ERROR:
                return PollResults.OK_END
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
                start = task.eval_code_checked(f"""{node.lhs}""")
                if start is EVAL_ERROR:
                    return PollResults.OK_END
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

        self._set_value(value, node, task)
            
        # except:
        #     task.main.runtime_error(f"assignment error {node.lhs}")
        #     return PollResults.OK_END

        return PollResults.OK_ADVANCE_TRUE
