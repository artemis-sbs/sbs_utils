from .quest import IF_EXP_REGEX, JUMP_ARG_REGEX,TIME_JUMP_REGEX, Quest, QuestNode, QuestError, OPT_COLOR, TIMEOUT_REGEX
from .sbsquest import SbsQuest, Button
import re

class Row(QuestNode):
    rule = re.compile(r"""row""")
    def __init__(self):
        pass

class Refresh(QuestNode):
    rule = re.compile(r"""refresh\s*(?P<label>\w+)""")
    def __init__(self, label):
        self.label = label


class Text(QuestNode):
    #rule = re.compile(r'tell\s+(?P<to_tag>\w+)\s+(?P<from_tag>\w+)\s+((['"]{3}|["'])(?P<message>[\s\S]+?)(['"]{3}|["']))')
    #(\s+color\s*["'](?P<color>[ \t\S]+)["'])?
    rule = re.compile(r"""((['"]{3,})(\n)?(?P<message>[\s\S]+?)(\n)?(['"]{3,}))"""+IF_EXP_REGEX)
    def __init__(self, message, if_exp):
        self.message = self.compile_formatted_string(message)
        if if_exp is not None:
            if_exp = if_exp.lstrip()
            self.code = compile(if_exp, "<string>", "eval")
        else:
            self.code = None

class AppendText(QuestNode):
    #rule = re.compile(r'tell\s+(?P<to_tag>\w+)\s+(?P<from_tag>\w+)\s+((['"]{3}|["'])(?P<message>[\s\S]+?)(['"]{3}|["']))')
    #(\s+color\s*["'](?P<color>[ \t\S]+)["'])?
    rule = re.compile(r"""(([\^]{3,})(\n)?(?P<message>[\s\S]+?)(\n)?([\^]{3,}))"""+IF_EXP_REGEX)
    def __init__(self, message, if_exp):
        self.message = self.compile_formatted_string(message)
        if if_exp is not None:
            if_exp = if_exp.lstrip()
            self.code = compile(if_exp, "<string>", "eval")
        else:
            self.code = None


class Face(QuestNode):
    rule = re.compile(r"""face\s*(((['"]{3}|["'])(?P<face>[\s\S]+?)\3)|(?P<face_exp>[ \t\S]+)?)""")
    def __init__(self, face=None, face_exp=None):
        self.face = face
        if face_exp:
            face_exp = face_exp.lstrip()
            self.code = compile(face_exp, "<string>", "eval")
        else:
            self.code = None

class Ship(QuestNode):
    rule = re.compile(r"""ship\s+(?P<ship>[ \t\S]+)""")
    def __init__(self, ship=None):
        self.ship= ship

class Blank(QuestNode):
    rule = re.compile(r"""blank""")
    def __init__(self):
        pass

class Section(QuestNode):
    rule = re.compile(r"""section""")
    def __init__(self):
        pass

class Area(QuestNode):
    rule = re.compile(r"""area\s+(?P<left>\d+)\s+(?P<top>\d+)\s+(?P<right>\d+)\s+(?P<bottom>\d+)""")
    def __init__(self, left=None, top=None, right=None, bottom=None):
        self.left = int(left) if left else 0
        self.top = int(top) if top else 0
        self.right = int(right) if right else 100
        self.bottom= int(bottom) if bottom else 100
        

class Choices(QuestNode):
    rule = re.compile(r"""choose"""+TIMEOUT_REGEX)
    def __init__(self, minutes=None, seconds=None, time_pop=None,time_push="", time_jump=""):
        self.seconds = 0 if  seconds is None else int(seconds)
        self.minutes = 0 if  minutes is None else int(minutes)
        self.time_jump = time_jump
        self.time_push = time_push == ">"
        self.time_pop = time_pop is not None
        self.buttons = Button.stack
        Button.stack = []

class ButtonControl(QuestNode):
    rule = re.compile(r"""button\s+["'](?P<message>.+?)["']"""+JUMP_ARG_REGEX+IF_EXP_REGEX)
    def __init__(self, message, pop, push, jump, if_exp):
        self.message = message
        self.jump = jump
        self.push = push == ">"
        self.pop = pop is not None
    
        if if_exp:
            if_exp = if_exp.lstrip()
            self.code = compile(if_exp, "<string>", "eval")
        else:
            self.code = None
        



class StoryQuest(SbsQuest):
    nodes = [
        # sbs specific
        Row,
            Text,
            AppendText,
            Face,
            Ship,
            Blank,
            Section,
            Area,
        Choices,
            ButtonControl,
        Refresh
    ] + SbsQuest.nodes 
