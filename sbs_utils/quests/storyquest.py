from .quest import JUMP_ARG_REGEX,TIME_JUMP_REGEX, Quest, QuestNode, QuestError, OPT_COLOR, TIMEOUT_REGEX
from .sbsquest import SbsQuest
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
    rule = re.compile(r"""text\s*((['"]{3}|["'])(?P<message>[\s\S]+?)\2)""")
    def __init__(self, message):
        self.message = message
        #self.color = color

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

class Separator(QuestNode):
    rule = re.compile(r"""separate""")
    def __init__(self):
        pass

class Section(QuestNode):
    rule = re.compile(r"""section""")
    def __init__(self):
        pass

class Size(QuestNode):
    rule = re.compile(r"""bounds\s+(?P<left>\d+)\s+(?P<top>\d+)\s+(?P<right>\d+)\s+(?P<bottom>\d+)""")
    def __init__(self, left=None, top=None, right=None, bottom=None):
        self.left = int(left) if left else 0
        self.top = int(top) if top else 0
        self.right = int(right) if right else 100
        self.bottom= int(bottom) if bottom else 100
        

class Choices(QuestNode):
    rule = re.compile(r"""choices"""+TIMEOUT_REGEX)
    def __init__(self, buttons=None, minutes=None, seconds=None, time_pop=None,time_push="", time_jump=""):
        self.buttons = buttons if buttons is not None else []
        self.seconds = 0 if  seconds is None else int(seconds)
        self.minutes = 0 if  minutes is None else int(minutes)
        self.time_jump = time_jump
        self.time_push = time_push == ">"
        self.time_pop = time_pop is not None
    def add_child(self, obj):
        self.buttons.append(obj)

class Button(QuestNode):
    rule = re.compile(r"""(?P<button>\*|\+|button|button\s+once)\s+["](?P<message>.+?)["]"""+OPT_COLOR+JUMP_ARG_REGEX+r"""(\s+if(?P<if_exp>.+))?""")
    def __init__(self, button, message, pop, jump, push, color, if_exp):
        self.message = message
        self.jump = jump
        self.push = push == '>'
        self.pop = pop == "<<-"
        self.sticky = (button == '+' or button=="button")
        self.color = color
        
        self.visited = set() if not self.sticky else None

        if if_exp:
            if_exp = if_exp.lstrip()
            self.code = compile(if_exp, "<string>", "eval")
        else:
            self.code = None
        

    def visit(self, id_tuple):
        if self.visited is not None:
            self.visited.add(id_tuple)
    
    def been_here(self, id_tuple):
        if self.visited is not None:
            return (id_tuple in self.visited)
        return False

    def should_present(self, id_tuple):
        if self.visited is not None:
            return not id_tuple in self.visited
        return True




class StoryQuest(SbsQuest):
    nodes = SbsQuest.nodes + [
        # sbs specific
        Row,
            Text,
            Face,
            Ship,
            Separator,
            Section,
            Size,
        Choices,
            Button,
        Refresh
    ] 
