from ...mast.mast_node import mast_node, IF_EXP_REGEX
import re
from ...mast.core_nodes.decorator_label import DecoratorLabel
from ...mast.core_nodes.yield_cmd import Yield
from ...procedural import routes 
from ...mast.core_nodes.inline_function import FuncCommand
import ast

@mast_node(append=False)
class RouteDecoratorLabel(DecoratorLabel):
    rule = re.compile(r'//(?P<path>(\w[\w\/]*))'+IF_EXP_REGEX)
    def __init__(self, path, if_exp=None, loc=None, compile_info=None):
        # Label stuff
        id = DecoratorLabel.next_label_id()
        path = path.strip('/')
        name = f"__route__{path}__{id}__" 
        super().__init__(name, loc)

        self.label_weight = id
        self.path= path
        self.if_exp = if_exp
        # need to negate if
        if self.if_exp is not None:
            self.if_exp = if_exp.strip()
            self.if_exp =  ast.unparse(ast.parse(self.if_exp))
            #tree = ast.parse(self.if_exp, mode='single')
            self.if_exp = f'not ({self.if_exp})'
            # This may cause an exception

            # Unparse the AST back into code (without comments)
            
            compile(self.if_exp, "<string>", "eval")

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
            cmd = Yield('fail', if_exp=self.if_exp, loc=0, compile_info=compile_info)
            cmd.file_num = self.file_num
            cmd.line_num = self.line_num
            cmd.line = f"yield fail {self.path} entry test {self.if_exp}"
            front_cmds.append(cmd)

        match paths:
            # two parameters, nav
            case ["popup",*b]: 
                routes.route_common_navigate(path, self)
            case ["comms",*b]: 
                routes.route_comms_navigate(self.path, self)
            case ["enable","comms"]: 
                # Just another spawn handler is disguise
                #routes.route_select_comms(self)
                pass
            case ["enable","grid","comms"]: 
                # Just another spawn handler is disguise
                #routes.route_select_grid(self)
                pass
            case ["science"]: 
                routes.route_science_navigate(self.path, self)
            case ["enable","science"]: 
                # Just another spawn handler is disguise
                #routes.route_select_science(self)
                pass
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
        #paths = path.split('/')

        p = compile_info.label if compile_info is not None else None
        if not self.can_fallthrough(p):
            # Always have a yield                    
            cmd = Yield('success', compile_info=compile_info)
            cmd.file_num = self.file_num
            cmd.line_num = self.line_num
            cmd.line = f"yield success at end of {self.name}"
            self.add_child(cmd)
#
#
# I tried to have separate nodes for this, but the performance hit 
# add about 0.05 to 0.07 seconds to legendary mot a big deal, but is it worth it?
# Keeping the code around incase the compexity of the syntax requires them 
#

# @mast_node(append=False)
# class CommsRouteDecoratorLabel(RouteDecoratorLabel):
#     rule = re.compile(r'//comms(?P<path>([\w\/]*))'+IF_EXP_REGEX)
#     def __init__(self,path, if_exp=None, loc=None, compile_info=None):
#         if path is None:
#             path = ""
#         if path.startswith('/'):
#             path = path[1:]

#         super().__init__(f"comms/{path}", if_exp, loc, compile_info)


# @mast_node(append=False)
# class EnableCommsRouteDecoratorLabel(RouteDecoratorLabel):
#     rule = re.compile(r'//enable/comms'+IF_EXP_REGEX)
#     def __init__(self, if_exp=None, loc=None, compile_info=None):
#         super().__init__(f"enable/comms", if_exp, loc, compile_info)

# @mast_node(append=False)
# class EnableGridCommsRouteDecoratorLabel(RouteDecoratorLabel):
#     rule = re.compile(r'//enable/grid/comms'+IF_EXP_REGEX)
#     def __init__(self, if_exp=None, loc=None, compile_info=None):
#         super().__init__(f"enable/grid/comms", if_exp, loc, compile_info)

# @mast_node(append=False)
# class EnableScienceRouteDecoratorLabel(RouteDecoratorLabel):
#     rule = re.compile(r'//enable/science'+IF_EXP_REGEX)
#     def __init__(self, if_exp=None, loc=None, compile_info=None):
#         super().__init__(f"enable/science", if_exp, loc, compile_info)


# @mast_node(append=False)
# class ScienceRouteDecoratorLabel(RouteDecoratorLabel):
#     rule = re.compile(r'//science'+IF_EXP_REGEX)
#     def __init__(self, if_exp=None, loc=None, compile_info=None):
#         super().__init__(f"science", if_exp, loc, compile_info)

# @mast_node(append=False)
# class GuiRouteDecoratorLabel(RouteDecoratorLabel):
#     rule = re.compile(r'//gui/(?P<path>(\w[\w\/]*))'+IF_EXP_REGEX)
#     def __init__(self,path, if_exp=None, loc=None, compile_info=None):
#         super().__init__(f"gui/{path}", if_exp, loc, compile_info)


# @mast_node(append=False)
# class SpawnRouteDecoratorLabel(RouteDecoratorLabel):
#     rule = re.compile(r'//spawn'+IF_EXP_REGEX)
#     def __init__(self, if_exp=None, loc=None, compile_info=None):
#         super().__init__(f"spawn", if_exp, loc, compile_info)

# @mast_node(append=False)
# class SpawnGridRouteDecoratorLabel(RouteDecoratorLabel):
#     rule = re.compile(r'//spawn/grid'+IF_EXP_REGEX)
#     def __init__(self, if_exp=None, loc=None, compile_info=None):
#         super().__init__(f"spawn/grid", if_exp, loc, compile_info)


# @mast_node(append=False)
# class FocusCommsRouteDecoratorLabel(RouteDecoratorLabel):
#     rule = re.compile(r'//focus/comms'+IF_EXP_REGEX)
#     def __init__(self, if_exp=None, loc=None, compile_info=None):
#         super().__init__(f"focus/comms", if_exp, loc, compile_info)

# @mast_node(append=False)
# class FocusComms2dRouteDecoratorLabel(RouteDecoratorLabel):
#     rule = re.compile(r'//focus/comms2d'+IF_EXP_REGEX)
#     def __init__(self, if_exp=None, loc=None, compile_info=None):
#         super().__init__(f"focus/comms2d", if_exp, loc, compile_info)


# @mast_node(append=False)
# class FocusNormalRouteDecoratorLabel(RouteDecoratorLabel):
#     rule = re.compile(r'//focus/normal'+IF_EXP_REGEX)
#     def __init__(self, if_exp=None, loc=None, compile_info=None):
#         super().__init__(f"focus/normal", if_exp, loc, compile_info)

# @mast_node(append=False)
# class FocusWeaponsRouteDecoratorLabel(RouteDecoratorLabel):
#     rule = re.compile(r'//focus/weapons'+IF_EXP_REGEX)
#     def __init__(self, if_exp=None, loc=None, compile_info=None):
#         super().__init__(f"focus/weapons", if_exp, loc, compile_info)

# @mast_node(append=False)
# class FocusScienceRouteDecoratorLabel(RouteDecoratorLabel):
#     rule = re.compile(r'//focus/science'+IF_EXP_REGEX)
#     def __init__(self, if_exp=None, loc=None, compile_info=None):
#         super().__init__(f"focus/science", if_exp, loc, compile_info)

# @mast_node(append=False)
# class FocusGridRouteDecoratorLabel(RouteDecoratorLabel):
#     rule = re.compile(r'//focus/grid'+IF_EXP_REGEX)
#     def __init__(self, if_exp=None, loc=None, compile_info=None):
#         super().__init__(f"focus/grid", if_exp, loc, compile_info)



# @mast_node(append=False)
# class SelectCommsRouteDecoratorLabel(RouteDecoratorLabel):
#     rule = re.compile(r'//select/comms'+IF_EXP_REGEX)
#     def __init__(self, if_exp=None, loc=None, compile_info=None):
#         super().__init__(f"select/comms", if_exp, loc, compile_info)

# @mast_node(append=False)
# class SelectComms2dRouteDecoratorLabel(RouteDecoratorLabel):
#     rule = re.compile(r'//select/comms2d'+IF_EXP_REGEX)
#     def __init__(self, if_exp=None, loc=None, compile_info=None):
#         super().__init__(f"select/comms2d", if_exp, loc, compile_info)


# @mast_node(append=False)
# class SelectNormalRouteDecoratorLabel(RouteDecoratorLabel):
#     rule = re.compile(r'//select/normal'+IF_EXP_REGEX)
#     def __init__(self, if_exp=None, loc=None, compile_info=None):
#         super().__init__(f"select/normal", if_exp, loc, compile_info)

# @mast_node(append=False)
# class SelectWeaponsRouteDecoratorLabel(RouteDecoratorLabel):
#     rule = re.compile(r'//select/weapons'+IF_EXP_REGEX)
#     def __init__(self, if_exp=None, loc=None, compile_info=None):
#         super().__init__(f"select/weapons", if_exp, loc, compile_info)

# @mast_node(append=False)
# class SelectScienceRouteDecoratorLabel(RouteDecoratorLabel):
#     rule = re.compile(r'//select/science'+IF_EXP_REGEX)
#     def __init__(self, if_exp=None, loc=None, compile_info=None):
#         super().__init__(f"select/science", if_exp, loc, compile_info)

# @mast_node(append=False)
# class SelectGridRouteDecoratorLabel(RouteDecoratorLabel):
#     rule = re.compile(r'//select/grid'+IF_EXP_REGEX)
#     def __init__(self, if_exp=None, loc=None, compile_info=None):
#         super().__init__(f"select/grid", if_exp, loc, compile_info)


# @mast_node(append=False)
# class PointCommsRouteDecoratorLabel(RouteDecoratorLabel):
#     rule = re.compile(r'//point/comms'+IF_EXP_REGEX)
#     def __init__(self, if_exp=None, loc=None, compile_info=None):
#         super().__init__(f"point/comms", if_exp, loc, compile_info)

# @mast_node(append=False)
# class PointComms2dRouteDecoratorLabel(RouteDecoratorLabel):
#     rule = re.compile(r'//point/comms2d'+IF_EXP_REGEX)
#     def __init__(self, if_exp=None, loc=None, compile_info=None):
#         super().__init__(f"point/comms2d", if_exp, loc, compile_info)


# @mast_node(append=False)
# class PointNormalRouteDecoratorLabel(RouteDecoratorLabel):
#     rule = re.compile(r'//point/normal'+IF_EXP_REGEX)
#     def __init__(self, if_exp=None, loc=None, compile_info=None):
#         super().__init__(f"point/normal", if_exp, loc, compile_info)

# @mast_node(append=False)
# class PointWeaponsRouteDecoratorLabel(RouteDecoratorLabel):
#     rule = re.compile(r'//point/weapons'+IF_EXP_REGEX)
#     def __init__(self, if_exp=None, loc=None, compile_info=None):
#         super().__init__(f"point/weapons", if_exp, loc, compile_info)

# @mast_node(append=False)
# class PointScienceRouteDecoratorLabel(RouteDecoratorLabel):
#     rule = re.compile(r'//point/science'+IF_EXP_REGEX)
#     def __init__(self, if_exp=None, loc=None, compile_info=None):
#         super().__init__(f"point/science", if_exp, loc, compile_info)

# @mast_node(append=False)
# class PointGridRouteDecoratorLabel(RouteDecoratorLabel):
#     rule = re.compile(r'//point/grid'+IF_EXP_REGEX)
#     def __init__(self, if_exp=None, loc=None, compile_info=None):
#         super().__init__(f"point/grid", if_exp, loc, compile_info)


# @mast_node(append=False)
# class ObjectGridRouteDecoratorLabel(RouteDecoratorLabel):
#     rule = re.compile(r'//object/grid'+IF_EXP_REGEX)
#     def __init__(self, if_exp=None, loc=None, compile_info=None):
#         super().__init__(f"object/grid", if_exp, loc, compile_info)

# @mast_node(append=False)
# class CollisionPassiveRouteDecoratorLabel(RouteDecoratorLabel):
#     rule = re.compile(r'//collision/passive'+IF_EXP_REGEX)
#     def __init__(self, if_exp=None, loc=None, compile_info=None):
#         super().__init__(f"collision/passive", if_exp, loc, compile_info)
        
# @mast_node(append=False)
# class CollisionInteractiveRouteDecoratorLabel(RouteDecoratorLabel):
#     rule = re.compile(r'//collision/interactive'+IF_EXP_REGEX)
#     def __init__(self, if_exp=None, loc=None, compile_info=None):
#         super().__init__(f"collision/interactive", if_exp, loc, compile_info)

# @mast_node(append=False)
# class ConsoleChangeRouteDecoratorLabel(RouteDecoratorLabel):
#     rule = re.compile(r'//console/change'+IF_EXP_REGEX)
#     def __init__(self, if_exp=None, loc=None, compile_info=None):
#         super().__init__(f"console/change", if_exp, loc, compile_info)

# @mast_node(append=False)
# class ConsoleMainscreenChangeRouteDecoratorLabel(RouteDecoratorLabel):
#     rule = re.compile(r'//console/mainscreen/change'+IF_EXP_REGEX)
#     def __init__(self, if_exp=None, loc=None, compile_info=None):
#         super().__init__(f"console/mainscreen/change", if_exp, loc, compile_info)

# @mast_node(append=False)
# class DamageInternalRouteDecoratorLabel(RouteDecoratorLabel):
#     rule = re.compile(r'//damage/internal'+IF_EXP_REGEX)
#     def __init__(self, if_exp=None, loc=None, compile_info=None):
#         super().__init__(f"damage/internal", if_exp, loc, compile_info)

# @mast_node(append=False)
# class DamageHeatRouteDecoratorLabel(RouteDecoratorLabel):
#     rule = re.compile(r'//damage/heat'+IF_EXP_REGEX)
#     def __init__(self, if_exp=None, loc=None, compile_info=None):
#         super().__init__(f"damage/heat", if_exp, loc, compile_info)

# @mast_node(append=False)
# class DamageObjectRouteDecoratorLabel(RouteDecoratorLabel):
#     rule = re.compile(r'//damage/object'+IF_EXP_REGEX)
#     def __init__(self, if_exp=None, loc=None, compile_info=None):
#         super().__init__(f"damage/object", if_exp, loc, compile_info)


# @mast_node(append=False)
# class DamageDestroyRouteDecoratorLabel(RouteDecoratorLabel):
#     rule = re.compile(r'//damage/destroy'+IF_EXP_REGEX)
#     def __init__(self, if_exp=None, loc=None, compile_info=None):
#         super().__init__(f"damage/destroy", if_exp, loc, compile_info)

# @mast_node(append=False)
# class DamageKilledRouteDecoratorLabel(RouteDecoratorLabel):
#     rule = re.compile(r'//damage/killed'+IF_EXP_REGEX)
#     def __init__(self, if_exp=None, loc=None, compile_info=None):
#         super().__init__(f"damage/killed", if_exp, loc, compile_info)

# @mast_node(append=False)
# class DockHangarRouteDecoratorLabel(RouteDecoratorLabel):
#     rule = re.compile(r'//dock/hangar'+IF_EXP_REGEX)
#     def __init__(self, if_exp=None, loc=None, compile_info=None):
#         super().__init__(f"dock/hangar", if_exp, loc, compile_info)

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
                              