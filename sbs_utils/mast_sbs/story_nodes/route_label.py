from ...mast.mast_node import mast_node, IF_EXP_REGEX
import re
from ...mast.core_nodes.decorator_label import DecoratorLabel
from ...mast.core_nodes.yield_cmd import Yield
from ...procedural import routes 
from ...mast.core_nodes.inline_function import FuncCommand


@mast_node(append=False)
class RouteDecoratorLabel(DecoratorLabel):
    rule = re.compile(r'//(?P<path>(\w[\w\/]*))'+IF_EXP_REGEX)

    def __init__(self, path, if_exp=None, loc=None, compile_info=None):
        # Label stuff
        id = DecoratorLabel.next_label_id()
        name = f"__route__{path}__{id}__" 
        super().__init__(name, loc)

        self.path= path
        self.if_exp = if_exp
        # need to negate if
        if self.if_exp is not None:
            self.if_exp = if_exp.strip()
            self.if_exp = f'not ({self.if_exp})'

        self.next = None
        self.loc = loc
        self.replace = None
        self.cmds = []

    def can_fallthrough(self, p):
        return False

    def generate_label_begin_cmds(self, compile_info=None):

        path = self.path.strip('/')
        paths = path.split('/')
        front_cmds = []
        main_cmds = []

        if self.if_exp:
            cmd = Yield('success', if_exp=self.if_exp, loc=0, compile_info=compile_info)
            cmd.file_num = self.file_num
            cmd.line_num = self.line_num
            cmd.line = f"yield success {self.path} entry test {self.if_exp}"
            front_cmds.append(cmd)

        match paths:
            # two parameters, nav
            case ["comms",*b]: 
                routes.route_comms_navigate(self.path, self)
            case ["enable","comms"]: 
                # Just another spawn handler is disguise
                routes.route_select_comms(self)
            case ["enable","grid","comms"]: 
                # Just another spawn handler is disguise
                routes.route_select_grid(self)
            case ["science",*b]: 
                routes.route_science_navigate(self.path, self)
            case ["enable","science"]: 
                # Just another spawn handler is disguise
                routes.route_select_science(self)
                # messages can occur first with science
                # routes.route_message_science(self)
            case ["gui",*b]: 
                routes.route_gui_navigate(self.path, self)
            case ["spawn"]: 
                routes.route_spawn(self)
            case ["spawn", "grid"]: 
                routes.route_spawn_grid(self)
            case ["focus", "comms"]: 
                routes.route_focus_comms(self)
            case ["focus", "comms2d"]: 
                routes.route_focus_comms_2d(self)
            case ["focus", "normal"]: 
                routes.route_focus_normal(self)
            case ["focus", "weapons"]: 
                routes.route_focus_weapons(self)
            case ["focus", "science"]: 
                routes.route_focus_science(self)
            case ["focus", "grid"]: 
                routes.route_focus_grid(self)
            case ["select", "comms"]: 
                routes.route_select_comms(self)
            case ["select", "comms2d"]: 
                routes.route_select_comms_2d(self)                
            case ["select", "normal"]: 
                routes.route_select_normal(self)                
            case ["select", "weapons"]: 
                routes.route_select_weapons(self)
            case ["select", "science"]: 
                routes.route_select_science(self)
            case ["select", "grid"]: 
                routes.route_select_grid(self)
            case ["object", "grid"]: 
                routes.route_object_grid(self)
            case ["point", "comms2d"]: 
                routes.route_point_comms_2d(self)                
            case ["point", "normal"]: 
                routes.route_point_normal(self)                
            case ["point", "comms"]: 
                routes.route_point_comms(self)
            case ["point", "weapons"]: 
                routes.route_point_weapons(self)
            case ["point", "science"]: 
                routes.route_point_science(self)
            case ["point", "grid"]: 
                routes.route_point_grid(self)
            case ["collision", "passive"]: 
                routes.route_collision_passive(self)
            case ["collision", "interactive"]: 
                routes.route_collision_interactive(self)
            case ["console", "change"]: 
                routes.route_change_console(self)
            case ["console", "mainscreen", "change"]: 
                routes.route_console_mainscreen_change(self)
            case ["damage", "internal"]: 
                routes.route_damage_internal(self)
            case ["damage", "heat"]: 
                routes.route_damage_heat(self)
            case ["damage", "object"]: 
                routes.route_damage_object(self)
            case ["damage","destroy"]: 
                routes.route_damage_destroy(self)
            case ["damage","killed"]: 
                routes.route_damage_killed(self)
            case ["dock", "hangar"]: 
                routes.route_dock_hangar(self)
            case ["shared", "signal", *b]: 
                #
                # This needs to run 
                # on the first run of main
                #
                cmd = FuncCommand(py_cmds=f'signal_register("{paths[2]}", "{self.name}", True)', compile_info=compile_info)
                cmd.file_num = self.file_num
                cmd.line_num = self.line_num
                cmd.line = f"signal_register in main for {self.name}"
                main_cmds.append(cmd)
            case ["signal", *b]: 
                #
                # This needs to run 
                # on the first run of main
                #
                cmd = FuncCommand(py_cmds=f'signal_register("{paths[1]}", "{self.name}", False)', compile_info=compile_info)
                cmd.file_num = self.file_num
                cmd.line_num = self.line_num
                cmd.line = f"signal_register in main for {self.name}"
                main_cmds.append(cmd)
            
            case _:
                raise Exception(f"Invalid route label {self.path}")
    
        for cmd in front_cmds:
            self.add_child(cmd)

        # Add any commands need to main
        for cmd in main_cmds:
            compile_info.main.add_child(cmd)


    def generate_label_end_cmds(self, compile_info=None):
        path = self.path.strip('/')
        paths = path.split('/')
        match paths:
            # two parameters, nav
            case ["enable", "comms"]: 
                cmd = FuncCommand(is_await=True, py_cmds='comms()', compile_info=compile_info)
                cmd.file_num = self.file_num
                cmd.line_num = self.line_num
                cmd.line = f"await comms() embedded in {self.name}"
                self.add_child(cmd)
            case ["enable", "grid", "comms"]: 
                cmd = FuncCommand(is_await=True, py_cmds='comms()', compile_info=compile_info)
                cmd.file_num = self.file_num
                cmd.line_num = self.line_num
                cmd.line = f"await comms() embedded in {self.name}"
                self.add_child(cmd)
            case ["enable", "science"]: 
                cmd = FuncCommand(is_await=True, py_cmds='scan()', compile_info=compile_info)
                cmd.file_num = self.file_num
                cmd.line_num = self.line_num
                cmd.line = f"await scan() embedded in {self.name}"
                self.add_child(cmd)

        p = compile_info.label if compile_info is not None else None
        if not self.can_fallthrough(p):
            # Always have a yield                    
            cmd = Yield('success', compile_info=compile_info)
            cmd.file_num = self.file_num
            cmd.line_num = self.line_num
            cmd.line = f"yield success at end of {self.name}"
            self.add_child(cmd)

