from .mast import IF_EXP_REGEX, TIMEOUT_REGEX, OPT_COLOR, Mast, MastNode, EndAwait,BLOCK_START
import re


class Route(MastNode):
    """
    Route unhandled things comms, science, events
    """
    rule = re.compile(r"""route\s+(?P<route>destroy|spawn|damage|comms\s+select|science\s+select|grid\s+select|grid\s+spawn|change\s*console)\s+(?P<name>\w+)""")
    def __init__(self, route, name, loc=None):
        self.loc = loc
        self.route = route
        self.label = name


class TransmitReceive(MastNode):
    #rule = re.compile(r'tell\s+(?P<to_tag>\w+)\s+(?P<from_tag>\w+)\s+((['"]{3}|["'])(?P<message>[\s\S]+?)(['"]{3}|["']))')
    OPT_FACE = r"""(\s*face((\s*(?P<faceq>['"]{3}|["'])(?P<face_string>[ \t\S]+?)(?P=faceq))|(\s+(?P<face_var>\w+))))?"""
    OPT_COMMS_ID = r"""(\s*title((\s*(?P<comq>['"]{3}|["'])(?P<comms_string>[ \t\S]+?)(?P=comq))|(\s+(?P<comms_var>\w+))))?"""
    rule = re.compile(r"""(?P<tr>receive|transmit)\s*(?P<q>['"]{3}|["'])(?P<message>[\s\S]+?)(?P=q)"""+OPT_COMMS_ID+OPT_FACE+OPT_COLOR)
    def __init__(self, tr, message, 
                 face_string=None, face_var=None, faceq=None,
                 comms_string=None, comms_var=None, comq=None,
                 q=None, color=None, loc=None):
        self.loc = loc
        self.transmit = tr == "transmit"
        self.message = self.compile_formatted_string(message)
        self.color = color if color is not None else "#fff"
        self.face_string = self.compile_formatted_string(face_string)
        self.face_var = face_var
        self.comms_string = self.compile_formatted_string(comms_string)
        self.comms_var = comms_var


class CommsInfo(MastNode):
    rule = re.compile(r"""comms_info(\s+(?P<q>['"]{3}|["'])(?P<message>[\s\S]+?)(?P=q))?"""+OPT_COLOR)
    def __init__(self, message, q=None, color=None, loc=None):
        self.loc = loc
        self.message = self.compile_formatted_string(message)
        self.color = color if color is not None else "#fff"


class Tell(MastNode):
    #rule = re.compile(r'tell\s+(?P<to_tag>\w+)\s+(?P<from_tag>\w+)\s+((['"]{3}|["'])(?P<message>[\s\S]+?)(['"]{3}|["']))')
    rule = re.compile(r"""have\s*(?P<from_tag>\*?\w+)\s+tell\s+(?P<to_tag>\*?\w+)\s+((['"]{3}|["'])(?P<message>[\s\S]+?)\4)"""+OPT_COLOR)
    def __init__(self, to_tag, from_tag, message, color=None, loc=None):
        self.loc = loc
        self.to_tag = to_tag
        self.from_tag = from_tag
        self.message = self.compile_formatted_string(message)
        self.color = color if color is not None else "#fff"

class Broadcast(MastNode):
    #rule = re.compile(r'tell\s+(?P<to_tag>\w+)\s+(?P<from_tag>\w+)\s+((['"]{3}|["'])(?P<message>[\s\S]+?)(['"]{3}|["']))')
    rule = re.compile(r"""have\s*(?P<to_tag>\*?\w+)\s+broadcast\s+(?P<q>['"]{3}|["'])(?P<message>[\s\S]+?)(?P=q)"""+OPT_COLOR)
    def __init__(self, to_tag, message, color=None, q=None,loc=None):
        self.to_tag = to_tag
        self.loc = loc
        self.message = self.compile_formatted_string(message)
        self.color = color if color is not None else "#fff"


class Comms(MastNode):
    rule = re.compile(r"""await\s*((?P<origin_tag>\w+)\s*)?comms(\s*(?P<selected_tag>\w+))?(\s*set\s*(?P<assign>\w+))?(\s+color\s*["'](?P<color>[ \t\S]+)["'])?"""+TIMEOUT_REGEX+'\s*'+BLOCK_START)
    def __init__(self, selected_tag=None, origin_tag=None, assign=None, minutes=None, seconds=None, time_pop=None,time_push="", time_jump="", color="white", loc=None):
        self.loc = loc
        # Origin is the player ship, selected is NPC/GridObject
        self.selected_tag = selected_tag
        self.origin_tag = origin_tag
        self.assign = assign
        self.buttons = []
        self.seconds = 0 if  seconds is None else int(seconds)
        self.minutes = 0 if  minutes is None else int(minutes)
        self.color = color

        self.timeout_label = None
        self.fail_label = None
        self.end_await_node = None
        EndAwait.stack.append(self)

class Scan(MastNode):
    rule = re.compile(r"""await(\s+(?P<from_tag>\w+))?\s+scan(\s+(?P<to_tag>\w+))?"""+BLOCK_START)
    def __init__(self, to_tag, from_tag, loc=None):
        self.loc = loc
        self.to_tag = to_tag
        self.from_tag = from_tag
        self.buttons = []

        self.end_await_node = None
        EndAwait.stack.append(self)

class ScanResult(MastNode):
    rule = re.compile(r"""scan\s*results\s*((['"]{3}|["'])(?P<message>[\s\S]+?)\2)""")
    def __init__(self, message=None, loc=None):
        self.loc = loc
        self.message = self.compile_formatted_string(message)

FOR_RULE = r'(\s+for\s+(?P<for_name>\w+)\s+in\s+(?P<for_exp>[\s\S]+?))?'
class ScanTab(MastNode):
    rule = re.compile(r"""scan\s*tab\s+(?P<q>["'])(?P<message>.+?)(?P=q)"""+FOR_RULE+IF_EXP_REGEX+r"\s*"+BLOCK_START)
    def __init__(self, message=None, button=None,  
                 if_exp=None, 
                 for_name=None, for_exp=None, 
                 clone=False, q=None, loc=None):
        if clone:
            return
        self.message = self.compile_formatted_string(message)
        self.loc = loc
        self.await_node = EndAwait.stack[-1]
        self.await_node.buttons.append(self)

        if if_exp:
            if_exp = if_exp.lstrip()
            self.code = compile(if_exp, "<string>", "eval")
        else:
            self.code = None

        self.for_name = for_name
        self.data = None
        if for_exp:
            for_exp = for_exp.lstrip()
            self.for_code = compile(for_exp, "<string>", "eval")
        else:
            self.cor_code = None


    def clone(self):
        proxy = ScanTab(clone=True)
        proxy.message = self.message
        proxy.code = self.code
        proxy.loc = self.loc
        proxy.await_node = self.await_node
        proxy.data = self.data
        proxy.for_code = self.for_code
        proxy.for_name = self.for_name

        return proxy
    
    def expand(self):
        pass



FOR_RULE = r'(\s+for\s+(?P<for_name>\w+)\s+in\s+(?P<for_exp>[\s\S]+?))?'
class Button(MastNode):
    
    rule = re.compile(r"""(?P<button>\*|\+)\s+(?P<q>["'])(?P<message>.+?)(?P=q)"""+OPT_COLOR+FOR_RULE+IF_EXP_REGEX+r"\s*"+BLOCK_START)
    def __init__(self, message=None, button=None,  
                 color=None, if_exp=None, 
                 for_name=None, for_exp=None, 
                 clone=False, q=None, loc=None):
        if clone:
            return
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

        self.for_name = for_name
        self.data = None
        if for_exp:
            for_exp = for_exp.lstrip()
            self.for_code = compile(for_exp, "<string>", "eval")
        else:
            self.cor_code = None

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

    def clone(self):
        proxy = Button(clone=True)
        proxy.message = self.message
        proxy.code = self.code
        proxy.color = self.color
        proxy.loc = self.loc
        proxy.await_node = self.await_node
        proxy.sticky = self.sticky
        proxy.visited = self.visited
        proxy.data = self.data
        proxy.for_code = self.for_code
        proxy.for_name = self.for_name

        return proxy
    
    def expand(self):
        pass



    

class Simulation(MastNode):
    """
    Handle commands to the simulation
    """
    rule = re.compile(r"""simulation\s+(?P<cmd>pause|create|resume)""")
    def __init__(self, cmd=None, loc=None):
        self.loc = loc
        self.cmd = cmd


class Load(MastNode):
    rule = re.compile(r'(from\s+(?P<lib>[\w\.\\\/-]+)\s+)?load\s+(?P<format>json|map)\s+(?P<name>[\w\.\\\/-]+)')

    def __init__(self, name, lib=None, format=None, loc=None):
        self.loc = loc
        self.name = name
        self.lib = lib
        self.format = format

class MastSbs(Mast):
    nodes =  [
        # sbs specific
        Route,
        TransmitReceive,
        Tell,
        Load,
        Broadcast,
        Comms,
        CommsInfo,
        Button,
        Simulation,
        Scan,
        ScanTab,
        ScanResult
    ] + Mast.nodes 
    