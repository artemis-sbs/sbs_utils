from sbs_utils.mast.mast import Assign
from sbs_utils.mast.mast import Await
from sbs_utils.mast.mast import AwaitCondition
from sbs_utils.mast.mast import Cancel
from sbs_utils.mast.mast import Comment
from sbs_utils.mast.mast import Delay
from sbs_utils.mast.mast import End
from sbs_utils.mast.mast import EndAwait
from sbs_utils.mast.mast import Event
from sbs_utils.mast.mast import IfStatements
from sbs_utils.mast.mast import Import
from sbs_utils.mast.mast import InlineData
from sbs_utils.mast.mast import Input
from sbs_utils.mast.mast import Jump
from sbs_utils.mast.mast import Label
from sbs_utils.mast.mast import Log
from sbs_utils.mast.mast import Logger
from sbs_utils.mast.mast import LoopBreak
from sbs_utils.mast.mast import LoopEnd
from sbs_utils.mast.mast import LoopStart
from sbs_utils.mast.mast import Marker
from sbs_utils.mast.mast import Mast
from sbs_utils.mast.mast import MastCompilerError
from sbs_utils.mast.mast import MastDataObject
from sbs_utils.mast.mast import MastNode
from sbs_utils.mast.mast import MatchStatements
from sbs_utils.mast.mast import Parallel
from sbs_utils.mast.mast import ParseData
from sbs_utils.mast.mast import PyCode
from sbs_utils.mast.mast import Rule
from sbs_utils.mast.mast import Scope
from sbs_utils.mast.mast import Timeout
from enum import Enum
from enum import IntEnum
from zipfile import ZipFile
def first_newline_index (s):
    ...
def first_non_newline_index (s):
    ...
def first_non_space_index (s):
    ...
class AssignRuntimeNode(MastRuntimeNode):
    """class AssignRuntimeNode"""
    def poll (self, mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mast.Assign):
        ...
class AwaitConditionRuntimeNode(MastRuntimeNode):
    """class AwaitConditionRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mast.AwaitCondition):
        ...
    def poll (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mast.AwaitCondition):
        ...
class AwaitRuntimeNode(MastRuntimeNode):
    """class AwaitRuntimeNode"""
    def enter (self, mast, task, node: sbs_utils.mast.mast.Await):
        ...
    def poll (self, mast, task, node: sbs_utils.mast.mast.Await):
        ...
class CancelRuntimeNode(MastRuntimeNode):
    """class CancelRuntimeNode"""
    def poll (self, mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mast.Cancel):
        ...
class DelayRuntimeNode(MastRuntimeNode):
    """class DelayRuntimeNode"""
    def enter (self, mast, task, node):
        ...
    def poll (self, mast, task, node):
        ...
class EndAwaitRuntimeNode(MastRuntimeNode):
    """class EndAwaitRuntimeNode"""
class EndRuntimeNode(MastRuntimeNode):
    """class EndRuntimeNode"""
    def poll (self, mast, task, node: sbs_utils.mast.mast.End):
        ...
class EventRuntimeNode(MastRuntimeNode):
    """class EventRuntimeNode"""
    def enter (self, mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node):
        ...
    def poll (self, mast, task, node):
        ...
class IfStatementsRuntimeNode(MastRuntimeNode):
    """class IfStatementsRuntimeNode"""
    def first_true (self, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mast.IfStatements):
        ...
    def poll (self, mast, task, node: sbs_utils.mast.mast.IfStatements):
        ...
class JumpRuntimeNode(MastRuntimeNode):
    """class JumpRuntimeNode"""
    def poll (self, mast, task, node: sbs_utils.mast.mast.Jump):
        ...
class LogRuntimeNode(MastRuntimeNode):
    """class LogRuntimeNode"""
    def enter (self, mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mast.Log):
        ...
class LoggerRuntimeNode(MastRuntimeNode):
    """class LoggerRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mast.Logger):
        ...
class LoopBreakRuntimeNode(MastRuntimeNode):
    """class LoopBreakRuntimeNode"""
    def enter (self, mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mast.LoopStart):
        ...
    def poll (self, mast, task, node: sbs_utils.mast.mast.LoopEnd):
        ...
class LoopEndRuntimeNode(MastRuntimeNode):
    """class LoopEndRuntimeNode"""
    def poll (self, mast, task, node: sbs_utils.mast.mast.LoopEnd):
        ...
class LoopStartRuntimeNode(MastRuntimeNode):
    """class LoopStartRuntimeNode"""
    def enter (self, mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mast.LoopStart):
        ...
    def poll (self, mast, task, node: sbs_utils.mast.mast.LoopStart):
        ...
class MastAsyncTask(object):
    """class MastAsyncTask"""
    def __init__ (self, main: 'MastScheduler', inputs=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def add_event (self, event_name, event):
        ...
    def call_leave (self):
        ...
    def eval_code (self, code):
        ...
    def exec_code (self, code):
        ...
    def format_string (self, message):
        ...
    def get_symbols (self):
        ...
    def get_value (self, key, defa):
        ...
    def get_variable (self, key):
        ...
    def jump (self, label='main', activate_cmd=0):
        ...
    def next (self):
        ...
    def pop_label (self, inc_loc=True):
        ...
    def push_label (self, label, activate_cmd=0, data=None):
        ...
    def run_event (self, event_name, event):
        ...
    def runtime_error (self, s):
        ...
    def set_value (self, key, value, scope):
        ...
    def set_value_keep_scope (self, key, value):
        ...
    def start_task (self, label='main', inputs=None, task_name=None) -> sbs_utils.mast.mastscheduler.MastAsyncTask:
        ...
    def tick (self):
        ...
class MastRuntimeError(object):
    """class MastRuntimeError"""
    def __init__ (self, message, line_no):
        """Initialize self.  See help(type(self)) for accurate signature."""
class MastRuntimeNode(object):
    """class MastRuntimeNode"""
    def enter (self, mast, scheduler, node):
        ...
    def leave (self, mast, scheduler, node):
        ...
    def poll (self, mast, scheduler, node):
        ...
class MastScheduler(object):
    """class MastScheduler"""
    def __init__ (self, mast: sbs_utils.mast.mast.Mast, overrides=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def cancel_task (self, name):
        ...
    def get_seconds (self, clock):
        """Gets time for a given clock default is just system """
    def get_value (self, key, defa=None):
        ...
    def get_variable (self, key):
        ...
    def is_running (self):
        ...
    def on_start_task (self, t):
        ...
    def runtime_error (self, message):
        ...
    def start_task (self, label='main', inputs=None, task_name=None) -> sbs_utils.mast.mastscheduler.MastAsyncTask:
        ...
    def tick (self):
        ...
class MatchStatementsRuntimeNode(MastRuntimeNode):
    """class MatchStatementsRuntimeNode"""
    def first_true (self, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mast.MatchStatements):
        ...
    def poll (self, mast, task, node: sbs_utils.mast.mast.MatchStatements):
        ...
class ParallelRuntimeNode(MastRuntimeNode):
    """class ParallelRuntimeNode"""
    def enter (self, mast, task, node: sbs_utils.mast.mast.Parallel):
        ...
    def poll (self, mast, task, node: sbs_utils.mast.mast.Parallel):
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
    def __init__ (self, label, active_cmd, data=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
class PyCodeRuntimeNode(MastRuntimeNode):
    """class PyCodeRuntimeNode"""
    def poll (self, mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mast.PyCode):
        ...
class TimeoutRuntimeNode(MastRuntimeNode):
    """class TimeoutRuntimeNode"""
    def poll (self, mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mast.Timeout):
        ...
