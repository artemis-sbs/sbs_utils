from ..mast.mast_node import MastNode, DescribableNode, STRING_REGEX_NAMED, mast_node, IF_EXP_REGEX
from ..mast.core_nodes.decorator_label import DecoratorLabel
from ..mast.core_nodes import Yield
import re


class StateMachineLabel(DecoratorLabel):
    #rule = re.compile(r'@map[ \t]+(?P<path>([\w \t]+))'+IF_EXP_REGEX)
    def __init__(self, name, if_exp=None, loc=None, compile_info=None):
        super().__init__(name, loc)
        self.description = ""
        self.if_exp = if_exp
        # need to negate if
        if self.if_exp is not None:
            self.if_exp = if_exp.strip()
            self.code = compile(self.if_exp, "<string>", "eval")

        self.next = None
        self.loc = loc
        self.replace = None
        self.cmds = []
        # This is a map of specific command type
        self.cmd_map = {}

    def can_fallthrough(self, parent):
        return False
    
    def map_cmd(self, key, cmd):
        cmds = self.cmd_map.get(key, [])
        cmds.append(cmd)
        self.cmd_map[key] = cmds

    def test(self, task):
        #
        # The test is used by UIs etc. to find 
        # things fitting what its looking for
        # e.g. The GUI wants to display missions for fighters
        #
        if self.code is None:
            return True
        return task.eval_code(self.code)

@mast_node(append=False)
class MissionLabel(StateMachineLabel):
    rule = re.compile(r'(@|\/\/)mission/(?P<path>[\/\w]+)[ \t]+'+STRING_REGEX_NAMED("display_name")+IF_EXP_REGEX)

    def __init__(self, path, display_name=None, q=None, if_exp=None, loc=None, compile_info=None):
        # Label stuff
        id = DecoratorLabel.next_label_id()
        name = f"mission/{path}/{id}"
        super().__init__(name, if_exp=if_exp, loc=loc)

        self.path= path
        self.display_name = display_name
        self.next = None
        self.loc = loc
        self.replace = None
        self.cmds = []
        if self.if_exp is not None:
            self.if_exp = if_exp.strip()
            try:
                self.code = compile(self.if_exp, "<string>", "eval")
            except:
                raise Exception(f"Syntax error '{if_exp}'")

    def can_fallthrough(self, parent):
        return False
    
    def test(self, task):
        if self.code is None:
            return True
        return task.eval_code(self.code)

@mast_node()
class StateLabel(DescribableNode):
    is_inline_label = True

    rule = re.compile(r'\&{3}[ \t]*(?P<path>[\/\w]+)([ \t]+'+STRING_REGEX_NAMED("display_name")+')?')
    def __init__(self, path, display_name=None, q=None, loc=None, compile_info=None):
        # Label stuff
        id = DecoratorLabel.next_label_id()
        name = f"state/{path}/{id}"
        super().__init__() #name, loc=loc)

        self.path= path
        self.display_name = display_name
        self.next = None
        self.loc = loc
        self.replace = None
        self.cmds = []
        
    def never_indent(self):
        return True

    def can_fallthrough(self, parent):
        return True
    
    def is_indentable(self):
        return False

    
    def test(self, task):
        if self.code is None:
            return True
        return task.eval_code(self.code)


class Ignore:
    class StateBlock(DescribableNode):
        def __init__(self):
            super().__init__()

        def is_indentable(self):
            return True



    class StartBlock(StateBlock):
        rule = re.compile(r"""start:""")
        def __init__(self, is_end=None, loc=None, compile_info=None):
            super().__init__()
            self.loc = loc
            if  isinstance(compile_info.label, StateMachineLabel):
                pass
            else:
                raise Exception("start block used in unsupported label")
            compile_info.label.map_cmd("start",self)
            
        def create_end_node(self, loc, dedent_obj, compile_info):
            # End should yield success
            cmd = Yield('success', compile_info=compile_info)
            cmd.file_num = self.file_num
            cmd.line_num = self.line_num
            cmd.line = f"yield success embedded in start"
            # Dedent use to skip block inner
            self.dedent_loc = loc+1

            return cmd
        
        def never_indent(self):
            return True


    class InitBlock(StateBlock):
        rule = re.compile(r"""init:""")
        def __init__(self, loc=None, compile_info=None):
            super().__init__()
            self.loc = loc
            if  isinstance(compile_info.label, StateMachineLabel):
                pass
            else:
                raise Exception("init block used in unsupported label")
            compile_info.label.map_cmd("init",self)

            
        def create_end_node(self, loc, dedent_obj, compile_info):
            # End should yield success
            cmd = Yield('success', compile_info=compile_info)
            cmd.file_num = self.file_num
            cmd.line_num = self.line_num
            cmd.line = f"yield success embedded in init"
            # Dedent use to skip block inner
            self.dedent_loc = loc+1

            return cmd



    class AbortBlock(StateBlock):
        rule = re.compile(r"""abort:""")
        def __init__(self, is_end=None, loc=None, compile_info=None):
            super().__init__()
            self.loc = loc
            if  isinstance(compile_info.label, StateMachineLabel):
                pass
            else:
                raise Exception("abort block used in unsupported label")
            compile_info.label.map_cmd("abort",self)

            
        def create_end_node(self, loc, dedent_obj, compile_info):
            # End should yield success
            cmd = Yield('success', compile_info=compile_info)
            cmd.file_num = self.file_num
            cmd.line_num = self.line_num
            cmd.line = f"yield success embedded in abort"
            # Dedent use to skip block inner
            self.dedent_loc = loc+1

            return cmd

    class CompleteBlock(StateBlock):
        rule = re.compile(r"""complete:""")
        def __init__(self, is_end=None, loc=None, compile_info=None):
            super().__init__()
            self.loc = loc
            if  isinstance(compile_info.label, StateMachineLabel):
                pass
            else:
                raise Exception("complete block used in unsupported label")
            compile_info.label.map_cmd("complete",self)

            
        def create_end_node(self, loc, dedent_obj, compile_info):
            # End should yield success
            cmd = Yield('success', compile_info=compile_info)
            cmd.file_num = self.file_num
            cmd.line_num = self.line_num
            cmd.line = f"yield success embedded in complete"
            # Dedent use to skip block inner
            self.dedent_loc = loc+1

            return cmd

    class ObjectiveBlock(StateBlock):
        rule = re.compile(r"""objective\/(?P<name>[\/\w]+)[ \t]+"""+STRING_REGEX_NAMED("display_name")+"""[ \t]*:""")
        def __init__(self, name=None, display_name=None, q=None, loc=None, compile_info=None):
            super().__init__()
            self.loc = loc
            if  isinstance(compile_info.label, StateMachineLabel):
                pass
            else:
                raise Exception("objective block used in unsupported label")
            compile_info.label.map_cmd("objective",self)
            self.display_name = display_name
            self.name = name
            

            
        def create_end_node(self, loc, dedent_obj, compile_info):
            # End should yield fail by default
            cmd = Yield('fail', compile_info=compile_info)
            cmd.file_num = self.file_num
            cmd.line_num = self.line_num
            cmd.line = f"yield fail embedded in objective"
            # Dedent use to skip block inner
            self.dedent_loc = loc+1

            return cmd

