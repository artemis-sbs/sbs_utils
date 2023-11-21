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





FOR_RULE = r'([ \t]+for[ \t]+(?P<for_name>\w+)[ \t]+in[ \t]+(?P<for_exp>[ \t\S]+?))?'
class Button(MastNode):
    
    rule = re.compile(r"""(?P<button>\*|\+)[ \t]*(?P<q>["'])(?P<message>[ \t\S]+?)(?P=q)"""+OPT_COLOR+FOR_RULE+IF_EXP_REGEX+r"[ \t]*"+BLOCK_START)
    def __init__(self, message=None, button=None,  
                color=None, if_exp=None, 
                for_name=None, for_exp=None, 
                clone=False, q=None, loc=None):
        if clone:
            return
        self.message = self.compile_formatted_string(message)
        self.sticky = (button == '+' or button=="button")
        self.color = color
        if color is not None:
            self.color = self.compile_formatted_string(color)
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
          Button,
        Scan
    ] + Mast.nodes 
    