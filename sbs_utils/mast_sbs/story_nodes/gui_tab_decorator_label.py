from ...mast.mast_node import IF_EXP_REGEX, mast_node
from ...mast.core_nodes.decorator_label import DecoratorLabel
import re
from ...agent import Agent

@mast_node(append=False)
class GuiTabDecoratorLabel(DecoratorLabel):
    rule = re.compile(r'(\/\/)gui/tab/(?P<path>([\w]+))'+IF_EXP_REGEX)

    all = {}

    def __init__(self, path, if_exp=None, loc=None, compile_info=None):
        # Label stuff
        id = DecoratorLabel.next_label_id()
        self.label_weight = id
        name = f"gui/tab/{path}/{id}"
        super().__init__(name, loc)

        self.path= path
        self.description = ""
        self.if_exp = if_exp

        GuiTabDecoratorLabel.all[path] = self
  
        # need to negate if
        self.code = None
        if self.if_exp is not None:
            self.if_exp = if_exp.strip()
            try:
                self.code = compile(self.if_exp, "<string>", "eval")
            except:
                raise Exception(f"Syntax error '{if_exp}'")
            
        self.next = None
        self.loc = loc
        self.replace = None
        self.cmds = []

    def can_fallthrough(self, parent):
        return False
    
    def generate_label_end_cmds(self, compile_info=None):
        # Allow this to follow into === labels
        pass
    
    def test(self, task):
        if self.code is None:
            return True
        return task.eval_code(self.code)

