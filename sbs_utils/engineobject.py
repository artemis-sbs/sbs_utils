from __future__ import annotations

class Stuff:
    """ A Common class for Role, Links and Inventory"""
    def __init__(self):
        self.clear()

    def clear(self):
        self.collections = {}

    def add_to_collection(self, collection, id):
        if collection not in self.collections:
            self.collections[collection] = set()
        self.collections[collection].add(id)

    def remove_from_collection(self, collection, id):
        the_set = self.collections.get(collection) 
        if the_set is not None:
            the_set.remove(id)
            return the_set
        return set()

    def collection_has(self,  collection, id):
        """ check if the object has a role
        :param role: The role to add e.g. spy, pirate etc.
        :type id: str
        :return: If the object has the role
        :rtype: bool
        """
        if collection not in self.collections:
            return False

        if isinstance(collection, str):
            return id in self.collections[collection]
        try:
            for r in collection:
                if id in self.collections[r]:
                    return True
        except:
            return False
        return False

    def remove_every_collection(self, id):
        for role in self.collections:
            self.remove_from_collection(role, id)

    def get_collections_in(self, id):
        roles = []
        for role in self.collections:
            if self.collection_has(id, role):
                roles.append(role)
        return roles
    def collection_set(self, collection):
        return self.collections.get(collection, set())

    def collection_list(self, collection):
        return list(self.collection_set(collection))






class SpawnData:
    id: int
    engine_object: any
    blob: any
    py_object: EngineObject

    def __init__(self, id, obj, blob, py_obj) -> None:
        self.id = id
        self.engine_object = obj
        self.blob = blob
        self.py_object = py_obj


class CloseData:
    id: int
    py_object: EngineObject
    distance: float

    def __init__(self, other_id, other_obj, distance) -> None:
        self.id = other_id
        self.py_object = other_obj
        self.distance = distance


class EngineObject():
    roles : Stuff = Stuff()
    _has_inventory : Stuff = Stuff()
    has_links : Stuff = Stuff()
    all = {}
    removing = set()

    def __init__(self):
        super().__init__()
        self.links = Stuff()
        self.inventory = Stuff()
    

    @classmethod
    def clear(cls):
        cls.all = {}
        cls.roles = Stuff()
        cls._has_inventory = Stuff()
        cls.has_links = Stuff()

    def destroyed(self):
        self.remove()

    def get_id(self):
        return self.id

    @classmethod
    def _add(cls, id, obj):
        cls.all[id] = obj

    @classmethod
    def _remove(cls, id):
        cls.all.pop(id)
        return cls.roles.remove_every_collection(id)

    ########## ROLES ########################
    def add_role(self, role: str):
        """ Add a role to the space object

        :param role: The role to add e.g. spy, pirate etc.
        :type id: str
        """
        self.roles.add_to_collection(role, self.id)

    def remove_role(self, role: str):
        """ Remove a role from the space object

        :param role: The role to add e.g. spy, pirate etc.
        :type id: str
        """
        self.roles.remove_from_collection(role, self.id)

    def has_role(self, role):
        """ check if the object has a role

        :param role: The role to add e.g. spy, pirate etc.
        :type id: str
        :return: If the object has the role
        :rtype: bool
        """
        return self.roles.collection_has(role, self.id)

    def get_roles(self, id):
        return self.roles.get_collections_in(id)

    @classmethod
    def get_objects_with_role(cls,role):
        id_set = cls.roles.collection_set(role)
        return [cls.get(x) for x in id_set]

    @classmethod
    def get_role_set(cls, role):
        return  cls.roles.collection_set(role)
    ############### LINKS ############
    def add_link(self, link_name: str, other: EngineObject | CloseData | int):
        """ Add a link to the space object. Links are uni-directional

        :param role: The role/link name to add e.g. spy, pirate etc.
        :type id: str
        """
        id = self.resolve_id(other)
        self.links.add_to_collection(link_name,id)
        self.has_links.add_to_collection(link_name, self.id)

    def remove_link(self, link_name: str, other: EngineObject | CloseData | int):
        """ Remove a role from the space object

        :param role: The role to add e.g. spy, pirate etc.
        :type id: str
        """
        id = EngineObject.resolve_id(other)
        the_set = self.links.remove_from_collection(link_name,id)
        if len(the_set)<1:
            self.has_links.remove_from_collection(self.id)

    def has_link_to(self, link_name: str | list[str], other: EngineObject | CloseData | int):
        """ check if the object has a role

        :param role: The role to add e.g. spy, pirate etc.
        :type id: str
        :return: If the object has the role
        :rtype: bool
        """
        id = self.resolve_id(other)
        return self.links.collection_has(link_name,id)

    def _remove_every_link(self, other: EngineObject | CloseData | int):
        id = self.resolve_id(other)
        for role in self.links:
            self._remove_link(role, id)

    def get_in_links(self, other: EngineObject | CloseData | int):
        id = self.resolve_id(other)
        return self.inventory.get_collections_in(id)
        
    def get_objects_with_link(self, link_name):
        the_set =  self.links.collection_set(link_name)
        if the_set:
            # return a list so you can remove while iterating
            return [self.get(x) for x in the_set]
        return []

    def get_link_set(self, link_name):
        return self.links.collection_set(link_name)

    def get_link_list(self, link_name):
        return self.links.collection_list(link_name)

    @classmethod
    def has_links_set(cls, collection_name):
        return cls.has_links.collection_set(collection_name)

    @classmethod
    def has_links_list(cls,collection_name):
        return cls.has_links.collection_list(collection_name)
    ####################################
    @classmethod
    def resolve_id(cls, other: EngineObject | CloseData | int):
        id = other
        if isinstance(other, EngineObject):
            id = other.id
        elif isinstance(other, CloseData):
            id = other.id
        elif isinstance(other, SpawnData):
            id = other.id
        return id

    @classmethod
    def resolve_py_object(cls, other: EngineObject | CloseData | int):
        py_object = other
        if isinstance(other, EngineObject):
            py_object = other
        elif isinstance(other, CloseData):
            py_object = other.py_object
        elif isinstance(other, SpawnData):
            py_object = other.py_object
        else:
            py_object = cls.get(other)
        return py_object

    @classmethod
    def get_objects_from_set(cls,the_set):
        return [cls.get(x) for x in the_set]
    ####################################

    ############### INVENTORY (Links to data) ############
    def add_inventory(self, collection_name: str, data: object):
        """ Add a link to the space object. Links are uni-directional

        :param role: The role/link name to add e.g. spy, pirate etc.
        :type id: str
        """
        self.inventory.add_to_collection(collection_name,data)
        self._has_inventory.add_to_collection(collection_name, self.id)

    def remove_inventory(self, collection_name: str, data: object):
        """ Remove a role from the space object

        :param role: The role to add e.g. spy, pirate etc.
        :type id: str
        """
        the_set = self.inventory.remove_from_collection(collection_name,data)
        if len(the_set)<1:
            self._has_inventory.remove_from_collection(collection_name, self.id)

    def has_any_inventory(self, collection_name: str | list[str]):
        return self._has_inventory.collection_has(collection_name,self.id)

    def has_in_inventory(self, link_name: str | list[str], data: object):
        """ check if the object has a role

        :param role: The role to add e.g. spy, pirate etc.
        :type id: str
        :return: If the object has the role
        :rtype: bool
        """
        return self.inventory.collection_has(link_name,data)

    def _remove_every_inventory(self, data: object):
        self.inventory.remove_every_collection(data)

    def get_inventory_in(self, data: object):
        return self.inventory.get_collections_in(data)
        
    def get_objects_in_inventory(self, collection_name):
        the_set =  self.inventory.collection_set(collection_name)
        if the_set:
            # return a list so you can remove while iterating
            return [self.get(x) for x in the_set]
        return []

    def get_inventory_set(self, collection_name):
        return self.links.collection_set(collection_name)
    def get_inventory_list(self, collection_name):
        return self.links.collection_list(collection_name)

    @classmethod
    def has_inventory_set(cls, collection_name):
        return cls._has_inventory.collection_set(collection_name)

    @classmethod
    def has_inventory_list(cls, collection_name):
        return cls._has_inventory.collection_list(collection_name)
    ###########################################################

    @classmethod
    def get(cls, id):
        o = cls.all.get(id)
        if o is None:
            return None
        return o

    @classmethod
    def get_as(cls, id, as_cls):
        o = cls.all.get(id)
        if o is None:
            return None
        if o.__class__ != as_cls:
            return None
        return o

    def py_class():
        return __class__

    def add(self):
        """ Add the object to the system, called by spawn normally
        """
        self._add(self.id, self)

    def remove(self):
        """ remove the object to the system, called by destroyed normally
        """
        self._remove(self.id)

    def update_engine_data(self, sim, data):
        this = sim.get_space_object(self.id)
        if this is None:
            # Object is destroyed
            return
        blob = this.data_set
        for (key, value) in data.items():
            if type(value) is tuple:
                blob.set(key, value[0], value[1])
            else:
                blob.set(key, value)

    def get_engine_data(self, sim, key, index=0):
        this = sim.get_space_object(self.id)
        if this is None:
            # Object is destroyed
            return
        blob = this.data_set
        return blob.get(key, index)

    def set_engine_data(self, sim, key, value, index=0):
        this = sim.get_space_object(self.id)
        if this is None:
            # Object is destroyed
            return
        blob = this.data_set
        blob.set(key, value, index)

    def get_engine_data_set(self, sim):
        this = sim.get_space_object(self.id)
        if this is None:
            # Object is destroyed
            return None
        return this.data_set


