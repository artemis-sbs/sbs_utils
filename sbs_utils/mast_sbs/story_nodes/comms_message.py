from ...mast.mast_node import  DescribableNode, STRING_REGEX_NAMED, mast_node
import re

#
#
#
from ...mast.mast_runtime_node import MastRuntimeNode, mast_runtime_node
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ...mast.mast import Mast
    from ...mast.mastscheduler import MastAsyncTask

from ...procedural.roles import role
from ...procedural.comms import comms_receive, comms_transmit, comms_speech_bubble, comms_broadcast, comms_message
from ...procedural.science import scan_results
from .define_format import DefineFormat
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

from ...helpers import FrameContext
    
@mast_runtime_node(CommsMessageStart)
class CommsMessageStartRuntimeNode(MastRuntimeNode):
    def enter(self, mast:'Mast', task:'MastAsyncTask', node: CommsMessageStart):
        SBS = FrameContext.context.sbs
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
            player_id = SBS.get_ship_of_client(task.maim.client_id) 
            comms_broadcast(player_id, msg, node.body_color)
        elif node.mtype == "<all>": 
            comms_broadcast(0, msg, node.body_color)
        elif node.mtype == "()": 
            comms_speech_bubble(msg, color=node.title_color)
        elif node.mtype == "<dialog>": 
            SBS.send_story_dialog(task.maim.client_id, node.title,msg, npc_face, node.title_color)
            player_id = SBS.get_ship_of_client(task.maim.client_id) 
            comms_message(msg, player_id, player_id,  node.title, npc_face, node.body_color, node.title_color, True)
        elif node.mtype == "<dialog_ships>": 
            SBS.send_story_dialog(task.maim.client_id, node.title,msg, npc_face, node.title_color)
            for p in role("__player__"):
                comms_message(msg, p, p,  node.title, npc_face, node.body_color, node.title_color, True)
        elif node.mtype == "<dialog_consoles>":
            player_id = SBS.get_ship_of_client(task.maim.client_id)
            for c in role("console"):
                if c.get_inventory_value("assigned_ship") == player_id:
                    SBS.send_story_dialog(c, node.title,msg, npc_face, node.title_color)
        elif node.mtype == "<dialog_consoles_all>":
            SBS.send_story_dialog(0, node.title,msg, npc_face, node.title_color)
            for c in role("console"):
                SBS.send_story_dialog(c, node.title,msg, npc_face, node.title_color)
        elif node.mtype == "<dialog_main>":
            SBS.send_story_dialog(0, node.title,msg, npc_face, node.title_color)
            for c in role("mainscreen") & role("console"):
                SBS.send_story_dialog(c, node.title,msg, npc_face, node.title_color)
