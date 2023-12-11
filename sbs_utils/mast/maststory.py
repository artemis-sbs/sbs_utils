from .mast import IF_EXP_REGEX, Mast, MastNode, EndAwait, PY_EXP_REGEX, OPT_COLOR, TIMEOUT_REGEX, BLOCK_START
import re
from .parsers import StyleDefinition
import logging

STYLE_REF_RULE = r"""([ \t]+style[ \t]*=[ \t]*((?P<style_name>\w+)|((?P<style_q>['"]{3}|["'])(?P<style>[^\n\r\f]+)(?P=style_q))))"""
OPT_STYLE_REF_RULE = STYLE_REF_RULE+"""?"""



class Text(MastNode):
    rule = re.compile(r"""((['"]{3,})(\n)?(?P<message>[\s\S]+?)(\n)?(['"]{3,}))"""+OPT_STYLE_REF_RULE+IF_EXP_REGEX)
    def __init__(self, message, if_exp, style_name=None, style=None, style_q=None, loc=None):
        self.loc = loc
        self.message = self.compile_formatted_string(message)
        if if_exp is not None:
            if_exp = if_exp.lstrip()
            self.code = compile(if_exp, "<string>", "eval")
        else:
            self.code = None
        self.style = style 
        self.style_name = style_name

class AppendText(MastNode):
    rule = re.compile(r"""(([\^]{3,})(\n)?(?P<message>[\s\S]+?)(\n)?([\^]{3,}))"""+IF_EXP_REGEX)
    def __init__(self, message, if_exp, loc=None):
        self.loc = loc
        #TODO: This needs to be smart with the 'text: ' stuff
        self.message = self.compile_formatted_string(message)
        if if_exp is not None:
            if_exp = if_exp.lstrip()
            self.code = compile(if_exp, "<string>", "eval")
        else:
            self.code = None





class OnMessage(MastNode):
    rule = re.compile(r"(?P<end>end_on)|(on[ \t]+message[ \t]+(?P<val>[ \t\S]+)"+BLOCK_START+")")
    stack = []
    def __init__(self, end=None, val=None, loc=None):
        self.loc = loc
        self.value = val
        if val:
            self.value = compile(val, "<string>", "eval")

        self.is_end = False
        #
        # Check to see if this is embedded in an await
        #
        self.await_node = None
        if len(EndAwait.stack) >0:
            self.await_node = EndAwait.stack[-1]
        self.end_node = None

        if end is not None:
            OnChange.stack[-1].end_node = self
            self.is_end = True
            OnChange.stack.pop()
        else:
            OnChange.stack.append(self)


class OnClick(MastNode):
    rule = re.compile(r"(?P<end>end_on)|(on[ \t]+click([ \t]+(?P<name>\w+))?"+BLOCK_START+")")
    # stack = []
    def __init__(self, end=None, name=None, loc=None):
        self.name = name
        self.loc = loc
        self.is_end = False
        self.end_node = None

        if end is not None:
            OnChange.stack[-1].end_node = self
            self.is_end = True
            OnChange.stack.pop()
        else:
            OnChange.stack.append(self)



class MastStory(Mast):
    nodes = [
        # sbs specific
        Text,
        AppendText,

        # OnMessage,
        # OnClick,
    ] + Mast.nodes 
