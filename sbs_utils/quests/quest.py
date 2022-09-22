from email import message
from enum import IntEnum
import re
import ast
import math

# tokens
#
# Optional color:
#       (\s+color\s*["'](?P<color>[ \t\S]+)["'])?
# name tag
#       (?P<name>\w+)
# Conditional
#       (\s+if(?P<if>.+))?
#
class QuestError:
    def __init__(self, message, line_no):
        if isinstance(message, str):
            self.messages = [message]
        else:
            self.messages = message
        self.line_no = line_no


class QuestNode:
    def add_child(self, cmd):
        pass

    def validate(self, quest):
        return None

    def gen(self):
        return ''

class Label(QuestNode):
    rule = re.compile(r'==\s*(?P<name>\w+)\s*==')
    def __init__(self, name):
        self.name = name
        self.cmds = []

    def add_child(self, cmd):
        self.cmds.append(cmd)
        

class Input(QuestNode):
    rule = re.compile(r'input\s+(?P<name>\w+)')
    def __init__(self, name):
        self.name = name

class Comment(QuestNode):
    rule = re.compile(r'#.*')
    def __init__(self):
        pass

class QuestData(object):
    def __init__(self, dictionary):
        #for dictionary in initial_data:
        for key in dictionary:
            setattr(self, key, dictionary[key])
    def __repr__(self):
        return repr(vars(self))


class Var(QuestNode):
    rule = re.compile(r"""var\s*(?P<name>\w+)\s*=\s* (?P<val>(\[[\s\S]+?\])|(\{[\s\S]+?\})|([+-]?\d+(\.\d+)?)|((["']{3}|["'])[\s\S]+?\8))""")
    def __init__(self, name, val):
        self.name = name
        self.val = val
        try:
            self.value = ast.literal_eval(val)
            if type(self.value) is dict:
                self.value = QuestData(self.value)

        except:
            self.value = None

    def validate(self, quest):
        if self.value is None:
            return QuestError( f'variable {self.name} cannot be set {self.val}', self.line_no)
    def gen(self):
        return f'var {self.name} {repr(self.value)}'
    

class Assign(QuestNode):
    rule = re.compile(r'(?P<lhs>[\w\.\[\]]+)\s*=(?P<exp>.*)')
    def __init__(self, lhs, exp):
        self.lhs = lhs
        exp = exp.lstrip()
        self.code = compile(exp, "<string>", "eval")
    def validate(self, quest):
        return None
        #if quest.labels.get(self.label) is None:
        #    return QuestError( f'Jump cannot find {self.to_tag}', self.line_no)
    def gen(self):
        return f'{self.lhs} = ...'



class Jump(QuestNode):
    rule = re.compile(r'->\s*(?P<label>\w+)')
    def __init__(self, label):
        self.label = label
    def validate(self, quest):
        if quest.labels.get(self.label) is None:
            return QuestError( f'Jump cannot find {self.to_tag}', self.line_no)
    def gen(self):
        return f'-> {self.label}"'

class Parallel(QuestNode):
    """
    Creates a new 'thread' to run in parallel
    """
    rule = re.compile(r"""((?P<name>[\w\.\[\]]+)\s*)?=>\s*(?P<label>\w+)""")
    def __init__(self, name=None, label=None):
        self.name = name
        self.label = label
        self.cmds = []

    def validate(self, quest):
        for cmd in self.cmds:
            if type(cmd) != Assign:
                return QuestError( f'Only assignments allowed as child', self.line_no)

        return None
        #if quest.labels.get(self.label) is None:
        #    return QuestError( f'Jump cannot find {self.to_tag}', self.line_no)
    def gen(self):
        s=""
        if self.name: 
            s+= f'{self.name} '
        s += f'=> {self.label}'
        

    def add_child(self, cmd):
        self.cmds.append(cmd)

class Await(QuestNode):
    """
    waits for an existing or a new 'thread' to run in parallel
    this needs to be a rule before Parallel
    """
    rule = re.compile(r"""await(\s*(?P<spawn>=>))?\s*(?P<label>\w+)""")
    def __init__(self, name=None, spawn=None, label=None):
        self.spawn = True if spawn is not None else False
        self.label = label
        self.cmds = []

    def validate(self, quest):
        for cmd in self.cmds:
            if type(cmd) != Assign:
                return QuestError( f'Only assignments allowed as child', self.line_no)

        return None
        #if quest.labels.get(self.label) is None:
        #    return QuestError( f'Jump cannot find {self.to_tag}', self.line_no)
    def gen(self):
        s=""
        if self.spawn: 
            s+= f'await {self.label} '
        s += f'await => {self.label}'
        

    def add_child(self, cmd):
        self.cmds.append(cmd)

class Cancel(QuestNode):
    """
    Cancels a new 'thread' to run in parallel
    """
    rule = re.compile(r"""cancel\s*(?P<name>[\w\.\[\]]+)""")
    def __init__(self, lhs=None, name=None):
        self.name = name

    def validate(self, quest):
        return None
        #if quest.labels.get(self.label) is None:
        #    return QuestError( f'Jump cannot find {self.to_tag}', self.line_no)
    def gen(self):
        s=""
        s += f'cancel {self.name}'



class End(QuestNode):
    rule = re.compile(r'->\s*END')
    def validate(self, _):
        return None
    def gen(self):
        return "->END"

class Delay(QuestNode):
    rule = re.compile(r'delay(\s*(?P<minutes>\d+)m)?(\s*(?P<seconds>\d+)s)?')
    def __init__(self, seconds=None, minutes=None):
        self.seconds = 0 if  seconds is None else int(seconds)
        self.minutes = 0 if  minutes is None else int(minutes)
    def validate(self, _):
        if self.minutes<=0 and self.seconds<=0:
            return QuestError("Delay has no time set", self.line_no)
    def gen(self):
        s = 'delay '
        if self.minutes:
            s += f"{self.minutes}m"
        if self.seconds:
            s += f"{self.seconds}s"
        return s





class Rule:
    def __init__(self, re, cls):
        self.re = re
        self.cls = cls

def first_non_space_index(s):
    for idx, c in enumerate(s):
        if not c.isspace():
            return idx
        if c=='\n':
            return idx

def first_non_newline_index(s):
    for idx, c in enumerate(s):
        if c!='\n':
            return idx


class Quest:
    def __init__(self, cmds=None):
        if cmds is None:
            return
        if isinstance(cmds, str):
            cmds = self.compile(cmds)
        else:
            self.build(cmds)
    
    def build(self, cmds):
        """
        Used to build via code not a script file
        should just process level things e.g. Input, Label, Var
        """
        self.clear()
        active = self.labels["main"]

        for cmd in cmds:
            match cmd.__class__.__name__:
                case "Input":
                    self.inputs[cmd.name] = cmd
                case "Label":
                    self.labels[cmd.name] = cmd
                    active = cmd
                case "Var":
                    self.vars[cmd.name] = cmd
                    active = cmd
                case _:
                    active.cmds.append(cmd)

    nodes = [
        Comment,
        Label,
        Input,
        Var,
        Await, # needs to be before Parallel
        Parallel, # needs to be before Assign
        Cancel,
        Assign,
        End,
        Jump,
        Delay,
    ]

    def clear(self):
        self.inputs = {}
        self.vars = {}
        self.labels = {} 
        self.labels["main"] = Label("main")
        self.cmd_stack = [self.labels["main"]]
        self.indent_stack = [0]
    
    def compile(self, lines):
        self.clear()
        active = self.labels["main"]
        line_no = -1
        while len(lines):
            mo = first_non_newline_index(lines)
            #line = lines[:mo]
            lines = lines[mo:]
            parsed = False
            indent = first_non_space_index(lines)
            if indent is None:
                continue
            if indent > self.indent_stack[-1]:
                # new indent
                self.cmd_stack.append(active_cmd)
                self.indent_stack.append(indent)
            while indent < self.indent_stack[-1]:
                self.cmd_stack.pop()
                self.indent_stack.pop()
            if indent>0:
                # strip spaces
                lines = lines[indent:]
        
            for node_cls in self.__class__.nodes:
                mo = node_cls.rule.match(lines)
                if mo:
                    span = mo.span()
                    line = lines[span[0]:span[1]]
                    lines = lines[span[1]:]
                    
                    parsed = True
                    data = mo.groupdict()
                    
                    match node_cls.__name__:
                        case "Label":
                            active = Label(**data)
                            self.labels[data['name']] = active
                            self.cmd_stack.pop()
                            self.cmd_stack.append(active)
                        case "Input":
                            input = Input(**data)
                            self.inputs[data['name']] = input

                        case "Comment":
                            # obj.line_no = line_no
                            # self.cmd_stack[-1].add_child(obj)
                            # active_cmd = obj
                            pass

                        case "Var":
                            var = Var(**data)
                            if var.value is not None:
                                self.vars[data['name']] = var.value


                        
                        case _:
                            obj = node_cls(**data)
                            obj.line_no = line_no
                            self.cmd_stack[-1].add_child(obj)
                            active_cmd = obj
                    break
            if not parsed:
                mo = lines.find('\n')
                line = lines[:mo]
                lines = lines[mo+1:]
                print(f"ERROR: {line_no} - {line}")




def validate_quest(quest):
    for name, value in quest.vars.items():
        validate_var(quest, name, value)

    for label in quest.labels.values():
        print()
        print(f"=={label.name}==")
        validate_label(quest, label)

def validate_label(quest, label):
    for cmd in label.cmds:
        validate_cmd(quest, cmd)

def validate_cmd(quest, cmd):
    err = cmd.validate(quest)
    if err:
        print(f"ERROR: line {err.line_no}")
        for msg in err.messages:
            print('\t'+msg)

    print(cmd.gen())

def validate_var(quest, name, value):
    if value is None:
        print(f"ERROR: var set is invalid {name}")
    v = Var(name, None)
    v.value = value
    print(v.gen())

