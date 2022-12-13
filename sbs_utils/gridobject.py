from __future__ import annotations
import sbs
import functools
from .engineobject import EngineObject, SpawnData, CloseData, Stuff


class GridObject(EngineObject):
    roles : Stuff = Stuff()
    _has_inventory : Stuff = Stuff()
    has_links : Stuff = Stuff()
    all = {}
    removing = set()

    def __init__(self):
        super().__init__()
        self._name = ""
        self._side = ""

    def find_close_list(self, sim, roles=None, max_dist=None, filter_func=None) -> list[CloseData]:
        """ Finds a list of matching objects
        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param roles: Roles to looks for can also be class name
        :type roles: str or List[str]
        :param max_dist: Max distance to search (faster)
        :type max_dist: float
        :param filter_func: Called to test each object to filter out non matches
        :type filter_func:
        :return: A list of close object
        :rtype: List[GridCloseData]
        """
        ret = []
        test_roles = None
        if roles is not None:
            test_role = set(roles)
        hullMap = sim.get_hull_map(self.host_id)
        if hullMap != None:
            num_units = hullMap.get_grid_object_count()
            for x in range(num_units):
                other = hullMap.get_grid_object_by_index(x)
                other_id = other.unique_ID
                other_go = GridObject.get(other_id)
                # skip this one
                if other_id == self.id:
                    continue
                if test_roles:
                    other_roles = set(other_go.get_roles())
                    intersect = test_roles.intersection(other_roles)
                    # if no overlap of roles - skip
                    if len(intersect)==0:
                        continue

                if filter_func and not filter_func(other_go):
                    continue
                
                test = 0
                if test < max_dist:
                    ret.append(CloseData(other_id, other_go, test))

                ret.append(CloseData(other_id, other_go, test))
                continue

                

            return ret

    def find_closest(self, sim, roles=None, max_dist=None, filter_func=None) -> CloseData:
        """ Finds the closest object matching the criteria

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param roles: Roles to looks for can also be class name
        :type roles: str or List[str] 
        :param max_dist: Max distance to search (faster)
        :type max_dist: float
        :param filter_func: Called to test each object to filter out non matches
        :type filter_func: function that takes ID
        :return: A list of close object
        :rtype: GridCloseData
        """
        close = self.find_close_list(sim, roles, max_dist, filter_func)
        # Maybe not the most efficient
        functools.reduce(lambda a, b: a if a.distance < b.distance else b, close)

    def target_closest(self, sim, roles=None, max_dist=None, filter_func=None):
        """ Find and target the closest object matching the criteria

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
        :rtype: GridCloseData
        """
        close = self.find_closest(sim, roles, max_dist, filter_func)
        if close.id is not None:
            self.target(sim, close.id)
        return close

    def target(self, sim, other_id: int):
        """ Set the item to target

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param other_id: the id of the object to target
        :type other_id: int
        :param shoot: if the object should be shot at
        :type shoot: bool
        """
        this = sim.get_grid_object(self.id)
        other = sim.get_grid_object(other_id)
        if other:
            x = blob.get("pathx", 0)
            y = blob.get("pathy", 0)

            blob = this.data_set
            blob.set("pathx", x, 0)
            blob.set("pathy", y, 0)

    def target_pos(self, sim, x:float, y:float):
        """ Set the item to target

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param other_id: the id of the object to target
        :type other_id: int
        :param shoot: if the object should be shot at
        :type shoot: bool
        """
        go = self.grid_object(sim)
        blob = go.data_set
        blob.set("pathx", x, 0)
        blob.set("pathy", y, 0)
    
    def clear_target(self, sim):
        """ Clear the target

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        """
        go = self.get_grid_object()
        blob = go.data_set
        x= blob.get("curx", x, 0)
        y=blob.get("curx", x, 0)
        self.target_pos(x,y)


    def grid_object(self, sim):
        """ get the simulation's space object for the object

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :return: simulation space object
        :rtype: simulation space object
        """
        hullMap: sbs.hullmap
        hullMap = sim.get_hull_map(self.host_id)
        return  hullMap.get_grid_object_by_id(self.id)

        
    def name(self, sim):
        """ Get the name of the object

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :return: name
        :rtype: str
        """
        go : sbs.grid_object
        go = self.grid_object(sim)
        if go is None:
            return ""
        return go.name

    def update_blob(self, sim:sbs.simulation, speed=None, icon_index=None, icon_scale=None, color=None):
        go = self.grid_object(sim)
        if go is None:
            return

        blob = go.data_set
        # blob.set("curx", x, 0)
        # blob.set("cury", y, 0)
        # blob.set("lastx", x, 0)
        # blob.set("lasty", y, 0)
        # blob.set("percent", 1.0, 0)
        if speed is not None:
            blob.set("move_speed", speed, 0)
        if icon_index is not None:
            blob.set("icon_index", icon_index, 0)
        if icon_scale is not None:
            blob.set("icon_scale", icon_scale, 0)
        if color is not None:
            blob.set("icon_color", color , 0)

      
    
    def spawn(self, sim:sbs.simulation, host_id, name, tag, x, y, icon_index, color,  go_type=None):
        self.host_id = host_id
        hullMap: sbs.hullmap
        hullMap = sim.get_hull_map(self.host_id)
        if go_type is None:
            go_type = self.__class__.__name__
        go : sbs.grid_object
        go   = hullMap.create_grid_object(name, tag, go_type)
        self.id = go.unique_ID
        self.add_role(go_type)
        self.add_role(self.__class__.__name__)

        blob = go.data_set
        blob.set("curx", x, 0)
        blob.set("cury", y, 0)
        blob.set("lastx", x, 0)
        blob.set("lasty", y, 0)
        blob.set("percent", 1.0, 0)
        blob.set("move_speed", 0, 0)
        blob.set("icon_index", icon_index, 0)
        blob.set("icon_scale", 1.0, 0)
        blob.set("icon_color", color , 0)



