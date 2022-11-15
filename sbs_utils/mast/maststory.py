from .mast import IF_EXP_REGEX, Mast, MastNode, PY_EXP_REGEX, OPT_COLOR, TIMEOUT_REGEX
from .mastsbs import MastSbs, EndAwait
import re
from .parsers import LayoutAreaParser
import logging

class Row(MastNode):
    rule = re.compile(r"""row""")
    def __init__(self, loc=None):
        pass
    
class Refresh(MastNode):
    rule = re.compile(r"""refresh\s*(?P<label>\w+)""")
    def __init__(self, label, loc=None):
        self.label = label

    
class Hole(MastNode):
    rule = re.compile(r"""hole""")
    def __init__(self,  loc=None):
        pass


class Text(MastNode):
    #rule = re.compile(r'tell\s+(?P<to_tag>\w+)\s+(?P<from_tag>\w+)\s+((['"]{3}|["'])(?P<message>[\s\S]+?)(['"]{3}|["']))')
    #(\s+color\s*["'](?P<color>[ \t\S]+)["'])?
    rule = re.compile(r"""((['"]{3,})(\n)?(?P<message>[\s\S]+?)(\n)?(['"]{3,}))"""+IF_EXP_REGEX)
    def __init__(self, message, if_exp, loc=None):
        self.message = self.compile_formatted_string(message)
        if if_exp is not None:
            if_exp = if_exp.lstrip()
            self.code = compile(if_exp, "<string>", "eval")
        else:
            self.code = None

class AppendText(MastNode):
    #rule = re.compile(r'tell\s+(?P<to_tag>\w+)\s+(?P<from_tag>\w+)\s+((['"]{3}|["'])(?P<message>[\s\S]+?)(['"]{3}|["']))')
    #(\s+color\s*["'](?P<color>[ \t\S]+)["'])?
    rule = re.compile(r"""(([\^]{3,})(\n)?(?P<message>[\s\S]+?)(\n)?([\^]{3,}))"""+IF_EXP_REGEX)
    def __init__(self, message, if_exp, loc=None):
        self.message = self.compile_formatted_string(message)
        if if_exp is not None:
            if_exp = if_exp.lstrip()
            self.code = compile(if_exp, "<string>", "eval")
        else:
            self.code = None


class Face(MastNode):
    rule = re.compile(r"""face\s*(((['"]{3}|["'])(?P<face>[\s\S]+?)\3)|(?P<face_exp>[ \t\S]+)?)""")
    def __init__(self, face=None, face_exp=None, loc=None):
        self.face = face
        if face_exp:
            face_exp = face_exp.lstrip()
            self.code = compile(face_exp, "<string>", "eval")
        else:
            self.code = None

class Ship(MastNode):
    rule = re.compile(r"""ship\s+(?P<q>['"]{3}|["'])(?P<ship>[\s\S]+?)(?P=q)""")
    def __init__(self, ship=None, q=None, loc=None):
        self.ship= ship

class Blank(MastNode):
    rule = re.compile(r"""blank""")
    def __init__(self, loc=None):
        pass

class Section(MastNode):
    rule = re.compile(r"""section""")
    def __init__(self, loc=None):
        pass

class Style(MastNode):
    rule = re.compile(r"""style(\s+area:\s*(?P<area>"""+LayoutAreaParser.AREA_LIST_TOKENS+r");)?(\s*row-height:\s*(?P<height>\d+(px)?);)?")
    def __init__(self, area, height, loc=None):
        LayoutAreaParser()
        tokens = LayoutAreaParser.lex(area)
        self.asts = LayoutAreaParser.parse_list(tokens)
        if (len(self.asts)!=4):
            raise Exception("Invalid area arguments")
        if height is not None:
            tokens = LayoutAreaParser.lex(height)
            self.height = LayoutAreaParser.parse_e2(tokens)
        else:
            self.height = None

class AwaitGui(MastNode):
    rule = re.compile(r"await\s+gui"+TIMEOUT_REGEX)
    def __init__(self, assign=None,minutes=None, seconds=None, loc=None):
        self.assign = assign
        self.seconds = 0 if  seconds is None else int(seconds)
        self.minutes = 0 if  minutes is None else int(minutes)
                
        self.buttons = []
        self.active = False
        self.nothing = False
        # just await gui
   
class Choose(MastNode):
    #d=r"(\s*timeout"+MIN_SECONDS_REGEX + r")?"
    #test = r"""await gui((((\s*(?P<choice>choice)(\s*set\s*(?P<assign>\w+))?)?):)?"""
    rule = re.compile(r"(await choice(\s*set\s*(?P<assign>\w+))?"+ TIMEOUT_REGEX+ r"\s*:)")
    def __init__(self, assign=None,minutes=None, seconds=None, loc=None):
        self.assign = assign
        self.seconds = 0 if  seconds is None else int(seconds)
        self.minutes = 0 if  minutes is None else int(minutes)
                
        self.buttons = []
        self.active = False

        self.timeout_label = None
        self.end_await_node = None
        EndAwait.stack.append(self)

class ButtonControl(MastNode):
    rule = re.compile(r"""((button\s+(?P<q>['"]{3}|["'])(?P<message>[\s\S]+?)(?P=q))(\s*data\s*=\s*(?P<data>"""+PY_EXP_REGEX+r"""))?"""+IF_EXP_REGEX+r"\s*:)|(?P<end>end_button)")
    stack = []
    def __init__(self, message, q, data=None, py=None, if_exp=None, end=None, loc=None):
        #self.message = message
        if message: #Message is none for end
            self.message = self.compile_formatted_string(message)
        self.end_node = None
        self.is_end = False
        self.loc = loc
    
        if if_exp:
            if_exp = if_exp.lstrip()
            self.code = compile(if_exp, "<string>", "eval")
        else:
            self.code = None

        if data:
            data = data.lstrip()
            if py:
                data = data[2:-2]
                data= data.strip()
            self.data_code = compile(data, "<string>", "eval")
        else:
            self.data_code = None


        if end is not None:
            ButtonControl.stack[-1].end_node = self
            self.is_end = True
            ButtonControl.stack.pop()
        else:
            ButtonControl.stack.append(self)



FLOAT_VALUE_REGEX = r"[+-]?([0-9]*[.])?[0-9]+"

class SliderControl(MastNode):
    rule = re.compile(r"""(?P<is_int>intslider|slider)"""+
        r"""\s+(?P<var>\w+)"""+
        r"""\s+(?P<low>"""+FLOAT_VALUE_REGEX+
        r""")\s+(?P<high>"""+FLOAT_VALUE_REGEX+
        r""")\s+(?P<value>"""+FLOAT_VALUE_REGEX+
        r""")""")
    def __init__(self, is_int=None, var=None, low=0.0, high=1.0, value=0.5, loc=None):
        self.var= var
        self.is_int = (is_int=="intslider")
        self.low = float(low)
        self.high = float(high)
        self.value = float(value)
    
class CheckboxControl(MastNode):
    rule = re.compile(r"""checkbox\s+(?P<var>[ \t\S]+)\s+(?P<q>['"]{3}|["'])(?P<message>[\s\S]+?)(?P=q)""")
    def __init__(self, var=None, message=None, q=None, loc=None):
        self.var= var
        #self.message = message
        self.message = self.compile_formatted_string(message)

class TextInputControl(MastNode):
    
    rule = re.compile(r"""input\s+(?P<var>[_\w][\w]*)(\s+(?P<q>['"]{3}|["'])(?P<label>[\s\S]+?)(?P=q))?""")
    def __init__(self, var=None, label=None,q=None, loc=None):
        self.var= var
        print(f"node {label}")
        self.label = self.compile_formatted_string(label) if label is not None else None
        print(f"self label {self.label}")



class DropdownControl(MastNode):
    
    rule = re.compile(r"""(dropdown\s+(?P<var>[ \t\S]+)\s+(?P<q>['"]{3}|["'])(?P<values>[\s\S]+?)(?P=q))|(?P<end>end_dropdown)""")
    stack = []
    def __init__(self, var=None, values=None, q=None,end=None, loc=None):
        self.is_end = False
        self.end_node = None
        self.loc = loc
        if end is not None:
            DropdownControl.stack[-1].end_node = self
            self.is_end = True
            DropdownControl.stack.pop()
        else:
            DropdownControl.stack.append(self)
            self.var= var
            self.values = self.compile_formatted_string(values)

class ImageControl(MastNode):
    rule = re.compile(r"""image\s*(?P<q>['"]{3}|["'])(?P<file>[\s\S]+?)(?P=q)"""+OPT_COLOR)
    def __init__(self, file, q, color, loc=None):
        self.file = self.compile_formatted_string(file)
        self.color = color if color is not None else "#fff"



class WidgetList(MastNode):
    #rule = re.compile(r'tell\s+(?P<to_tag>\w+)\s+(?P<from_tag>\w+)\s+((['"]{3}|["'])(?P<message>[\s\S]+?)(['"]{3}|["']))')
    #(\s+color\s*["'](?P<color>[ \t\S]+)["'])?
    rule = re.compile(r"""widget_list\s+((?P<clear>clear)|(?P<console>['"]\w+['"])(\s*(?P<q>['"]{3}|["'])(?P<widgets>[\s\S]+?)(?P=q)))""")
    def __init__(self, clear, console, widgets, q, loc=None):
        if clear == "clear":
            self.console = ""
            self.widgets = ""
        else:
            self.console = console
            self.widgets = widgets


class MastStory(MastSbs):
    nodes = [
        # sbs specific
        Row,
            Text,
            AppendText,
            Face,
            Ship,
            Blank,
            Hole,
            Section,
            Style,
        Choose,
        AwaitGui,
        ButtonControl,
        SliderControl,
        CheckboxControl,
        DropdownControl,
        ImageControl,
        TextInputControl,
        WidgetList,
        Refresh
    ] + MastSbs.nodes 
