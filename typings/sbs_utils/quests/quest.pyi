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
class Assign(QuestNode):
    """class Assign"""
    def __init__ (self, lhs, exp):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def gen (self):
        ...
    def validate (self, quest):
        ...
class Await(QuestNode):
    """waits for an existing or a new 'thread' to run in parallel
    this needs to be a rule before Parallel"""
    def __init__ (self, name=None, spawn=None, label=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def add_child (self, cmd):
        ...
    def gen (self):
        ...
    def validate (self, quest):
        ...
class Cancel(QuestNode):
    """Cancels a new 'thread' to run in parallel"""
    def __init__ (self, lhs=None, name=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def gen (self):
        ...
    def validate (self, quest):
        ...
class Comment(QuestNode):
    """class Comment"""
    def __init__ (self):
        """Initialize self.  See help(type(self)) for accurate signature."""
class Delay(QuestNode):
    """class Delay"""
    def __init__ (self, seconds=None, minutes=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def gen (self):
        ...
    def validate (self, _):
        ...
class End(QuestNode):
    """class End"""
    def gen (self):
        ...
    def validate (self, _):
        ...
class Input(QuestNode):
    """class Input"""
    def __init__ (self, name):
        """Initialize self.  See help(type(self)) for accurate signature."""
class Jump(QuestNode):
    """class Jump"""
    def __init__ (self, label):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def gen (self):
        ...
    def validate (self, quest):
        ...
class Label(QuestNode):
    """class Label"""
    def __init__ (self, name):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def add_child (self, cmd):
        ...
class Parallel(QuestNode):
    """Creates a new 'thread' to run in parallel"""
    def __init__ (self, name=None, label=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def add_child (self, cmd):
        ...
    def gen (self):
        ...
    def validate (self, quest):
        ...
class Quest(object):
    """class Quest"""
    def __init__ (self, cmds=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def build (self, cmds):
        """Used to build via code not a script file
        should just process level things e.g. Input, Label, Var"""
    def clear (self):
        ...
    def compile (self, lines):
        ...
class QuestData(object):
    """class QuestData"""
    def __init__ (self, dictionary):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def __repr__ (self):
        """Return repr(self)."""
class QuestError(object):
    """class QuestError"""
    def __init__ (self, message, line_no):
        """Initialize self.  See help(type(self)) for accurate signature."""
class QuestNode(object):
    """class QuestNode"""
    def add_child (self, cmd):
        ...
    def gen (self):
        ...
    def validate (self, quest):
        ...
class Rule(object):
    """class Rule"""
    def __init__ (self, re, cls):
        """Initialize self.  See help(type(self)) for accurate signature."""
class Var(QuestNode):
    """class Var"""
    def __init__ (self, name, val):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def gen (self):
        ...
    def validate (self, quest):
        ...
