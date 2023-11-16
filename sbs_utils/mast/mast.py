from asyncio.log import logger
from enum import IntEnum, Enum
import re
import ast
import os
from .. import fs
from zipfile import ZipFile
from .. import faces, scatter
from ..agent import Agent, get_story_id
import math
import itertools
import logging
import random
from io import StringIO
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



class Log(MastNode):
    rule = re.compile(r"""log[ \t]+(name[ \t]+(?P<logger>[\w\.]*)[ \t]+)?(?P<q>['"]{3}|["'])(?P<message>[\s\S]+?)(?P=q)([ \t]+(?P<level>debug|info|warning|error|critical))?""")
    
    def __init__(self, message, logger=None, level=None, q=None, loc=None):
        self.message = self.compile_formatted_string(message)
        self.level = level if level is not None else "debug"
        self.logger = logger if logger is not None else "mast.story"
        self.loc = loc

class Logger(MastNode):
    rule = re.compile(r"""logger([ \t]+name[ \t]+(?P<logger>[\w\.]*))?([ \t]+string[ \t]+(?P<var>\w*))?([ \t]+file[ \t]*(?P<q>['"]{3}|["'])(?P<name>[^\n\r\f]+)(?P=q))?""")

    def __init__(self, logger=None, var=None, name=None, q=None, loc=None):
        self.var = var
        if name is not None:
            name = self.compile_formatted_string(name)
        self.name = name
        self.logger = logger if logger is not None else "mast.story"
        self.loc = loc

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

CLOSE_FUNC = r"\)[ \t]*(?=\r\n|\n|\#)"
class FuncCommand(MastNode):
    rule = re.compile(r'(?P<py_cmds>[\w\.]+\s*\([^\n\r\f]+[ \t]*(?=\r\n|\n|\#))')
    def __init__(self, py_cmds=None, loc=None):
        self.loc = loc
        if py_cmds:
            py_cmds= py_cmds.lstrip()
            self.code = compile(py_cmds, "<string>", "exec")



class Input(MastNode):
    rule = re.compile(r'input[ \t]+(?P<name>\w+)')

    def __init__(self, name, loc=None):
        self.loc = loc
        self.name = name

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
        r'(?P<scope>(shared|temp)\s+)?(?P<lhs>[\w\.\[\]]+)\s*(?P<oper>=|\+=|-=|\*=|%=|/=|//=)\s*(?P<exp>('+PY_EXP_REGEX+'|'+STRING_REGEX+'|.*))')

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


class Parallel(MastNode):
    """
    Creates a new 'task' to run in parallel
    """

    def __init__(self, name=None, is_block=None, await_task=None, 
                 any_labels=None, all_labels=None, label=None, inputs=None, loc=None):
        self.loc = loc
        self.name = name
        self.labels = label
        self.await_task = await_task
        self.code = None
        self.end_await_node = None
        self.minutes = 0
        self.seconds = 0
        self.timeout_label = None
        self.on_change = None
        self.fail_label = None
        if is_block:
            self.timeout_label = None
            self.fail_label = None
            EndAwait.stack.append(self)

        if await_task and name:
            self.await_task = True
            return
    
        self.labels = label
        self.all = False
        self.any = False
        
        if all_labels:
            self.all = True
            self.labels = re.split(r'\s*&\s*', all_labels)
        elif any_labels:
            self.any = True
            self.labels = re.split(r'\s*\|\s*', any_labels)

        if inputs:
            inputs = inputs.lstrip()
            self.code = compile(inputs, "<string>", "eval")
        
    task_name =  re.compile(r"""(?P<await_task>await)[ \t]+(?P<name>\w+)""")
    schedule_rule = re.compile(r"""(?P<await_task>await[ \t]*)?(var[ \t]+(?P<name>\w+)[ \t]*)?(schedule|\=>)[ \t]*(?P<label>\w+)(?P<inputs>[ \t]*"""+ DICT_REGEX+")?")
    any_all_rule = re.compile(r"""await[ \t]*(var[ \t]+(?P<name>\w+)[ \t]*)?(all[ \t]+(?P<all_labels>[ \t]*(\w+)(([ \t]*&[ \t]*)\w+)*)|any[ \t]+(?P<any_labels>[ \t]*(\w+)(([ \t]*\|[ \t]*)\w+)*))""") # (?P<inputs>\s*"""+ DICT_REGEX+")?")
    schedule_all_rule = re.compile(r"""(schedule[ \t]+|\=\>[ \t]*)all[ \t]+(?P<all_labels>[ \t]*(\w+)(([ \t]*&[ \t]*)\w+)*)(?P<inputs>[ \t]*"""+ DICT_REGEX+")?")
    #await_rule = re.compile(r"await\s+")
    #await_return_rule = re.compile(r"await\s*(?P<ret>->)?\s*")
    block_rule = re.compile(r"[ \t]*:")

    @classmethod
    def parse(cls, lines):
        #
        # schedule any/all
        #
        match_any_all_await =  Parallel.schedule_all_rule.match(lines) 
        if match_any_all_await:
            span = match_any_all_await.span()
            data = match_any_all_await.groupdict()
            data["await_task"] = True
            end = span[1]
            block =  Parallel.block_rule.match(lines[end:])
            
            if block:
                end+= block.span()[1]
                data["is_block"] = True
           
            return ParseData(span[0], end, data)
        
        #
        # await / schedule
        #
        match_sched_await =  Parallel.schedule_rule.match(lines) 
        if match_sched_await:
            span = match_sched_await.span()
            data = match_sched_await.groupdict()
            end = span[1]
            block =  Parallel.block_rule.match(lines[end:])
            
            if block:
                end+= block.span[1]
                data["is_block"] = True
           
            return ParseData(span[0], end, data)
        #
        # Await any/all
        #
        match_any_all_await =  Parallel.any_all_rule.match(lines) 
        if match_any_all_await:
            span = match_any_all_await.span()
            data = match_any_all_await.groupdict()
            data["await_task"] = True
            end = span[1]
            block =  Parallel.block_rule.match(lines[end:])
            
            if block:
                end+= block.span()[1]
                data["is_block"] = True
           
            return ParseData(span[0], end, data)
      
        #
        # Await an variable
        #
        match_task_await =  Parallel.task_name.match(lines) 
        if match_task_await:
            span = match_task_await.span()
            data = match_task_await.groupdict()
            data["await_task"] = True
            end = span[1]
            block =  Parallel.block_rule.match(lines[end:])
            
            if block:
                end+= block.span()[1]
                data["is_block"] = True
           
            return ParseData(span[0], end, data)


class Behavior(MastNode):
    """
    Creates a new 'task' to run in parallel
    """
    # yield bt sel a|a   [data]
    # await bt until fail seq a&b [data] 
    # await bt until success seq a&b [data]
    # await bt invert seq a&b [data]
    # await bt invert seq a&b [data]
    rule =  re.compile(r"""((?P<yield_await>await|yield)[ \t]+)?bt[ \t]+(((?P<invert>invert)|(until\s+(?P<until>fail|success)))[ \t]+)?((seq[ \t]*(?P<seq_labels>[ \t]*(\w+)(([ \t]*&[ \t]*)\w+)*))|(sel[ \t]*(?P<sel_labels>[ \t]*(\w+)(([ \t]*\|[ \t]*)\w+)*)))"""
                       + r"""(?P<inputs>[ \t]*"""+ DICT_REGEX+")?"
                       + r"""(?P<is_block>[ \t]*:)?""")
    
    

    # yield success
    # yield fail 
    # yield success if cond
    # yield fail if cond


    def __init__(self, yield_await=None, is_block=None, invert=None, until=None, sel_labels=None, seq_labels=None, inputs=None, loc=None):
        self.loc = loc
        
        self.end_await_node = None
        self.minutes = 0
        self.seconds = 0
        self.timeout_label = None
        self.on_change = None
        self.fail_label = None
        self.invert = invert is not None
        self.until = until
        self.code = None
        self.name = None
        self.conditional = None
        self.is_yield = yield_await=="yield"
        self.is_await = yield_await=="await"
        self.end_await_node = None

        if is_block:
            self.timeout_label = None
            self.fail_label = None
            EndAwait.stack.append(self)

        self.sequence =  seq_labels is not None
        self.fallback =  sel_labels is not None
        if seq_labels is not None:
            self.labels = re.split(r'\s*&\s*', seq_labels)
        elif sel_labels:
            self.labels = re.split(r'\s*\|\s*', sel_labels)

        if inputs:
            inputs = inputs.lstrip()
            self.code = compile(inputs, "<string>", "eval")
        

    

        
class EndAwait(MastNode):
    rule = re.compile(r'end_await')
    stack = []
    def __init__(self, loc=None):
        self.loc = loc
        EndAwait.stack[-1].end_await_node = self
        EndAwait.stack.pop()

#
# Deprecated
#
# class Event(MastNode):
#     rule = re.compile(r'(event[ \t]+(?P<event>[\w|_]+)'+BLOCK_START+')|(end_event)')
#     stack = []
#     def __init__(self, event=None, loc=None):
#         self.loc = loc
#         self.end = None
#         self.event = event
#         if event is None:
#             Event.stack[-1].end = self
#             Event.stack.pop()
#         else:
#             Event.stack.append(self)

MIN_SECONDS_REGEX = r"""([ \t]*((?P<minutes>\d+))m)?([ \t]*((?P<seconds>\d+)s))?"""
TIMEOUT_REGEX = r"([ \t]*timeout"+MIN_SECONDS_REGEX + r")?"
class Timeout(MastNode):
    rule = re.compile(r'timeout([ \t]*((?P<minutes>\d+))m)?([ \t]*((?P<seconds>\d+)s))?:')
    def __init__(self, minutes, seconds, loc=None):
        self.loc = loc
        
        self.await_node = EndAwait.stack[-1]
        EndAwait.stack[-1].timeout_label = self
        self.await_node.seconds = 0 if  seconds is None else int(seconds)
        self.await_node.minutes = 0 if  minutes is None else int(minutes)



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



class AwaitFail(MastNode):
    rule = re.compile(r'fail:')
    def __init__(self, loc=None):
        self.loc = loc
        
        self.await_node = EndAwait.stack[-1]
        EndAwait.stack[-1].fail_label = self



class AwaitCondition(MastNode):
    """
    waits for an existing or a new 'task' to run in parallel
    this needs to be a rule before Parallel
    """
    rule = re.compile(r"""await[ \t]+until[ \t]+(?P<if_exp>[^:]+)"""+BLOCK_START)
                      
    def __init__(self, if_exp=None, loc=None):
        self.loc = loc
        self.timeout_label = None
        self.on_change = None
        self.end_await_node = None
        self.fail_label = None

        # Done int timeout now
        self.seconds = 0 
        self.minutes = 0
        
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
    rule = re.compile(r"""cancel[ \t]*(?P<name>[\w\.\[\]]+)""")

    def __init__(self, lhs=None, name=None, loc=None):
        self.loc = loc
        self.name = name


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


class Delay(MastNode):
    clock = r"([ \t]*(?P<clock>\w+))"
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

class Mast(Agent):
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
        self.id = get_story_id()
        self.add()
        

        if cmds is None:
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
        Log,
        Logger,
        Input,
        #        Var,
        Import,
        AwaitCondition,
        FuncCommand,
#        Await,  # needs to be before Parallel
        Timeout,
        Change,
        EndAwait,
        AwaitFail,
        Behavior, # Needs to be in front of parallel
        Parallel,  # needs to be before Assign
        Cancel,
        Assign,
        Fail,
        Yield,
        End,
        ReturnIf,
        Jump,
        Delay,
        Marker,
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
            self.set_inventory_value("mast", self)
            self.set_inventory_value("SHARED", self.get_id())
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
            if len(errors) > 0:
                message = f"Compile errors\nCannot compile file {file_name}"
                errors.append(message)
            return errors
        return []
        

    def process_file_content(self,content, file_name):
        file_name, ext = os.path.splitext(file_name)
        errors = []
        match ext:
            case _:
                if content is not None:
                    errors = self.compile(content, file_name)

                    if len(errors) > 0:
                        message = f"Compile errors\nCannot compile file {file_name}"
                        errors.append(message)

        return errors
        
       

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
                                errors.append(f"ERROR: duplicate label '{label_name }'. Use 'replace: {data['name']}' if this is intentional. {file_name}:{line_no} - {line}")
                                break
                            elif existing_label and replace:
                                # Make the pervious version jump to the replacement
                                # making fall through also work
                                existing_label.cmds = [Jump(jump_name=label_name,loc=0)]

                            #####
                            # Dangling if, for, end_await
                            for node in EndAwait.stack:
                                errors.append(f"ERROR: Missing end_await prior to label '{active_name}'cmd {node.loc}")
                            EndAwait.stack.clear()
                            for node in LoopStart.loop_stack:
                                errors.append(f"ERROR: Missing next of loop prior to label''{active_name}'cmd {node.loc}")
                            LoopStart.loop_stack.clear()
                            for node in IfStatements.if_chains:
                                errors.append(f"ERROR: Missing end_if prior to label '{active_name}'cmd {node.loc}")
                            IfStatements.if_chains.clear()
                            for node in MatchStatements.chains:
                                errors.append(f"ERROR: Missing end_match prior to label '{active_name}'cmd {node.loc}")
                            MatchStatements.chains.clear()
                            next = Label(**data)
                            active.next = next
                            active = next
                            active_name = label_name
                            self.labels[data['name']] = active
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
                                    file_name = os.path.join(fs.get_mission_dir(), name)
                                    spec = importlib.util.spec_from_file_location(module_name, file_name)
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
                        case "Marker":
                            pass

                        case _:
                            try:
                                loc = len(self.cmd_stack[-1].cmds)
                                obj = node_cls(loc=loc, **data)
                                obj.file_num = file_num
                                obj.line_num = line_no
                            except Exception as e:
                                logger = logging.getLogger("mast.compile")
                                logger.error(f"ERROR: {line_no} - {line}")
                                logger.error(f"Exception: {e}")

                                errors.append(f"ERROR: {line_no} - {line}")
                                errors.append(f"Exception: {e}")
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
                    logger.error(f"ERROR: {line_no} - {lines[0:mo]}")
                    errors.append(f"ERROR: {line_no} - {lines[0:mo]}")
                    lines = lines[mo+1:]

        for node in EndAwait.stack:
            errors.append(f"ERROR: Missing end_await prior to label '{active_name}'cmd {node.loc}")
        EndAwait.stack.clear()
        for node in LoopStart.loop_stack:
            errors.append(f"ERROR: Missing next of loop prior to label''{active_name}'cmd {node.loc}")
        LoopStart.loop_stack.clear()
        for node in IfStatements.if_chains:
            errors.append(f"ERROR: Missing end_if prior to label '{active_name}'cmd {node.loc}")
        IfStatements.if_chains.clear()
        for node in MatchStatements.chains:
            errors.append(f"ERROR: Missing end_match prior to label '{active_name}'cmd {node.loc}")
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
        




