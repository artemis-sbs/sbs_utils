from ..mast_node import MastNode, mast_node, BLOCK_START, ParseData
import re



class WithEnd(MastNode):
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
class WithStart(MastNode):
    rule = re.compile(r'(with[ \t]*(?P<obj>[^\n\r\f]+))')
    with_vars = 0
    def __init__(self, obj=None, name=None, loc=None, compile_info=None):
        super().__init__()
        if obj:
            self.code = compile(obj, "<string>", "eval")
        else:
            self.code = None
        self.name = name
        self.with_name = f"__WITH_{WithStart.with_vars}"
        WithStart.with_vars += 1

        self.loc = loc
        self.end = None
        
    def is_indentable(self):
        return True
    
    @classmethod
    def parse(cls, lines):
        mo = cls.rule.match(lines)
        if mo:
            span = mo.span()
            data = mo.groupdict()
            obj= data.get("obj")
            if obj is None:
                return None
            obj = obj.strip()

            if not obj.endswith(":"):
                return None
            obj = obj[:-1]
            obj = obj.strip()
            
            has_as = obj.rsplit(" as ")
            if len(has_as)==2:
                data["name"] = has_as[1]
                data["obj"] = has_as[0]
            elif len(has_as)!=1:
                return None
            else:
                data["obj"] = obj

            return ParseData(span[0], span[1], data)
        else:
            return None


    def create_end_node(self, loc, _,  compile_info):
        end =  WithEnd(self, loc=loc)
        # Dedent is one passed the end node
        self.dedent_loc = loc+1
        return end
   
from ..pollresults import PollResults
from ..mast_runtime_node import MastRuntimeNode, mast_runtime_node
from ..mast import Scope
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..mast import Mast
    from ..mastscheduler import MastAsyncTask

@mast_runtime_node(WithStart)
class WithStartRuntimeNode(MastRuntimeNode):
    def poll(self, mast, task, node:WithStart):
        value = task.eval_code(node.code)
        if value is None:
            return PollResults.OK_ADVANCE_TRUE
        
        if node.name is not None:
            task.set_value(node.name, value, Scope.NORMAL)
        task.set_value(node.with_name, value, Scope.NORMAL)

        if not hasattr(value, '__enter__'):
            return PollResults.OK_ADVANCE_TRUE
        value.__enter__()
        
        return PollResults.OK_ADVANCE_TRUE
    
    
@mast_runtime_node(WithEnd)
class WithEndRuntimeNode(MastRuntimeNode):
    def poll(self, mast, task, node:WithEnd):
        value = task.get_variable(node.start.with_name)
        if value is None:
            return PollResults.OK_ADVANCE_TRUE
        if not hasattr(value, '__exit__'):
            return PollResults.OK_ADVANCE_TRUE
        value.__exit__()
        # In case then WithEnd runs again?
        #task.set_variable(node.start.with_name, None)
        return PollResults.OK_ADVANCE_TRUE


