from sbs_utils.quests.quest import Assign
from sbs_utils.quests.quest import Await
from sbs_utils.quests.quest import Cancel
from sbs_utils.quests.quest import Comment
from sbs_utils.quests.quest import Delay
from sbs_utils.quests.quest import End
from sbs_utils.quests.quest import Input
from sbs_utils.quests.quest import Jump
from sbs_utils.quests.quest import Label
from sbs_utils.quests.quest import Parallel
from sbs_utils.quests.quest import Quest
from sbs_utils.quests.quest import QuestData
from sbs_utils.quests.quest import QuestError
from sbs_utils.quests.quest import QuestNode
from sbs_utils.quests.quest import Rule
from sbs_utils.quests.quest import Var
from enum import IntEnum
def first_non_newline_index (s):
    ...
def first_non_space_index (s):
    ...
def validate_cmd (quest, cmd):
    ...
def validate_label (quest, label):
    ...
def validate_quest (quest):
    ...
def validate_var (quest, name, value):
    ...
class AssignRunner(QuestRuntimeNode):
    """class AssignRunner"""
    def poll (self, quest, thread, node: sbs_utils.quests.quest.Assign):
        ...
class AwaitRunner(QuestRuntimeNode):
    """class AwaitRunner"""
    def enter (self, quest, thread, node: sbs_utils.quests.quest.Await):
        ...
    def poll (self, quest, thread, node: sbs_utils.quests.quest.Await):
        ...
class CancelRunner(QuestRuntimeNode):
    """class CancelRunner"""
    def poll (self, quest, thread: sbs_utils.quests.questrunner.QuestAsync, node: sbs_utils.quests.quest.Cancel):
        ...
class DelayRunner(QuestRuntimeNode):
    """class DelayRunner"""
    def enter (self, quest, thread, node):
        ...
    def poll (self, quest, thread, node):
        ...
class EndRunner(QuestRuntimeNode):
    """class EndRunner"""
    def poll (self, quest, thread, node: sbs_utils.quests.quest.End):
        ...
class JumpRunner(QuestRuntimeNode):
    """class JumpRunner"""
    def poll (self, quest, thread, node: sbs_utils.quests.quest.Jump):
        ...
class ParallelRunner(QuestRuntimeNode):
    """class ParallelRunner"""
    def enter (self, quest, thread, node: sbs_utils.quests.quest.Parallel):
        ...
    def poll (self, quest, thread, node: sbs_utils.quests.quest.Parallel):
        ...
class PollResults(IntEnum):
    """An enumeration."""
    OK_ADVANCE_FALSE : 3
    OK_ADVANCE_TRUE : 2
    OK_END : 99
    OK_JUMP : 1
    OK_RUN_AGAIN : 4
class QuestAsync(object):
    """class QuestAsync"""
    def __init__ (self, main: sbs_utils.quests.questrunner.QuestRunner, inputs=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def call_leave (self):
        ...
    def eval_code (self, code):
        ...
    def get_symbols (self):
        ...
    def jump (self, label='main'):
        ...
    def next (self, first=False):
        ...
    def runtime_error (self, s):
        ...
    def start_thread (self, label='main', inputs=None, thread_name=None) -> sbs_utils.quests.questrunner.QuestAsync:
        ...
    def tick (self):
        ...
class QuestRunner(object):
    """class QuestRunner"""
    def __init__ (self, quest: sbs_utils.quests.quest.Quest, overrides=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def cancel_thread (self, name):
        ...
    def runtime_error (self, message):
        ...
    def start_thread (self, label='main', inputs=None, thread_name=None) -> sbs_utils.quests.questrunner.QuestAsync:
        ...
    def tick (self):
        ...
class QuestRuntimeError(object):
    """class QuestRuntimeError"""
    def __init__ (self, message, line_no):
        """Initialize self.  See help(type(self)) for accurate signature."""
class QuestRuntimeNode(object):
    """class QuestRuntimeNode"""
    def enter (self, quest, runner, node):
        ...
    def leave (self, quest, runner, node):
        ...
    def poll (self, quest, runner, node):
        ...
