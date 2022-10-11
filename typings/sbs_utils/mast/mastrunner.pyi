from sbs_utils.mast.mast import Assign
from sbs_utils.mast.mast import Await
from sbs_utils.mast.mast import Cancel
from sbs_utils.mast.mast import Comment
from sbs_utils.mast.mast import Delay
from sbs_utils.mast.mast import End
from sbs_utils.mast.mast import IfStatements
from sbs_utils.mast.mast import Import
from sbs_utils.mast.mast import InlineData
from sbs_utils.mast.mast import InlineLabelBreak
from sbs_utils.mast.mast import InlineLabelEnd
from sbs_utils.mast.mast import InlineLabelStart
from sbs_utils.mast.mast import Input
from sbs_utils.mast.mast import Jump
from sbs_utils.mast.mast import Label
from sbs_utils.mast.mast import Mast
from sbs_utils.mast.mast import MastCompilerError
from sbs_utils.mast.mast import MastDataObject
from sbs_utils.mast.mast import MastNode
from sbs_utils.mast.mast import Parallel
from sbs_utils.mast.mast import PyCode
from sbs_utils.mast.mast import Rule
from sbs_utils.mast.mast import Scope
from enum import Enum
from enum import IntEnum
from zipfile import ZipFile
def first_newline_index (s):
    ...
def first_non_newline_index (s):
    ...
def first_non_space_index (s):
    ...
class AssignRunner(MastRuntimeNode):
    """class AssignRunner"""
    def poll (self, mast, thread: sbs_utils.mast.mastrunner.MastAsync, node: sbs_utils.mast.mast.Assign):
        ...
class AwaitRunner(MastRuntimeNode):
    """class AwaitRunner"""
    def enter (self, mast, thread, node: sbs_utils.mast.mast.Await):
        ...
    def poll (self, mast, thread, node: sbs_utils.mast.mast.Await):
        ...
class CancelRunner(MastRuntimeNode):
    """class CancelRunner"""
    def poll (self, mast, thread: sbs_utils.mast.mastrunner.MastAsync, node: sbs_utils.mast.mast.Cancel):
        ...
class DelayRunner(MastRuntimeNode):
    """class DelayRunner"""
    def enter (self, mast, thread, node):
        ...
    def poll (self, mast, thread, node):
        ...
class EndRunner(MastRuntimeNode):
    """class EndRunner"""
    def poll (self, mast, thread, node: sbs_utils.mast.mast.End):
        ...
class IfStatementsRunner(MastRuntimeNode):
    """class IfStatementsRunner"""
    def first_true (self, thread: sbs_utils.mast.mastrunner.MastAsync, node: sbs_utils.mast.mast.IfStatements):
        ...
    def poll (self, mast, thread, node: sbs_utils.mast.mast.IfStatements):
        ...
class InlineLabelBreakRunner(MastRuntimeNode):
    """class InlineLabelBreakRunner"""
    def enter (self, mast, thread: sbs_utils.mast.mastrunner.MastAsync, node: sbs_utils.mast.mast.InlineLabelStart):
        ...
    def poll (self, mast, thread, node: sbs_utils.mast.mast.InlineLabelEnd):
        ...
class InlineLabelEndRunner(MastRuntimeNode):
    """class InlineLabelEndRunner"""
    def poll (self, mast, thread, node: sbs_utils.mast.mast.InlineLabelEnd):
        ...
class InlineLabelStartRunner(MastRuntimeNode):
    """class InlineLabelStartRunner"""
    def enter (self, mast, thread: sbs_utils.mast.mastrunner.MastAsync, node: sbs_utils.mast.mast.InlineLabelStart):
        ...
    def poll (self, mast, thread, node: sbs_utils.mast.mast.InlineLabelStart):
        ...
class JumpRunner(MastRuntimeNode):
    """class JumpRunner"""
    def poll (self, mast, thread, node: sbs_utils.mast.mast.Jump):
        ...
class MastAsync(object):
    """class MastAsync"""
    def __init__ (self, main: sbs_utils.mast.mastrunner.MastRunner, inputs=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def call_leave (self):
        ...
    def eval_code (self, code):
        ...
    def format_string (self, message):
        ...
    def get_symbols (self):
        ...
    def get_value (self, key, defa):
        ...
    def jump (self, label='main', activate_cmd=0):
        ...
    def jump_inline_end (self, label_name, break_op):
        ...
    def jump_inline_start (self, label_name):
        ...
    def next (self):
        ...
    def pop_label (self):
        ...
    def push_label (self, label):
        ...
    def runtime_error (self, s):
        ...
    def set_value (self, key, value, scope):
        ...
    def start_thread (self, label='main', inputs=None, thread_name=None) -> sbs_utils.mast.mastrunner.MastAsync:
        ...
    def tick (self):
        ...
class MastRunner(object):
    """class MastRunner"""
    def __init__ (self, mast: sbs_utils.mast.mast.Mast, overrides=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def cancel_thread (self, name):
        ...
    def get_value (self, key, defa=None):
        ...
    def is_running (self):
        ...
    def on_start_thread (self, t):
        ...
    def runtime_error (self, message):
        ...
    def start_thread (self, label='main', inputs=None, thread_name=None) -> sbs_utils.mast.mastrunner.MastAsync:
        ...
    def tick (self):
        ...
class MastRuntimeError(object):
    """class MastRuntimeError"""
    def __init__ (self, message, line_no):
        """Initialize self.  See help(type(self)) for accurate signature."""
class MastRuntimeNode(object):
    """class MastRuntimeNode"""
    def enter (self, mast, runner, node):
        ...
    def leave (self, mast, runner, node):
        ...
    def poll (self, mast, runner, node):
        ...
class ParallelRunner(MastRuntimeNode):
    """class ParallelRunner"""
    def enter (self, mast, thread, node: sbs_utils.mast.mast.Parallel):
        ...
    def poll (self, mast, thread, node: sbs_utils.mast.mast.Parallel):
        ...
class PollResults(IntEnum):
    """An enumeration."""
    OK_ADVANCE_FALSE : 3
    OK_ADVANCE_TRUE : 2
    OK_END : 99
    OK_JUMP : 1
    OK_RUN_AGAIN : 4
class PushData(object):
    """class PushData"""
    def __init__ (self, label, active_cmd):
        """Initialize self.  See help(type(self)) for accurate signature."""
class PyCodeRunner(MastRuntimeNode):
    """class PyCodeRunner"""
    def poll (self, mast, thread: sbs_utils.mast.mastrunner.MastAsync, node: sbs_utils.mast.mast.PyCode):
        ...
