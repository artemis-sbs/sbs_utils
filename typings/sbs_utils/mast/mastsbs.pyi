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
    def __init__ (self, message=None, button=None, color=None, if_exp=None, for_name=None, for_exp=None, clone=False, q=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def been_here (self, id_tuple):
        ...
    def clone (self):
        ...
    def expand (self):
        ...
    def parse (lines):
        ...
    def should_present (self, id_tuple):
        ...
    def visit (self, id_tuple):
        ...
class Comms(MastNode):
    """class Comms"""
    def __init__ (self, selected_tag=None, origin_tag=None, assign=None, minutes=None, seconds=None, time_pop=None, time_push='', time_jump='', color='white', loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class CommsInfo(MastNode):
    """class CommsInfo"""
    def __init__ (self, message, q=None, color=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class FollowRoute(MastNode):
    """Route unhandled things comms, science, events"""
    def __init__ (self, route, origin_tag, selected_tag, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class MastSbs(Mast):
    """class MastSbs"""
    def _add (id, obj):
        ...
    def _remove (id):
        ...
    def get (id):
        ...
    def get_as (id, as_cls):
        ...
    def get_objects_from_set (the_set):
        ...
    def get_role_object (link_name):
        ...
    def get_role_objects (role):
        ...
    def get_role_set (role):
        ...
    def has_inventory_list (collection_name):
        ...
    def has_inventory_set (collection_name):
        ...
    def has_links_list (collection_name):
        ...
    def has_links_set (collection_name):
        ...
    def resolve_id (other: 'EngineObject | CloseData | int'):
        ...
    def resolve_py_object (other: 'EngineObject | CloseData | int'):
        ...
class Route(MastNode):
    """Route unhandled things comms, science, events"""
    def __init__ (self, route, name, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class Scan(MastNode):
    """class Scan"""
    def __init__ (self, to_tag=None, from_tag=None, fog=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class ScanResult(MastNode):
    """class ScanResult"""
    def __init__ (self, message=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class ScanTab(MastNode):
    """class ScanTab"""
    def __init__ (self, message=None, button=None, if_exp=None, for_name=None, for_exp=None, clone=False, q=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def clone (self):
        ...
    def expand (self):
        ...
    def parse (lines):
        ...
class Simulation(MastNode):
    """Handle commands to the simulation"""
    def __init__ (self, cmd=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class TransmitReceive(MastNode):
    """class TransmitReceive"""
    def __init__ (self, tr, message, origin, selected, face_string=None, face_var=None, faceq=None, comms_string=None, comms_var=None, comq=None, q=None, color=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
