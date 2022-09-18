import sbs


class SpaceObject:
    pass

class SpawnData:
    id : int
    object : any
    blob: any
    def __init__(self, id, obj, blob) -> None:
        self.id = id
        self.object = obj
        self.blob = blob

class CloseData:
    id: int
    obj: SpaceObject
    distance: float

    def __init__(self, other_id, other_obj, distance) -> None:
        self.id = other_id
        self.obj = other_obj
        self.distance = distance

class SpaceObject:
    ids = {'all':{}}
    debug = True
    def __init__(self):
        pass

    def destroyed(self):
        self.remove()

    def get_id(self):
        return self.id


    def _add(id, obj):
        SpaceObject.ids['all'][id] = obj

    def _remove(id):
        return SpaceObject._remove_every_role(id)

    def _add_role(role, id, obj):
        if role not in SpaceObject.ids:
            SpaceObject.ids[role]={}
        SpaceObject.ids[role][id] = obj

    def add_role(self, role: str):
        """ Add a role to the space object

        :param role: The role to add e.g. spy, pirate etc.
        :type id: str
        """
        SpaceObject._add_role(role, self.id, self)

    def _remove_role(role, id):
        if role not in SpaceObject.remove:
            SpaceObject.removing[role]={}
        if SpaceObject.ids[role].get(id) is not None:
            SpaceObject.removing[role].append(id) 
        return SpaceObject.ids['all'][id]

    def remove_role(self, role: str):
        """ Remove a role from the space object

        :param role: The role to add e.g. spy, pirate etc.
        :type id: str
        """

        SpaceObject._remove_role(role, self.id)

    def has_role(self, role):
        """ check if the object has a role

        :param role: The role to add e.g. spy, pirate etc.
        :type id: str
        :return: If the object has the role
        :rtype: bool
        """

        if role not in SpaceObject.ids:
            return False

        if isinstance(role, str):
            return SpaceObject.ids[role].get(self.id) is not None
        try:
            for r in role:
                if SpaceObject.ids[r].get(self.id) is not None:
                    return True
        except:
            return False
        return False


    def _remove_every_role(id):
        for role, _ in SpaceObject.ids:
            SpaceObject.remove_role(role, id)


    def get(id):
        o = SpaceObject.ids['all'].get(id)
        if o is None:
            return None
        return o

    def get_as(id, cls):
        o = SpaceObject.ids['all'].get(id)
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
        SpaceObject._add(self.id, self)

    def remove(self):
        """ remove the object to the system, called by destroyed normally
        """
        SpaceObject._remove(self.id)

    def get_space_object(self, sim):
        """ Gets the simulation space object

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :return: The simulation space object
        :rtype: The simulation space_object
        """

        return sim.get_space_object(self.id)

    def find_close_list(self, sim, roles=None, max_dist=None, filter_func=None)-> list[CloseData]:
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
        :rtype: List[CloseData]
        """
        ret = []
        test = max_dist
        ids = SpaceObject.ids.get(roles)
        if ids is None:
            ids = SpaceObject.ids['all']
        else:
            # non need to check role later
            roles = None

        items = ids.items()
        if filter_func is not None:
            items = filter(filter_func, items)

        for (other_id, other_obj) in items:
            # if this is self skip
            if other_id == self.id:
                continue

            if roles is not None and not other_obj.has_role(roles):
                continue

            if max_dist is None:
                ret.append(CloseData(other_id, other_obj, test))
                continue

            # test distance
            test = sbs.distance_id(self.id, other_id)
            if test < max_dist:
                ret.append(CloseData(other_id, other_obj, test))

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
        :rtype: CloseData
        """
        close_id = None
        close_obj = None
        dist = max_dist

        ###### TODO USe boardtest if max_dist used

        ids = SpaceObject.ids.get(roles)
        if ids is None:
            ids = SpaceObject.ids['all']
        else:
            # non need to check role later
            print(f"count {len(ids)}")
            roles = None

            
        items = ids.items()
        if filter_func is not None:
            items = filter(filter_func, items)

        for (other_id, other_obj) in items:
            # if this is self skip
            if other_id == self.id:
                continue
            if roles is not None and not other_obj.has_role(roles):
                continue

            test = sbs.distance_id(self.id, other_id)
            if dist is None:
                close_id = other_id
                close_obj = other_obj
                dist = test
            elif test < dist:
                close_id = other_id
                close_obj = other_obj
                dist = test

        return CloseData(close_id, close_obj, dist)

    def target_closest(self, sim, roles=None, max_dist=None, filter_func=None, shoot: bool = True):
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
        :rtype: CloseData
        """
        close = self.find_closest(sim, roles, max_dist, filter_func)
        if close.id is not None:
            self.target(sim, close.id, shoot)

    def target(self, sim, other_id: int, shoot: bool = True):
        """ Set the item to target

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param other_id: the id of the object to target
        :type other_id: int
        :param shoot: if the object should be shot at
        :type shoot: bool
        """
        this = sim.get_space_object(self.id)
        other = sim.get_space_object(other_id)

        blob = this.data_set
        blob.set("target_pos_x", other.pos.x)
        blob.set("target_pos_y", other.pos.y)
        blob.set("target_pos_z", other.pos.z)
        if shoot:
            blob.set("target_id", other.unique_ID)
        else:
            blob.set("target_id", 0)


    def clear_target(self, sim):
        """ Clear the target

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        """
        this = sim.get_space_object(self.id)

        blob = this.data_set
        blob.set("target_pos_x", this.pos.x)
        blob.set("target_pos_y", this.pos.y)
        blob.set("target_pos_z", this.pos.z)
        blob.set("target_id", 0)

    def debug_mark_loc(sim,  x: float, y: float, z: float, name: str, color: str):
        """ Adds a nav point to the location passed if debug mode is on

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param x: x location
        :type x: float
        :param y: y location
        :type y: float
        :param z: z location
        :type z: float
        :param name: name of the navpoint
        :type name: str
        :param color: color of the navpoint
        :type color: str
        """
        if SpaceObject.debug:
            return sim.add_navpoint(x, y, z, name, color)
        return None

    def debug_remove_mark_loc(sim, name: str):
        if SpaceObject.debug:
            return sim.delete_navpoint_by_name(name)
        return None

    def log(s: str):
        if SpaceObject.debug:
            print(s)

    def space_object(self, sim):
        """ get the simulation's space object for the object

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :return: simulation space object
        :rtype: simulation space object
        """
        return sim.get_space_object(self.id)

    def side(self, sim):
        """ Get the side of the object

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :return: side
        :rtype: str
        """
        so = self.space_object(sim)
        if so is not None:
            return so.side
        return ""
        
    def name(self, sim):
        """ Get the name of the object

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :return: name
        :rtype: str
        """
        so = self.space_object(sim)
        if so is None:
            return ""
        blob = so.data_set
        return blob.get("name_tag", 0)

    def comm_id(self, sim):
        """ Get the text to use in the comms messages

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :return: this is name or name(side)
        :rtype: str
        """
        name = self.name(sim)
        side = self.side(sim)
        if (side != ""):
            return f"{name}({side})"
        return name



class MSpawn:
    def spawn_common(self, sim, obj, x,y,z,name, side):
        sim.reposition_space_object(obj, x, y, z)
        self.add()
        self.add_role(self.__class__.__name__)
        blob = obj.data_set
        if side is not None:
            name = name if name is not None else f"{side} {self.id}"
            blob.set("name_tag", name, 0)
            obj.side = side
            self.add_role(self.side)
        elif name is not None:
            blob.set("name_tag", name, 0)
        
        return blob

class MSpawnPlayer(MSpawn):
    def _make_new_player(self, sim, behave, data_id):
        self.id = sim.make_new_player(behave, data_id)
        sbs.assign_player_ship(self.id)
        return sim.get_space_object(self.id)

    def _spawn(self, sim, x, y, z, name, side, art_id):
        # playerID will be a NUMBER, a unique value for every space object that you create.
        ship = self._make_new_player(sim, "behav_playership", art_id)
        blob = self.spawn_common(sim, ship, x,y,z,name, side)
        return SpawnData(id, ship, blob)


    def spawn(self, sim, x, y, z, name, side, art_id):
        """ Spawn a new player

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param x: x location
        :type x: float
        :param y: y location
        :type y: float
        :param z: z location
        :type z: float
        :param name: name of object
        :type name: str
        :param side: name of object
        :type side: str
        :param art_id: art id
        :type art_id: str
        :param behave_id: the simulation behavior
        :type behave_id: str
        :return: spawn data
        :rtype: SpawnData
        """
        return self._spawn(sim, x, y, z, name, side, art_id)

    def spawn_v(self, sim, v, name, side, art_id):
        """ Spawn a new player

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param v: location
        :type v: Vec3
        :param name: name of object
        :type name: str
        :param side: name of object
        :type side: str
        :param art_id: art id
        :type art_id: str
        
        :return: spawn data
        :rtype: SpawnData
        """
        return self.spawn(sim, v.x, v.y, v.z, name, side, art_id)

class MSpawnActive(MSpawn):
    """
    Mixin to add Spawn as an Active
    """
    def _make_new_active(self, sim,  behave, data_id):
        self.id = sim.make_new_active(behave, data_id)
        return self.get_space_object(sim)

    def _spawn(self, sim, x, y, z, name, side, art_id, behave_id):
        ship = self._make_new_active(sim, behave_id, art_id)
        blob = self.spawn_common(sim, ship, x,y,z,name, side)
        return SpawnData(id, ship, blob)

    def spawn(self, sim, x, y, z, name, side, art_id, behave_id):
        """ Spawn a new active object e.g. npc, station

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param x: x location
        :type x: float
        :param y: y location
        :type y: float
        :param z: z location
        :type z: float
        :param name: name of object
        :type name: str
        :param side: name of object
        :type side: str
        :param art_id: art id
        :type art_id: str
        :param behave_id: the simulation behavior
        :type behave_id: str

        :return: spawn data
        :rtype: SpawnData
        """
        return self._spawn(sim, x, y, z, name, side, art_id, behave_id)

    def spawn_v(self, sim, v, name, side, art_id, behave_id):
        """ Spawn a new Active Object e.g. npc, station

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param v: location
        :type v: Vec3
        :param name: name of object
        :type name: str
        :param side: name of object
        :type side: str
        :param art_id: art id
        :type art_id: str
        :param behave_id: the simulation behavior
        :type behave_id: str

        :return: spawn data
        :rtype: SpawnData
        """
        return self.spawn(sim, v.x, v.y, v.z, name, side, art_id, behave_id)

class MSpawnPassive(MSpawn):
    """
    Mixin to add Spawn as an Passive
    """
    def _make_new_passive(self, sim, behave, data_id):
        self.id = sim.make_new_passive(behave, data_id)
        return sim.get_space_object(self.id)

    def _spawn(self, sim, x, y, z, name, side, art_id, behave_id):
        ship = self._make_new_passive(sim, behave_id, art_id)
        blob = self.spawn_common(sim, ship, x,y,z,name, side)
        return SpawnData(id, ship, blob)

    def spawn(self, sim, x, y, z, name, side, art_id, behave_id):
        """ Spawn a new passive object e.g. Asteroid, etc.

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param x: x location
        :type x: float
        :param y: y location
        :type y: float
        :param z: z location
        :type z: float
        :param name: name of object
        :type name: str
        :param side: name of object
        :type side: str
        :param art_id: art id
        :type art_id: str
        :param behave_id: the simulation behavior
        :type behave_id: str

        :return: spawn data
        :rtype: SpawnData
        """
        return self._spawn(sim, x, y, z, name, side, art_id, behave_id)

    def spawn_v(self, sim, v, name, side, art_id, behave_id):
        """ Spawn a new passive object e.g. asteroid, etc.

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param v: location
        :type v: Vec3
        :param name: name of object
        :type name: str
        :param side: name of object
        :type side: str
        :param art_id: art id
        :type art_id: str
        :param behave_id: the simulation behavior
        :type behave_id: str
        :return: spawn data
        :rtype: SpawnData
        """
        return self.spawn(sim, v.x, v.y, v.z, name, side, art_id, behave_id)

