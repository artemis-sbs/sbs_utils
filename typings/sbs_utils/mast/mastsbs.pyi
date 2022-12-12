from sbs_utils.mast.mast import EndAwait
from sbs_utils.mast.mast import Mast
from sbs_utils.mast.mast import MastNode
class Broadcast(MastNode):
    """class Broadcast"""
    def __init__ (self, to_tag, message, color=None, q=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class Button(MastNode):
    """class Button"""
    def __init__ (self, button, message, color, if_exp, q=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def been_here (self, id_tuple):
        ...
    def parse (lines):
        ...
    def should_present (self, id_tuple):
        ...
    def visit (self, id_tuple):
        ...
class ButtonSet(MastNode):
    """class ButtonSet"""
    def __init__ (self, use=None, name=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class Closest(MastNode):
    ...
    def __init__ (self, assign, name, role, max, the_filter, q=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class Comms(MastNode):
    """class Comms"""
    def __init__ (self, to_tag, from_tag, assign=None, minutes=None, seconds=None, time_pop=None, time_push='', time_jump='', color='white', loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class Find(MastNode):
    ...
    def __init__ (self, assign, name, role, max, the_filter, inc_dist, q=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class MastSbs(Mast):
    """class MastSbs"""
class Near(MastNode):
    """class Near"""
    def __init__ (self, to_tag, from_tag, distance, minutes=None, seconds=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class Role(MastNode):
    """Handle commands to the simulation"""
    def __init__ (self, name, roles, cmd=None, q=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class Simulation(MastNode):
    """Handle commands to the simulation"""
    def __init__ (self, cmd=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class Target(MastNode):
    """Creates a new 'task' to run in parallel"""
    def __init__ (self, cmd=None, from_tag=None, to_tag=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class Tell(MastNode):
    """class Tell"""
    def __init__ (self, to_tag, from_tag, message, color=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
