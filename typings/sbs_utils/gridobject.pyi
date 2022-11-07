class GridCloseData(object):
    """class GridCloseData"""
    def __init__ (self, other_id, other_obj, distance) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
class GridObject(object):
    """class GridObject"""
    def __init__ (self):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _add (id, obj):
        ...
    def _add_role (role, id, obj):
        ...
    def _remove (id):
        ...
    def _remove_every_role (id):
        ...
    def _remove_role (role, id):
        ...
    def add (self):
        """Add the object to the system, called by spawn normally
                """
    def add_role (self, role: str):
        """Add a role to the space object
        
        :param role: The role to add e.g. spy, pirate etc.
        :type id: str"""
    def clear_target (self, sim):
        """Clear the target
        
        :param sim: The simulation
        :type sim: Artemis Cosmos simulation"""
    def destroyed (self):
        ...
    def find_close_list (self, sim, roles=None, max_dist=None, filter_func=None) -> list:
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
    def find_closest (self, sim, roles=None, max_dist=None, filter_func=None) -> sbs_utils.gridobject.GridCloseData:
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
    def get_as (id, cls):
        ...
    def get_id (self):
        ...
    def get_roles (self):
        ...
    def grid_object (self, sim):
        """get the simulation's space object for the object
        
        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :return: simulation space object
        :rtype: simulation space object"""
    def has_role (self, role):
        """check if the object has a role
        
        :param role: The role to add e.g. spy, pirate etc.
        :type id: str
        :return: If the object has the role
        :rtype: bool"""
    def name (self, sim):
        """Get the name of the object
        
        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :return: name
        :rtype: str"""
    def py_class ():
        ...
    def remove (self):
        """remove the object to the system, called by destroyed normally
                """
    def remove_role (self, role: str):
        """Remove a role from the space object
        
        :param role: The role to add e.g. spy, pirate etc.
        :type id: str"""
    def spawn (self, sim: sbs.simulation, host_id, name, tag, x, y, icon_index, color, go_type=None):
        ...
    def target (self, sim, other_id: int):
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
    def target_pos (self, sim, x: float, y: float):
        """Set the item to target
        
        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param other_id: the id of the object to target
        :type other_id: int
        :param shoot: if the object should be shot at
        :type shoot: bool"""
    def update_blob (self, sim: sbs.simulation, speed=None, icon_index=None, icon_scale=None, color=None):
        ...
class GridSpawnData(object):
    """class GridSpawnData"""
    def __init__ (self, id, obj, blob, py_obj) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
