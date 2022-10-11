import sbs
import functools


class GridObject:
    pass


class GridSpawnData:
    id: int
    engine_object: any
    blob: any
    py_object: GridObject

    def __init__(self, id, obj, blob, py_obj) -> None:
        self.id = id
        self.engine_object = obj
        self.blob = blob
        self.py_object = py_obj


class GridCloseData:
    id: int
    obj: GridObject
    distance: float

    def __init__(self, other_id, other_obj, distance) -> None:
        self.id = other_id
        self.obj = other_obj
        self.distance = distance


class GridObject:
    ids = {'all': {}}
    debug = True
    removing = set()

    def __init__(self):
        pass

    def destroyed(self):
        self.remove()

    def get_id(self):
        return self.id

    def _add(id, obj):
        GridObject.ids['all'][id] = obj

    def _remove(id):
        return GridObject._remove_every_role(id)

    def _add_role(role, id, obj):
        if role not in GridObject.ids:
            GridObject.ids[role] = {}
        GridObject.ids[role][id] = obj

    def add_role(self, role: str):
        """ Add a role to the space object

        :param role: The role to add e.g. spy, pirate etc.
        :type id: str
        """
        GridObject._add_role(role, self.id, self)

    def _remove_role(role, id):
        if GridObject.ids.get(role) is not None:
            GridObject.ids[role].pop(id, None)

    def remove_role(self, role: str):
        """ Remove a role from the space object

        :param role: The role to add e.g. spy, pirate etc.
        :type id: str
        """

        GridObject._remove_role(role, self.id)

    def has_role(self, role):
        """ check if the object has a role

        :param role: The role to add e.g. spy, pirate etc.
        :type id: str
        :return: If the object has the role
        :rtype: bool
        """

        if role not in GridObject.ids:
            return False

        if isinstance(role, str):
            return GridObject.ids[role].get(self.id) is not None
        try:
            for r in role:
                if GridObject.ids[r].get(self.id) is not None:
                    return True
        except:
            return False
        return False

    def _remove_every_role(id):
        for role, _ in GridObject.ids:
            GridObject.remove_role(role, id)

    def get_roles(self):
        roles = []
        for role in GridObject.ids:
            if self.has_role(role):
                roles.append(role)
        return roles

    def get(id):
        o = GridObject.ids['all'].get(id)
        if o is None:
            return None
        return o

    def get_as(id, cls):
        o = GridObject.ids['all'].get(id)
        if o is None:
            return None
        if o.__class__ != cls:
            return None
        return o

    def py_class():
        return __class__

    def add(self):
        """ Add the object to the system, called by spawn normally
        """
        GridObject._add(self.id, self)

    def remove(self):
        """ remove the object to the system, called by destroyed normally
        """
        GridObject._remove(self.id)

    def find_close_list(self, sim, roles=None, max_dist=None, filter_func=None) -> list[GridCloseData]:
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
                    ret.append(GridCloseData(other_id, other_go, test))

                ret.append(GridCloseData(other_id, other_go, test))
                continue

                

            return ret

    def find_closest(self, sim, roles=None, max_dist=None, filter_func=None) -> GridCloseData:
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



