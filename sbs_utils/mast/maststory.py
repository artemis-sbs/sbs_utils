from .mast import IF_EXP_REGEX, Mast, MastNode, PY_EXP_REGEX, OPT_COLOR, TIMEOUT_REGEX, BLOCK_START
from .mastsbs import MastSbs, EndAwait
import re
from .parsers import StyleDefinition
import logging

STYLE_REF_RULE = r"""([ \t]+style[ \t]*=[ \t]*((?P<style_name>\w+)|((?P<style_q>['"]{3}|["'])(?P<style>[^\n\r\f]+)(?P=style_q))))"""
OPT_STYLE_REF_RULE = STYLE_REF_RULE+"""?"""


    
class Refresh(MastNode):
    rule = re.compile(r"""refresh([ \t]*(?P<label>\w+))?""")
    def __init__(self, label, loc=None):
        self.loc = loc
        self.label = label

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
        self.style_def = None
        self.style_name = None
        if style is not None:
            self.style_def = StyleDefinition.parse(style)
        elif style_name is not None:
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




class OnChange(MastNode):
    rule = re.compile(r"(?P<end>end_on)|(on[ \t]+change[ \t]+(?P<val>[^:]+)"+BLOCK_START+")")
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

class AwaitGui(MastNode):
    rule = re.compile(r"await[ \t]+gui"+TIMEOUT_REGEX)
    def __init__(self, assign=None,minutes=None, seconds=None, loc=None):
        self.loc = loc
        self.assign = assign
        self.seconds = 0 if  seconds is None else int(seconds)
        self.minutes = 0 if  minutes is None else int(minutes)
                
        self.buttons = []
        self.active = False
        self.nothing = False
        # just await gui

class Disconnect(MastNode):
    rule = re.compile(r'disconnect:')
    def __init__(self, loc=None):
        self.loc = loc
        self.await_node = EndAwait.stack[-1]
        if self.await_node is not None:
            self.await_node.disconnect_label = self


class Choose(MastNode):
    #d=r"(\s*timeout"+MIN_SECONDS_REGEX + r")?"
    #test = r"""await gui((((\s*(?P<choice>choice)(\s*set\s*(?P<assign>\w+))?)?):)?"""
    rule = re.compile(r"(await choice([ \t]*set[ \t]*(?P<assign>\w+))?"+OPT_STYLE_REF_RULE+ r"[ \t]*"+BLOCK_START+r")")
    def __init__(self, assign=None, style_name=None, style=None, style_q=None, loc=None):
        self.loc = loc
        self.assign = assign
        self.seconds = 0
        self.minutes = 0
                
        self.buttons = []
        self.active = False

        self.disconnect_label = None
        self.timeout_label = None
        self.fail_label = None
        self.end_await_node = None
        EndAwait.stack.append(self)

        self.style_def = None
        self.style_name = None
        if style is not None:
            self.style_def = StyleDefinition.parse(style)
        elif style_name is not None:
            self.style_name = style_name


FLOAT_VALUE_REGEX = r"[+-]?([0-9]*[.])?[0-9]+"

class RerouteGui(MastNode):
    rule = re.compile(r"""reroute([ \t]+((?P<gui>server|clients)|(client[ \t]+(?P<var>[_\w][\w]*))))?[ \t]+(?P<label>[_\w][\w]*)""")
    def __init__(self, gui, var=None, label=None, loc=None):
        self.loc = loc
        self.gui = gui
        self.var = var
        self.label = label
        


class MastStory(MastSbs):
    nodes = [
        # sbs specific
        Text,
        AppendText,

        Choose,
            Disconnect,
        OnChange,
        OnMessage,
        OnClick,
        AwaitGui,

        
            RerouteGui,
            Refresh,
    ] + MastSbs.nodes 
