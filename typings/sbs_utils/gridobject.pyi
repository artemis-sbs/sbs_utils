from sbs_utils.engineobject import CloseData
from sbs_utils.engineobject import EngineObject
from sbs_utils.engineobject import SpawnData
from sbs_utils.engineobject import Stuff
class GridObject(EngineObject):
    """class GridObject"""
    def __init__ (self):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _add (id, obj):
        ...
    def _remove (id):
        ...
    def clear ():
        ...
    def clear_target (self, sim):
        """Clear the target
        
        :param sim: The simulation
        :type sim: Artemis Cosmos simulation"""
    @property
    def comms_id (self: 'GridObject') -> 'str':
        """str, cached version of comms_id"""
    def find_close_list (self, sim, roles=None, max_dist=None, filter_func=None) -> 'list[CloseData]':
        """Finds a list of matching objects
        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param roles: Roles to looks for can also be class name
        :type roles: str or List[str]
        :param max_dist: Max distance to search (faster)
        :type max_dist: float
        :param filter_func: Called to test each object to filter out non matches
        :type filter_func:
        :return: A list of close object
        :rtype: List[GridCloseData]"""
    def find_closest (self, sim, roles=None, max_dist=None, filter_func=None) -> 'CloseData':
        """Finds the closest object matching the criteria
        
        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param roles: Roles to looks for can also be class name
        :type roles: str or List[str]
        :param max_dist: Max distance to search (faster)
        :type max_dist: float
        :param filter_func: Called to test each object to filter out non matches
        :type filter_func: function that takes ID
        :return: A list of close object
        :rtype: GridCloseData"""
    def get (id):
        ...
    def get_as (id, as_cls):
        ...
    def get_engine_data (self, sim, key, index=0):
        ...
    def get_engine_data_set (self, sim):
        ...
    def get_objects_from_set (the_set):
        ...
    def get_role_object (link_name):
        ...
    def get_role_objects (role):
        ...
    def get_role_set (role):
        ...
    @property
    def gotype (self: 'GridObject') -> 'str':
        """str, cached version of type"""
    def grid_object (self, sim):
        """get the simulation's space object for the object
        
        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
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
    def name (self: 'GridObject') -> 'str':
        """str, cached version of name"""
    def resolve_id (other: 'EngineObject | CloseData | int'):
        ...
    def resolve_py_object (other: 'EngineObject | CloseData | int'):
        ...
    def set_engine_data (self, sim, key, value, index=0):
        ...
    def set_name (self, sim, name):
        """Set the name of the object
        
        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param name: The object name
        :type str: The object name"""
    def set_tag (self, sim, tag):
        """Set the name of the object
        
        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param name: The object name
        :type str: The object name"""
    def spawn (self, sim: 'sbs.simulation', host_id, name, tag, x, y, icon_index, color, go_type=None):
        ...
    @property
    def tag (self: 'GridObject') -> 'str':
        """str, cached version of tag"""
    def target (self, sim, other_id: 'int'):
        """Set the item to target
        
        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param other_id: the id of the object to target
        :type other_id: int
        :param shoot: if the object should be shot at
        :type shoot: bool"""
    def target_closest (self, sim, roles=None, max_dist=None, filter_func=None):
        """Find and target the closest object matching the criteria
        
        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param roles: Roles to looks for can also be class name
        :type roles: str or List[str]
        :param max_dist: Max distance to search (faster)
        :type max_dist: float
        :param filter_func: Called to test each object to filter out non matches
        :type filter_func: function
        :param shoot: if the target should be shot at
        :type shoot: bool
        :return: A list of close object
        :rtype: GridCloseData"""
    def target_pos (self, sim, x: 'float', y: 'float'):
        """Set the item to target
        
        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param other_id: the id of the object to target
        :type other_id: int
        :param shoot: if the object should be shot at
        :type shoot: bool"""
    def update_blob (self, sim: 'sbs.simulation', speed=None, icon_index=None, icon_scale=None, color=None):
        ...
    def update_engine_data (self, sim, data):
        ...
