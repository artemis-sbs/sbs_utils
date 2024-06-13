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
from inspect import getmembers, isfunction , signature
import sys
from ..helpers import format_exception



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
OPT_DATA_REGEX = r"""(?P<data>([ \t]*\{[^\n\r\f]+\}))?"""
PY_EXP_REGEX = r"""((?P<py>~~)[\s\S]*?(?P=py))"""
STRING_REGEX = r"""((?P<quote>((["']{3})|["']))[ \t\S]*(?P=quote))"""


IF_EXP_REGEX = r"""([ \t]+if(?P<if_exp>[^:\n\r\f]+))?"""
BLOCK_START = r":[ \t]*(?=\r\n|\n|\#)"


class ParseData:
    def __init__(self, start, end, data):
        self.start = start
        self.end = end
        self.data = data


class MastNode:
    file_num:int
    line_num:int
    is_label = False

    def __init__(self):
        self.dedent_loc = None
    
    def add_child(self, cmd):
        #print("ADD CHILD")
        pass

    def is_indentable(self):
        return False
    
    def is_virtual(self):
        """ 
        Virtual nodes are not added to the command stack
        instead the interact with other nodes
        """
        return False

    def create_end_node(self, loc, dedent_obj, compile_info):
        self.dedent_loc = loc

    def post_dedent(self,compile_info):
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
    rule = re.compile(r'(?P<m>=|\?){2,}\s*(?P<replace>replace:)?[ \t]*(?P<name>\w+)[ \t]*((?P=m){2,})?')
    is_label = True

    def __init__(self, name, replace=None, m=None, loc=None, compile_info=None):
        super().__init__()

        self.name = name
        self.cmds = []
        self.next = None
        self.loc = loc
        self.replace = replace is not None

    def add_child(self, cmd):
        self.cmds.append(cmd)


class RouteLabel(Label):
    route_label = 0
    rule = re.compile(r'\/{2,}(?P<path>([\w\/]+))'+IF_EXP_REGEX)

    def __init__(self, path, if_exp=None, loc=None, compile_info=None):
        # Label stuff
        name = f"__route__{path}__{RouteLabel.route_label}__" 
        RouteLabel.route_label += 1

        super().__init__(name)

        self.path= path
        self.if_exp = if_exp
        # need to negate if
        if self.if_exp is not None:
            self.if_exp = if_exp.strip()
            self.if_exp = 'not ' + self.if_exp

        self.next = None
        self.loc = loc
        self.replace = None
        self.cmds = []

    def generate_label(self, compile_info=None):
        from ..procedural import routes 
        

        path = self.path.strip('/')
        paths = path.split('/', 1)

        match paths:
            # two parameters, nav
            case ["comms",*b]: 
                routes.route_comms_navigate(self.path, self)
            case ["science",*b]: 
                routes.route_science_navigate(self.path, self)
            case ["gui",*b]: 
                routes.route_gui_navigate(self.path, self)
            case ["spawn"]: 
                routes.route_spawn(self)
            case ["spawn", "grid"]: 
                routes.route_spawn_grid(self)
            case ["focus", "comms"]: 
                routes.route_focus_comms(self)
            case ["focus", "weapons"]: 
                routes.route_focus_weapons(self)
            case ["focus", "science"]: 
                routes.route_focus_science(self)
            case ["focus", "grid"]: 
                routes.route_focus_grid(self)
            case ["select", "comms"]: 
                routes.route_select_comms(self)
            case ["select", "weapons"]: 
                routes.route_select_weapons(self)
            case ["select", "science"]: 
                routes.route_select_science(self)
            case ["select", "grid"]: 
                routes.route_select_grid(self)
            case ["object", "grid"]: 
                routes.route_object_grid(self)
            case ["point", "comms"]: 
                routes.route_point_comms(self)
            case ["point", "weapons"]: 
                routes.route_point_weapons(self)
            case ["point", "science"]: 
                routes.route_point_science(self)
            case ["point", "grid"]: 
                routes.route_point_grid(self)
            case ["collision", "object"]: 
                routes.route_collision_object(self)
            case ["console", "change"]: 
                routes.route_change_console(self)
            case ["console", "mainscreen", "change"]: 
                routes.route_console_mainscreen_change(self)
            case ["damage", "internal"]: 
                routes.route_damage_internal(self)
            case ["damage", "heat"]: 
                routes.route_damage_heat(self)
            case ["damage", "object"]: 
                routes.route_damage_object(self)
            case ["dock"]: 
                routes.route_dock(self)
            
            case _:
                raise f"Invalid route label {self.path}"
                    
        if self.if_exp:
            cmd = Yield('success', if_exp=self.if_exp, loc=0, compile_info=compile_info)
            cmd.file_num = self.file_num
            cmd.line_num = self.line_num
            cmd.line = "yield success to test RouteLabel"
            self.add_child(cmd)

    def on_end_label(self, compile_info=None):
            cmd = Yield('success', loc=len(self.cmds), compile_info=compile_info)
            cmd.file_num = self.file_num
            cmd.line_num = self.line_num
            cmd.line = "yield success to close RouteLabel"
            self.add_child(cmd)
    def add_child(self, cmd):
        self.cmds.append(cmd)


class LoopEnd(MastNode):
    """
    LoopEnd is a node that is injected to allow loops to know where the end is
    """
    #rule = re.compile(r'((?P<loop>next)[ \t]*(?P<name>\w+))')
    def __init__(self, start=None, name=None,loc=None, compile_info=None):
        super().__init__()
        self.start = start
        self.loc = loc
        self.start.end = self
        


class LoopStart(MastNode):
    rule = re.compile(r'(for[ \t]*(?P<name>\w+)[ \t]*)(?P<while_in>in|while)((?P<cond>[^\n\r\f]+))'+BLOCK_START)
    loop_stack = {}
    def __init__(self, while_in=None, cond=None, name=None, loc=None, compile_info=None):
        super().__init__()
        if cond:
            cond = cond.lstrip()
            self.code = compile(cond, "<string>", "eval")
        else:
            self.code = None
        self.name = name
        self.is_while = while_in == "while"
        self.loc = loc
        self.end = None
        self.indent = compile_info.indent

    def post_dedent(self,compile_info):
        #
        # This needs to happen after the dedent, indents are all processed
        #
        LoopStart.loop_stack[compile_info.indent] =self
        
        
    def is_indentable(self):
        return True

    def create_end_node(self, loc, dedent_obj, compile_info):
        end =  LoopEnd(self, loc=loc, compile_info=compile_info)

        # if dedent_obj.__class__ == LoopStart:
        #     LoopStart.loop_stack.pop()
        #     LoopStart.loop_stack.pop()
        #     LoopStart.loop_stack.append(dedent_obj)
        # else:
        #     LoopStart.loop_stack.pop()
        if LoopStart.loop_stack[self.indent] != self:
            raise "For loop indention issue"
        
        LoopStart.loop_stack[self.indent] = None


        # Dedent is one passed the end node
        self.dedent_loc = loc+1
        return end
        

class WithEnd(MastNode):
    """
    LoopEnd is a node that is injected to allow loops to know where the end is
    """
    #rule = re.compile(r'((?P<loop>next)[ \t]*(?P<name>\w+))')
    def __init__(self, start=None, name=None,loc=None, compile_info=None):
        super().__init__()
        self.start = start
        self.loc = loc
        self.start.end = self


class WithStart(MastNode):
    rule = re.compile(r'(with[ \t]*(?P<obj>[^\n\r\f]+))')
    with_vars = 0
    def __init__(self, obj=None, name=None, loc=None, compile_info=None):
        super().__init__()
        if obj:
            self.code = compile(obj, "<string>", "eval")
        else:
            self.code = None
        self.name = name
        self.with_name = f"__WITH_{WithStart.with_vars}"
        WithStart.with_vars += 1

        self.loc = loc
        self.end = None
        
    def is_indentable(self):
        return True
    
    @classmethod
    def parse(cls, lines):
        mo = cls.rule.match(lines)
        if mo:
            span = mo.span()
            data = mo.groupdict()
            obj= data.get("obj")
            if obj is None:
                return None
            obj = obj.strip()

            if not obj.endswith(":"):
                return None
            obj = obj[:-1]
            obj = obj.strip()
            
            has_as = obj.rsplit(" as ")
            if len(has_as)==2:
                data["name"] = has_as[1]
                data["obj"] = has_as[0]
            elif len(has_as)!=1:
                return None
            else:
                data["obj"] = obj

            return ParseData(span[0], span[1], data)
        else:
            return None


    def create_end_node(self, loc, _,  compile_info):
        end =  WithEnd(self, loc=loc)
        # Dedent is one passed the end node
        self.dedent_loc = loc+1
        return end
        



class LoopBreak(MastNode):

    #rule = re.compile(r'(?P<op>break|continue)\s*(?P<name>\w+)')
    rule = re.compile(r'(?P<op>break|continue)'+IF_EXP_REGEX)
    def __init__(self, op=None, name=None, if_exp=None, loc=None, compile_info=None):
        super().__init__()
        self.name = name
        self.op = op

        # Find the right for loop
        prev_indent = -1
        for (i, obj) in LoopStart.loop_stack.items():
            # Skip anything th
            if i >= compile_info.indent or obj is None:
                continue

            if i > prev_indent:
                prev_indent = i
        if prev_indent >-1:
            self.start = LoopStart.loop_stack.get(prev_indent, None)

        if self.start is None:
            raise Exception("MAST break/continue indention error") 

        self.loc = loc
        if if_exp:
            if_exp = if_exp.lstrip()
            self.if_code = compile(if_exp, "<string>", "eval")
        else:
            self.if_code = None

    

class IfStatements(MastNode):
    rule = re.compile(r'((?P<end>else:)|(((?P<if_op>if|elif)[ \t]+?(?P<if_exp>[ \t\S]+?)'+BLOCK_START+')))')

    if_chains = {}

    def __init__(self, end=None, if_op=None, if_exp=None, loc=None, compile_info=None):
        super().__init__()
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
            self.if_node = IfStatements.if_chains.get(compile_info.indent)
            if self.if_node is not None:
                self.if_node.if_chain.append(self)
            IfStatements.if_chains[compile_info.indent] = None
        elif "else:" == self.end:
            self.if_node = IfStatements.if_chains.get(compile_info.indent)
            if self.if_node is not None:
                self.if_node.if_chain.append(self)
            
        elif "elif" == self.if_op:
            self.if_node = IfStatements.if_chains.get(compile_info.indent)
            if self.if_node is not None:
                self.if_node.if_chain.append(self)
            
        elif "if" == self.if_op:
            self.if_chain = [self]
            self.if_node = self
            IfStatements.if_chains[compile_info.indent] = self
            

    def is_indentable(self):
        return True
    
    def create_end_node(self, loc, dedent_obj, compile_info):
        self.if_node.dedent_loc = loc

        return None

class MatchStatements(MastNode):
    #rule = re.compile(r'((?P<end>case[ \t]*_:|end_match)|(((?P<op>match|case)[ \t]+?(?P<exp>[^\n\r\f]+)'+BLOCK_START+')))')
    rule = re.compile(r'((?P<op>match|case)[ \t]+?(?P<exp>(_)|([^\n\r\f]+))'+BLOCK_START+')')
    chains = []
    def __init__(self, end=None, op=None, exp=None, loc=None, compile_info=None):
        super().__init__()

        self.loc = loc
        self.match_exp = None
        self.end = end
        self.op = op
        self.chain = None
        self.match_node = None

        if "case" == op:
            the_match_node = MatchStatements.chains[-1]
            self.match_node = the_match_node
            the_match_node.chain.append(self)
        elif "match" == op:
            self.match_node = self
            self.chain = []
            MatchStatements.chains.append(self)
            
        if op == "match":
            self.match_exp = exp.lstrip()
        elif exp:
            exp = exp.lstrip()
            if exp == "_":
                self.code = compile('True', "<string>", "eval")
            else:
                exp = self.match_node.match_exp +"==" + exp
                self.code = compile(exp, "<string>", "eval")
        else:
            self.code = None

    def is_indentable(self):
        return True
    
    def create_end_node(self, loc, dedent_obj, compile_info):
        if dedent_obj is None:
            # Dandling
            self.match_node.dedent_loc = loc
            if self.op == 'match':
                MatchStatements.chains.pop()
        elif dedent_obj.__class__ == MatchStatements and self.op == 'match':
            if dedent_obj.op=='match':
                MatchStatements.chains.pop()
                MatchStatements.chains.pop()
                self.match_node.dedent_loc = loc
                MatchStatements.chains.append(dedent_obj)
            else:
                self.match_node.dedent_loc = loc

        elif dedent_obj.__class__ == MatchStatements:
            self.match_node.dedent_loc = loc
        else:
            self.match_node.dedent_loc = loc
            if self.op == 'match':
                MatchStatements.chains.pop()

        return None

class PyCode(MastNode):
    rule = re.compile(r'((\~{2,})\n?(?P<py_cmds>[\s\S]+?)\n?(\~{2,}))')

    def __init__(self, py_cmds=None, loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        if py_cmds:
            py_cmds= py_cmds.lstrip()
            self.code = compile(py_cmds, "<string>", "exec")

class Import(MastNode):
    rule = re.compile(r'(from[ \t]+(?P<lib>[\w\.\\\/-]+)[ \t]+)?import\s+(?P<name>[\w\.\\\/-]+)')

    def __init__(self, name, lib=None, loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        self.name = name
        self.lib = lib


class Comment(MastNode):
    #rule = re.compile(r'#[ \t\S]*)')
    rule = re.compile(r'(#[ \t\S]*)|(/\*[^*]*\*+(?:[^/*][^*]*\*+)*/)|([!]{3,}\s*(?P<com>\w+)\s*[!]{3,}[\s\S]+[!]{3,}\s*end\s+(?P=com)\s*[!]{3,})')

    def __init__(self, com=None, loc=None, compile_info=None):
        super().__init__()
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
        r'(?P<scope>(shared|temp)\s+)?(?P<lhs>[\w\.\[\]]+)\s*(?P<oper>=|\+=|-=|\*=|%=|/=|//=)(?P<a_wait>\s*await)?\s*(?P<exp>('+PY_EXP_REGEX+'|'+STRING_REGEX+'|[^\n\r\f]+))')

    """ Note this doesn't support destructuring. To do so isn't worth the effort"""
    def __init__(self, scope, lhs, oper, exp,a_wait=None,  quote=None, py=None, loc=None, compile_info=None):
        super().__init__()
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
        self.is_await = a_wait is not None

        if lhs in Mast.globals:
            raise Exception(f"Variable assignment to a keyword {lhs}")



class Jump(MastNode):
    #rule = re.compile(r"""(((?P<jump>jump|->|push|->>|popjump|<<->|poppush|<<->>)[ \t]*(?P<jump_name>\w+))|(?P<pop>pop|<<-))"""+OPT_ARGS_REGEX+IF_EXP_REGEX)
    rule = re.compile(r"""(?P<jump>jump|->)[ \t]*(?P<jump_name>\w+)"""+OPT_DATA_REGEX+IF_EXP_REGEX)
    def __init__(self, pop=None, jump=None, jump_name=None, if_exp=None, data=None, loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        self.label = jump_name
        # self.push = jump == 'push' or jump == "->>"
        # self.pop = pop is not None
        # self.pop_jump = jump == 'popjump'or jump == "<<->"
        # self.pop_push = jump == 'poppush'or jump == "<<->>"
        if if_exp:
            if_exp = if_exp.lstrip()
            self.if_code = compile(if_exp, "<string>", "eval")
        else:
            self.if_code = None
        self.data = data
        if data is not None:
            data = data.lstrip()
            self.data = compile(data, "<string>", "eval")


CLOSE_FUNC = r"\)[ \t]*(?=\r\n|\n|\#)"
class FuncCommand(MastNode):
    rule = re.compile(r'(?P<is_await>await\s+)?(?P<py_cmds>[\w\.]+\s*\([^\n\r\f]+[ \t]*(?=\r\n|\n|\#))')
    def __init__(self, is_await=None, py_cmds=None, loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        self.is_await = is_await != None
        if py_cmds:
            py_cmds= py_cmds.lstrip()
            self.code = compile(py_cmds, "<string>", "eval")

# class EndAwait(MastNode):
#     rule = re.compile(r'end_await')
#     stack = []
#     def __init__(self, loc=None, compile_info=None):
#         super().__init__()
#         self.loc = loc
#         self.await_node = Await.stack[-1]
#         Await.stack[-1].end_await_node = self
#         Await.stack.pop()


class Await(MastNode):
    """
    waits for an existing or a new 'task' to run in parallel
    this needs to be a rule before Parallel
    """
    stack = []
    rule = re.compile(r"""await[ \t]+(until[ \t]+(?P<until>\w+)[ \t]+)?(?P<if_exp>[^:\n\r\f]+)"""+BLOCK_START)
    def __init__(self, until=None, if_exp=None, is_end = None, loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        self.end_await_node = None
        self.inlines = None
        self.buttons = None
        self.until = until

        self.timeout_label = None
        self.on_change = None
        self.fail_label = None
        self.is_end = is_end
        if self.is_end is None:
            self.inlines = []
            self.buttons = []
            Await.stack.append(self)
        else:
            Await.stack[-1].end_await_node = self

        if if_exp:
            if_exp = if_exp.lstrip()
            self.code = compile(if_exp, "<string>", "eval")
        else:
            self.code = None

    def add_inline(self, inline_data):
        self.inlines.append(inline_data)

    def is_indentable(self):
        return True
    
    def create_end_node(self, loc, dedent_obj, compile_info):
        self.dedent_loc = loc
        end = Await(is_end=True, loc = loc)
        end.dedent_loc = loc+1
        return end

MIN_SECONDS_REGEX = r"""([ \t]*((?P<minutes>\d+))m)?([ \t]*((?P<seconds>\d+)s))?"""
TIMEOUT_REGEX = r"([ \t]*timeout"+MIN_SECONDS_REGEX + r")?"





class AwaitInlineLabel(MastNode):
    rule = re.compile(r"\=(?P<val>[^:\n\r\f]+)"+BLOCK_START)
    def __init__(self, val=None, loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        self.inline = val
        self.await_node = Await.stack[-1]
        Await.stack[-1].add_inline(self)

    def is_indentable(self):
        return True

    def create_end_node(self, loc, dedent_obj, compile_info):
        """ cascade the dedent up to the start"""
        self.dedent_loc = loc+1
        


class OnChange(MastNode):
    rule = re.compile(r"on[ \t]+(change[ \t]+)?(?P<val>[^:]+)"+BLOCK_START)
    stack = []
    def __init__(self, end=None, val=None, loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        self.value = val
        if val:
            self.value = compile(val, "<string>", "eval")

        self.is_end = False
        #
        # Check to see if this is embedded in an await
        #
        self.await_node = None
        if len(Await.stack) >0:
            self.await_node = Await.stack[-1]
        self.end_node = None

        if end is not None:
            OnChange.stack[-1].end_node = self
            self.is_end = True
            OnChange.stack.pop()
        else:
            OnChange.stack.append(self)

    def is_indentable(self):
        return True

    def create_end_node(self, loc, dedent_obj, compile_info):
        """ cascade the dedent up to the start"""
        self.dedent_loc = loc
        end = OnChange("on_end", loc = loc)
        end.dedent_loc = loc+1
        return end


# OPT_STYLE = r"""([ \t]*style[ \t]*["'](?P<color>[ \t\S]+)["'])?"""
# FOR_RULE = r'([ \t]+for[ \t]+(?P<for_name>\w+)[ \t]+in[ \t]+(?P<for_exp>[ \t\S]+?))?'
OPT_BLOCK_START = r"(?P<block>\:)?[ \t]*(?=\r\n|\n|\#)"
class Button(MastNode):
    #### Pre routeLabels rule = re.compile(r"""(?P<button>\*|\+)[ \t]*(?P<q>["'])(?P<message>[ \t\S]+?)(?P=q)"""+OPT_STYLE+FOR_RULE+IF_EXP_REGEX+r"[ \t]*"+BLOCK_START)
    rule = re.compile(r"""(?P<button>\*|\+)[ \t]*(?P<q>["'])(?P<message>[ \t\S]+?)(?P=q)([ \t]*(?P<path>[\w\/]+))?"""+OPT_DATA_REGEX+IF_EXP_REGEX+r"[ \t]*"+OPT_BLOCK_START)
    def __init__(self, message=None, button=None,  
                color=None, if_exp=None, 
                #for_name=None, for_exp=None, 
                clone=False, 
                q=None, label=None, 
                new_task=None, data=None, path=None, block=None,loc=None, compile_info=None):
        super().__init__()
        #
        # Remember any field in here need to be set in clone()
        #
        if clone:
            return
        self.message = self.compile_formatted_string(message)
        self.sticky = (button == '+' or button=="button")
        self.color = color
        if color is not None:
            self.color = self.compile_formatted_string(color)
        self.visited = set() if not self.sticky else None
        self.loc = loc
        # Note: label is used with python buttons
        # and is generally None
        self.await_node = None
        self.is_block = block is not None
        self.use_sub_task = new_task
        self.label_to_run = None
        
        if compile_info is not None:
            self.label_to_run = compile_info.label
        if compile_info is not None and isinstance(compile_info.label, RouteLabel):
            if self.is_block:
                self.use_sub_task = True
                label = compile_info.label
        elif label is None:
            self.await_node = Await.stack[-1]
            self.await_node.buttons.append(self)
        self.label = label
        
        
        self.data = data
        if data is not None and isinstance(data, str):
            data = data.lstrip()
            self.data = compile(data, "<string>", "eval")
        self.path = None
        #
        # path from regex could be a path or a label
        # paths start with //, but we don't need those later
        #
        if path is not None and path.startswith('//'):
            self.path = path.strip('/')
        elif label is None:
            self.label = path
            self.use_sub_task = True

        

        if if_exp:
            if_exp = if_exp.lstrip()
            self.code = compile(if_exp, "<string>", "eval")
        else:
            self.code = None

        # self.for_name = for_name
        # if for_exp:
        #     for_exp = for_exp.lstrip()
        #     self.for_code = compile(for_exp, "<string>", "eval")
        # else:
        #     self.for_code = None
        

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
        proxy.label = self.label
        proxy.code = self.code
        proxy.color = self.color
        proxy.loc = self.loc
        proxy.await_node = self.await_node
        proxy.sticky = self.sticky
        proxy.visited = self.visited
        proxy.data = self.data
        # proxy.for_code = self.for_code
        # proxy.for_name = self.for_name
        proxy.is_block = self.is_block
        proxy.use_sub_task = self.use_sub_task
        proxy.path = self.path
        proxy.label_to_run = self.label_to_run
        ####
        # This is used by the gui buttons
        proxy.layout_item = None 
        

        return proxy
    
    def expand(self):
        pass

    def is_indentable(self):
        return True
    
    def create_end_node(self, loc, dedent_obj, compile_info):
        """ cascade the dedent up to the start"""
        if self.await_node is not None:
            self.await_node.dedent_loc = loc

    def resolve_data_context(self, task):
        if self.data is not None and not isinstance(self.data, dict):
            print( f"TODO: data {self.data}")
            self.data = task.eval_code(self.data)
            self.message = task.format_string(self.message)

    def run(self, task, button_promise):
        task_data = self.data
        if self.data is not None and not isinstance(self.data, dict):
            print( f"TODO: data {self.data}")
            task_data = task.eval_code(self.data)

        if self.use_sub_task and self.label:
            #print(f"NEW TASK LABEL {self.message}")
            
            sub_task = task.start_task(self.label, inputs=task_data, defer=True)
            #
            # Block commands in a sub task is a strait jump to the button
            # The button should dedent to a yield_idle
            #
            #
            if self.is_block:
                #print(f"BLOCK NEW TASK LABEL {self.message}")
                sub_task.jump(self.label, activate_cmd=self.loc+1)

            sub_task.set_variable("BUTTON_PROMISE", button_promise)
            sub_task.tick_in_context()
            return sub_task
        elif self.label:
            #print(f"LABEL {self.label} {self.message}")
            task.push_inline_block(self.label)
            task.tick_in_context()
        else:
            #print(f"INLINE {self.path} {self.label_to_run} {task.active_label} {self.message}")
            task.push_inline_block(task.active_label,self.loc+1)
            task.tick_in_context()

        return None


class Yield(MastNode):
    rule = re.compile(r'(->|yield[ \t])[ \t]*(?P<res>(FAIL|fail|SUCCESS|success|END|end|IDLE|idle|RESULT|result))(?P<exp>[^\n\r\f]+)?')
    def __init__(self, res= None, exp=None, if_exp=None, loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        self.result = res.lower()
        self.code = exp
        if exp is not None:
            exp = exp.lstrip()
            self.code = compile(exp, "<string>", "eval")
            #self.result  = "code"

        if if_exp:
            if_exp = if_exp.lstrip()
            self.if_code = compile(if_exp, "<string>", "eval")
        else:
            self.if_code = None

    @classmethod
    def parse(cls, lines):
        mo = cls.rule.match(lines)
        if not mo:
            return None
        span = mo.span()
        data = mo.groupdict()
        # res= data.get("res")
        obj= data.get("exp")
        if obj is not None:
            obj = obj.lstrip()
            is_if = obj.startswith("if ")

            has_if = obj.rsplit(" if ")
            if len(has_if)==2:
                data["if_exp"] = has_if[1]
                data["exp"] = has_if[0]
            elif is_if:
                data["exp"] = None
                data["if_exp"] = obj[3:]

        return ParseData(span[0], span[1], data)
        



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
    nl_idx=0
    for idx, c in enumerate(s):
        if c != '\n' and c != '\t' and c != ' ':
            return (idx,nl, nl_idx)
        if c == '\n':
            nl+=1
            nl_idx = idx
    return (len(s), nl, nl_idx)

def first_newline_index(s):
    for idx, c in enumerate(s):
        if c == '\n':
            return idx
    return len(s)


class ExpParseData:
    def __init__(self):
        self.in_string = False
        self.paren = 0
        self.bracket = 0
        self.brace = 0
        self.is_assign = False
        self.is_block = False
        self.idx = -1
        self.double_assign = False

    @property
    def in_something(self):
        return self.in_string or (self.paren>0) or (self.bracket>0) or (self.brace>0)
    @property
    def is_valid(self):
        return not (self.in_something or self.double_assign)

def find_exp_end(s, expect_block):
    data = ExpParseData()

    for idx, c in enumerate(s):
        if c == '\n' and not data.in_something:
            data.idx = idx
            return data
        if c == '=' and not data.in_something and not data.is_assign:
            data.is_assign = True
            continue
        elif c == '=' and not data.in_something and data.is_assign:
            data.double_assign = True
            return data
        
        if c == ':' and not data.in_something and expect_block:
            data.is_block = True
            data.idx = idx
            return data
        
        if c == '(' and not data.in_string:
            data.paren+=1
            continue
        if c == ')' and not data.in_string:
            data.paren-=1
            continue
        if c == '[' and not data.in_string:
            data.bracket+=1
            continue
        if c == ']' and not data.in_string:
            data.bracket-=1
            continue
        if c == '{' and not data.in_string:
            data.brace+=1
            continue
        if c == '}' and not data.in_string:
            data.brace-=1
            continue
        if c == '"' and not data.in_string:
            data.in_string = True
            continue
        if c == '"' and data.in_string:
            data.in_string = False
            continue

    data.idx = len(s)
    return data

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

    def __init__(self, cmds=None, is_import=False):
        super().__init__()

        self.lib_name = None
        self.is_import = is_import
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
        Comment,#NO EXP
        Label,#NO EXP
        RouteLabel,
        IfStatements,
        MatchStatements,
        LoopStart,
        WithStart,
        LoopBreak,
        PyCode,
        Import, #NO EXP
        Await,  # New Await Block
        FuncCommand,
        OnChange, 
        AwaitInlineLabel,
        Button,
        #Fail,
        Yield,
        #End,
        #ReturnIf,
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
        self.lib_name = None
        #### runtime
        self.schedulers = set()
        self.signal_observers = {}

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
        """TODO: Deprecate for signals?

        Args:
            source (_type_): _description_
            label (_type_): _description_
        """
        for scheduler in self.schedulers:
            if scheduler == source:
                continue
            scheduler.refresh(label)


    def signal_register(self, name, task, label_info):
        info = self.signal_observers.get(name, {})
        info[task] = label_info
        self.signal_observers[name] = info

    def signal_unregister(self, name, task):
        info = self.signal_observers.get(name,None)
        if info is None:
            return
        del info[task]
        self.signal_observers[name] = info

    def signal_emit(self, name, sender_task, data):
        tasks = self.signal_observers.get(name, {})
        for task in tasks:
            label_info = tasks[task]
            task.emit_signal(name, sender_task, label_info, data)

    def update_shared_props_by_tag(self, tag, props, test):
        for scheduler in self.schedulers:
            if scheduler.page is not None:
                scheduler.page.update_props_by_tag(tag, props, test)


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
        add = self.__class__(is_import=True)
        #add.basedir = self.basedir
        # add.is_import = True
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
                                cmd.if_chain[c].loc += offset
                        elif cmd.__class__.__name__ == "MatchStatements" and cmd.chain:
                            for c in range(len(cmd.chain)):
                                cmd.chain[c] += offset


                    main.cmds.extend(node.cmds)

                else:
                    self.labels[label] = node


        return errors


    def compile(self, lines, file_name):
        # Catching compiler errors lower to give better error message
        errors = []
        try:
            return self._compile(lines, file_name)
        except Exception as e:
            logger = logging.getLogger("mast.compile")
            logger.error(f"Exception: {e}")
            errors.append(f"\nException: {e}")
            errors.append(format_exception("",""))
            return errors # return with first errors

        

    def _compile(self, lines, file_name):
        file_num = self.clear(file_name)
        line_no = 1 # file line num are 1 based
        
        errors = []
        active = self.labels.get("main")
        active_name = "main"
        indent_stack = [(0,None)]
        prev_node = None

        class CompileInfo:
            def __init__(self) -> None:
                self.indent = None
                self.is_indent = None
                self.is_dedent = None
                self.label = None
                self.prev_node = None
                

        def inject_dedent(ind_level, indent_node, dedent_node, info):
            if len(indent_stack)==0:
                logger = logging.getLogger("mast.compile")
                error = f"\nERROR: Indention Error {line_no} - {file_name}\n\n"
                logger.error(error )
                errors.append(error)
                return
            
            if ind_level == 0:
                return
            loc = len(self.cmd_stack[-1].cmds)
            end_obj = indent_node.create_end_node(loc, dedent_node, info)
            if end_obj:
                end_obj.line_num = indent_node.line_num
                end_obj.line = indent_node.line
                end_obj.file_num = file_num
                self.cmd_stack[-1].add_child(end_obj)
                
            

        def inject_remaining_dedents():
            nonlocal indent_stack
            l = indent_stack[::-1]
            for (ind_level, ind_obj) in l:
                info = CompileInfo()
                info.indent = ind_level
                info.is_indent = False
                info.is_dedent = True
                inject_dedent(ind_level, ind_obj, None, info)
            indent_stack = [(0,None)]


        while len(lines):
            mo = first_non_whitespace_index(lines)
            line_no += mo[1] if mo is not None else 0
            #line = lines[:mo]
            lines = lines[mo[0]:]
            indent = max((mo[0] - mo[2]) -1,0)
            #Mast.current_indent = indent  # Replaced with compile_info
         
            # Keep location in file
            parsed = False
            if len(lines)==0:
                # Pop out all indents
                inject_remaining_dedents()
                break
            
            for node_cls in self.__class__.nodes:
                #mo = node_cls.rule.match(lines)
                mo = node_cls.parse(lines)
                if not mo:
                    continue
                #span = mo.span()
                data = mo.data

                line = lines[mo.start:mo.end]
                lines = lines[mo.end:]

                line_no += line.count('\n')
                

                parsed = True
                is_indent = False
                is_dedent = False

                if node_cls.__name__ != "Comment":
                    (cur_indent, _)  = indent_stack[-1] 
                    if indent > cur_indent:
                        #print(f"INDENT {indent}")
                        is_indent = True
                        # indent_stack.append(indent)
                    elif indent < cur_indent:
                        #print(f"DEDENT {indent}")
                        is_dedent = True
                
                logger = logging.getLogger("mast.compile")
                logger.debug(f"PARSED: {node_cls.__name__:} {line}")



                #match node_cls.__name__:
                # Throw comments and markers away
                if node_cls.__name__ == "Comment":
                    pass
                elif node_cls.__name__=="RouteLabel":
                    # label_name = data['name']
                    inject_remaining_dedents()
                    
                    next = RouteLabel(**data)
                    next.file_num = file_num
                    next.line_num = line_no
                    label_name = next.name
                    # No fallthrough
                    active.next = None
                    
                    if isinstance(active, RouteLabel):
                        active.on_end_label()
                    active = next

                    active_name = label_name
                    self.labels[active_name] = active
                    _info = CompileInfo()
                    _info.indent = indent
                    _info.is_dedent = is_dedent
                    _info.is_indent = is_indent
                    _info.label = active
                    next.generate_label(_info)
                    # Sets a variable for the label
                    Agent.SHARED.set_inventory_value(label_name, active)

                    self.cmd_stack.pop()
                    self.cmd_stack.append(active)
                    prev_node = None

                elif node_cls.is_label:
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

                    inject_remaining_dedents()

                    next = Label(**data)
                    active.next = next
                    if isinstance(active, RouteLabel):
                        active.on_end_label()
                    active = next
                    active_name = label_name
                    self.labels[active_name] = active
                    exists =  Agent.SHARED.get_inventory_value(label_name)
                    exists =  Mast.globals.get(label_name, exists)
                    if exists and not replace:
                        errors.append(f"\nERROR: label conflicts with shared name, rename label '{label_name }'. {file_name}:{line_no} - {line}")
                        break

                    # Sets a variable for the label
                    Agent.SHARED.set_inventory_value(label_name, active)

                    self.cmd_stack.pop()
                    self.cmd_stack.append(active)
                    prev_node = None

                
                elif node_cls.__name__== "Import":
                    lib_name = data.get("lib")
                    name = data['name']

                    if name.endswith('.py'):
                        import importlib
                        module_name = name[:-3]
                        if sys.modules.get(module_name) is None:
                            #print(f"import {self.basedir} {module_name}")
                            # if its not in this dir try the mission script dir
                            if os.path.isfile(os.path.join(self.basedir, name)):
                                import_file_name = os.path.join(self.basedir, name)
                            else:
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
                    prev_node = None
                else:
                    try:
                        loc = len(self.cmd_stack[-1].cmds)
                        info = CompileInfo()
                        info.indent = indent
                        info.is_dedent = is_dedent
                        info.is_indent = is_indent
                        info.label=active
                        
                        obj = node_cls(compile_info=info,loc=loc, **data)
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

                    if is_indent:
                        if prev_node is None or not prev_node.is_indentable():
                            errors.append(f"\nERROR: Bad indention {file_name} {line_no} - {line}")
                            return errors # return with first errors
                        block_node = prev_node
                        indent_stack.append((indent,block_node))
                    if is_dedent:
                        if len(indent_stack)==0:
                            errors.append(f"\nERROR: Bad indention {file_name} {line_no} - {line}")
                            return errors # return with first errors
                        
                        (i_loc,_) = indent_stack[-1]
                        while i_loc > indent:
                            (i_loc,i_obj) = indent_stack.pop()
                            # Should equal i_obj
                            end_obj = i_obj.create_end_node(loc, obj,info)
                            #
                            # So far only loops need this
                            # Creates the end node
                            #
                            if end_obj:
                                self.cmd_stack[-1].add_child(end_obj)
                                loc+=1
                                end_obj.file_num = file_num
                                end_obj.line_num = line_no
                                end_obj.line = obj.line
                                obj.loc += 1
                            
                            (i_loc,_) = indent_stack[-1]
                    #
                    # This is for nesting things
                    # like for loops, that should wait to do things 
                    #
                    obj.post_dedent(info)        
                    self.cmd_stack[-1].add_child(obj)
                    prev_node = obj
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

        # for node in Await.stack:
        #     errors.append(f"\nERROR: Missing end_await prior to label '{active_name}'cmd {node.loc}")
        # Await.stack.clear()
        # for node in LoopStart.loop_stack:
        #     errors.append(f"\nERROR: Missing next of loop prior to label''{active_name}'cmd {node.loc}")
        # LoopStart.loop_stack.clear()
        # for node in IfStatements.if_chains:
        #     errors.append(f"\nERROR: Missing end_if prior to label '{active_name}'cmd {node.loc}")
        # IfStatements.if_chains.clear()
        # for node in MatchStatements.chains:
        #     errors.append(f"\nERROR: Missing end_match prior to label '{active_name}'cmd {node.loc}")
        # MatchStatements.chains.clear()

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
