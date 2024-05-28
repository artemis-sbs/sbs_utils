from .mast import IF_EXP_REGEX, Mast, MastNode
import re

STYLE_REF_RULE = r"""([ \t]+style[ \t]*=[ \t]*((?P<style_name>\w+)|((?P<style_q>['"]{3}|["'])(?P<style>[^\n\r\f]+)(?P=style_q))))"""
OPT_STYLE_REF_RULE = STYLE_REF_RULE+"""?"""



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


class MastStory(Mast):
    nodes = [
        # sbs specific
        Text,
        AppendText,

    ] + Mast.nodes 
