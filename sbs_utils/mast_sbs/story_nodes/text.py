from ...mast.mast_node import IF_EXP_REGEX, MastNode, mast_node
import re
#
# Runtime import
#
from ...procedural.gui import gui_text_area
from ...mast.mast_runtime_node import MastRuntimeNode, mast_runtime_node
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ...mast.mast import Mast
    from ...mast.mastscheduler import MastAsyncTask

STYLE_REF_RULE = r"""([ \t]+style[ \t]*=[ \t]*((?P<style_name>\w+)|((?P<style_q>['"]{3}|["'])(?P<style>[^\n\r\f]+)(?P=style_q))))"""
OPT_STYLE_REF_RULE = STYLE_REF_RULE+"""?"""


@mast_node(append=False)
class Text(MastNode):
    rule = re.compile(r"""((['"]{3,})(\n)?(?P<message>[\s\S]+?)(\n)?(['"]{3,}))"""+OPT_STYLE_REF_RULE+IF_EXP_REGEX)
    def __init__(self, message, if_exp, style_name=None, style=None, style_q=None, loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        self.message = self.compile_formatted_string(message)
        if if_exp is not None:
            if_exp = if_exp.lstrip()
            self.code = compile(if_exp, "<string>", "eval")
        else:
            self.code = None
        self.style = style 
        self.style_name = style_name


@mast_runtime_node(Text)
class TextRuntimeNode(MastRuntimeNode):
    current = None
    def enter(self, mast:'Mast', task:'MastAsyncTask', node: Text):
        self.tag = task.main.page.get_tag()
        msg = ""
        self.task = task 
        value = True
        TextRuntimeNode.current = self
        if node.code is not None:
            value = task.eval_code(node.code)
        if value:
            msg = task.format_string(node.message)
            #msg = node.message
            style = node.style
            if style is None:
                style = node.style_name
            self.layout_text = gui_text_area(msg,style)

@mast_node(append=False)
class AppendText(MastNode):
    rule = re.compile(r"""(([\^]{3,})(\n)?(?P<message>[\s\S]+?)(\n)?([\^]{3,}))"""+IF_EXP_REGEX)
    def __init__(self, message, if_exp, loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        #TODO: This needs to be smart with the 'text: ' stuff
        self.message = self.compile_formatted_string(message)
        if if_exp is not None:
            if_exp = if_exp.lstrip()
            self.code = compile(if_exp, "<string>", "eval")
        else:
            self.code = None
@mast_runtime_node(AppendText)
class AppendTextRuntimeNode(MastRuntimeNode):
    def enter(self, mast:'Mast', task:'MastAsyncTask', node: AppendText):
        msg = ""
        value = True
        if node.code is not None:
            value = task.eval_code(node.code)
        if value:
            msg = task.format_string(node.message)
            text = TextRuntimeNode.current
            if text is not None:
                text.layout_text.message += '\n'
                text.layout_text.message += msg
