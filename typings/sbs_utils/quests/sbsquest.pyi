from sbs_utils.quests.quest import Quest
from sbs_utils.quests.quest import QuestError
from sbs_utils.quests.quest import QuestNode
class Button(QuestNode):
    """class Button"""
    def __init__ (self, button, message, jump, color, if_exp):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def been_here (self, id_tuple):
        ...
    def gen (self):
        ...
    def should_present (self, id_tuple):
        ...
    def validate (self, quest):
        ...
    def visit (self, id_tuple):
        ...
class Comms(QuestNode):
    """class Comms"""
    def __init__ (self, to_tag, from_tag, buttons=None, minutes=None, seconds=None, time_jump='', color='white'):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def add_child (self, obj):
        ...
    def gen (self):
        ...
    def validate (self, quest):
        ...
class Near(QuestNode):
    """class Near"""
    def __init__ (self, to_tag, from_tag, distance, jump, minutes=None, seconds=None, time_jump=''):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def gen (self):
        ...
    def validate (self, quest):
        ...
class SbsQuest(Quest):
    """class SbsQuest"""
class Target(QuestNode):
    """Creates a new 'thread' to run in parallel"""
    def __init__ (self, cmd=None, from_tag=None, to_tag=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def gen (self):
        ...
    def validate (self, quest):
        ...
class Tell(QuestNode):
    """class Tell"""
    def __init__ (self, to_tag, from_tag, message):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def gen (self):
        ...
    def validate (self, quest):
        ...
