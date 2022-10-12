from .mast import IF_EXP_REGEX, OPT_JUMP_REGEX, OPT_JUMP_REGEX, TIMEOUT_REGEX, OPT_COLOR, Mast, MastNode, MastCompilerError
import re


class Target(MastNode):
    """
    Creates a new 'thread' to run in parallel
    """
    rule = re.compile(r"""(?P<from_tag>[\w\.\[\]]+)\s*(?P<cmd>target|approach)(\s*(?P<to_tag>[\w\.\[\]]+))?""")
    def __init__(self, cmd=None, from_tag=None, to_tag=None):
        self.from_tag = from_tag
        self.to_tag = to_tag
        self.approach = cmd=="approach"
        print(f'target {self.from_tag} {self.to_tag}')

        
class Tell(MastNode):
    #rule = re.compile(r'tell\s+(?P<to_tag>\w+)\s+(?P<from_tag>\w+)\s+((['"]{3}|["'])(?P<message>[\s\S]+?)(['"]{3}|["']))')
    rule = re.compile(r"""(?P<from_tag>\w+)\s+tell\s+(?P<to_tag>\w+)\s+((['"]{3}|["'])(?P<message>[\s\S]+?)\4)""")
    def __init__(self, to_tag, from_tag, message):
        self.to_tag = to_tag
        self.from_tag = from_tag
        self.message = message


class Comms(MastNode):
    rule = re.compile(r"""(?P<from_tag>\w+)\s*comms\s*(?P<to_tag>\w+)(\s*set\s*(?P<assign>\w+))?(\s+color\s*["'](?P<color>[ \t\S]+)["'])?"""+TIMEOUT_REGEX)
    def __init__(self, to_tag, from_tag, assign=None, minutes=None, seconds=None, time_pop=None,time_push="", time_jump="", color="white"):
        self.to_tag = to_tag
        self.from_tag = from_tag
        self.assign = assign
        self.buttons = Button.stack 
        Button.stack=[]
        self.seconds = 0 if  seconds is None else int(seconds)
        self.minutes = 0 if  minutes is None else int(minutes)
        self.time_jump = time_jump
        self.time_push = time_push == ">"
        self.time_pop = time_pop is not None
        self.color = color



class Button(MastNode):
    rule = re.compile(r"""(?P<button>\*|\+)\s+(?P<q>["'])(?P<message>.+?)(?P=q)"""+OPT_COLOR+OPT_JUMP_REGEX+IF_EXP_REGEX)
    stack = []
    def __init__(self, q, button, message, pop, push, jump, color, await_name, with_data, py, if_exp):
        self.stack.append(self)
        self.message = self.compile_formatted_string(message)
        self.jump = jump
        self.await_name= await_name
        self.with_data = with_data
        self.push = push == ">"
        self.pop = pop is not None
        self.sticky = (button == '+' or button=="button")
        self.color = color
        
        self.visited = set() if not self.sticky else None

        if if_exp:
            if_exp = if_exp.lstrip()
            self.code = compile(if_exp, "<string>", "eval")
        else:
            self.code = None
        

    def visit(self, id_tuple):
        if self.visited is not None:
            self.visited.add(id_tuple)
    
    def been_here(self, id_tuple):
        if self.visited is not None:
            return (id_tuple in self.visited)
        return False

    def should_present(self, id_tuple):
        if self.visited is not None:
            return not id_tuple in self.visited
        return True


class Near(MastNode):
    rule = re.compile(r'(?P<from_tag>\w+)\s+near\s+(?P<to_tag>\w+)\s*(?P<distance>\d+)'+OPT_JUMP_REGEX+TIMEOUT_REGEX)
    def __init__(self, to_tag, from_tag, distance, pop="", push="", jump="", minutes=None, seconds=None, time_pop="",time_push="", time_jump="", await_name=None, with_data=None, py=None):
        self.to_tag = to_tag
        self.from_tag = from_tag
        self.distance = 0 if distance is None else int(distance)
        self.jump = jump
        self.push = push == '>'
        self.pop = pop != ""
        self.seconds = 0 if  seconds is None else int(seconds)
        self.minutes = 0 if  minutes is None else int(minutes)
        self.time_jump = time_jump
        self.time_push = time_push == '>'
        self.time_pop = pop != ""


class Simulation(MastNode):
    """
    Handle commands to the simulation
    """
    rule = re.compile(r"""simulation\s+(?P<cmd>pause|create|resume)""")
    def __init__(self, cmd=None):
        self.cmd = cmd


class MastSbs(Mast):
    nodes = Mast.nodes + [
        # sbs specific
        Target,
        Tell,
        Comms,
        Button,
        Near,
        Simulation
    ]
