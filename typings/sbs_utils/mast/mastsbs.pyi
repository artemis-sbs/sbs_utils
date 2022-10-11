from sbs_utils.mast.mast import Mast
from sbs_utils.mast.mast import MastCompilerError
from sbs_utils.mast.mast import MastNode
class Button(MastNode):
    """class Button"""
    def __init__ (self, button, message, pop, push, jump, color, await_name, with_data, py, if_exp):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def been_here (self, id_tuple):
        ...
    def gen (self):
        ...
    def should_present (self, id_tuple):
        ...
    def validate (self, mast):
        ...
    def visit (self, id_tuple):
        ...
class Comms(MastNode):
    """class Comms"""
    def __init__ (self, to_tag, from_tag, buttons=None, minutes=None, seconds=None, time_pop=None, time_push='', time_jump='', color='white'):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def add_child (self, obj):
        ...
    def gen (self):
        ...
    def validate (self, mast):
        ...
class MastSbs(Mast):
    """class MastSbs"""
class Near(MastNode):
    """class Near"""
    def __init__ (self, to_tag, from_tag, distance, pop='', push='', jump='', minutes=None, seconds=None, time_pop='', time_push='', time_jump=''):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def gen (self):
        ...
    def validate (self, mast):
        ...
class Simulation(MastNode):
    """Handle commands to the simulation"""
    def __init__ (self, cmd=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
class Target(MastNode):
    """Creates a new 'thread' to run in parallel"""
    def __init__ (self, cmd=None, from_tag=None, to_tag=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def gen (self):
        ...
    def validate (self, mast):
        ...
class Tell(MastNode):
    """class Tell"""
    def __init__ (self, to_tag, from_tag, message):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def gen (self):
        ...
    def validate (self, mast):
        ...
