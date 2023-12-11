from enum import Enum
import re
import ast
import os
from .. import fs
from zipfile import ZipFile
from .. import faces, scatter
from ..agent import Agent
import math
import itertools
import logging
import random
from inspect import getmembers, isfunction  
import sys



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
OPT_ARGS_REGEX = r"""(?P<args>([ \t]*\{[^\n\r\f]+\}))?"""
PY_EXP_REGEX = r"""((?P<py>~~)[\s\S]*?(?P=py))"""
STRING_REGEX = r"""((?P<quote>((["']{3})|["']))[ \t\S]*(?P=quote))"""

OPT_COLOR = r"""([ \t]*color[ \t]*["'](?P<color>[ \t\S]+)["'])?"""
IF_EXP_REGEX = r"""([ \t]+if(?P<if_exp>[^\n\r\f]+))?"""
BLOCK_START = r":[ \t]*(?=\r\n|\n|\#)"




class ParseData:
    def __init__(self, start, end, data):
        self.start = start
        self.end = end
        self.data = data


class MastNode:
    file_num:int
    line_num:int
    
    def add_child(self, cmd):
        #print("ADD CHILD")
        pass

    def compile_formatted_string(self, message):
        if message is None:
            return message
        if "{" in message:
            message = f'''f"""{message}"""'''
            code = compile(message, "<string>", "eval")
            return code
        else:
            return message

    @classmethod
    def parse(cls, lines):
        mo = cls.rule.match(lines)

        if mo:
            span = mo.span()
            data = mo.groupdict()
            return ParseData(span[0], span[1], data)
        else:
            return None



class Label(MastNode):
    rule = re.compile(r'(?P<m>=|\?){2,}\s*(?P<replace>replace:)?[ \t]*(?P<name>\w+)[ \t]*(?P=m){2,}')

    def __init__(self, name, replace=None, m=None, loc=None):
        self.name = name
        self.cmds = []
        self.next = None
        self.loc = loc
        self.replace = replace is not None

    def add_child(self, cmd):
        self.cmds.append(cmd)




class LoopStart(MastNode):
    rule = re.compile(r'(for[ \t]*(?P<name>\w+)[ \t]*)(?P<while_in>in|while)((?P<cond>[^\n\r\f]+))'+BLOCK_START)
    loop_stack = []
    def __init__(self, while_in=None, cond=None, name=None, loc=None):
        if cond:
            cond = cond.lstrip()
            self.code = compile(cond, "<string>", "eval")
        else:
            self.code = None
        self.name = name
        self.is_while = while_in == "while"
        self.loc = loc
        self.end = None
        LoopStart.loop_stack.append(self)


class LoopBreak(MastNode):
    #rule = re.compile(r'(?P<op>break|continue)\s*(?P<name>\w+)')
    rule = re.compile(r'(?P<op>break|continue)'+IF_EXP_REGEX)
    def __init__(self, op=None, name=None, if_exp=None, loc=None):
        self.name = name
        self.op = op
        self.start = LoopStart.loop_stack[-1]
        self.loc = loc
        if if_exp:
            if_exp = if_exp.lstrip()
            self.if_code = compile(if_exp, "<string>", "eval")
        else:
            self.if_code = None

class LoopEnd(MastNode):
    rule = re.compile(r'((?P<loop>next)[ \t]*(?P<name>\w+))')
    def __init__(self, loop=None, name=None, loc=None):
        self.loop = True if loop is not None and 'next' in loop else False
        self.name = name
        self.start = LoopStart.loop_stack.pop()
        self.loc = loc
        self.start.end = self


class IfStatements(MastNode):
    rule = re.compile(r'((?P<end>else:|end_if)|(((?P<if_op>if|elif)[ \t]+?(?P<if_exp>[ \t\S]+?)'+BLOCK_START+')))')

    if_chains = []

    def __init__(self, end=None, if_op=None, if_exp=None, loc=None):
        self.code = None
        if if_exp:
            if_exp = if_exp.lstrip()
            self.code = compile(if_exp, "<string>", "eval")

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
    rule = re.compile(r'((?P<end>case[ \t]*_:|end_match)|(((?P<op>match|case)[ \t]+?(?P<exp>[^\n\r\f]+)'+BLOCK_START+')))')
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


class Import(MastNode):
    rule = re.compile(r'(from[ \t]+(?P<lib>[\w\.\\\/-]+)[ \t]+)?import\s+(?P<name>[\w\.\\\/-]+)')

    def __init__(self, name, lib=None, loc=None):
        self.loc = loc
        self.name = name
        self.lib = lib


class Comment(MastNode):
    #rule = re.compile(r'(#[ \t\S]*)|((?P<com>[!]{3,})[\s\S]+(?P=com))')
    rule = re.compile(r'(#[ \t\S]*)|(/\*[^*]*\*+(?:[^/*][^*]*\*+)*/)|([!]{3,}\s*(?P<com>\w+)\s*[!]{3,}[\s\S]+[!]{3,}\s*end\s+(?P=com)\s*[!]{3,})')

    def __init__(self, com=None, loc=None):
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
    EQUALS = 1
    INC=2
    DEC = 3
    MUL = 4
    MOD = 5
    DIV=6
    INT_DIV = 7
    oper_map = {"=": EQUALS, "+=": INC,  "-=": DEC, "*=": MUL, "%=": MOD, "/=": DIV, "//=":INT_DIV }
    # '|'+STRING_REGEX+ddd
    rule = re.compile(
        r'(?P<scope>(shared|temp)\s+)?(?P<lhs>[\w\.\[\]]+)\s*(?P<oper>=|\+=|-=|\*=|%=|/=|//=)\s*(?P<exp>('+PY_EXP_REGEX+'|'+STRING_REGEX+'|[^\n\r\f]+))')

    """ Note this doesn't support destructuring. To do so isn't worth the effort"""
    def __init__(self, scope, lhs, oper, exp, quote=None, py=None, loc=None):
        self.lhs = lhs
        self.loc = loc
        self.oper = Assign.oper_map.get(oper)
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

        if lhs in Mast.globals:
            raise Exception(f"Variable assignment to a keyword {lhs}")



class Jump(MastNode):
    rule = re.compile(r"""(((?P<jump>jump|->|push|->>|popjump|<<->|poppush|<<->>)[ \t]*(?P<jump_name>\w+))|(?P<pop>pop|<<-))"""+OPT_ARGS_REGEX+IF_EXP_REGEX)

    def __init__(self, pop=None, jump=None, jump_name=None, if_exp=None, args=None, loc=None):
        self.loc = loc
        self.label = jump_name
        self.push = jump == 'push' or jump == "->>"
        self.pop = pop is not None
        self.pop_jump = jump == 'popjump'or jump == "<<->"
        self.pop_push = jump == 'poppush'or jump == "<<->>"
        self.args = args
        if if_exp:
            if_exp = if_exp.lstrip()
            self.if_code = compile(if_exp, "<string>", "eval")
        else:
            self.if_code = None
        if args is not None:
            args = args.lstrip()
            self.args = compile(args, "<string>", "eval")


CLOSE_FUNC = r"\)[ \t]*(?=\r\n|\n|\#)"
class FuncCommand(MastNode):
    rule = re.compile(r'(?P<is_await>await\s+)?(?P<py_cmds>[\w\.]+\s*\([^\n\r\f]+[ \t]*(?=\r\n|\n|\#))')
    def __init__(self, is_await=None, py_cmds=None, loc=None):
        self.loc = loc
        self.is_await = is_await != None
        if py_cmds:
            py_cmds= py_cmds.lstrip()
            self.code = compile(py_cmds, "<string>", "eval")
        

class Await(MastNode):
    """
    waits for an existing or a new 'task' to run in parallel
    this needs to be a rule before Parallel
    """
    rule = re.compile(r"""await[ \t]+(until[ \t]+(?P<until>\w+)[ \t]+)?(?P<if_exp>[^:\n\r\f]+)"""+BLOCK_START)
    def __init__(self, until=None, if_exp=None, loc=None):
        self.loc = loc
        self.end_await_node = None
        self.inlines = []
        self.buttons = []
        self.until = until

        self.timeout_label = None
        self.on_change = None
        self.fail_label = None
        
        EndAwait.stack.append(self)

        if if_exp:
            if_exp = if_exp.lstrip()
            self.code = compile(if_exp, "<string>", "eval")
        else:
            self.code = None

    def add_inline(self, inline_data):
        self.inlines.append(inline_data)


        
class EndAwait(MastNode):
    rule = re.compile(r'end_await')
    stack = []
    def __init__(self, loc=None):
        self.loc = loc
        self.await_node = EndAwait.stack[-1]
        EndAwait.stack[-1].end_await_node = self
        EndAwait.stack.pop()


MIN_SECONDS_REGEX = r"""([ \t]*((?P<minutes>\d+))m)?([ \t]*((?P<seconds>\d+)s))?"""
TIMEOUT_REGEX = r"([ \t]*timeout"+MIN_SECONDS_REGEX + r")?"
# class Timeout(MastNode):
#     rule = re.compile(r'timeout([ \t]*((?P<minutes>\d+))m)?([ \t]*((?P<seconds>\d+)s))?:')
#     def __init__(self, minutes, seconds, loc=None):
#         self.loc = loc
        
#         self.await_node = EndAwait.stack[-1]
#         EndAwait.stack[-1].timeout_label = self
#         self.await_node.seconds = 0 if  seconds is None else int(seconds)
#         self.await_node.minutes = 0 if  minutes is None else int(minutes)



#
# Allow a state change to be handled in await
#
class Change(MastNode):
    rule = re.compile(r"change[ \t]+(?P<val>[^:]+)"+BLOCK_START)
    def __init__(self, end=None, val=None, loc=None):
        self.loc = loc
        self.value = val
        if val:
            self.value = compile(val, "<string>", "eval")
        #
        # Check to see if this is embedded in an await
        #
        self.await_node = None
        if len(EndAwait.stack) >0:
            self.await_node = EndAwait.stack[-1]
            # Only add on change if we need them
            if self.await_node.on_change  is None:
                self.await_node.on_change  = []
            self.await_node.on_change.append(self)



# class AwaitFail(MastNode):
#     rule = re.compile(r'fail:')
#     def __init__(self, loc=None):
#         self.loc = loc
        
#         self.await_node = EndAwait.stack[-1]
#         EndAwait.stack[-1].fail_label = self


class AwaitInlineLabel(MastNode):
    rule = re.compile(r"\=(?P<val>[^:\n\r\f]+)"+BLOCK_START)
    def __init__(self, val=None, loc=None):
        self.loc = loc
        self.inline = val
        self.await_node = EndAwait.stack[-1]
        EndAwait.stack[-1].add_inline(self)

class OnChange(MastNode):
    rule = re.compile(r"(?P<end>end_on)|(on[ \t]+(change[ \t]+)?(?P<val>[^:]+)"+BLOCK_START+")")
    stack = []
    def __init__(self, end=None, val=None, loc=None):
        self.loc = loc
        self.value = val
        if val:
            self.value = compile(val, "<string>", "eval")

        self.is_end = False
        #
        # Check to see if this is embedded in an await
        #
        self.await_node = None
        if len(EndAwait.stack) >0:
            self.await_node = EndAwait.stack[-1]
        self.end_node = None

        if end is not None:
            OnChange.stack[-1].end_node = self
            self.is_end = True
            OnChange.stack.pop()
        else:
            OnChange.stack.append(self)



FOR_RULE = r'([ \t]+for[ \t]+(?P<for_name>\w+)[ \t]+in[ \t]+(?P<for_exp>[ \t\S]+?))?'
class Button(MastNode):
    
    rule = re.compile(r"""(?P<button>\*|\+)[ \t]*(?P<q>["'])(?P<message>[ \t\S]+?)(?P=q)"""+OPT_COLOR+FOR_RULE+IF_EXP_REGEX+r"[ \t]*"+BLOCK_START)
    def __init__(self, message=None, button=None,  
                color=None, if_exp=None, 
                for_name=None, for_exp=None, 
                clone=False, q=None, loc=None):
        if clone:
            return
        self.message = self.compile_formatted_string(message)
        self.sticky = (button == '+' or button=="button")
        self.color = color
        if color is not None:
            self.color = self.compile_formatted_string(color)
        self.visited = set() if not self.sticky else None
        self.loc = loc
        self.await_node = EndAwait.stack[-1]
        self.await_node.buttons.append(self)

        if if_exp:
            if_exp = if_exp.lstrip()
            self.code = compile(if_exp, "<string>", "eval")
        else:
            self.code = None

        self.for_name = for_name
        self.data = None
        if for_exp:
            for_exp = for_exp.lstrip()
            self.for_code = compile(for_exp, "<string>", "eval")
        else:
            self.cor_code = None

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

    def clone(self):
        proxy = Button(clone=True)
        proxy.message = self.message
        proxy.code = self.code
        proxy.color = self.color
        proxy.loc = self.loc
        proxy.await_node = self.await_node
        proxy.sticky = self.sticky
        proxy.visited = self.visited
        proxy.data = self.data
        proxy.for_code = self.for_code
        proxy.for_name = self.for_name

        return proxy
    
    def expand(self):
        pass



class End(MastNode):
    rule = re.compile(r'->[ \t]*END'+IF_EXP_REGEX)
    def __init__(self,  if_exp=None, loc=None):
        self.loc = loc
        if if_exp:
            if_exp = if_exp.lstrip()
            self.if_code = compile(if_exp, "<string>", "eval")
        else:
            self.if_code = None

class ReturnIf(MastNode):
    rule = re.compile(r'->[ \t]*RETURN'+IF_EXP_REGEX)
    def __init__(self, if_exp=None,  loc=None):
        self.loc = loc
        if if_exp:
            if_exp = if_exp.lstrip()
            self.if_code = compile(if_exp, "<string>", "eval")
        else:
            self.if_code = None


class Fail(MastNode):
    rule = re.compile(r'->[ \t]*FAIL'+IF_EXP_REGEX)
    def __init__(self, if_exp=None, loc=None):
        self.loc = loc
        if if_exp:
            if_exp = if_exp.lstrip()
            self.if_code = compile(if_exp, "<string>", "eval")
        else:
            self.if_code = None

class Yield(MastNode):
    rule = re.compile(r'yield([ \t]+(?P<res>(?i:fail|success)))?' +IF_EXP_REGEX)
    def __init__(self, res= None, if_exp=None, loc=None):
        self.loc = loc
        self.result = res

        if if_exp:
            if_exp = if_exp.lstrip()
            self.if_code = compile(if_exp, "<string>", "eval")
        else:
            self.if_code = None


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

def first_non_whitespace_index(s):
    nl = 0
    for idx, c in enumerate(s):
        if c != '\n' and c != '\t' and c != ' ':
            return (idx,nl)
        if c == '\n':
            nl+=1
    return (len(s), nl)

def first_newline_index(s):
    for idx, c in enumerate(s):
        if c == '\n':
            return idx
    return len(s)

class InlineData:
    def __init__(self, start, end):
        self.start = start
        self.end = end
import builtins as __builtin__
from ..helpers import FrameContext
def mast_print(*args, **kwargs):
    task = FrameContext.task 
    if len(args)==1 and task is not None:
        return __builtin__.print(task.compile_and_format_string(args[0]))
    #    args[0] = ">>>"+args[0]
    return __builtin__.print(*args, **kwargs)



class Mast():
    include_code = False

    globals = {
        "math": math, 
        "faces": faces,
        "scatter": scatter,
        "random": random,
        "print": mast_print, 
        "dir":dir, 
        "itertools": itertools,
        "next": next,
        "len": len,
        "reversed": reversed,
        "int": int,
        "str": str,
        "hex": hex,
        "min": min,
        "max": max,
        "abs": abs,
        "sim": None,
        "map": map,
        "filter": filter,
        "list": list,
        "set": set,
        "iter": iter,
        "sorted": sorted,
        "mission_dir": fs.get_mission_dir(),
        "data_dir": fs.get_artemis_data_dir(),
        "MastDataObject": MastDataObject,
        "range": range,
        "INFO": logging.INFO,
        "DEBUG": logging.DEBUG,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
        "__build_class__":__build_class__, # ability to define classes
        "__name__":__name__ # needed to define classes?
    }
    inline_count = 0
    source_map_files = []

    def __init__(self, cmds=None):
        super().__init__()

        self.lib_name = None
        self.is_import = False
        self.basedir = None
        

        if cmds is None:
            self.clear("no_mast_file")
            return
        if isinstance(cmds, str):
            cmds = self.compile(cmds, "<string>")
        # else:
        #     self.build(cmds)
        

    def make_global(func):
        add_to = Mast.globals
        add_to[func.__name__] = func


    def make_global_var(name, value):
        Mast.globals[name] = value
        
    def import_python_module(mod_name, prepend=None):
        #print(f"{mod_name}")
        sca = sys.modules.get(mod_name)
        if sca:
            for (name, func) in getmembers(sca,isfunction):
                #print(f"IMPORT {name}")
                if prepend == None:
                    Mast.globals[name] = func
                elif prepend == True:
                    Mast.globals[f"{mod_name}_{name}"] = func
                elif isinstance(prepend, str):
                    Mast.globals[f"{prepend}_{name}"] = func


    nodes = [
        Comment,
        Label,
        IfStatements,
        MatchStatements,
        LoopStart,
        LoopEnd,
        LoopBreak,
        PyCode,
        Import,
        Await,  # New Await Block
        FuncCommand,
        #        AwaitCondition,
        #Timeout,
        Change,
        OnChange,
        EndAwait,
        #AwaitFail, # Fail Label
        AwaitInlineLabel,
        Button,

        Fail,
        Yield,
        End,
        ReturnIf,
            Jump,
        Assign,
    ]

    def get_source_file_name(file_num):
        if file_num is None:
            return "<string>"
        if file_num >= len(Mast.source_map_files):
            return "<unknown>"
        return Mast.source_map_files[file_num]

    def clear(self, file_name):
        self.inputs = {}
        if not self.is_import:
            #self.set_inventory_value("mast", self)
            Agent.SHARED.set_inventory_value("SHARED", Agent.SHARED.get_id())
            Mast.source_map_files = []
            # print("Multi Shares")

        # self.vars = {"mast": self}
        self.labels = {}
        self.inline_labels = {}
        self.labels["main"] = Label("main")
        self.cmd_stack = [self.labels["main"]]
        self.indent_stack = [0]
        self.main_pruned = False
        self.schedulers = set()
        self.lib_name = None

        Mast.source_map_files.append(file_name)
        return len(Mast.source_map_files)-1
                
    
    def prune_main(self):
        if self.main_pruned:
            return
        main = self.labels.get("main")
        # Convert all the assigned from the main into comments
        # removing is bad it will affect if statements
        # If statements may run twice?
        #
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

    def update_shared_props_by_tag(self, tag, props):
        for scheduler in self.schedulers:
            if scheduler.page is not None:
                scheduler.page.update_props_by_tag(tag, props)


    def remove_scheduler(self, scheduler):
        self.schedulers.remove(scheduler)

    def from_file(self, file_name, lib_name=None):
        """ Docstring"""
        content = None
        errors= None
        if self.lib_name is not None:
            content, errors = self.content_from_lib_or_file(file_name, self.lib_name)
        else:
            content, errors = self.content_from_lib_or_file(file_name, lib_name)
            if lib_name is not None and content is not None:
                self.lib_name = lib_name
        if errors is not None:
            return errors
        if content is not None:
            errors = self.compile(content, file_name)
            # if len(errors) > 0:
            #     message = f"\nCompile errors\nCannot compile file {file_name}"
            #     errors.append(message)
            return errors
        return []
        

    # def process_file_content(self,content, file_name):
    #     file_name, ext = os.path.splitext(file_name)
    #     errors = []
    #     match ext:
    #         case _:
    #             if content is not None:
    #                 errors = self.compile(content, file_name)

    #                 if len(errors) > 0:
    #                     message = f"Compile errors\nCannot compile file {file_name}"
    #                     errors.append(message)

    #     return errors
        
       

    def content_from_lib_or_file(self, file_name, lib_name):
        try:
            if lib_name is not None:
                lib_name = os.path.join(fs.get_mission_dir(), lib_name)
                with ZipFile(lib_name) as lib_file:
                    with lib_file.open(file_name) as f:
                        content = f.read().decode('UTF-8')
                        return content, None

            else:
                if self.basedir is None:
                    file_name = os.path.join(fs.get_mission_dir(), file_name)
                    self.basedir = os.path.dirname(file_name)
                else:
                    file_name = os.path.join(self.basedir, file_name)
                    # if its not in this dir try the mission script dir
                    if not os.path.isfile(file_name):
                        file_name = os.path.join(fs.get_mission_dir(), file_name)
                    
                with open(file_name) as f:
                    content = f.read()
                return content, None
        except:
            message = f"File load error\nCannot load file {file_name}"
            return None, [message]
            
        
    

    def import_content(self, filename, lib_file):
        add = self.__class__()
        add.basedir = self.basedir
        add.is_import = True
        errors = add.from_file(filename, lib_file)
        if len(errors)==0:
            for label, node in add.labels.items():
                if label == "main":
                    main = self.labels["main"]

                    offset = len(main.cmds)
                    for cmd in node.cmds:
                        cmd.loc += offset
                        # If and match staements need more fixups
                        if cmd.__class__.__name__ == "IfStatements" and cmd.if_chain:
                            for c in range(len(cmd.if_chain)):
                                cmd.if_chain[c] += offset
                        elif cmd.__class__.__name__ == "MatchStatements" and cmd.chain:
                            for c in range(len(cmd.chain)):
                                cmd.chain[c] += offset


                    main.cmds.extend(node.cmds)

                else:
                    self.labels[label] = node


        return errors

    def compile(self, lines, file_name):
        file_num = self.clear(file_name)
        line_no = 1 # file line num are 1 based
        
        errors = []
        active = self.labels.get("main")
        active_name = "main"

        while len(lines):
            mo = first_non_whitespace_index(lines)
            line_no += mo[1] if mo is not None else 0
            #line = lines[:mo]
            lines = lines[mo[0]:]
            # Keep location in file


            parsed = False
            # indent = first_non_space_index(lines)
            # if indent is None:
            #     continue
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
            # if indent > 0:
            #     # strip spaces
            #     lines = lines[indent:]
            if len(lines)==0:
                break

            for node_cls in self.__class__.nodes:
                #mo = node_cls.rule.match(lines)
                mo = node_cls.parse(lines)
                if mo:
                    #span = mo.span()
                    data = mo.data

                    line = lines[mo.start:mo.end]
                    lines = lines[mo.end:]

                    line_no += line.count('\n')
                    

                    parsed = True
                
                    
                    logger = logging.getLogger("mast.compile")
                    logger.debug(f"PARSED: {node_cls.__name__:} {line}")

                    match node_cls.__name__:
                        case "Label":
                            label_name = data['name']
                            existing_label = self.labels.get(label_name) 
                            replace = data.get('replace')
                            if existing_label and not replace:
                                parsed = False
                                errors.append(f"\nERROR: duplicate label '{label_name }'. Use 'replace: {data['name']}' if this is intentional. {file_name}:{line_no} - {line}")
                                break
                            elif existing_label and replace:
                                # Make the pervious version jump to the replacement
                                # making fall through also work
                                existing_label.cmds = [Jump(jump_name=label_name,loc=0)]

                            
                            #####
                            # Dangling if, for, end_await
                            for node in EndAwait.stack:
                                errors.append(f"\nERROR: Missing end_await prior to label '{active_name}'cmd {node.loc}")
                            EndAwait.stack.clear()
                            for node in LoopStart.loop_stack:
                                errors.append(f"\nERROR: Missing next of loop prior to label''{active_name}'cmd {node.loc}")
                            LoopStart.loop_stack.clear()
                            for node in IfStatements.if_chains:
                                errors.append(f"\nERROR: Missing end_if prior to label '{active_name}'cmd {node.loc}")
                            IfStatements.if_chains.clear()
                            for node in MatchStatements.chains:
                                errors.append(f"\nERROR: Missing end_match prior to label '{active_name}'cmd {node.loc}")
                            MatchStatements.chains.clear()
                            next = Label(**data)
                            active.next = next
                            active = next
                            active_name = label_name
                            self.labels[data['name']] = active
                            exists =  Agent.SHARED.get_inventory_value(label_name)
                            exists =  Mast.globals.get(label_name, exists)
                            if exists and not replace:
                                errors.append(f"\nERROR: label conflicts with shared name, rename label '{label_name }'. {file_name}:{line_no} - {line}")
                                break

                            # Sets a variable for the label
                            Agent.SHARED.set_inventory_value(label_name, active)

                            self.cmd_stack.pop()
                            self.cmd_stack.append(active)
                        case "Input":
                            input = Input(**data)
                            self.inputs[data['name']] = input

                        case "Import":
                            lib_name = data.get("lib")
                            name = data['name']

                            if name.endswith('.py'):
                                import importlib
                                module_name = name[:-3]
                                if sys.modules.get(module_name) is None:
                                    import_file_name = os.path.join(fs.get_mission_dir(), name)
                                    spec = importlib.util.spec_from_file_location(module_name, import_file_name)
                                    module = importlib.util.module_from_spec(spec)
                                    sys.modules[module_name] = module
                                    spec.loader.exec_module(module)
                                    Mast.import_python_module(module_name)
                            else:
                                err = self.import_content(name, lib_name)
                                if err is not None:
                                    errors.extend(err)
                                    for e in err:
                                        print("import error "+e)


                        # Throw comments and markers away
                        case "Comment":
                            pass

                        case _:
                            try:
                                loc = len(self.cmd_stack[-1].cmds)
                                obj = node_cls(loc=loc, **data)
                                obj.file_num = file_num
                                obj.line_num = line_no
                            except Exception as e:
                                logger = logging.getLogger("mast.compile")
                                logger.error(f"ERROR: {file_name} {line_no} - {line}")
                                logger.error(f"Exception: {e}")

                                errors.append(f"\nERROR: {file_name} {line_no} - {line}")
                                errors.append(f"\nException: {e}")
                                return errors # return with first errors

                            obj.line = line if Mast.include_code else None
                            
                            

                            self.cmd_stack[-1].add_child(obj)
                    break
            if not parsed:
                mo = first_non_newline_index(lines)

                if mo:
                    # this just blank lines
                    #line_no += mo
                    line = lines[:mo]
                    lines = lines[mo:]
                else:
                    mo = first_newline_index(lines)

                    logger = logging.getLogger("mast.compile")
                    error = f"\nERROR: {line_no} - {file_name}\n\n    {lines[0:mo]}\n"
                    logger.error(error )
                    errors.append(error)
                    lines = lines[mo+1:]

        for node in EndAwait.stack:
            errors.append(f"\nERROR: Missing end_await prior to label '{active_name}'cmd {node.loc}")
        EndAwait.stack.clear()
        for node in LoopStart.loop_stack:
            errors.append(f"\nERROR: Missing next of loop prior to label''{active_name}'cmd {node.loc}")
        LoopStart.loop_stack.clear()
        for node in IfStatements.if_chains:
            errors.append(f"\nERROR: Missing end_if prior to label '{active_name}'cmd {node.loc}")
        IfStatements.if_chains.clear()
        for node in MatchStatements.chains:
            errors.append(f"\nERROR: Missing end_match prior to label '{active_name}'cmd {node.loc}")
        MatchStatements.chains.clear()

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
