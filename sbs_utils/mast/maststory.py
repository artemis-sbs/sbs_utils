from .mast import IF_EXP_REGEX, Mast, MastNode, DecoratorLabel, DescribableNode, STRING_REGEX_NAMED
import re
from ..agent import Agent

STYLE_REF_RULE = r"""([ \t]+style[ \t]*=[ \t]*((?P<style_name>\w+)|((?P<style_q>['"]{3}|["'])(?P<style>[^\n\r\f]+)(?P=style_q))))"""
OPT_STYLE_REF_RULE = STYLE_REF_RULE+"""?"""



class MapDecoratorLabel(DecoratorLabel):
    rule = re.compile(r'@map/(?P<path>[\/\w]+)[ \t]+'+STRING_REGEX_NAMED("display_name")+IF_EXP_REGEX)

    def __init__(self, path, display_name, if_exp=None, q=None, loc=None, compile_info=None):
        # Label stuff
        id = DecoratorLabel.next_label_id()
        name = f"map/{path}/{id}"
        super().__init__(name, loc)

        self.path= path
        self.display_name= display_name
        self.description = ""
        self.if_exp = if_exp
        # need to negate if
        if self.if_exp is not None:
            self.if_exp = if_exp.strip()
            self.if_exp = f'not ({self.if_exp})'

        self.next = None
        self.loc = loc
        self.replace = None
        self.cmds = []

    def can_fallthrough(self):
        return True


class GuiTabDecoratorLabel(DecoratorLabel):
    rule = re.compile(r'(@|\/\/)gui/tab/(?P<path>([\w]+))'+IF_EXP_REGEX)

    def __init__(self, path, if_exp=None, loc=None, compile_info=None):

        # Label stuff
        id = DecoratorLabel.next_label_id()
        name = f"gui/tab/{path}/{id}"
        super().__init__(name, loc)

        self.path= path
        self.description = ""
        self.if_exp = if_exp

        from ..procedural.gui import gui_add_console_tab
        for con in ["helm", "comms", "engineering", "science", "weapons"]:
            if con != path:
                gui_add_console_tab(Agent.SHARED, con, path, self)
        gui_add_console_tab(Agent.SHARED, path, "__back_tab__", "console_selected")

        # need to negate if
        self.code = None
        if self.if_exp is not None:
            self.if_exp = if_exp.strip()
            try:
                self.code = compile(self.if_exp, "<string>", "eval")
            except:
                raise Exception(f"Syntax error '{if_exp}'")
            
        self.next = None
        self.loc = loc
        self.replace = None
        self.cmds = []

    def can_fallthrough(self):
        return True
    
    def test(self, task):
        if self.code is None:
            return True
        return task.eval_code(self.code)


class GuiConsoleDecoratorLabel(DecoratorLabel):
    rule = re.compile(r'(@|//)console/(?P<path>([\w]+))[ \t]+'+STRING_REGEX_NAMED("display_name")+IF_EXP_REGEX)

    def __init__(self, path, display_name, if_exp=None, loc=None, compile_info=None, q=None):
        # Label stuff
        id = DecoratorLabel.next_label_id()
        name = f"console/{path}/{id}"
        super().__init__(name, loc)

        self.path= path
        self.display_name = display_name

        from ..procedural.gui import gui_add_console_type
        gui_add_console_type(path, display_name, None, self)

        self.code = None
        if if_exp is not None:
            if_exp = if_exp.strip()
            try:
                self.code = compile(if_exp, "<string>", "eval")
            except:
                raise Exception(f"Syntax error '{if_exp}'")

        self.next = None
        self.loc = loc
        self.replace = None
        self.cmds = []

    def can_fallthrough(self):
        return True

    def test(self, task):
        if self.code is None:
            return True
        return task.eval_code(self.code)


#
# This would allow listbox template in MAST
# But it was flaky
#
# class ItemTemplateLabel(DecoratorLabel):
#     rule = re.compile(r'@template/item[ \t]+(?P<name>([\w]+))'+IF_EXP_REGEX)

#     def __init__(self, name, if_exp=None, loc=None, compile_info=None):
#         # Label stuff
#         id = DecoratorLabel.next_label_id()
#         name = name
#         super().__init__(name)
#         self.description = ""
#         self.if_exp = if_exp
#         # need to negate if
#         if self.if_exp is not None:
#             self.if_exp = if_exp.strip()
#             self.if_exp = 'not ' + self.if_exp

#         self.next = None
#         self.loc = loc
#         self.replace = None
#         self.cmds = []

#     def can_fallthrough(self):
#         return False


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
FORMAT_EXP = r"(\[(?P<format>([\$\#]?\w+[ \t]*(,[ \t]*\#?\w+)?))\])?"
class CommsMessageStart(DescribableNode):
    rule = re.compile(r"(?P<mtype>\<\<|\>\>|\(\)|\<scan\>)"+FORMAT_EXP+"([ \t]+"+STRING_REGEX_NAMED("title")+")?")
    current_comms_message = None

    def __init__(self, mtype, title,  q=None, format=None, loc=None, compile_info=None):
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

from .mastmission import StartBlock, InitBlock, AbortBlock, CompleteBlock, ObjectiveBlock, MissionLabel
class MastStory(Mast):
    nodes = [
        # sbs specific
        Text,
        AppendText,
        CommsMessageStart,
        WeightedText,
        DefineFormat,
        MapDecoratorLabel,
        GuiTabDecoratorLabel,
        GuiConsoleDecoratorLabel,
        # ItemTemplateLabel this didn't work exactly, maybe sometime post v1.0
        ## Mission Nodes
        MissionLabel, StartBlock,InitBlock, AbortBlock, CompleteBlock, ObjectiveBlock
    ] + Mast.nodes 
