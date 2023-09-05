from .mast import IF_EXP_REGEX, Mast, MastNode, PY_EXP_REGEX, OPT_COLOR, TIMEOUT_REGEX, BLOCK_START
from .mastsbs import MastSbs, EndAwait
import re
from .parsers import StyleDefinition
import logging

STYLE_REF_RULE = r"""([ \t]+style[ \t]*=[ \t]*((?P<style_name>\w+)|((?P<style_q>['"]{3}|["'])(?P<style>.*?)(?P=style_q))))"""
OPT_STYLE_REF_RULE = STYLE_REF_RULE+"""?"""


class Row(MastNode):
    rule = re.compile(r"""row"""+OPT_STYLE_REF_RULE)
    def __init__(self, style_name=None, style=None, style_q=None, loc=None):
        self.loc = loc
        self.style_def = None
        self.style_name = None
        if style is not None:
            self.style_def = StyleDefinition.parse(style)
        elif style_name is not None:
            self.style_name = style_name
    
class Refresh(MastNode):
    rule = re.compile(r"""refresh[ \t]*(?P<label>\w+)?""")
    def __init__(self, label, loc=None):
        self.loc = loc
        self.label = label

    
class Hole(MastNode):
    rule = re.compile(r"""hole""")
    def __init__(self,  loc=None):
        self.loc = loc


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


class Face(MastNode):
    rule = re.compile(r"""face[ \t]*(((['"]{3}|["'])(?P<face>[\s\S]+?)\3)|(?P<face_exp>[ \t\S]+)?)"""+OPT_STYLE_REF_RULE)
    def __init__(self, face=None, face_exp=None, style_name=None, style=None, style_q=None, loc=None):
        self.loc = loc
        self.face = face
        if face_exp:
            face_exp = face_exp.lstrip()
            self.code = compile(face_exp, "<string>", "eval")
        else:
            self.code = None
        self.style_def = None
        self.style_name = None
        if style is not None:
            self.style_def = StyleDefinition.parse(style)
        elif style_name is not None:
            self.style_name = style_name

class Ship(MastNode):
    rule = re.compile(r"""ship[ \t]+(?P<q>['"]{3}|["'])(?P<ship>[\s\S]+?)(?P=q)"""+OPT_STYLE_REF_RULE)
    def __init__(self, ship=None, q=None, style_name=None, style=None, style_q=None, loc=None):
        self.loc = loc
        self.ship= self.compile_formatted_string(ship)
        self.style_def = None
        self.style_name = None
        if style is not None:
            self.style_def = StyleDefinition.parse(style)
        elif style_name is not None:
            self.style_name = style_name

class GuiContent(MastNode):
    rule = re.compile(r"""gui[ \t]+(?P<gui>page|control)[ \t]+(?P<var>\w+)[ \t]+(?P<exp>("""+PY_EXP_REGEX+'|.*))'+OPT_STYLE_REF_RULE)
    def __init__(self, gui=None, var=None, exp=None, py=None, style_name=None, style=None, style_q=None, loc=None):
        self.loc = loc
        self.gui= gui
        self.var= var
        exp = exp.lstrip()
        if py:
            exp = exp[2:-2]
            exp = exp.strip()
        self.code = compile(exp, "<string>", "eval")
        self.style_def = None
        self.style_name = None
        if style is not None:
            self.style_def = StyleDefinition.parse(style)
        elif style_name is not None:
            self.style_name = style_name


class Blank(MastNode):
    rule = re.compile(r"""blank"""+OPT_STYLE_REF_RULE)
    def __init__(self, style_name=None, style=None, style_q=None, loc=None):
        self.loc = loc
        self.style_def = None
        self.style_name = None
        if style is not None:
            self.style_def = StyleDefinition.parse(style)
        elif style_name is not None:
            self.style_name = style_name




class Section(MastNode):
    rule = re.compile(r"""section"""+OPT_STYLE_REF_RULE)
    def __init__(self, style_name=None, style=None, style_q=None, loc=None):
        self.loc = loc
        self.style_def = None
        self.style_name = None
        if style is not None:
            self.style_def = StyleDefinition.parse(style)
        elif style_name is not None:
            self.style_name = style_name

class Clickable(MastNode):
    rule = re.compile(r"((section"+STYLE_REF_RULE+r"""[ \t]*clickable[ \t]*(?P<q>['"]{3}|["'])(?P<message>.*?)(?P=q)([ \t]*data[ \t]*=[ \t]*(?P<data>"""+PY_EXP_REGEX+r"""))?)[ \t]*"""+BLOCK_START+r")|(?P<end>end_clickable)")
    stack = []
    def __init__(self, message, q, data=None, py=None, end=None, style_name=None, style=None, style_q=None, loc=None):
        #self.message = message
        self.loc = loc
        if message: #Message is none for end
            self.message = self.compile_formatted_string(message)
        self.end_node = None
        self.is_end = False
        
        if data:
            data = data.lstrip()
            if py:
                data = data[2:-2]
                data= data.strip()
            self.data_code = compile(data, "<string>", "eval")
        else:
            self.data_code = None

        if end is not None:
            Clickable.stack[-1].end_node = self
            self.is_end = True
            Clickable.stack.pop()
        else:
            Clickable.stack.append(self)

        
        self.style_def = None
        self.style_name = None
        if style is not None:
            self.style_def = StyleDefinition.parse(style)
        elif style_name is not None:
            self.style_name = style_name
        
    @classmethod
    def dd_parse(cls, lines):
        mo = cls.rule.match(lines)

        if mo:
            span = mo.span()
            data = mo.groupdict()
            found = lines[span[0]:span[1]]
            return Mast.ParseData(span[0], span[1], data)
        else:
            return None

class Style(MastNode):
    rule = re.compile(r"""style[ \t]+(?P<name>\.?\w+)[ \t]*=[ \t]*(?P<q>['"]{3}|["'])(?P<style>.*?)(?P=q)""")
    def __init__(self, name, style=None, q=None,loc=None):
        self.loc = loc
        style_def = StyleDefinition.parse(style)
        
        StyleDefinition.styles[name] = style_def

class OnChange(MastNode):
    rule = re.compile(r"(?P<end>end_on)|(on[ \t]+change[ \t]+(?P<val>[^:]+)"+BLOCK_START+")")
    #stack = []
    def __init__(self, end=None, val=None, loc=None):
        self.value = val
        self.loc = loc
        self.is_end = False
        if val:
            self.value = compile(val, "<string>", "eval")
        self.end_node = None

        if end is not None:
            Clickable.stack[-1].end_node = self
            self.is_end = True
            Clickable.stack.pop()
        else:
            Clickable.stack.append(self)


class OnClick(MastNode):
    rule = re.compile(r"(?P<end>end_on)|(on[ \t]+click([ \t]+(?P<name>\w+))?"+BLOCK_START+")")
    # stack = []
    def __init__(self, end=None, name=None, loc=None):
        self.name = name
        self.loc = loc
        self.is_end = False
        self.end_node = None

        if end is not None:
            Clickable.stack[-1].end_node = self
            self.is_end = True
            Clickable.stack.pop()
        else:
            Clickable.stack.append(self)

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

class AwaitSelect(MastNode):
    rule = re.compile(r"await[ \t]+select[ \t](?P<console>comms|weapons|grid|science)"+TIMEOUT_REGEX)
    def __init__(self, console=None,minutes=None, seconds=None, loc=None):
        self.loc = loc
        self.console = console
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

class ButtonControl(MastNode):
    rule = re.compile(r"""((button[ \t]+(?P<q>['"]{3}|["'])(?P<message>[ \t\S]+?)(?P=q))([ \t]*data[ \t]*=[ \t]*(?P<data>"""+PY_EXP_REGEX+r"""))?"""+OPT_STYLE_REF_RULE+IF_EXP_REGEX+r"[ \t]*"+BLOCK_START+")|(?P<end>end_button)")
    stack = []
    def __init__(self, message, q, data=None, py=None, if_exp=None, end=None,style_name=None, style=None, style_q=None, loc=None):
        #self.message = message
        self.loc = loc
        if message: #Message is none for end
            self.message = self.compile_formatted_string(message)
        self.end_node = None
        self.is_end = False
    
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

        self.style_def = None
        self.style_name = None
        if style is not None:
            self.style_def = StyleDefinition.parse(style)
        elif style_name is not None:
            self.style_name = style_name



FLOAT_VALUE_REGEX = r"[+-]?([0-9]*[.])?[0-9]+"

class SliderControl(MastNode):
    rule = re.compile(r"""(?P<is_int>intslider|slider|scrollbar)"""+
        r"""[ \t]+(?P<var>\w+)"""+
        r"""[ \t]+(?P<q>['"]{3}|["'])(?P<props>[ \t\S]+?)(?P=q)"""+
        OPT_STYLE_REF_RULE)
    def __init__(self, is_int=None, var=None, q=None, props=None, style_name=None, style=None, style_q=None,loc=None):
        self.loc = loc
        self.var= var
        self.is_int = (is_int=="intslider")
        self.is_scroll = (is_int=="scrollbar")
        self.props = self.compile_formatted_string(props)
        
        self.style_def = None
        self.style_name = None
        if style is not None:
            self.style_def = StyleDefinition.parse(style)
        elif style_name is not None:
            self.style_name = style_name
    
class CheckboxControl(MastNode):
    rule = re.compile(r"""checkbox[ \t]+(?P<var>[ \t\S]+)[ \t]+(?P<q>['"]{3}|["'])(?P<message>[ \t\S]+?)(?P=q)"""+OPT_STYLE_REF_RULE)
    def __init__(self, var=None, message=None, q=None, style_name=None, style=None, style_q=None, loc=None):
        self.loc = loc
        self.var= var
        #self.message = message
        self.message = self.compile_formatted_string(message)

        self.style_def = None
        self.style_name = None
        if style is not None:
            self.style_def = StyleDefinition.parse(style)
        elif style_name is not None:
            self.style_name = style_name

class Icon(MastNode):
    rule = re.compile(r"""icon[ \t]+(?P<q>['\"]{3}|[\"'])(?P<props>[ \t\S]+?)(?P=q)"""+OPT_STYLE_REF_RULE)
    def __init__(self, props=None, q=None, style_name=None, style=None, style_q=None, loc=None):
        self.loc = loc
        self.props = self.compile_formatted_string(props)

        self.style_def = None
        self.style_name = None
        if style is not None:
            self.style_def = StyleDefinition.parse(style)
        elif style_name is not None:
            self.style_name = style_name


class RadioControl(MastNode):
    rule = re.compile(r"""(?P<radio>radio|vradio)[ \t]+(?P<var>[ \t\S]+)[ \t]+(?P<q>['"]{3}|["'])(?P<message>[ \t\S]+?)(?P=q)"""+OPT_STYLE_REF_RULE)
    def __init__(self, radio, var=None, message=None, q=None, style_name=None, style=None, style_q=None, loc=None):
        self.loc = loc
        self.vertical = radio == "vradio"
        self.var= var
        self.message = self.compile_formatted_string(message)

        self.style_def = None
        self.style_name = None
        if style is not None:
            self.style_def = StyleDefinition.parse(style)
        elif style_name is not None:
            self.style_name = style_name


class RerouteGui(MastNode):
    rule = re.compile(r"""reroute([ \t]+((?P<gui>server|clients)|(client[ \t]+(?P<var>[_\w][\w]*))))?[ \t]+(?P<label>[_\w][\w]*)""")
    def __init__(self, gui, var=None, label=None, loc=None):
        self.loc = loc
        self.gui = gui
        self.var = var
        self.label = label

        

class TextInputControl(MastNode):
    
    rule = re.compile(r"""input[ \t]+(?P<var>[_\w][\w]*)([ \t]+(?P<q>['"]{3}|["'])(?P<label>[ \t\S]+?)(?P=q))?"""+OPT_STYLE_REF_RULE)
    def __init__(self, var=None, label=None,q=None, style_name=None, style=None, style_q=None, loc=None):
        self.loc = loc
        self.var= var
        #print(f"node {label}")
        self.label = self.compile_formatted_string(label) if label is not None else None
        #print(f"self label {self.label}")

        self.style_def = None
        self.style_name = None
        if style is not None:
            self.style_def = StyleDefinition.parse(style)
        elif style_name is not None:
            self.style_name = style_name



class DropdownControl(MastNode):
    
    rule = re.compile(r"""(dropdown[ \t]+(?P<var>[ \t\S]+)[ \t]+(?P<q>['"]{3}|["'])(?P<values>[\s\S]+?)(?P=q)"""+OPT_STYLE_REF_RULE+BLOCK_START+""")|(?P<end>end_dropdown)""")
    stack = []
    def __init__(self, var=None, values=None, q=None,end=None, style_name=None, style=None, style_q=None, loc=None):
        self.loc = loc
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
        
        self.style_def = None
        self.style_name = None
        if style is not None:
            self.style_def = StyleDefinition.parse(style)
        elif style_name is not None:
            self.style_name = style_name

class ImageControl(MastNode):
    rule = re.compile(r"""image[ \t]*(?P<q>['"]{3}|["'])(?P<file>[ \t\S]+?)(?P=q)"""+OPT_STYLE_REF_RULE)
    def __init__(self, file, q, style_name=None, style=None, style_q=None, loc=None):
        self.loc = loc
        self.file = self.compile_formatted_string(file)
        
        self.style_def = None
        self.style_name = None
        if style is not None:
            self.style_def = StyleDefinition.parse(style)
        elif style_name is not None:
            self.style_name = style_name



class WidgetList(MastNode):
    #rule = re.compile(r'tell\s+(?P<to_tag>\w+)\s+(?P<from_tag>\w+)\s+((['"]{3}|["'])(?P<message>[\s\S]+?)(['"]{3}|["']))')
    #(\s+color\s*["'](?P<color>[ \t\S]+)["'])?
    rule = re.compile(r"""widget_list[ \t]+((?P<clear>clear)|(?P<console>['"]\w+['"])([ \t]*(?P<q>['"]{3}|["'])(?P<widgets>[ \t\S]+?)(?P=q)))""")
    def __init__(self, clear, console, widgets, q, loc=None):
        self.loc = loc
        if clear == "clear":
            self.console = ""
            self.widgets = ""
        else:
            self.console = console
            self.widgets = widgets

class BuildaConsole(MastNode):
    rule = re.compile(r"""(activate[ \t]+console[ \t]+(?P<console>\w+))|(layout[ \t]+widget[ \t]+['"](?P<widget>\w+)['"])""")
    def __init__(self, console, widget, loc=None):
        self.loc = loc
        self.console = console
        self.widget = widget


class Console(MastNode):
    #rule = re.compile(r'tell\s+(?P<to_tag>\w+)\s+(?P<from_tag>\w+)\s+((['"]{3}|["'])(?P<message>[\s\S]+?)(['"]{3}|["']))')
    #(\s+color\s*["'](?P<color>[ \t\S]+)["'])?
    rule = re.compile(r"""console[ \t]+(?P<console>\w+)""")
    def __init__(self,  console, loc=None):
        self.loc = loc
        self.var = False
        widgets = None
        match console:
            case "helm":
                console =  "normal_helm"
                widgets = "3dview^2dview^helm_movement^throttle^request_dock^shield_control^ship_data^text_waterfall^main_screen_control"
            case "weapons":
                console =  "normal_weap"
                widgets = "2dview^weapon_control^weap_beam_freq^ship_data^shield_control^text_waterfall^main_screen_control"
            case "science":
                console =  "normal_sci"
                widgets = "science_2d_view^ship_data^text_waterfall^science_data^science_sorted_list"
            case "engineering":
                console =  "normal_engi"
                widgets = "ship_internal_view^grid_object_list^grid_face^grid_control^text_waterfall^eng_heat_controls^eng_power_controls^ship_data"
            case "comms":
                console =  "normal_comm"
                widgets = "text_waterfall^comms_waterfall^comms_control^comms_face^comms_sorted_list^ship_data^red_alert"
            case "mainscreen":
                console =  "normal_main"
                widgets = "3dview^ship_data^text_waterfall"
            case "clear":
                console = ""
                widgets = ""
            case _:
                self.var = True

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
            Icon,
            GuiContent,
            Blank,
            Hole,
            Clickable,
            Section,
            Style,
        Choose,
        Disconnect,
        OnChange,
        OnClick,
        AwaitGui,
        AwaitSelect,
        ButtonControl,
        RerouteGui,
        SliderControl,
        CheckboxControl,
        RadioControl,
        DropdownControl,
        ImageControl,
        TextInputControl,
        WidgetList,
        Console,
        BuildaConsole,
        Refresh
    ] + MastSbs.nodes 
