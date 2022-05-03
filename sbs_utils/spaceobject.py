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

    def add(id, obj):
        SpaceObject.ids['all'][id] = obj

    def remove(id):
        return SpaceObject.remove_role('all',id)

    def add_role(role, id, obj):
        if role not in SpaceObject.ids:
            SpaceObject.ids[role]={}
        SpaceObject.ids[role][id] = obj

    def remove_role(role, id):
        if role not in SpaceObject.remove:
            SpaceObject.removing[role]={}
        if SpaceObject.ids[role].get(id) is not None:
            SpaceObject.removing[role].add(id) 
        return SpaceObject.ids['all'][id]

    def has_role(role, id):
        if role not in SpaceObject.ids:
            return False

        if isinstance(role, str):
            return SpaceObject.ids[role].get(id) is not None
        try:
            for r in role:
                if SpaceObject.ids[r].get(id) is not None:
                    return True
        except:
            return False
        return False

    def remove_every(id):
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

    def add_id(self):
        SpaceObject.add(self.id, self)

    def remove_id(self):
        SpaceObject.remove(self.id)

    def get_space_object(self, sim):
        return sim.get_space_object(self.id)

    def find_close_list(self, sim, roles=None, max_dist=None, filter_func=None)-> list[CloseData]:
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

    def find_closest(self, sim, roles=None, max_dist=None, filter_func=None):
        close_id = None
        close_obj = None
        dist = max_dist

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
        close = self.find_closest(sim, roles, max_dist, filter_func)
        if close.id is not None:
            self.target(sim, close.id, shoot)

    def target(self, sim, other_id: int, shoot: bool = True):
        this = sim.get_space_object(self.id)
        other = sim.get_space_object(other_id)

        blob = this.data_set
        blob.set("target_pos_x", other.pos.x)
        blob.set("target_pos_y", other.pos.y)
        blob.set("target_pos_z", other.pos.z)
        if shoot:
            blob.set("target_id", other.unique_ID)


    def clear_target(self, sim):
        this = sim.get_space_object(self.id)

        blob = this.data_set
        blob.set("target_pos_x", this.pos.x)
        blob.set("target_pos_y", this.pos.y)
        blob.set("target_pos_z", this.pos.z)
        blob.set("target_id", 0)

    def debug_mark_loc(sim,  x: float, y: float, z: float, name: str, color: str):
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


class MSpawn:
    def spawn_common(self, sim, obj, x,y,z,name, side):
        sim.reposition_space_object(obj, x, y, z)
        self.add_id()
        SpaceObject.add_role(self.__class__.__name__, self.id, self)
        blob = obj.data_set
        if side is not None:
            name = name if name is not None else f"{side} {self.id}"
            blob.set("name_tag", name, 0)
            obj.side = side
        elif name is not None:
            blob.set("name_tag", name, 0)
        
        return blob

class MSpawnPlayer(MSpawn):
    def make_new_player(self, sim, behave, data_id):
        self.id = sim.make_new_player(behave, data_id)
        sbs.assign_player_ship(self.id)
        return sim.get_space_object(self.id)

    def spawn(self, sim, x, y, z, name, side, art_id):
        # playerID will be a NUMBER, a unique value for every space object that you create.
        ship = self.make_new_player(sim, "behav_playership", art_id)
        blob = self.spawn_common(sim, ship, x,y,z,name, side)
        return SpawnData(id, ship, blob)

    def spawn_v(self, sim, v, name, side, art_id):
        return self.spawn(sim, v.x, v.y, v.z, name, side, art_id)

class MSpawnActive(MSpawn):
    """
    Mixin to add Spawn as an Active
    """
    def make_new_active(self, sim,  behave, data_id):
        self.id = sim.make_new_active(behave, data_id)
        return self.get_space_object(sim)

    def spawn(self, sim, x, y, z, name, side, art_id, behave_id):
        ship = self.make_new_active(sim, behave_id, art_id)
        blob = self.spawn_common(sim, ship, x,y,z,name, side)
        return SpawnData(id, ship, blob)

    def spawn_v(self, sim, v, name, side, art_id, behave_id):
        return self.spawn(self, sim, v.x, v.y, v.z, name, side, art_id, behave_id)

class MSpawnPassive(MSpawn):
    """
    Mixin to add Spawn as an Passive
    """
    def make_new_passive(self, sim, behave, data_id):
        self.id = sim.make_new_passive(behave, data_id)
        return sim.get_space_object(self.id)

    def spawn(self, sim, x, y, z, name, side, art_id, behave_id):
        ship = self.make_new_passive(sim, behave_id, art_id)
        blob = self.spawn_common(sim, ship, x,y,z,name, side)
        return SpawnData(id, ship, blob)

    def spawn_v(self, sim, v, name, side, art_id, behave_id):
        return self.spawn(sim, v.x, v.y, v.z, name, side, art_id, behave_id)

