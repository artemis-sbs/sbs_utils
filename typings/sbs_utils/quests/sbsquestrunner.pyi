from sbs_utils.quests.sbsquest import Button
from sbs_utils.quests.sbsquest import Comms
from sbs_utils.quests.sbsquest import Near
from sbs_utils.quests.sbsquest import Target
from sbs_utils.quests.sbsquest import Tell
from sbs_utils.consoledispatcher import ConsoleDispatcher
from sbs_utils.quests.errorpage import ErrorPage
from sbs_utils.gui import Gui
from sbs_utils.quests.questrunner import PollResults
from sbs_utils.quests.questrunner import QuestAsync
from sbs_utils.quests.questrunner import QuestRunner
from sbs_utils.quests.questrunner import QuestRuntimeNode
from sbs_utils.quests.quest import Quest
from sbs_utils.spaceobject import SpaceObject
class CommsRunner(QuestRuntimeNode):
    """class CommsRunner"""
    def comms_message (self, sim, message, an_id, event):
        ...
    def comms_selected (self, sim, an_id, event):
        ...
    def enter (self, quest: sbs_utils.quests.quest.Quest, thread: sbs_utils.quests.questrunner.QuestAsync, node: sbs_utils.quests.sbsquest.Comms):
        ...
    def leave (self, quest: sbs_utils.quests.quest.Quest, thread: sbs_utils.quests.questrunner.QuestAsync, node: sbs_utils.quests.sbsquest.Comms):
        ...
    def poll (self, quest: sbs_utils.quests.quest.Quest, thread: sbs_utils.quests.questrunner.QuestAsync, node: sbs_utils.quests.sbsquest.Comms):
        ...
    def set_buttons (self, from_id, to_id):
        ...
class NearRunner(QuestRuntimeNode):
    """class NearRunner"""
    def enter (self, quest: sbs_utils.quests.quest.Quest, thread: sbs_utils.quests.questrunner.QuestAsync, node: sbs_utils.quests.sbsquest.Near):
        ...
    def poll (self, quest: sbs_utils.quests.quest.Quest, thread: sbs_utils.quests.questrunner.QuestAsync, node: sbs_utils.quests.sbsquest.Near):
        ...
class SbsQuestRunner(QuestRunner):
    """class SbsQuestRunner"""
    def __init__ (self, quest: sbs_utils.quests.quest.Quest, overrides=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def run (self, sim, label='main', inputs=None):
        ...
    def runtime_error (self, message):
        ...
    def tick (self, sim):
        ...
class TargetRunner(QuestRuntimeNode):
    """class TargetRunner"""
    def enter (self, quest: sbs_utils.quests.quest.Quest, thread: sbs_utils.quests.questrunner.QuestAsync, node: sbs_utils.quests.sbsquest.Target):
        ...
    def poll (self, quest, thread, node: sbs_utils.quests.sbsquest.Target):
        ...
class TellRunner(QuestRuntimeNode):
    """class TellRunner"""
    def enter (self, quest: sbs_utils.quests.quest.Quest, thread: sbs_utils.quests.questrunner.QuestAsync, node: sbs_utils.quests.sbsquest.Tell):
        ...
    def poll (self, quest: sbs_utils.quests.quest.Quest, thread: sbs_utils.quests.questrunner.QuestAsync, node: sbs_utils.quests.sbsquest.Tell):
        ...
