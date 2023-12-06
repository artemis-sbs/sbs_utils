from .mast import IF_EXP_REGEX, TIMEOUT_REGEX, OPT_COLOR, Mast, MastNode, EndAwait,BLOCK_START
import re




class CommsInfo(MastNode):
    rule = re.compile(r"""comms_info([ \t]+(?P<q>['"]{3}|["'])(?P<message>[ \t\S]+?)(?P=q))?"""+OPT_COLOR)
    def __init__(self, message, q=None, color=None, loc=None):
        self.loc = loc
        self.message = self.compile_formatted_string(message)
        self.color = color if color is not None else "#fff"




class Comms(MastNode):
    rule = re.compile(r"""await[ \t]*((?P<origin_tag>\w+)[ \t]*)?comms([ \t]*(?P<selected_tag>\w+))?([ \t]*set\s*(?P<assign>\w+))?([ \t]+color[ \t]*["'](?P<color>[ \t\S]+)["'])?"""+TIMEOUT_REGEX+r'[ \t]*'+BLOCK_START)
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
        if color is not None:
            self.color = self.compile_formatted_string(color)

        self.timeout_label = None
        self.on_change = None
        self.focus = None
        self.fail_label = None
        self.end_await_node = None
        EndAwait.stack.append(self)

    def add_inline(self, _):
        pass
        """ Temp just needed until I can remove this"""



class Scan(MastNode):
    rule = re.compile(r"""await([ \t]+(?P<from_tag>\w+))?[ \t]+scan([ \t]+(?P<to_tag>\w+))?(\s+fog\s+(?P<fog>\d+))?"""+BLOCK_START)
    def __init__(self, to_tag=None, from_tag=None, fog = None, loc=None):
        self.loc = loc
        self.to_tag = to_tag
        self.from_tag = from_tag
        self.fog = int(fog) if fog is not None else 5000
        self.buttons = []
        self.on_change = None
        self.focus = None

        self.end_await_node = None
        EndAwait.stack.append(self)

class Focus(MastNode):
    rule = re.compile(r'focus:')
    def __init__(self, loc=None):
        self.loc = loc
        self.await_node = EndAwait.stack[-1]
        if self.await_node is not None:
            self.await_node.focus = self


   

class MastSbs(Mast):
    nodes =  [
        # sbs specific
        Comms,
          Focus,
        Scan
    ] + Mast.nodes 
    