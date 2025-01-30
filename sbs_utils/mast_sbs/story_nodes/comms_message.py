from ...mast.mast import  MastNode, DescribableNode, STRING_REGEX_NAMED, mast_node
import re

#
#
#
from ...mast.mast import Mast
from ...mast.mastscheduler import MastAsyncTask
from ...mast.mast_runtime_node import MastRuntimeNode, mast_runtime_node
from ...procedural.roles import role
from ...procedural.comms import comms_receive, comms_transmit, comms_speech_bubble, comms_broadcast, comms_message
from ...procedural.science import scan_results
import sbs
import random


# Import these so the node get registered
FORMAT_EXP = r"(\[(?P<format>([\$\#]?\w+[ \t]*(,[ \t]*\#?\w+)*))\])?"
#FORMAT_EXP = r"(\[(?P<format>(\$\w+)|(\#?\w+[ \t]*(,[ \t]*\#?\w+)*)|((\w+[ \t]*:[ \t]*([^;\]]*;)*)))\])"
@mast_node()
class CommsMessageStart(DescribableNode):
    rule = re.compile(r"(?P<mtype>\<\<|\>\>|\(\)|\<(all|scan|client|ship|dialog|dialog_main|dialog_consoles_all|dialog_consoles|dialog_ships)\>)"+FORMAT_EXP+"([ \t]+"+STRING_REGEX_NAMED("title")+")?")
    current_comms_message = None

    def __init__(self, mtype, title,  q=None, format=None, loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        self.format = format
        self.title_color = "white"
        self.body_color = "white"
        self.npc_face = None

        if format is not None:
            f = DefineFormat.resolve_colors(format)
            if len(f)>=1:
                self.title_color = f[0]
            if len(f)>=2:
                self.body_color = f[1]
            if len(f)>=3:
                self.npc_face = f[2]
                
                
        self.mtype = mtype 
        self.title = title
        if mtype == "<scan>" and title is not None:
            self.append_text("%", title)
        elif  CommsMessageStart.current_comms_message is not None:
            raise Exception("Comms message indent error")
        CommsMessageStart.current_comms_message = self

    def is_indentable(self):
        return True

    def create_end_node(self, loc, dedent_obj, compile_info):
        self.dedent_loc = loc
        CommsMessageStart.current_comms_message = None

    def post_dedent(self,compile_info):
        pass

        
@mast_node(append=False)
class WeightedText(MastNode):
    rule = re.compile(r"""(?P<mtype>\%\d*|\")(?P<text>[^\n\r\f]*)""")
    def __init__(self, mtype, text,  loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        # Try to attach to a label
        if loc == 0 and compile_info is not None and compile_info.label is not None:
            compile_info.label.append_text(mtype, text)
        elif isinstance(compile_info.prev_node, DescribableNode):
            compile_info.prev_node.append_text(mtype, text)
        else:
            raise Exception("Weighted text without start. or not indented properly.")
        

    def is_indentable(self):
        return False
        
    def is_virtual(self):
        return True    

@mast_node(append=False)
class DefineFormat(MastNode):
    rule = re.compile(r"""\=\$(?P<name>\w+)(?P<format>[^\n\r\f]*)""")
    colors = {
        "alert": ["red", "white"],
        "info": ["blue", "white"],
        "status": ["orange", "white"]
    }
    def is_indentable(self):
        return False

    def is_virtual(self):
        return True
    
    def __init__(self, name, format, loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        DefineFormat.colors[name] = [c.strip() for c in format.split(",")]
        

    @staticmethod
    def resolve_colors(c):
        colors = c.split(",")
        ret = []
        for c in colors:
            c = c.strip()
            if c.startswith("$"):
                ret.extend(DefineFormat.colors.get(c[1:], ["white", "white"]))
            else:
                ret.append(c)
        return ret
    
@mast_runtime_node(CommsMessageStart)
class CommsMessageStartRuntimeNode(MastRuntimeNode):
    def enter(self, mast:Mast, task:MastAsyncTask, node: CommsMessageStart):
        if len(node.options)==0:
            return
        msg = random.choice(node.options)
        npc_face = None
        if node.npc_face:
            npc_face = task.get_variable(node.npc_face)

        if node.mtype == "<<": 
            comms_receive(msg, node.title, color=node.body_color, title_color=node.title_color,face=npc_face)
        elif node.mtype == ">>": 
            comms_transmit(msg, node.tile, color=node.body_color, title_color=node.title_color,face=npc_face)
        elif node.mtype == "<scan>": 
            scan_results(msg)
        elif node.mtype == "<client>": 
            comms_broadcast(task.maim.client_id, msg, node.body_color)
        elif node.mtype == "<ship>":
            player_id = sbs.get_ship_of_client(task.maim.client_id) 
            comms_broadcast(player_id, msg, node.body_color)
        elif node.mtype == "<all>": 
            comms_broadcast(0, msg, node.body_color)
        elif node.mtype == "()": 
            comms_speech_bubble(msg, color=node.title_color)
        elif node.mtype == "<dialog>": 
            sbs.send_story_dialog(task.maim.client_id, node.title,msg, npc_face, node.title_color)
            player_id = sbs.get_ship_of_client(task.maim.client_id) 
            comms_message(msg, player_id, player_id,  node.title, npc_face, node.body_color, node.title_color, True)
        elif node.mtype == "<dialog_ships>": 
            sbs.send_story_dialog(task.maim.client_id, node.title,msg, npc_face, node.title_color)
            for p in role("__player__"):
                comms_message(msg, p, p,  node.title, npc_face, node.body_color, node.title_color, True)
        elif node.mtype == "<dialog_consoles>":
            player_id = sbs.get_ship_of_client(task.maim.client_id)
            for c in role("console"):
                if c.get_inventory_value("assigned_ship") == player_id:
                    sbs.send_story_dialog(c, node.title,msg, npc_face, node.title_color)
        elif node.mtype == "<dialog_consoles_all>":
            sbs.send_story_dialog(0, node.title,msg, npc_face, node.title_color)
            for c in role("console"):
                sbs.send_story_dialog(c, node.title,msg, npc_face, node.title_color)
        elif node.mtype == "<dialog_main>":
            sbs.send_story_dialog(0, node.title,msg, npc_face, node.title_color)
            for c in role("mainscreen") & role("console"):
                sbs.send_story_dialog(c, node.title,msg, npc_face, node.title_color)
