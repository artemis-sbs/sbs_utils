from sbs_utils.agent import Agent
from sbs_utils.agent import SpawnData
from sbs_utils.helpers import FrameContext
class GridObject(Agent):
    """class GridObject"""
    def __init__ (self):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _add (id, obj):
        ...
    def _remove (id):
        ...
    def clear ():
        ...
    @property
    def comms_id (self: 'GridObject') -> 'str':
        """str, cached version of comms_id"""
    @comms_id.setter
    def comms_id (self: 'GridObject', comms_id):
        """str, cached version of comms_id"""
    def get (id):
        ...
    def get_as (id, as_cls):
        ...
    def get_engine_object (self):
        """Gets the simulation space object
        
        :return: The simulation space object
        :rtype: The simulation space_object"""
    def get_objects_from_set (the_set):
        ...
    def get_role_object (link_name):
        ...
    def get_role_objects (role):
        ...
    def get_role_set (role):
        ...
    @property
    def go_type (self: 'GridObject') -> 'str':
        """str, cached version of type"""
    def grid_object (self):
        """get the simulation's space object for the object
        
        :return: simulation space object
        :rtype: simulation space object"""
    def has_inventory_list (collection_name):
        ...
    def has_inventory_set (collection_name):
        ...
    def has_links_list (collection_name):
        ...
    def has_links_set (collection_name):
        ...
    @property
    def host (self: 'GridObject') -> 'int':
        """the host id of the grid object"""
    @property
    def is_grid_object (self):
        ...
    @property
    def name (self: 'GridObject') -> 'str':
        """str, cached version of name"""
    @name.setter
    def name (self: 'GridObject', name):
        """str, cached version of name"""
    def remove_id (id):
        ...
    def resolve_id (other: 'Agent | CloseData | int'):
        ...
    def resolve_py_object (other: 'Agent | CloseData | int'):
        ...
    def set_go_type (self, go_type):
        """Set the name of the object
        
        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param name: The object name
        :type str: The object name"""
    def set_name (self, name):
        """Set the name of the object
        
        :param name: The object name
        :type str: The object name"""
    def set_tag (self, tag):
        """Set the name of the object
        
        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param name: The object name
        :type str: The object name"""
    def spawn (self, host_id, name, tag, x, y, icon_index, color, go_type=None):
        ...
    @property
    def tag (self: 'GridObject') -> 'str':
        """str, cached version of tag"""
    def update_blob (self, speed=None, icon_index=None, icon_scale=None, color=None):
        ...
