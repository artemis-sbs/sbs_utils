from asyncio.log import logger
from enum import IntEnum, Enum
import re
import ast
import os
from .. import fs
from zipfile import ZipFile
from .. import faces, scatter
import math
import itertools
import logging
import random
from io import StringIO


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
STRING_REGEX = r"""((?P<quote>((["']{3})|["']))[ \t\S]*(?P=quote))"""

JUMP_CMD_REGEX = r"""((?P<pop><<-(\s*(?P<pop_jump>\w+)\s*<<)?)|(->(?P<push>>)?\s*(?P<jump>\w+)))"""
#JUMP_ARG_REGEX = r"""\s*((?P<pop><<-)|(->(?P<push>>)?\s*(?P<jump>\w+))|(=>\s*(?P<await_name>\w+)(?P<with_data>\s*("""+PY_EXP_REGEX+"|"+DICT_REGEX+"""))?))"""
#OPT_JUMP_REGEX = r"("+JUMP_ARG_REGEX+r""")?"""

#TIME_PY_EXP_REGEX = r"""((?P<time_py>~~)[\s\S]+?(?P=time_py))"""
#TIME_JUMP_ARG_REGEX = r"""\s*((?P<time_pop><<-)|(->(?P<time_push>>)?\s*(?P<time_jump>\w+))|(=>\s*(?P<time_await_name>\w+)(?P<time_with_data>\s*("""+TIME_PY_EXP_REGEX+"|"+DICT_REGEX+"""))?))"""
#TIME_OPT_JUMP_REGEX = r"("+TIME_JUMP_ARG_REGEX+r""")?"""
#TIME_JUMP_REGEX = TIME_OPT_JUMP_REGEX
#r"""((\s*((?P<time_pop><<-)|(->(?P<time_push>>))?\s*(?P<time_jump>\w+))))?"""
MIN_SECONDS_REGEX = r"""(\s*((?P<minutes>\d+))m)?(\s*((?P<seconds>\d+)s))?"""
TIMEOUT_REGEX = r"(\s*timeout"+MIN_SECONDS_REGEX + r")?"
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
            message = f'''f"""{message}"""'''
            code = compile(message, "<string>", "eval")
            return code
        else:
            return message


class Label(MastNode):
    rule = re.compile(r'(={2,})\s*(?P<name>\w+)\s*(={2,})')

    def __init__(self, name, loc=None):
        self.name = name
        self.cmds = []
        self.next = None
        self.loc = loc

    def add_child(self, cmd):
        self.cmds.append(cmd)


class Log(MastNode):
    rule = re.compile(r"""log\s+(name\s+(?P<logger>[\w\.]*)\s+)?(?P<q>['"]{3}|["'])(?P<message>[\s\S]+?)(?P=q)(\s+(?P<level>debug|info|warning|error|critical))?""")
    
    def __init__(self, message, logger=None, level=None, q=None, loc=None):
        self.message = self.compile_formatted_string(message)
        self.level = level if level is not None else "debug"
        self.logger = logger if logger is not None else "mast.story"
        self.loc = loc

class Logger(MastNode):
    rule = re.compile(r"""logger(\s+name\s+(?P<logger>[\w\.]*))?(\s+string\s+(?P<var>\w*))?(\s+file\s*(?P<q>['"]{3}|["'])(?P<name>[\s\S]+?)(?P=q))?""")

    def __init__(self, logger=None, var=None, name=None, q=None, loc=None):
        self.var = var
        if name is not None:
            name = self.compile_formatted_string(name)
        self.name = name
        self.logger = logger if logger is not None else "mast.story"
        self.loc = loc

class LoopStart(MastNode):
    rule = re.compile(r'(for\s*(?P<name>\w+)\s*)(in|while)((?P<if_exp>[\s\S]+?):)')
    loop_stack = []
    def __init__(self, if_exp=None, name=None, loc=None):
        if if_exp:
            if_exp = if_exp.lstrip()
            self.code = compile(if_exp, "<string>", "eval")
        else:
            self.code = None
        self.name = name
        self.iter = None
        self.loc = loc
        self.end = None
        LoopStart.loop_stack.append(self)


class LoopBreak(MastNode):
    rule = re.compile(r'(?P<op>break|continue)\s*(?P<name>\w+)')
    def __init__(self, op=None, name=None, loc=None):
        self.name = name
        self.op = op
        self.start = LoopStart.loop_stack[-1]
        self.loc = loc

class LoopEnd(MastNode):
    rule = re.compile(r'((?P<loop>next)\s*(?P<name>\w+))')
    def __init__(self, loop=None, name=None, loc=None):
        self.loop = True if loop is not None and 'next' in loop else False
        self.name = name
        self.start = LoopStart.loop_stack.pop()
        self.loc = loc
        self.start.end = self


class IfStatements(MastNode):
    rule = re.compile(r'((?P<end>else:|end_if)|(((?P<if_op>if|elif)\s+?(?P<if_exp>[\s\S]+?)[:])))')

    if_chains = []

    def __init__(self, end=None, if_op=None, if_exp=None, loc=None):

        if if_exp:
            if_exp = if_exp.lstrip()
            self.code = compile(if_exp, "<string>", "eval")
        else:
            self.code = None

        self.end = end
        self.if_op = if_op
        self.if_chain = None
        self.if_node = None
        self.loc = loc


        if "end_if" == self.end:
            self.if_node = IfStatements.if_chains[-1]
            IfStatements.if_chains[-1].if_chain.append(loc)
            IfStatements.if_chains.pop()
        elif "else:" == self.end:
            self.if_node = IfStatements.if_chains[-1]
            IfStatements.if_chains[-1].if_chain.append(loc)
        elif "elif" == self.if_op:
            self.if_node = IfStatements.if_chains[-1]
            IfStatements.if_chains[-1].if_chain.append(loc)
        elif "if" == self.if_op:
            self.if_chain = [loc]
            IfStatements.if_chains.append(self)

class MatchStatements(MastNode):
    rule = re.compile(r'((?P<end>case\s*_:|end_match)|(((?P<op>match|case)\s+?(?P<exp>[\s\S]+?):)))')
    chains = []
    def __init__(self, end=None, op=None, exp=None, loc=None):
        self.loc = loc
        self.match_exp = None
        self.end = end
        self.op = op
        self.chain = None
        self.match_node = None

        if "end_match" == end:
            the_match_node = MatchStatements.chains[-1]
            self.match_node = the_match_node
            the_match_node.chain.append(loc)
            MatchStatements.chains.pop()
        elif end is not None and end.startswith("case"):
            the_match_node = MatchStatements.chains[-1]
            self.match_node = the_match_node
            the_match_node.chain.append(loc)
            self.end = "case_:"
        elif "case" == op:
            the_match_node = MatchStatements.chains[-1]
            self.match_node = the_match_node
            the_match_node.chain.append(loc)
        elif "match" == op:
            self.match_node = self
            self.chain = []
            MatchStatements.chains.append(self)
        
        if op == "match":
            self.match_exp = exp.lstrip()
        elif exp:
            exp = exp.lstrip()
            exp = self.match_node.match_exp +"==" + exp
            self.code = compile(exp, "<string>", "eval")
        else:
            self.code = None


class PyCode(MastNode):
    rule = re.compile(r'((\~{2,})\n?(?P<py_cmds>[\s\S]+?)\n?(\~{2,}))')

    def __init__(self, py_cmds=None, loc=None):
        self.loc = loc
        if py_cmds:
            py_cmds= py_cmds.lstrip()
            self.code = compile(py_cmds, "<string>", "exec")



class Input(MastNode):
    rule = re.compile(r'input\s+(?P<name>\w+)')

    def __init__(self, name, loc=None):
        self.loc = loc
        self.name = name

class Import(MastNode):
    rule = re.compile(r'(from\s+(?P<lib>[\w\.\\\/-]+)\s+)?import\s+(?P<name>[\w\.\\\/-]+)')

    def __init__(self, name, lib=None, loc=None):
        self.loc = loc
        self.name = name
        self.lib = lib

class Comment(MastNode):
    #rule = re.compile(r'(#[ \t\S]*)|((?P<com>[!]{3,})[\s\S]+(?P=com))')
    rule = re.compile(r'(#[ \t\S]*)|(\/\*[\s\S]+\*\/)|([!]{3,}\s*(?P<com>\w+)\s*[!]{3,}[\s\S]+[!]{3,}\s*end\s+(?P=com)\s*[!]{3,})')

    def __init__(self, com=None, loc=None):
        self.loc = loc

class Marker(MastNode):
    rule = re.compile(r'[-*+]{3,}')
    def __init__(self, loc=None):
        self.loc = loc


class Scope(Enum):
    SHARED = 1  # per mast instance
    NORMAL = 2  # per scheduler
    TEMP = 99  # Per task?
    UNKNOWN = 100

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
    def __init__(self, scope, lhs, exp, quote=None, py=None, loc=None):
        self.lhs = lhs
        self.loc = loc
        self.scope = None if scope is None else Scope[scope.strip(
        ).upper()]
        
        #print(f"quote: {quote}")
        exp = exp.lstrip()
        if quote:
            exp = 'f'+exp        
        if py:
            exp = exp[2:-2]
            exp = exp.strip()
        self.code = compile(exp, "<string>", "eval")



class Jump(MastNode):
    rule = re.compile(JUMP_CMD_REGEX+IF_EXP_REGEX)

    def __init__(self, pop, pop_jump, push, jump, if_exp, loc=None):
        self.loc = loc
        self.label = jump
        self.push = push == ">"
        self.pop = pop is not None
        self.pop_jump = pop_jump
        if if_exp:
            if_exp = if_exp.lstrip()
            self.code = compile(if_exp, "<string>", "eval")
        else:
            self.code = None



class Parallel(MastNode):
    """
    Creates a new 'task' to run in parallel
    """
    rule = re.compile(r"""((?P<name>[\w\.\[\]]+)\s*)?=>\s*(?P<label>\w+)(?P<inputs>\s*"""+ DICT_REGEX+")?"+IF_EXP_REGEX)

    def __init__(self, name=None, label=None, inputs=None, if_exp=None, loc=None):
        self.loc = loc
        self.name = name
        self.label = label
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


class Await(MastNode):
    """
    waits for an existing or a new 'task' to run in parallel
    this needs to be a rule before Parallel
    """
    rule = re.compile(r"""await((\s*(?P<label>\w+))|((\s*(?P<spawn>=>))\s*(?P<name>\w+)(?P<inputs>\s*"""+DICT_REGEX+")?))"+IF_EXP_REGEX)
                      
    def __init__(self, name=None, spawn=None, label=None, inputs=None, if_exp=None, loc=None):
        self.loc = loc
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

class EndAwait(MastNode):
    rule = re.compile(r'end_await')
    stack = []
    def __init__(self, loc=None):
        self.loc = loc
        EndAwait.stack[-1].end_await_node = self
        EndAwait.stack.pop()


class Event(MastNode):
    rule = re.compile(r'(event\s+(?P<event>[\w|_]+):)|(end_event)')
    stack = []
    def __init__(self, event=None, loc=None):
        self.loc = loc
        self.end = None
        self.event = event
        if event is None:
            Event.stack[-1].end = self
            Event.stack.pop()
        else:
            Event.stack.append(self)



class Timeout(MastNode):
    rule = re.compile(r'timeout\s*:')
    def __init__(self, loc=None):
        self.loc = loc
        self.await_node = EndAwait.stack[-1]
        EndAwait.stack[-1].timeout_label = self


class AwaitCondition(MastNode):
    """
    waits for an existing or a new 'task' to run in parallel
    this needs to be a rule before Parallel
    """
    rule = re.compile(r"""await\s+until\s+(?P<if_exp>[^:]+)"""+TIMEOUT_REGEX+""":""")
                      
    def __init__(self, minutes=None, seconds=None, if_exp=None, loc=None):
        self.loc = loc
        self.timeout_label = None
        self.end_await_node = None

        self.seconds = 0 if  seconds is None else int(seconds)
        self.minutes = 0 if  minutes is None else int(minutes)
        
        EndAwait.stack.append(self)

        if if_exp:
            if_exp = if_exp.lstrip()
            self.code = compile(if_exp, "<string>", "eval")
        else:
            self.code = None


class Cancel(MastNode):
    """
    Cancels a new 'task' to run in parallel
    """
    rule = re.compile(r"""cancel\s*(?P<name>[\w\.\[\]]+)""")

    def __init__(self, lhs=None, name=None, loc=None):
        self.loc = loc
        self.name = name


class End(MastNode):
    rule = re.compile(r'->\s*END')
    def __init__(self,  loc=None):
        self.loc = loc

class Delay(MastNode):
    clock = r"(\s*(?P<clock>\w+))"
    rule = re.compile(r'delay'+clock+MIN_SECONDS_REGEX)

    def __init__(self, clock, seconds=None, minutes=None, loc=None):
        self.loc = loc
        self.seconds = 0 if seconds is None else int(seconds)
        self.minutes = 0 if minutes is None else int(minutes)
        self.clock = clock


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
        "scatter": scatter,
        "random": random,
        "print": print, 
        "dir":dir, 
        "itertools": itertools,
        "next": next,
        "len": len,
        "reversed": reversed,
        "int": int,
        "min": min,
        "max": max,
        "abs": abs,
        "map": map,
        "filter": filter,
        "list": list,
        "mission_dir": fs.get_mission_dir(),
        "data_dir": fs.get_artemis_data_dir(),
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
                    active.next = cmd
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
        MatchStatements,
        LoopStart,
        LoopEnd,
        LoopBreak,
        PyCode,
        Log,
        Logger,
        Input,
        Event,
        #        Var,
        Import,
        AwaitCondition,
        Await,  # needs to be before Parallel
        Timeout,
        EndAwait,
        Parallel,  # needs to be before Assign
        Cancel,
        Assign,
        End,
        Jump,
        Delay,
        Marker,
    ]

    def clear(self):
        self.inputs = {}
        self.vars = {"mast": self}
        self.labels = {}
        self.inline_labels = {}
        self.labels["main"] = Label("main")
        self.cmd_stack = [self.labels["main"]]
        self.indent_stack = [0]
        self.main_pruned = False
        self.schedulers = set()
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

    def add_scheduler(self, scheduler):
        self.schedulers.add(scheduler)

    def refresh_schedulers(self, source, label):
        for scheduler in self.schedulers:
            if scheduler == source:
                continue
            scheduler.refresh(label)

    def remove_scheduler(self, scheduler):
        self.schedulers.remove(scheduler)

    def from_file(self, filename, lib_name=None):
        """ Docstring"""

        # Import from lib
        if lib_name is not None:
            return self.from_lib_file(filename, lib_name)

        # Import from already in a lib
        if self.lib_name is not None:
            return self.from_lib_file(filename, self.lib_name)
            
        file_name = os.path.join(fs.get_mission_dir(), filename)
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
            errors = self.compile(content)

            if len(errors) > 0:
                message = f"Compile errors\nCannot compile file {file_name}"
                errors.append(message)

        return errors
        

    def from_lib_file(self, file_name, lib_name):
        lib_name = os.path.join(fs.get_mission_dir(), lib_name)
        content = None

        errors = []
        try:
            with ZipFile(lib_name) as lib_file:
                with lib_file.open(file_name) as f:
                    content = f.read().decode('UTF-8')
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
        return []


    def import_content(self, filename, lib_file):
        add = self.__class__()
        errors = add.from_file(filename, lib_file)
        if len(errors)==0:
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
        active = self.labels.get("main")
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
                    
                    logger = logging.getLogger("mast.compile")
                    logger.debug(f"PARSED: {node_cls.__name__:} {line}")

                    match node_cls.__name__:
                        case "Label":
                            next = Label(**data)
                            active.next = next
                            active = next
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


                        # Throw comments and markers away
                        case "Comment":
                            pass
                        case "Marker":
                            pass

                        case _:
                            try:
                                loc = len(self.cmd_stack[-1].cmds)
                                obj = node_cls(loc=loc, **data)
                            except Exception as e:
                                logger = logging.getLogger("mast.compile")
                                logger.error(f"ERROR: {line_no} - {line}")
                                logger.error(f"Exception: {e}")

                                errors.append(f"ERROR: {line_no} - {line}")
                                errors.append(f"Exception: {e}")
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

                    logger = logging.getLogger("mast.compile")
                    logger.error(f"ERROR: {line_no} - {lines[0:mo]}")

                    errors.append(f"ERROR: {line_no} - {lines[0:mo]}")
                    lines = lines[mo+1:]
        return errors

    def enable_logging():
        logger = logging.getLogger("mast")
        handler  = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s|%(name)s|%(message)s"))
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        # fh = logging.FileHandler('mast.log')
        # fh.setLevel(logging.DEBUG)
        # logger.addHandler(fh)
        




