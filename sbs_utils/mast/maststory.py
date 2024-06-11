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

class CommsMessageStart(MastNode):
    rule = re.compile(r"""(?P<mtype>\<\<|\>\>)(\[(?P<format>([\$\#]?\w+[ \t]*(,[ \t]*\#?\w+)?))\])?(?P<title>[^:\n\r\f]*)""")
    current_comms_message = None

    def is_indentable(self):
        return True
    
    def __init__(self, mtype, title,  format=None, loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        self.format = format
        self.title_color = "white"
        self.body_color = "white"

        if format is not None:
            f = DefineFormat.resolve_colors(format)
            if len(f)==1:
                self.title_color = f[0]
            if len(f)==2:
                self.title_color = f[0]
                self.body_color = f[1]
                
        self.receive = mtype == "<<"
        self.title = title
        self.options = []
        if  CommsMessageStart.current_comms_message is not None:
            raise "Comms message indent error"
        CommsMessageStart.current_comms_message = self

    def create_end_node(self, loc, dedent_obj, compile_info):
        self.dedent_loc = loc
        CommsMessageStart.current_comms_message = None

    def add_option(self, text, weight=1):
        self.options.append(text)

    def append_text(self, text):
        if len(self.options)==0:
            self.options.append(text)
        else:
            self.options[-1] += "\n"+text

class CommsMessageOption(MastNode):
    rule = re.compile(r"""(?P<mtype>\%\d*|\")(?P<text>[^:\n\r\f]*)""")
    def __init__(self, mtype, text,  loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        if CommsMessageStart.current_comms_message is None:
            raise "Comms message text without start. or not indented properly."
        if mtype =='"':
            CommsMessageStart.current_comms_message.append_text(text)
        else:
            CommsMessageStart.current_comms_message.add_option(text)

    def is_indentable(self):
        return False
        
    def is_virtual(self):
        return True    


class DefineFormat(MastNode):
    rule = re.compile(r"""\=\$(?P<name>\w+)(?P<format>[^:\n\r\f]*)""")
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


class MastStory(Mast):
    nodes = [
        # sbs specific
        Text,
        AppendText,
        CommsMessageStart,
        CommsMessageOption,
        DefineFormat

    ] + Mast.nodes 
