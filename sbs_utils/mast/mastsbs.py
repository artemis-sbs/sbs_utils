from .mast import IF_EXP_REGEX, JUMP_ARG_REGEX, OPT_JUMP_REGEX, TIMEOUT_REGEX, OPT_COLOR, Mast, MastNode, MastCompilerError
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

    def validate(self, mast):
        # this may not be the right check
        if mast.vars.get(self.from_tag) is None:
            return MastCompilerError( f'approach/target with invalid var {self.from_tag}', self.line_no)

    def gen(self):
        if self.approach: 
            return f'approach {self.from_tag} {self.to_tag}'
        else:
            return f'target {self.from_tag} {self.to_tag}'
        
class Tell(MastNode):
    #rule = re.compile(r'tell\s+(?P<to_tag>\w+)\s+(?P<from_tag>\w+)\s+((['"]{3}|["'])(?P<message>[\s\S]+?)(['"]{3}|["']))')
    rule = re.compile(r"""(?P<from_tag>\w+)\s+tell\s+(?P<to_tag>\w+)\s+((['"]{3}|["'])(?P<message>[\s\S]+?)\4)""")
    def __init__(self, to_tag, from_tag, message):
        self.to_tag = to_tag
        self.from_tag = from_tag
        self.message = message
    def validate(self, mast):
        messages = []
        if mast.inputs.get(self.to_tag) is None:
            messages.append(f'Tell cannot find {self.to_tag}')
        elif mast.inputs.get(self.from_tag) is None:
            messages.append(f'Tell cannot find {self.from_tag}')
        if len(messages):
            return MastCompilerError(messages, self.line_no)

    def gen(self):
        return f'tell {self.to_tag} {self.from_tag} "{self.message}"'

class Comms(MastNode):
    rule = re.compile(r"""(?P<from_tag>\w+)\s*comms\s*(?P<to_tag>\w+)(\s+color\s*["'](?P<color>[ \t\S]+)["'])?"""+TIMEOUT_REGEX)
    def __init__(self, to_tag, from_tag, buttons=None, minutes=None, seconds=None, time_pop=None,time_push="", time_jump="", color="white"):
        self.to_tag = to_tag
        self.from_tag = from_tag
        self.buttons = buttons if buttons is not None else []
        self.seconds = 0 if  seconds is None else int(seconds)
        self.minutes = 0 if  minutes is None else int(minutes)
        self.time_jump = time_jump
        self.time_push = time_push == ">"
        self.time_pop = time_pop is not None
        self.color = color
    def add_child(self, obj):
        self.buttons.append(obj)

    def validate(self, mast):
        messages = []
        if mast.inputs.get(self.to_tag) is None:
           messages.append( f'Comms cannot find {self.to_tag}')
        elif mast.inputs.get(self.from_tag) is None:
            messages.append(f'Comms cannot find {self.from_tag}')
        elif self.time_jump and mast.labels.get(self.time_jump) is None:
            messages.append(f'Comms cannot find {self.time_jump}')
            
        for button in self.buttons:
            err = button.validate(mast)
            if err:
                messages.extend(err.messages)
        if len(messages):
            return MastCompilerError(messages, self.line_no)

    def gen(self):
        s = f"comms {self.to_tag} {self.from_tag}"
        if self.minutes or self.seconds:
            s += f" timeout"
        if self.minutes:
            s += f" {self.minutes}m"
        if self.seconds:
            s += f" {self.seconds}s"
        if self.time_jump:
            s += f"->{self.time_jump}"
        
        for button in self.buttons:
            s += '\n'
            s+= button.gen()
        return s


class Button(MastNode):
    rule = re.compile(r"""(?P<button>\*|\+)\s+["'](?P<message>.+?)["']"""+OPT_COLOR+JUMP_ARG_REGEX+IF_EXP_REGEX)
    stack = []
    def __init__(self, button, message, pop, push, jump, color, if_exp):
        self.stack.append(self)
        self.message = message
        self.jump = jump
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

    def validate(self, mast):
        if mast.labels.get(self.jump) is None:
            return MastCompilerError(f'Button cannot find {self.jump}', self.line_no)

    def gen(self):
        return f'   button "{self.message}" -> {self.jump}'

class Near(MastNode):
    rule = re.compile(r'(?P<from_tag>\w+)\s+near\s+(?P<to_tag>\w+)\s*(?P<distance>\d+)'+OPT_JUMP_REGEX+TIMEOUT_REGEX)
    def __init__(self, to_tag, from_tag, distance, pop="", push="", jump="", minutes=None, seconds=None, time_pop="",time_push="", time_jump=""):
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

    def validate(self, mast):
        messages = []
        if mast.inputs.get(self.to_tag) is None:
            messages.append(f'Near cannot find {self.to_tag}')
        elif mast.inputs.get(self.from_tag) is None:
            messages.append(f'Near cannot find {self.from_tag}')

        if len(messages):
            return MastCompilerError(messages, self.line_no)

    def gen(self):
        s = f"near {self.to_tag} {self.from_tag} {self.distance} -> {self.jump}"
        if self.minutes or self.seconds:
            s += f" timeout"
        if self.minutes:
            s += f" {self.minutes}m"
        if self.seconds:
            s += f" {self.seconds}s"
        if self.time_jump:
            s += f"->{self.time_jump}"
        return s

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
