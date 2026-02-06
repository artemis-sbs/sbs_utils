from ...mast.mast_node import mast_node, IF_EXP_REGEX
import re
from ...mast.core_nodes.decorator_label import DecoratorLabel
from ...mast.core_nodes.yield_cmd import Yield
from ...mast.core_nodes.inline_function import FuncCommand

import ast

@mast_node(append=False)
class SignalRouteDecoratorLabel(DecoratorLabel):
    rule = re.compile(r'//(?P<shared>shared/)?signal/(?P<path>(\w[\w\/]*))'+IF_EXP_REGEX)
    def __init__(self, path, shared=None, if_exp=None, loc=None, compile_info=None):
        # Label stuff
        id = DecoratorLabel.next_label_id()
        path = path.strip('/')
        name = f"__route__{path}__{id}__" 
        super().__init__(name, loc)

        self.label_weight = id
        self.path= path
        self.shared = shared
        self.if_exp = if_exp
        # need to negate if
        if self.if_exp is not None:
            self.if_exp = if_exp.strip()
            # Strip comments and catch syntax errors
            self.if_exp =  ast.unparse(ast.parse(self.if_exp))
            self.if_exp = f'not ({self.if_exp})'

        self.next = None
        self.loc = loc
        self.replace = None
        self.cmds = []

    def can_fallthrough(self, p):
        return False

    def generate_label_begin_cmds(self, compile_info=None):
        front_cmds = []
        main_cmds = []

        if self.if_exp:
            cmd = Yield('fail', if_exp=self.if_exp, loc=0, compile_info=compile_info)
            cmd.file_num = self.file_num
            cmd.line_num = self.line_num
            cmd.line = f"yield fail {self.path} entry test {self.if_exp}"
            front_cmds.append(cmd)

        if self.shared: 
            #
            # This needs to run 
            # on the first run of main
            #
            cmd = FuncCommand(py_cmds=f'signal_register("{self.path}", "{self.name}", True)', compile_info=compile_info)
            cmd.file_num = self.file_num
            cmd.line_num = self.line_num
            cmd.line = f"signal_register in main for {self.name}"
            main_cmds.append(cmd)
        else: 
            #
            # This needs to run 
            # on the first run of main
            #
            cmd = FuncCommand(py_cmds=f'signal_register("{self.path}", "{self.name}", False)', compile_info=compile_info)
            cmd.file_num = self.file_num
            cmd.line_num = self.line_num
            cmd.line = f"signal_register in main for {self.name}"
            main_cmds.append(cmd)
    
        for cmd in front_cmds:
            self.add_child(cmd)

        # Add any commands need to main
        for cmd in main_cmds:
            compile_info.main.add_child(cmd)


    def generate_label_end_cmds(self, compile_info=None):
        path = self.path.strip('/')
        #paths = path.split('/')

        p = compile_info.label if compile_info is not None else None
        if not self.can_fallthrough(p):
            # Always have a yield                    
            cmd = Yield('success', compile_info=compile_info)
            cmd.file_num = self.file_num
            cmd.line_num = self.line_num
            cmd.line = f"yield success at end of {self.name}"
            self.add_child(cmd)

# @mast_node(append=False)
# class SharedSignalRouteDecoratorLabel(RouteDecoratorLabel):
#     rule = re.compile(r'//shared/signal/(?P<path>(\w[\w\/]*))'+IF_EXP_REGEX)
#     def __init__(self,path, if_exp=None, loc=None, compile_info=None):
#         super().__init__(f"shared/signal/{path}", if_exp, loc, compile_info)

# @mast_node(append=False)
# class SignalRouteDecoratorLabel(RouteDecoratorLabel):
#     rule = re.compile(r'//signal/(?P<path>(\w[\w\/]*))'+IF_EXP_REGEX)
#     def __init__(self,path, if_exp=None, loc=None, compile_info=None):
#         super().__init__(f"signal/{path}", if_exp, loc, compile_info)
                              