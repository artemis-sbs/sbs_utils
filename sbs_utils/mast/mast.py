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
LIST_REGEX = r"""(\[[\s\S]+?\])"""
DICT_REGEX = r"""(\{[\s\S]+?\})"""
PY_EXP_REGEX = r"""((?P<py>~~)[\s\S]+?(?P=py))"""
STRING_REGEX = r"""((?P<quote>((["']{3})|["']))[\s\S]+?(?P=quote))"""

JUMP_CMD_REGEX = r"""((?P<pop><<-)|(->(?P<push>>)?\s*(?P<jump>\w+)))"""
JUMP_ARG_REGEX = r"""\s*((?P<pop><<-)|(->(?P<push>>)?\s*(?P<jump>\w+))|(=>\s*(?P<await_name>\w+)(?P<with_data>\s*("""+PY_EXP_REGEX+"|"+DICT_REGEX+"""))?))"""
OPT_JUMP_REGEX = JUMP_ARG_REGEX+r"""?"""
TIME_JUMP_REGEX = r"""((?P<time_pop><<-)|(->(?P<time_push>>)?\s*(?P<time_jump>\w+)))?"""
MIN_SECONDS_REGEX = r"""(\s*((?P<minutes>\d+))m)?(\s*((?P<seconds>\d+)s))?"""
TIMEOUT_REGEX = r"(\s*timeout"+MIN_SECONDS_REGEX + \
    r"\s*" + TIME_JUMP_REGEX + r")?"
OPT_COLOR = r"""(\s*color\s*["'](?P<color>[ \t\S]+)["'])?"""
IF_EXP_REGEX = r"""(\s+if(?P<if_exp>.+))?"""



class MastCompilerError:
    def __init__(self, message, line_no):
        if isinstance(message, str):
            self.messages = [message]
        else:
            self.messages = message
        self.line_no = line_no


class MastNode:
    def add_child(self, cmd):
        #print("ADD CHILD")
        pass

    def compile_formatted_string(self, message):
        if "{" in message:
            message = f"""f'''{message}'''"""
            code = compile(message, "<string>", "eval")
            return code
        else:
            return message


class Label(MastNode):
    rule = re.compile(r'(={2,})\s*(?P<name>\w+)\s*(={2,})')

    def __init__(self, name):
        self.name = name
        self.cmds = []

    def add_child(self, cmd):
        self.cmds.append(cmd)



class InlineLabelStart(MastNode):
    rule = re.compile(r'((\-{2,})\s*(?P<name>\w+)\s*)(\((?P<if_exp>[\s\S]+?)\))\s*(\-{2,})')

    def __init__(self, if_exp=None, name=None):
        if if_exp:
            if_exp = if_exp.lstrip()
            self.code = compile(if_exp, "<string>", "eval")
        else:
            self.code = None
        self.name = name
        self.iter = None


class InlineLabelBreak(MastNode):
    rule = re.compile(r'(?P<op>break|continue)\s*(?P<name>\w+)')
    def __init__(self, op=None, name=None):
        self.name = name
        self.op = op

class InlineLabelEnd(MastNode):
    rule = re.compile(r'((\-{2,})\s*(end|(?P<loop>next))\s*(?P<name>\w+)\s*(\-{2,}))')
    def __init__(self, loop=None, name=None):
        self.loop = True if loop is not None and 'next' in loop else False
        self.name = name


class IfStatements(MastNode):
    rule = re.compile(r'(\-{2,})\s*((?P<end>else|endif)|(((?P<if_op>if|elif)\s+?(\((?P<if_exp>[\s\S]+?)\)))))\s*(\-{2,})')
    def __init__(self, end=None, if_op=None, if_exp=None):
        if if_exp:
            if_exp = if_exp.lstrip()
            self.code = compile(if_exp, "<string>", "eval")
        else:
            self.code = None
        self.end = end
        self.if_op = if_op
        self.if_chain = None

class PyCode(MastNode):
    rule = re.compile(r'((\~{2,})\n?(?P<py_cmds>[\s\S]+?)\n?(\~{2,}))')

    def __init__(self, py_cmds=None):
        if py_cmds:
            py_cmds= py_cmds.lstrip()
            self.code = compile(py_cmds, "<string>", "exec")



class Input(MastNode):
    rule = re.compile(r'input\s+(?P<name>\w+)')

    def __init__(self, name):
        self.name = name


class Import(MastNode):
    rule = re.compile(r'(from\s+(?P<lib>[\w\.\/-]+)\s+)?import\s+(?P<name>[\w\.\/-]+)')

    def __init__(self, name, lib=None):
        self.name = name
        self.lib = lib


class Comment(MastNode):
    rule = re.compile(r'#[ \t\S]*')

    def __init__(self):
        pass


class Scope(Enum):
    SHARED = 1  # per mast instance
    NORMAL = 2  # per runner
    TEMP = 99  # Per thread?

class MastDataObject(object):
    def __init__(self, dictionary):
        # for dictionary in initial_data:
        for key in dictionary:
            setattr(self, key, dictionary[key])

    def __repr__(self):
        return repr(vars(self))

class Assign(MastNode):
    # '|'+STRING_REGEX+
    rule = re.compile(
        r'(?P<scope>(shared|temp)\s+)?(?P<lhs>[\w\.\[\]]+)\s*=\s*(?P<exp>('+PY_EXP_REGEX+'|'+STRING_REGEX+'|.*))')

    """ Not this doesn't support destructuring. To do so isn't worth the effort"""
    def __init__(self, scope, lhs, exp, quote=None, py=None):
        self.lhs = lhs
        self.scope = Scope.NORMAL if scope is None else Scope[scope.strip(
        ).upper()]
        
        #print(f"quote: {quote}")
        exp = exp.lstrip()
        if quote:
            exp = 'f'+exp        
        if py:
            exp = exp[2:-2]
            exp = exp.strip()

        #print(f"EXP: {exp}")
        self.code = compile(exp, "<string>", "eval")



class Jump(MastNode):
    rule = re.compile(JUMP_CMD_REGEX+IF_EXP_REGEX)

    def __init__(self, pop, push, jump, if_exp):
        self.label = jump
        self.push = push == ">"
        self.pop = pop is not None
        if if_exp:
            if_exp = if_exp.lstrip()
            self.code = compile(if_exp, "<string>", "eval")
        else:
            self.code = None



class Parallel(MastNode):
    """
    Creates a new 'thread' to run in parallel
    """
    rule = re.compile(r"""((?P<name>[\w\.\[\]]+)\s*)?=>\s*(?P<label>\w+)(?P<inputs>\s*"""+ DICT_REGEX+")?"+IF_EXP_REGEX)

    def __init__(self, name=None, label=None, inputs=None, if_exp=None):
        self.name = name
        self.label = label
        self.cmds = []
        if inputs:
            inputs = inputs.lstrip()
            self.code = compile(inputs, "<string>", "eval")
        if if_exp:
            if_exp = if_exp.lstrip()
            self.if_code = compile(if_exp, "<string>", "eval")
        else:
            self.if_code = None



    def add_child(self, cmd):
        self.cmds.append(cmd)


class Await(MastNode):
    """
    waits for an existing or a new 'thread' to run in parallel
    this needs to be a rule before Parallel
    """
    rule = re.compile(r"""await((\s*(?P<label>\w+))|((\s*(?P<spawn>=>))\s*(?P<name>\w+)(?P<inputs>\s*"""+DICT_REGEX+")?))"+IF_EXP_REGEX)
                      
    def __init__(self, name=None, spawn=None, label=None, inputs=None, if_exp=None):
        self.spawn = True if spawn is not None else False
        self.label = label
        if name:
            self.label = name
        self.cmds = []
        if inputs:
            inputs = inputs.lstrip()
            self.code = compile(inputs, "<string>", "eval")
        else:
            self.code = None
        if if_exp:
            if_exp = if_exp.lstrip()
            self.if_code = compile(if_exp, "<string>", "eval")
        else:
            self.if_code = None


    def add_child(self, cmd):
        self.cmds.append(cmd)


class Cancel(MastNode):
    """
    Cancels a new 'thread' to run in parallel
    """
    rule = re.compile(r"""cancel\s*(?P<name>[\w\.\[\]]+)""")

    def __init__(self, lhs=None, name=None):
        self.name = name


class End(MastNode):
    rule = re.compile(r'->\s*END')

class Delay(MastNode):
    rule = re.compile(r'delay\s*'+MIN_SECONDS_REGEX)

    def __init__(self, seconds=None, minutes=None):
        self.seconds = 0 if seconds is None else int(seconds)
        self.minutes = 0 if minutes is None else int(minutes)


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
    return len(s)


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

class InlineData:
    def __init__(self, start, end):
        self.start = start
        self.end = end


class Mast:
    globals = {
        "math": math, 
        "faces": faces, 
        "print": print, 
        "dir":dir, 
        "itertools": itertools,
        "next": next,
        "len": len,
        "MastDataObject": MastDataObject,
        "range": range,
        "__build_class__":__build_class__, # ability to define classes
        "__name__":__name__ # needed to define classes?
    }
    inline_count = 0
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
        IfStatements,
        InlineLabelStart,
        InlineLabelEnd,
        InlineLabelBreak,
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
        self.inline_labels = {}
        self.labels["main"] = Label("main")
        self.cmd_stack = [self.labels["main"]]
        self.indent_stack = [0]
        self.main_pruned = False
        self.runners = set()
        self.lib_name = None
        
    
    def prune_main(self):
        if self.main_pruned:
            return
        main = self.labels.get("main")
        # Convert all the assigned from the main into comments
        # removing is bad it will affect if statements
        if main is not None:
            for i in range(len(main.cmds)):
                cmd = main.cmds[i]
                if cmd.__class__ == Assign and cmd.scope == Scope.SHARED:
                    main.cmds[i] = Comment()
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
                #print("LIB Opened")
                with lib_file.open(file_name) as f:
                    #print("LIB content")
                    content = f.read().decode('UTF-8')
                    #print(f"LIB {content[0:10]}")
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

    def compile(self, lines):
        self.clear()
        line_no = 0
        errors = []
        if_chains = []
        while len(lines):
            mo = first_non_newline_index(lines)
            line_no += mo if mo is not None else 0
            #line = lines[:mo]
            lines = lines[mo:]
            parsed = False
            indent = first_non_space_index(lines)
            if indent is None:
                continue
            ###########################################
            ### Support indent as meaningful
            ###########################################
            # if indent > self.indent_stack[-1]:
            #     # new indent
            #     self.cmd_stack.append(active_cmd)
            #     self.indent_stack.append(indent)
            # while indent < self.indent_stack[-1]:
            #     self.cmd_stack.pop()
            #     self.indent_stack.pop()
            if indent > 0:
                # strip spaces
                lines = lines[indent:]
            if len(lines)==0:
                break

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

                        case "InlineLabelStart":
                            inline = InlineLabelStart(**data)
                            label_name = f"{active.name}:{inline.name}"
                            start = len(self.cmd_stack[-1].cmds)
                            #print(f"INLINE START {label_name} start {start}")
                            self.cmd_stack[-1].add_child(inline)
                            self.inline_labels[label_name] = InlineData(start, None)

                        case "InlineLabelEnd":
                            inline = InlineLabelEnd(**data)
                            label_name = f"{active.name}:{inline.name}"
                            end = len(self.cmd_stack[-1].cmds)
                            #print(f"INLINE END {label_name} end {end}")
                            self.cmd_stack[-1].add_child(inline)
                            data = self.inline_labels.get(label_name, InlineData(None,None))
                            data.end = end
                            self.inline_labels[label_name] = data

                        case "IfStatements":
                            if_node = IfStatements(**data)
                            loc = len(self.cmd_stack[-1].cmds)
                            self.cmd_stack[-1].add_child(if_node)
                            if "endif" == if_node.end:
                                if_node.if_chain = if_chains[-1]
                                if_chains[-1].append(loc)
                                if_chains.pop()
                            elif "else" == if_node.end:
                                if_node.if_chain = if_chains[-1]
                                if_chains[-1].append(loc)
                            elif "elif" == if_node.if_op:
                                if_node.if_chain = if_chains[-1]
                                if_chains[-1].append(loc)
                            elif "if" == if_node.if_op:
                                if_node.if_chain = [loc]
                                if_chains.append(if_node.if_chain)

                        case "Comment":
                            # obj.line_no = line_no
                            # self.cmd_stack[-1].add_child(obj)
                            # active_cmd = obj
                            pass

                        case _:
                            try:
                                obj = node_cls(**data)
                            except Exception as e:
                                errors.append(f"ERROR: {line_no} - {line}")
                                errors.append(f"Exception: {e.msg}")
                                return errors # return with first errors

                            obj.line_no = line_no
                            self.cmd_stack[-1].add_child(obj)
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




