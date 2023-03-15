from enum import Enum
from enum import IntEnum
from zipfile import ZipFile
def first_newline_index (s):
    ...
def first_non_newline_index (s):
    ...
def first_non_space_index (s):
    ...
def getmembers (object, predicate=None):
    ...
def isfunction (object):
    ...
class Assign(MastNode):
    """class Assign"""
    def __init__ (self, scope, lhs, oper, exp, quote=None, py=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class AwaitCondition(MastNode):
    """waits for an existing or a new 'task' to run in parallel
    this needs to be a rule before Parallel"""
    def __init__ (self, minutes=None, seconds=None, if_exp=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class AwaitFail(MastNode):
    """class AwaitFail"""
    def __init__ (self, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class Cancel(MastNode):
    """Cancels a new 'task' to run in parallel"""
    def __init__ (self, lhs=None, name=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class Comment(MastNode):
    """class Comment"""
    def __init__ (self, com=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class Delay(MastNode):
    """class Delay"""
    def __init__ (self, clock, seconds=None, minutes=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class DoCommand(MastNode):
    """class DoCommand"""
    def __init__ (self, py_cmds=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class End(MastNode):
    """class End"""
    def __init__ (self, if_exp=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class EndAwait(MastNode):
    """class EndAwait"""
    def __init__ (self, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class Event(MastNode):
    """class Event"""
    def __init__ (self, event=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class Fail(MastNode):
    """class Fail"""
    def __init__ (self, if_exp=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class IfStatements(MastNode):
    """class IfStatements"""
    def __init__ (self, end=None, if_op=None, if_exp=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class Import(MastNode):
    """class Import"""
    def __init__ (self, name, lib=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class InlineData(object):
    """class InlineData"""
    def __init__ (self, start, end):
        """Initialize self.  See help(type(self)) for accurate signature."""
class Input(MastNode):
    """class Input"""
    def __init__ (self, name, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class Jump(MastNode):
    """class Jump"""
    def __init__ (self, pop, pop_jump_type, pop_jump, push, jump, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class Label(MastNode):
    """class Label"""
    def __init__ (self, name, replace=None, m=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def add_child (self, cmd):
        ...
    def parse (lines):
        ...
class Log(MastNode):
    """class Log"""
    def __init__ (self, message, logger=None, level=None, q=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class Logger(MastNode):
    """class Logger"""
    def __init__ (self, logger=None, var=None, name=None, q=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class LoopBreak(MastNode):
    """class LoopBreak"""
    def __init__ (self, op=None, name=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class LoopEnd(MastNode):
    """class LoopEnd"""
    def __init__ (self, loop=None, name=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class LoopStart(MastNode):
    """class LoopStart"""
    def __init__ (self, while_in=None, cond=None, name=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class Marker(MastNode):
    """class Marker"""
    def __init__ (self, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class Mast(object):
    """class Mast"""
    def __init__ (self, cmds=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def add_scheduler (self, scheduler):
        ...
    def build (self, cmds):
        """Used to build via code not a script file
        should just process level things e.g. Input, Label, Var"""
    def clear (self):
        ...
    def compile (self, lines):
        ...
    def content_from_lib_or_file (self, file_name, lib_name):
        ...
    def enable_logging ():
        ...
    def from_file (self, file_name, lib_name=None):
        """Docstring"""
    def import_content (self, filename, lib_file):
        ...
    def import_python_module (mod_name, prepend=None):
        ...
    def make_global (func):
        ...
    def make_global_var (name, value):
        ...
    def process_file_content (self, content, file_name):
        ...
    def prune_main (self):
        ...
    def refresh_schedulers (self, source, label):
        ...
    def remove_scheduler (self, scheduler):
        ...
class MastCompilerError(object):
    """class MastCompilerError"""
    def __init__ (self, message, line_no):
        """Initialize self.  See help(type(self)) for accurate signature."""
class MastDataObject(object):
    """class MastDataObject"""
    def __init__ (self, dictionary):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def __repr__ (self):
        """Return repr(self)."""
class MastNode(object):
    """class MastNode"""
    def add_child (self, cmd):
        ...
    def compile_formatted_string (self, message):
        ...
    def parse (lines):
        ...
class MatchStatements(MastNode):
    """class MatchStatements"""
    def __init__ (self, end=None, op=None, exp=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class Parallel(MastNode):
    """Creates a new 'task' to run in parallel"""
    def __init__ (self, name=None, is_block=None, await_task=None, reflect=None, all_any=None, conditional=None, labels=None, inputs=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class ParseData(object):
    """class ParseData"""
    def __init__ (self, start, end, data):
        """Initialize self.  See help(type(self)) for accurate signature."""
class PyCode(MastNode):
    """class PyCode"""
    def __init__ (self, py_cmds=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class ReturnIf(MastNode):
    """class ReturnIf"""
    def __init__ (self, if_exp=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class Rule(object):
    """class Rule"""
    def __init__ (self, re, cls):
        """Initialize self.  See help(type(self)) for accurate signature."""
class Scope(Enum):
    """class Scope"""
    NORMAL : 2
    SHARED : 1
    TEMP : 99
    UNKNOWN : 100
class Timeout(MastNode):
    """class Timeout"""
    def __init__ (self, minutes, seconds, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
