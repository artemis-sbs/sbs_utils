from email import message
from enum import IntEnum
import re
import ast
import math

class QuestError:
    def __init__(self, message, line_no):
        if isinstance(message, str):
            self.messages = [message]
        else:
            self.messages = message
        self.line_no = line_no

class QuestRuntimeNode:
    def enter(self, quest, runner, node):
        pass
    def leave(self, quest, runner, node):
        pass

    def poll(self, quest, runner, node):
        return PollResults.OK_ADVANCE_TRUE

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
        #self.exp = exp
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

class Tell(QuestNode):
    #rule = re.compile(r'tell\s+(?P<to_tag>\w+)\s+(?P<from_tag>\w+)\s+((['"]{3}|["'])(?P<message>[\s\S]+?)(['"]{3}|["']))')
    rule = re.compile(r"""tell\s+(?P<to_tag>\w+)\s+(?P<from_tag>\w+)\s+((['"]{3}|["'])(?P<message>[\s\S]+?)\4)""")
    def __init__(self, to_tag, from_tag, message):
        self.to_tag = to_tag
        self.from_tag = from_tag
        self.message = message
    def validate(self, quest):
        messages = []
        if quest.inputs.get(self.to_tag) is None:
            messages.append(f'Tell cannot find {self.to_tag}')
        elif quest.inputs.get(self.from_tag) is None:
            messages.append(f'Tell cannot find {self.from_tag}')
        if len(messages):
            return QuestError(messages, self.line_no)

    def gen(self):
        return f'tell {self.to_tag} {self.from_tag} "{self.message}"'


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


class Comms(QuestNode):
    rule = re.compile(r'comms\s*(?P<to_tag>\w+)\s*(?P<from_tag>\w+)(\s*timeout(\s*(?P<minutes>\d+)m)?(\s*(?P<seconds>\d+)s)?\s*->\s*(?P<time_jump>\w+)?)?')
    def __init__(self, to_tag, from_tag, buttons=None, minutes=None, seconds=None, time_jump=""):
        self.to_tag = to_tag
        self.from_tag = from_tag
        self.buttons = buttons if buttons is not None else []
        self.seconds = 0 if  seconds is None else int(seconds)
        self.minutes = 0 if  minutes is None else int(minutes)
        self.time_jump = time_jump
    def add_child(self, obj):
        self.buttons.append(obj)

    def validate(self, quest):
        messages = []
        if quest.inputs.get(self.to_tag) is None:
           messages.append( f'Comms cannot find {self.to_tag}')
        elif quest.inputs.get(self.from_tag) is None:
            messages.append(f'Comms cannot find {self.from_tag}')
        elif self.time_jump and quest.labels.get(self.time_jump) is None:
            messages.append(f'Comms cannot find {self.time_jump}')
            
        for button in self.buttons:
            err = button.validate(quest)
            if err:
                messages.extend(err.messages)
        if len(messages):
            return QuestError(messages, self.line_no)

    def gen(self):
        s = f"comms {self.to_tag} {self.from_tag}"
        if self.minutes or self.seconds:
            s += f" timeout"
        if self.minutes:
            s += f" {self.minutes}m"
        if self.seconds:
            s += f" {self.seconds}s"
        if self.time_jump:
            s += f"->{self.time_jump}"
        
        for button in self.buttons:
            s += '\n'
            s+= button.gen()
        return s


class Button(QuestNode):
    rule = re.compile(r'button\s+"(?P<message>.+?)"\s*->\s*(?P<jump>\w+)')
    def __init__(self, message, jump):
        self.message = message
        self.jump = jump

    def validate(self, quest):
        if quest.labels.get(self.jump) is None:
            return QuestError(f'Button cannot find {self.jump}', self.line_no)

    def gen(self):
        return f'   button "{self.message}" -> {self.jump}'

class Near(QuestNode):
    rule = re.compile(r'near\s*(?P<to_tag>\w+)\s*(?P<from_tag>\w+)\s*(?P<distance>\d+)\s*(->\s*(?P<jump>\w+))?(\s*timeout(\s*(?P<minutes>\d+)m)?(\s*(?P<seconds>\d+)s)?\s*->\s*(?P<time_jump>\w+)?)?')
    def __init__(self, to_tag, from_tag, distance, jump, minutes=None, seconds=None, time_jump=""):
        self.to_tag = to_tag
        self.from_tag = from_tag
        self.distance = 0 if distance is None else int(distance)
        self.jump = jump
        self.seconds = 0 if  seconds is None else int(seconds)
        self.minutes = 0 if  minutes is None else int(minutes)
        self.time_jump = time_jump

    def validate(self, quest):
        messages = []
        if quest.inputs.get(self.to_tag) is None:
            messages.append(f'Near cannot find {self.to_tag}')
        elif quest.inputs.get(self.from_tag) is None:
            messages.append(f'Near cannot find {self.from_tag}')

        if len(messages):
            return QuestError(messages, self.line_no)

    def gen(self):
        s = f"near {self.to_tag} {self.from_tag} {self.distance} -> {self.jump}"
        if self.minutes or self.seconds:
            s += f" timeout"
        if self.minutes:
            s += f" {self.minutes}m"
        if self.seconds:
            s += f" {self.seconds}s"
        if self.time_jump:
            s += f"->{self.time_jump}"
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
                    self.inputs[cmd.name] = cmd
                    active = cmd
                case _:
                    active.cmds.append(cmd)

    nodes = [
        Label,
        Input,
        Var,
        Assign,
        End,
        Jump,
        Delay,
        
        Tell,
        Comms,
        Button,
        Near
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
        
            for node_cls in Quest.nodes:
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
                


    def compile_OLD(self, lines):
        self.clear()
        active = self.labels["main"]
        # tag =  "\w+"
        lines = lines.split('\n')
        for line_no, line in enumerate(lines):
            parsed = False
            indent = first_non_space_index(line)
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
                line = line[indent:]

            for node_cls in Quest.nodes:
                mo = node_cls.rule.match(line)

                if mo:
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

                        case "Var":
                            var = Var(**data)
                            self.vars[data['name']] = var


                        
                        case _:
                            obj = node_cls(**data)
                            obj.line_no = line_no
                            self.cmd_stack[-1].add_child(obj)
                            active_cmd = obj
                    break
            if not parsed:
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



# Using enum.IntEnum 
class PollResults(IntEnum):
     OK_JUMP = 1
     OK_ADVANCE_TRUE = 2
     OK_ADVANCE_FALSE=3
     OK_RUN_AGAIN = 4
     OK_END = 99

class EndRunner(QuestRuntimeNode):
    def poll(self, quest, thread, node):
        return PollResults.OK_END

class AssignRunner(QuestRuntimeNode):
    def poll(self, quest, thread, node):
        allowed = {"math": math}| quest.vars
        value = eval(node.code, {"__builtins__": {}}, allowed)
        locals = {"__quest_value": value} | quest.vars
        exec(f"""{node.lhs} = __quest_value""",{"__builtins__": {}}, locals)

        return PollResults.OK_ADVANCE_TRUE

class JumpRunner(QuestRuntimeNode):
    def poll(self, quest, thread, node):
        thread.jump(node.label)
        return PollResults.OK_JUMP

    
class DelayRunner(QuestRuntimeNode):
    def enter(self, quest, thread, node):
        self.timeout = node.minutes*60+node.seconds
        self.tag = None

    def poll(self, quest, thread, node):
        self.timeout -= 1
        if self.timeout <= 0:
            return PollResults.OK_ADVANCE_TRUE

        return PollResults.OK_RUN_AGAIN


class QuestThread:
    
    def __init__(self, main):
        self.done = False
        self.runner = None
        self.main= main

    def jump(self, label = "main"):
        self.cmds = self.main.quest.labels[label].cmds
        self.active_label = label
        self.active_cmd = 0
        #self.runner = None
        self.done = False
        self.next(True)
    
    def tick(self):
        if self.done:
            # should unschedule
            return PollResults.OK_END

        while not self.done:
            if self.runner:
                cmd = self.cmds[self.active_cmd]
                match self.runner.poll(self.main.quest, self, cmd):
                    case PollResults.OK_ADVANCE_TRUE:
                        self.next()
                    case PollResults.OK_END:
                        self.done = True
                    case PollResults.OK_RUN_AGAIN:
                        break

        return PollResults.OK_RUN_AGAIN

    def next(self, first=False):
        if self.runner:
            cmd = self.cmds[self.active_cmd]
            self.runner.leave(self.main.quest, self, cmd)

        if not first:
            self.active_cmd += 1
        if self.active_cmd >= len(self.cmds):
            self.done = True
            return
        
        cmd = self.cmds[self.active_cmd]
        runner_cls = self.main.nodes.get(cmd.__class__.__name__, QuestRuntimeNode)
        
        self.runner = runner_cls()
        self.runner.enter(self.main.quest, self, cmd)



class QuestRunner:
    runners = {
        "End": EndRunner,
        "Jump": JumpRunner,
        "Assign": AssignRunner,
        "Delay": DelayRunner,
    }

    def __init__(self, quest: Quest, inputs, overrides=None):
        if overrides is None:
            overrides = {}
        self.nodes = QuestRunner.runners | overrides
        self.inputs = inputs
        self.vars = inputs | quest.vars
        self.quest = quest
        self.threads = []
    

    def start(self, label = "main"):
        t= QuestThread(self)
        t.jump(label)
        self.threads.append(t)

    def tick(self):
        done = []
        for thread in self.threads:
            res = thread.tick()
            if res == PollResults.OK_END:
                done.append(thread)
        for rem in done:
            self.threads.remove(rem)
        if len(self.threads):
            return True
        else:
            return False




    
