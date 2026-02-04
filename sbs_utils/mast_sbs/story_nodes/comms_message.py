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
    rule = re.compile(r"(?P<mtype>\<\<|\>\>|\(\)|\<(all|scan|client|ship|dialog|dialog_main|dialog_consoles_all|dialog_consoles|dialog_ships|var[ \t]+(?P<var>\w+))\>)"+FORMAT_EXP+"([ \t]+"+STRING_REGEX_NAMED("title")+")?")
    current_comms_message = None

    def __init__(self, mtype, title,  q=None, var=None, format=None, loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        self.format = format
        self.title_color = None
        self.body_color = None
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
        self.var = var
        if mtype == "<scan>" and title is not None:
            self.append_text("%", title)
        elif  CommsMessageStart.current_comms_message is not None:
            raise Exception("Comms message indent error")
        elif var is not None:
            self.mtype = "var"
        CommsMessageStart.current_comms_message = self

    def __str__(self):
        return random.choice(self.options)

    def is_indentable(self):
        return True

    def create_end_node(self, loc, dedent_obj, compile_info):
        self.dedent_loc = loc
        CommsMessageStart.current_comms_message = None

    def post_dedent(self,compile_info):
        CommsMessageStart.current_comms_message = None

from ...helpers import FrameContext
    
@mast_runtime_node(CommsMessageStart)
class CommsMessageStartRuntimeNode(MastRuntimeNode):
    def enter(self, mast:'Mast', task:'MastAsyncTask', node: CommsMessageStart):
        SBS = FrameContext.context.sbs
        if len(node.options)==0:
            return
        msg = random.choice(node.options)
        msg = task.compile_and_format_string(msg)
        npc_face = None
        if node.npc_face:
            npc_face = task.get_variable(node.npc_face)

        if node.mtype == "<<": 
            comms_receive(msg, node.title, color=node.body_color, title_color=node.title_color,face=npc_face)
        elif node.mtype == ">>": 
            comms_transmit(msg, node.title, color=node.body_color, title_color=node.title_color,face=npc_face)
        elif node.mtype == "<scan>": 
            scan_results(msg)
        elif node.mtype == "var": 
            task.set_variable(node.var, node)
        elif node.mtype == "<all>": 
            comms_broadcast(0, msg, node.body_color)
        elif node.mtype == "()": 
            comms_speech_bubble(msg, color=node.title_color)

