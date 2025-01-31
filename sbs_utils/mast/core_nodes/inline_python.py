from ..mast_node  import MastNode, mast_node
import re

from ...agent import Agent
from ..pollresults import PollResults
from ..mast_runtime_node import MastRuntimeNode, mast_runtime_node
class MastAsyncTask:
    pass

@mast_node()
class PyCode(MastNode):
    rule = re.compile(r'((\~{2,})\n?(?P<py_cmds>[\s\S]+?)\n?(\~{2,}))')

    def __init__(self, py_cmds=None, loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        if py_cmds:
            py_cmds= py_cmds.lstrip()
            self.code = compile(py_cmds, "<string>", "exec")

@mast_runtime_node(PyCode)
class PyCodeRuntimeNode(MastRuntimeNode):
    def poll(self, mast, task:MastAsyncTask, node:PyCode):
        def export(cls):
            add_to = task.main.inventory.collections
            def decorator(*args, **kwargs):
                # if 'task' in inspect.signature(cls).parameters:
                #     kwargs['task'] = task
                #add_to[cls.__name__] = cls
                return cls(*args, **kwargs)
            add_to[cls.__name__] = decorator
            return decorator

        def export_var(name, value, shared=False):
            if shared:
                #
                #task.main.mast.vars[name] = value
                Agent.SHARED.set_inventory_value(name, value, None)
            else:
                # task.main.vars[name] = value
                task.main.set_inventory_value(name, value, None)
        task.exec_code(node.code,{"export": export, "export_var": export_var}, None )
        return PollResults.OK_ADVANCE_TRUE
