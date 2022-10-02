import pickle
from email import message
from enum import IntEnum, Enum
import re
import ast
import os
from .. import fs
from zipfile import ZipFile
from .. import faces
import math
import itertools


# tokens
#
# Optional color:
#       (\s+color\s*["'](?P<color>[ \t\S]+)["'])?
# name tag
#       (?P<name>\w+)
# Conditional
#       (\s+if(?P<if>.+))?
#
JUMP_CMD_REGEX = r"""((?P<pop><<-)|(->(?P<push>>)?\s*(?P<jump>\w+)))"""
JUMP_ARG_REGEX = r"""(\s*((?P<pop><<-)|(->(?P<push>>)?\s*(?P<jump>\w+))))"""
OPT_JUMP_REGEX = JUMP_ARG_REGEX+r"""?"""
TIME_JUMP_REGEX = r"""((?P<time_pop><<-)|(->(?P<time_push>>)?\s*(?P<time_jump>\w+)))?"""
MIN_SECONDS_REGEX = r"""(\s*((?P<minutes>\d+))m)?(\s*((?P<seconds>\d+)s))?"""
TIMEOUT_REGEX = r"(\s*timeout"+MIN_SECONDS_REGEX + \
    r"\s*" + TIME_JUMP_REGEX + r")?"
OPT_COLOR = r"""(\s*color\s*["'](?P<color>[ \t\S]+)["'])?"""
IF_EXP_REGEX = r"""(\s+if(?P<if_exp>.+))?"""
LIST_REGEX = r"""(\[[\s\S]+?\])"""
DICT_REGEX = r"""(\{[\s\S]+?\})"""
STRING_REGEX = r"""((?P<quote>((["']{3})|["']))[\s\S]+?(?P=quote))"""



class QuestError:
    def __init__(self, message, line_no):
        if isinstance(message, str):
            self.messages = [message]
        else:
            self.messages = message
        self.line_no = line_no


class QuestNode:
    def add_child(self, cmd):
        #print("ADD CHILD")
        pass

    def validate(self, quest):
        return None

    def gen(self):
        return ''

    def compile_formatted_string(self, message):
        if "{" in message:
            message = f"""f'''{message}'''"""
            code = compile(message, "<string>", "eval")
            return code
        else:
            return message


class Label(QuestNode):
    rule = re.compile(r'(={2,})\s*(?P<name>\w+)\s*(={2,})')

    def __init__(self, name):
        self.name = name
        self.cmds = []

    def add_child(self, cmd):
        self.cmds.append(cmd)

class InlineLabel(QuestNode):
    rule = re.compile(r'((\-{2,})(\(\s*((?P<if_exp>.+))\))?(\-{2,}))\n(?P<cmds>[\s\S]+?)\n((\-{2,})(?P<loop>loop)?(\-{2,}))')

    def __init__(self, if_exp=None, loop=None, cmds=None):
        if if_exp:
            if_exp = if_exp.lstrip()
            self.code = compile(if_exp, "<string>", "eval")
        else:
            self.code = None
        self.loop = True if loop is not None and 'loop' in loop else False
        self.cmds = cmds
        self.label_name = None

class PyCode(QuestNode):
    rule = re.compile(r'(\~{2,})\n(?P<py_cmds>[\s\S]+?)\n(\~{2,})')

    def __init__(self, py_cmds=None):
        self.code = compile(py_cmds, "<string>", "exec")


class Input(QuestNode):
    rule = re.compile(r'input\s+(?P<name>\w+)')

    def __init__(self, name):
        self.name = name


class Import(QuestNode):
    rule = re.compile(r'(from\s+(?P<lib>[\w\.\/-]+)\s+)?import\s+(?P<name>[\w\.\/-]+)')

    def __init__(self, name, lib=None):
        self.name = name
        self.lib = lib


class Comment(QuestNode):
    rule = re.compile(r'#[ \t\S]*')

    def __init__(self):
        pass


class QuestData(object):
    def __init__(self, dictionary):
        # for dictionary in initial_data:
        for key in dictionary:
            setattr(self, key, dictionary[key])

    def __repr__(self):
        return repr(vars(self))


class Var(QuestNode):
    rule = re.compile(
        r"""var\s*(?P<name>\w+)\s*=\s* (?P<val>(\[[\s\S]+?\])|(\{[\s\S]+?\})|([+-]?\d+(\.\d+)?)|((["']{3}|["'])[\s\S]+?\8))""")

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
            return QuestError(f'variable {self.name} cannot be set {self.val}', self.line_no)

    def gen(self):
        return f'var {self.name} {repr(self.value)}'


class Scope(Enum):
    SHARED = 1  # per quest instance
    NORMAL = 2  # per runner
    TEMP = 99  # Per thread?



class Assign(QuestNode):
    # '|'+STRING_REGEX+
    rule = re.compile(
        r'(?P<scope>(shared|temp)\s+)?(?P<lhs>[\w\.\[\]]+)\s*=\s*(?P<exp>('+LIST_REGEX+'|'+DICT_REGEX+'|'+STRING_REGEX+'|.*))')

    """ Not this doesn't support destructuring. To do so isn't worth the effort"""
    def __init__(self, scope, lhs, exp, quote=None):
        self.lhs = lhs
        self.scope = Scope.NORMAL if scope is None else Scope[scope.strip(
        ).upper()]
        #print(f"EXP: {exp}")
        #print(f"quote: {quote}")
        exp = exp.lstrip()
        if quote:
            exp = 'f'+exp        
        self.code = compile(exp, "<string>", "eval")

    def validate(self, quest):
        return None
        # if quest.labels.get(self.label) is None:
        #    return QuestError( f'Jump cannot find {self.to_tag}', self.line_no)

    def gen(self):
        return f'{self.lhs} = ...'


class Jump(QuestNode):
    rule = re.compile(JUMP_CMD_REGEX+IF_EXP_REGEX)

    def __init__(self, pop, push, jump, if_exp):
        self.label = jump
        self.push = push == "->>"
        self.pop = pop is not None
        if if_exp:
            if_exp = if_exp.lstrip()
            self.code = compile(if_exp, "<string>", "eval")
        else:
            self.code = None

    def validate(self, quest):
        if quest.labels.get(self.label) is None:
            return QuestError(f'Jump cannot find {self.to_tag}', self.line_no)

    def gen(self):
        if self.push:
            return f'-> {self.label}"'
        elif self.pop:
            return f'<<- {self.label}"'
        else:
            return f'->> {self.label}"'


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
                return QuestError(f'Only assignments allowed as child', self.line_no)

        return None
        # if quest.labels.get(self.label) is None:
        #    return QuestError( f'Jump cannot find {self.to_tag}', self.line_no)

    def gen(self):
        s = ""
        if self.name:
            s += f'{self.name} '
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
                return QuestError(f'Only assignments allowed as child', self.line_no)

        return None
        # if quest.labels.get(self.label) is None:
        #    return QuestError( f'Jump cannot find {self.to_tag}', self.line_no)

    def gen(self):
        s = ""
        if self.spawn:
            s += f'await {self.label} '
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
        # if quest.labels.get(self.label) is None:
        #    return QuestError( f'Jump cannot find {self.to_tag}', self.line_no)

    def gen(self):
        s = ""
        s += f'cancel {self.name}'


class End(QuestNode):
    rule = re.compile(r'->\s*END')

    def validate(self, _):
        return None

    def gen(self):
        return "->END"


class Delay(QuestNode):
    rule = re.compile(r'delay\s*'+MIN_SECONDS_REGEX)

    def __init__(self, seconds=None, minutes=None):
        self.seconds = 0 if seconds is None else int(seconds)
        self.minutes = 0 if minutes is None else int(minutes)

    def validate(self, _):
        if self.minutes <= 0 and self.seconds <= 0:
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
        if c == '\n':
            return idx


def first_non_newline_index(s):
    for idx, c in enumerate(s):
        if c != '\n':
            return idx
    return len(s)


def first_newline_index(s):
    for idx, c in enumerate(s):
        if c == '\n':
            return idx
    return len(s)


class Quest:
    globals = {
        "math": math, 
        "faces": faces, 
        "print": print, 
        "dir":dir, 
        "itertools": itertools,
        "next": next,
        "range": range,
        "__build_class__":__build_class__, # ability to define classes
        "__name__":__name__ # needed to define classes?
    }
    def __init__(self, cmds=None):
        self.lib_name = None

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
        InlineLabel,
        PyCode,
        Input,
        #        Var,
        Import,
        Await,  # needs to be before Parallel
        Parallel,  # needs to be before Assign
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
        self.main_pruned = False
        self.runners = set()
        self.lib_name = None
        self.inline_count = 0

    def to_pickle(self):
        b = pickle.dumps(self.labels)
        with open("test.p") as f:
            f.write(b)

    def prune_main(self):
        if self.main_pruned:
            return
        main = self.labels.get("main")
        # remove all the assigned from the main
        if main is not None:
            main.cmds = [cmd for cmd in main.cmds if not (
                cmd.__class__ == Assign and cmd.scope == Scope.SHARED)]
            self.main_pruned = True

    def add_runner(self, runner):
        self.runners.add(runner)

    def refresh_runners(self, source, label):
        for runner in self.runners:
            if runner == source:
                continue
            runner.refresh(label)

    def remove_runner(self, runner):
        self.runners.remove(runner)

    def from_file(self, filename, lib_name=None):
        """ Docstring"""

        # Import from lib
        if lib_name is not None:
            return self.from_lib_file(filename, lib_name)

        # Import from already in a lib
        if self.lib_name is not None:
            return self.from_lib_file(filename, self.lib_name)
            
        file_name = os.path.join(fs.get_mission_dir(), filename)
        print(f"file to import: {file_name}")
        self.basedir = os.path.dirname(file_name)
        content = None
        errors = []
        try:
            with open(file_name) as f:
                content = f.read()
        except:
            message = f"File load error\nCannot load file {file_name}"
            print(message)
            errors.append(message)

        if content is not None:
            print( f"Compiling file {file_name}")
            errors = self.compile(content)

            if len(errors) > 0:
                message = f"Compile errors\nCannot compile file {file_name}"
                errors.append(message)

        if len(errors) > 0:
            return errors
        return None

    def from_lib_file(self, file_name, lib_name):
        lib_name = os.path.join(fs.get_mission_dir(), lib_name)
        content = None

        errors = []
        try:
            with ZipFile(lib_name) as lib_file:
                print("LIB Opened")
                with lib_file.open(file_name) as f:
                    print("LIB content")
                    content = f.read().decode('UTF-8')
                    print(f"LIB {content[0:10]}")
                    self.lib_name = lib_name
        except:
            message = f"File load error\nCannot load file {file_name}"
            print(message)
            errors.append(message)
            

        if content is not None:
            errors = self.compile(content)

            if len(errors) > 0:
                message = f"Compile errors\nCannot compile file {file_name}"
                errors.append(message)

        if len(errors) > 0:
            return errors
        return None


    def import_content(self, filename, lib_file):
        add = self.__class__()
        errors = add.from_file(filename, lib_file)
        if errors is None:
            for label, node in add.labels.items():
                if label == "main":
                    main = self.labels["main"]
                    main.cmds.extend(node.cmds)
                else:
                    self.labels[label] = node
        return errors

        
    def compile_inline(self, node:InlineLabel):
        add = self.__class__()
        errors = add.compile(node.cmds)
        if len(errors)<1:
            main = add.labels.get("main")
            self.labels[node.label_name] = main
            # add repeat
            # if node.loop:
            #     loop = Jump(None, None, node.label_name,None )
            #     loop.code = node.code
            #     main.cmds.append(loop)
            # # add a pop
            # main.cmds.append(Jump(True, None, None, None))
        else:
            if len(errors) > 0:
                message = f"Compile errors\nCannot compile inline"
                errors.append(message)
        if len(add.labels.keys()) != 1:
            message = f"Compile errors\nInline too many labels"
            if errors is None:
                errors = []
            errors.append(message)

        return errors

    def compile(self, lines):
        self.clear()
        active_cmd = self.labels["main"]
        line_no = 0
        errors = []
        while len(lines):
            mo = first_non_newline_index(lines)
            line_no += mo if mo is not None else 0
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
            if indent > 0:
                # strip spaces
                lines = lines[indent:]

            for node_cls in self.__class__.nodes:
                mo = node_cls.rule.match(lines)
                if mo:
                    span = mo.span()
                    line = lines[span[0]:span[1]]

                    lines = lines[span[1]:]
                    line_no += line.count('\n')
                    parsed = True
                    data = mo.groupdict()
                    # print(f"PARSED: {node_cls.__name__:}")
                    match node_cls.__name__:
                        case "Label":
                            active = Label(**data)
                            self.labels[data['name']] = active
                            self.cmd_stack.pop()
                            self.cmd_stack.append(active)
                        case "Input":
                            input = Input(**data)
                            self.inputs[data['name']] = input

                        case "Import":
                            lib_name = data.get("lib")
                            err = self.import_content(data['name'], lib_name)
                            if err is not None:
                                errors.extend(err)
                                for e in err:
                                    print("import error "+e)

                        case "InlineLabel":
                            label_name = f"___inline_{self.inline_count}"
                            inline = InlineLabel(**data)
                            inline.label_name = label_name
                            print(f"Inline {label_name} {inline.cmds} {inline.loop}")
                            
                            err = self.compile_inline(inline)
                            if len(err)>0:
                                errors.extend(err)
                                for e in err:
                                    print("inline error "+e)
                            else:
                                self.inline_count += 1
                                inline.line_no = line_no
                                self.cmd_stack[-1].add_child(inline)
                                active_cmd = inline
                                #save memory
                                inline.cmds = None


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
                mo = first_non_newline_index(lines)

                if mo:
                    # this just blank lines
                    line_no += mo
                    line = lines[:mo]
                    lines = lines[mo:]
                else:
                    mo = first_newline_index(lines)
                    errors.append(f"ERROR: {line_no} - {lines[0:mo]}")
                    lines = lines[mo+1:]
        return errors


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
