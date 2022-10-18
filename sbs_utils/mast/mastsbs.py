from .mast import IF_EXP_REGEX, TIMEOUT_REGEX, OPT_COLOR, Mast, MastNode, MastCompilerError
import re


class Target(MastNode):
    """
    Creates a new 'thread' to run in parallel
    """
    rule = re.compile(r"""have\s*(?P<from_tag>[\w\.\[\]]+)\s*(?P<cmd>target|approach)(\s*(?P<to_tag>[\w\.\[\]]+))?""")
    def __init__(self, cmd=None, from_tag=None, to_tag=None, loc=None):
        self.from_tag = from_tag
        self.to_tag = to_tag
        self.approach = cmd=="approach"

        
class Tell(MastNode):
    #rule = re.compile(r'tell\s+(?P<to_tag>\w+)\s+(?P<from_tag>\w+)\s+((['"]{3}|["'])(?P<message>[\s\S]+?)(['"]{3}|["']))')
    rule = re.compile(r"""have\s*(?P<from_tag>\w+)\s+tell\s+(?P<to_tag>\w+)\s+((['"]{3}|["'])(?P<message>[\s\S]+?)\4)""")
    def __init__(self, to_tag, from_tag, message, loc=None):
        self.to_tag = to_tag
        self.from_tag = from_tag
        self.message = message


class Timeout(MastNode):
    rule = re.compile(r'timeout\s*:')
    def __init__(self, loc=None):
        self.loc = loc
        self.await_node = EndAwait.stack[-1]
        EndAwait.stack[-1].timeout_label = self

class EndAwait(MastNode):
    rule = re.compile(r'end_await')
    #rule = re.compile(r'end_wait')
    stack = []
    def __init__(self, loc=None):
        self.loc = loc
        EndAwait.stack[-1].end_await_node = self
        EndAwait.stack.pop()


class Comms(MastNode):
    rule = re.compile(r"""await\s*(?P<from_tag>\w+)\s*comms\s*(?P<to_tag>\w+)(\s*set\s*(?P<assign>\w+))?(\s+color\s*["'](?P<color>[ \t\S]+)["'])?"""+TIMEOUT_REGEX+'\s*:')
    def __init__(self, to_tag, from_tag, assign=None, minutes=None, seconds=None, time_pop=None,time_push="", time_jump="", color="white", loc=None):
        self.to_tag = to_tag
        self.from_tag = from_tag
        self.assign = assign
        self.buttons = []
        self.seconds = 0 if  seconds is None else int(seconds)
        self.minutes = 0 if  minutes is None else int(minutes)
        self.color = color

        self.timeout_label = None
        self.end_await_node = None
        EndAwait.stack.append(self)

class Button(MastNode):
    rule = re.compile(r"""(?P<button>\*|\+)\s+(?P<q>["'])(?P<message>.+?)(?P=q)"""+OPT_COLOR+IF_EXP_REGEX+"\s*:")
    def __init__(self, button, message,  color, if_exp, q=None, loc=None):
        self.message = self.compile_formatted_string(message)
        self.sticky = (button == '+' or button=="button")
        self.color = color
        self.visited = set() if not self.sticky else None
        self.loc = loc
        self.await_node = EndAwait.stack[-1]
        self.await_node.buttons.append(self)

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
    rule = re.compile(r'await\s*(?P<from_tag>\w+)\s+near\s+(?P<to_tag>\w+)\s*(?P<distance>\d+)'+TIMEOUT_REGEX+"\s*:")
    def __init__(self, to_tag, from_tag, distance, minutes=None, seconds=None, loc=None):
        self.to_tag = to_tag
        self.from_tag = from_tag
        self.distance = 0 if distance is None else int(distance)
        
        self.seconds = 0 if  seconds is None else int(seconds)
        self.minutes = 0 if  minutes is None else int(minutes)

        self.timeout_label = None
        self.end_await_node = None
        EndAwait.stack.append(self)
    

class Simulation(MastNode):
    """
    Handle commands to the simulation
    """
    rule = re.compile(r"""simulation\s+(?P<cmd>pause|create|resume)""")
    def __init__(self, cmd=None, loc=None):
        self.cmd = cmd


class MastSbs(Mast):
    nodes =  [
        # sbs specific
        Target,
        Tell,
        Comms,
        Timeout,
        EndAwait,
        Button,
        Near,
      #  Simulation
    ] + Mast.nodes 
    