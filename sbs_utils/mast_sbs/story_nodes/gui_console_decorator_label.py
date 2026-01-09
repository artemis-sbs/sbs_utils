from ...mast.mast_node import IF_EXP_REGEX, STRING_REGEX_NAMED, mast_node
from ...mast.core_nodes.decorator_label import DecoratorLabel
from ...mast.core_nodes.inline_function import FuncCommand
import re




@mast_node(append=False)
class GuiConsoleDecoratorLabel(DecoratorLabel):
    rule = re.compile(r'(@|//)console/(?P<path>([\w]+))(?P<priority>([ \t]*!\d+))?(?P<weight>([ \t]*\^\d+))?[ \t]+'+STRING_REGEX_NAMED("display_name")+IF_EXP_REGEX)

    def __init__(self, path, display_name, weight=None,priority=None,
                 if_exp=None, loc=None, 
                 compile_info=None, q=None):
        # Label stuff
        from ...procedural.gui import gui_add_console_type
        id = DecoratorLabel.next_label_id()
        self.label_weight = id
        name = f"console/{path}/{id}"
        super().__init__(name, loc)

        self.path= path
        self.display_name = display_name

        self.raw_weight = 101
        if weight is not None:
            try:
                weight = weight.strip()
                weight = weight[1:]
                self.raw_weight = int(weight)
            except:
                self.raw_weight = 101
        self.priority = 100
        if priority is not None:
            try:
                priority  = priority.strip()
                priority  = priority[1:]
                self.priority  = int(priority)
            except:
                self.priority  = 101

        
        gui_add_console_type(path, display_name, None, self)

        self.code = None
        if if_exp is not None:
            if_exp = if_exp.strip()
            try:
                self.code = compile(if_exp, "<string>", "eval")
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

    def generate_label_begin_cmds(self, compile_info=None):
        #
        # Set the active tab
        # 
        cmd = FuncCommand(py_cmds=f'gui_tab_activate("{self.path}, {self.path}")', compile_info=compile_info)
        cmd.file_num = self.file_num
        cmd.line_num = self.line_num
        cmd.line = f"gui_tab_activate {self.name}"
        self.add_child(cmd)

    def test(self, task):
        if self.code is None:
            return True
        return task.eval_code(self.code)

