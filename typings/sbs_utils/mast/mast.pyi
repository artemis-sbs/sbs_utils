from enum import Enum
from enum import IntEnum
from zipfile import ZipFile
def first_newline_index (s):
    ...
def first_non_newline_index (s):
    ...
def first_non_space_index (s):
    ...
class Assign(MastNode):
    """class Assign"""
    def __init__ (self, scope, lhs, exp, quote=None, py=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
class Await(MastNode):
    """waits for an existing or a new 'thread' to run in parallel
    this needs to be a rule before Parallel"""
    def __init__ (self, name=None, spawn=None, label=None, inputs=None, if_exp=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def add_child (self, cmd):
        ...
class Cancel(MastNode):
    """Cancels a new 'thread' to run in parallel"""
    def __init__ (self, lhs=None, name=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
class Comment(MastNode):
    """class Comment"""
    def __init__ (self, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
class Delay(MastNode):
    """class Delay"""
    def __init__ (self, seconds=None, minutes=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
class End(MastNode):
    """class End"""
    def __init__ (self, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
class IfStatements(MastNode):
    """class IfStatements"""
    def __init__ (self, end=None, if_op=None, if_exp=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
class Import(MastNode):
    """class Import"""
    def __init__ (self, name, lib=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
class InlineData(object):
    """class InlineData"""
    def __init__ (self, start, end):
        """Initialize self.  See help(type(self)) for accurate signature."""
class Input(MastNode):
    """class Input"""
    def __init__ (self, name, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
class Jump(MastNode):
    """class Jump"""
    def __init__ (self, pop, pop_jump, push, jump, if_exp, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
class Label(MastNode):
    """class Label"""
    def __init__ (self, name, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def add_child (self, cmd):
        ...
class LoopBreak(MastNode):
    """class LoopBreak"""
    def __init__ (self, op=None, name=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
class LoopEnd(MastNode):
    """class LoopEnd"""
    def __init__ (self, loop=None, name=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
class LoopStart(MastNode):
    """class LoopStart"""
    def __init__ (self, if_exp=None, name=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
class Marker(MastNode):
    """class Marker"""
    def __init__ (self, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
class Mast(object):
    """class Mast"""
    def __init__ (self, cmds=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def add_runner (self, runner):
        ...
    def build (self, cmds):
        """Used to build via code not a script file
        should just process level things e.g. Input, Label, Var"""
    def clear (self):
        ...
    def compile (self, lines):
        ...
    def enable_logging ():
        ...
    def from_file (self, filename, lib_name=None):
        """Docstring"""
    def from_lib_file (self, file_name, lib_name):
        ...
    def import_content (self, filename, lib_file):
        ...
    def prune_main (self):
        ...
    def refresh_runners (self, source, label):
        ...
    def remove_runner (self, runner):
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
class MatchStatements(MastNode):
    """class MatchStatements"""
    def __init__ (self, end=None, op=None, exp=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
class Parallel(MastNode):
    """Creates a new 'thread' to run in parallel"""
    def __init__ (self, name=None, label=None, inputs=None, if_exp=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def add_child (self, cmd):
        ...
class PyCode(MastNode):
    """class PyCode"""
    def __init__ (self, py_cmds=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
class Rule(object):
    """class Rule"""
    def __init__ (self, re, cls):
        """Initialize self.  See help(type(self)) for accurate signature."""
class Scope(Enum):
    """An enumeration."""
    NORMAL : 2
    SHARED : 1
    TEMP : 99
