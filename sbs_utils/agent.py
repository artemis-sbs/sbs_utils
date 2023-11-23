from __future__ import annotations

task_ids = 0x0080000000000000
def get_task_id():
    global task_ids
    task_ids += 1
    return task_ids
    
story_ids = 0x0040000000000000
def get_story_id():
    global story_ids
    story_ids += 1
    return story_ids


class Stuff:
    """ A Common class for Role, Links and Inventory"""
    def __init__(self):
        self.clear()

    def clear(self):
        self.collections = {}

    def remove_collection(self, collection):
        self.collections.pop(collection, None)

    def dedicated_collection(self, collection, id):
        if id is None:
            self.remove_collection(collection)
            return
        self.collections[collection] = set()
        self.collections[collection].add(id)


    def add_to_collection(self, collection, id):
        collections = collection.split(",")
        for collection in collections:
            if collection not in self.collections:
                self.collections[collection] = set()
            self.collections[collection].add(id)

    def remove_from_collection(self, collection, id):
        collections = collection.split(",")
        for collection in collections:
            the_set = self.collections.get(collection) 
            if the_set is not None:
                the_set.discard(id)

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
            return id in self.collection_set(collection)
        try:
            for r in collection:
                if id in self.collection_set(r):
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
            if self.collection_has(role, id):
                roles.append(role)
        return roles
    # def collection_set(self, collection):
    #     return self.collections.get(collection, set())
    def collection_set(self, collection):
        the_set = self.collections.get(collection)
        if the_set and not isinstance(the_set,set):
            return {the_set}
        elif the_set is None:
            return set()
        return the_set

    def collection_list(self, collection):
        return list(self.collection_set(collection))






class SpawnData:
    id: int
    engine_object: any
    blob: any
    py_object: Agent

    def __init__(self, id, obj, blob, py_obj) -> None:
        self.id = id
        self.engine_object = obj
        self.blob = blob
        self.py_object = py_obj


class CloseData:
    id: int
    py_object: Agent
    distance: float

    def __init__(self, other_id, other_obj, distance) -> None:
        self.id = other_id
        self.py_object = other_obj
        self.distance = distance


class Agent():
    roles : Stuff = Stuff()
    _has_inventory : Stuff = Stuff()
    has_links : Stuff = Stuff()
    all = {}
    removing = set()
    SHARED = None


    def __init__(self):
        super().__init__()
        self.links = Stuff()
        self.inventory = Stuff()

    @property
    def is_player(self):
        return False

    @property
    def is_npc(self):
        return False

    @property
    def is_terrain(self):
        return False

    @property
    def is_active(self):
        return False

    @property
    def is_passive(self):
        return False
    
    @property
    def is_grid_object(self):
        return False



    @classmethod
    def clear(cls):
        Agent.all = {}
        Agent.roles = Stuff()
        Agent._has_inventory = Stuff()
        Agent.has_links = Stuff()

    def destroyed(self):
        self.remove()

    def get_id(self):
        return self.id

    @classmethod
    def _add(cls, id, obj):
        Agent.all[id] = obj

    @classmethod
    def _remove(cls, id):
        Agent.all.pop(id, None) #Allow remove if not added
        return Agent.roles.remove_every_collection(id)

    ########## ROLES ########################
    def add_role(self, role: str):
        """ Add a role to the space object

        :param role: The role to add e.g. spy, pirate etc.
        :type id: str
        """
        role = role.strip().lower()
        self.roles.add_to_collection(role, self.id)

    def remove_role(self, role: str):
        """ Remove a role from the space object

        :param role: The role to add e.g. spy, pirate etc.
        :type id: str
        """
        role = role.strip().lower()
        self.roles.remove_from_collection(role, self.id)

    def has_role(self, role):
        """ check if the object has a role

        :param role: The role to add e.g. spy, pirate etc.
        :type id: str
        :return: If the object has the role
        :rtype: bool
        """
        role = role.strip().lower()
        return self.roles.collection_has(role, self.id)

    def get_roles(self, id):
        return self.roles.get_collections_in(id)

    @classmethod
    def get_role_objects(cls,role):
        role = role.strip().lower()
        id_set = cls.roles.collection_set(role)
        return [cls.get(x) for x in id_set]

    @classmethod
    def get_role_set(cls, role):
        role = role.strip().lower()
        return  cls.roles.collection_set(role)

    @classmethod
    def get_role_object(cls, link_name):
        link_name = link_name.strip().lower()
        the_set =  cls.roles.collection_set(link_name)
        if len(the_set)==1:
            # return a list so you can remove while iterating
            return cls.get(next(iter(the_set)))
        return None
 
    ############### LINKS ############
    def add_link(self, link_name: str, other: Agent | CloseData | int):
        """ Add a link to the space object. Links are uni-directional

        :param role: The role/link name to add e.g. spy, pirate etc.
        :type id: str
        """
        id = self.resolve_id(other)
        link_name = link_name.strip().lower()
        self.links.add_to_collection(link_name,id)
        self.has_links.add_to_collection(link_name, self.id)

    def set_dedicated_link(self, link_name: str, other: Agent | CloseData | int):
        link_name = link_name.strip().lower()
        self.links.dedicated_collection(link_name, self.resolve_id(other))
        if other is not None:
            self.has_links.add_to_collection(link_name, self.id)

    def remove_link(self, link_name: str, other: Agent | CloseData | int):
        """ Remove a role from the space object

        :param role: The role to add e.g. spy, pirate etc.
        :type id: str
        """
        id = Agent.resolve_id(other)
        self.links.remove_from_collection(link_name,id)
        # Remove any empty from has links
        collections = link_name.split(",")
        for collection in collections:
            collection = collection.strip().lower()
            the_set = self.links.collections.get(collection)
            if the_set is not None and len(the_set)<1:
                self.has_links.remove_from_collection(collection, self.id)

    def remove_link_all(self, link_name: str):
        """ Remove a role from the space object
        :param role: The role to add e.g. spy, pirate etc.
        :type id: str
        """
        link_name = link_name.strip().lower()
        self.links.remove_collection(link_name)
        self.has_links.remove_from_collection(link_name, self.id)

    def has_link_to(self, link_name: str | list[str], other: Agent | CloseData | int):
        """ check if the object has a role

        :param role: The role to add e.g. spy, pirate etc.
        :type id: str
        :return: If the object has the role
        :rtype: bool
        """
        link_name = link_name.strip().lower()
        id = self.resolve_id(other)
        return self.links.collection_has(link_name,id)

    def _remove_every_link(self, other: Agent | CloseData | int):
        id = self.resolve_id(other)
        for role in self.links:
            self._remove_link(role, id)

    def get_in_links(self, other: Agent | CloseData | int):
        id = self.resolve_id(other)
        return self.links.get_collections_in(id)
        
    def get_link_objects(self, link_name):
        link_name = link_name.strip().lower()
        the_set =  self.links.collection_set(link_name)
        if the_set:
            # return a list so you can remove while iterating
            return [self.get(x) for x in the_set]
        return []

    def get_dedicated_link(self, link_name):
        link_name = link_name.strip().lower()
        the_set =  self.links.collection_set(link_name)
        if len(the_set)==1:
            # return a list so you can remove while iterating
            return next(iter(the_set))
        return None

    def get_dedicated_link_object(self, link_name):
        return self.resolve_py_object(self.get_dedicated_link(link_name))
        

    def get_link_set(self, link_name):
        link_name = link_name.strip().lower()
        return self.links.collection_set(link_name)

    def get_link_list(self, link_name):
        link_name = link_name.strip().lower()
        return self.links.collection_list(link_name)

    @classmethod
    def has_links_set(cls, collection_name):
        collection_name = collection_name.strip().lower()
        return cls.has_links.collection_set(collection_name)

    @classmethod
    def has_links_list(cls,collection_name):
        collection_name = collection_name.strip().lower()
        return cls.has_links.collection_list(collection_name)
    ####################################
    @classmethod
    def resolve_id(cls, other: Agent | CloseData | int):
        id = other
        if isinstance(other, Agent):
            id = other.id
        elif isinstance(other, CloseData):
            id = other.id
        elif isinstance(other, SpawnData):
            id = other.id
        return id

    @classmethod
    def resolve_py_object(cls, other: Agent | CloseData | int):
        py_object = other
        if isinstance(other, Agent):
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
        collection_name = collection_name.strip()
        self.inventory.add_to_collection(collection_name,data)
        self._has_inventory.add_to_collection(collection_name, self.id)

    def remove_inventory(self, collection_name: str, data: object):
        """ Remove a role from the space object

        :param role: The role to add e.g. spy, pirate etc.
        :type id: str
        """
        self.inventory.remove_from_collection(collection_name,data)
        # Remove any empty from has links
        collections = collection_name.split(",")
        for collection in collections:
            collection = collection.strip()
            the_set = self.inventory.collections.get(collection)
            if len(the_set)<1:
                self._has_inventory.remove_from_collection(collection, self.id)

    def has_any_inventory(self, collection_name: str | list[str]):
        collection_name = collection_name.strip()
        return self._has_inventory.collection_has(collection_name,self.id)

    def has_in_inventory(self, collection_name: str | list[str], data: object):
        """ check if the object has a role

        :param role: The role to add e.g. spy, pirate etc.
        :type id: str
        :return: If the object has the role
        :rtype: bool
        """
        collection_name = collection_name.strip()
        return self.inventory.collection_has(collection_name,data)

    def _remove_every_inventory(self, data: object):
        self.inventory.remove_every_collection(data)

    def get_inventory_in(self, data: object):
        return self.inventory.get_collections_in(data)
        
    def get_inventory_objects(self, collection_name):
        collection_name = collection_name.strip()
        the_set =  self.inventory.collection_set(collection_name)
        if the_set:
            # return a list so you can remove while iterating
            return [self.get(x) for x in the_set]
        return []

    def get_inventory_set(self, collection_name):
        collection_name = collection_name.strip()
        return self.inventory.collection_set(collection_name)
    
    def get_inventory_list(self, collection_name):
        collection_name = collection_name.strip()
        return self.inventory.collection_list(collection_name)

    def get_inventory_value(self, collection_name, default=None):
        collection_name = collection_name.strip()
        return self.inventory.collections.get(collection_name, default)

    def set_inventory_value(self, collection_name, value):
        collection_name = collection_name.strip()
        self.inventory.collections[collection_name]=value
        if value is not None:
            self._has_inventory.add_to_collection(collection_name, self.id)
        else:
            self._has_inventory.remove_from_collection(collection_name, self.id)

    @classmethod
    def has_inventory_set(cls, collection_name):
        collection_name = collection_name.strip()
        return cls._has_inventory.collection_set(collection_name)

    @classmethod
    def has_inventory_list(cls, collection_name):
        collection_name = collection_name.strip()
        return cls._has_inventory.collection_list(collection_name)
    
    # Task overrides this to respect scope
    def get_variable(self, key, default=None):
        return self.get_inventory_value(key, default)
    # Task overrides this to respect scope
    def set_variable(self, key, value):
        self.get_inventory_value(key, value)
    
    # Task overrides this to respect scope
    def set_variable(self, key, value):
        return self.set_inventory_value(key, value)
    
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

    def update_engine_data(self, data):
        blob = self.get_engine_data_set()
        if blob is not None:
            for (key, value) in data.items():
                if type(value) is tuple:
                    blob.set(key, value[0], value[1])
                else:
                    blob.set(key, value)

    def get_engine_data(self, key, index=0):
        blob = self.get_engine_data_set()
        if blob is not None:
            return blob.get(key, index)
        return None

    def set_engine_data(self, key, value, index=0):
        blob = self.get_engine_data_set()
        if blob is not None:
            blob.set(key, value, index)

    def get_engine_data_set(self):
        this = self.get_engine_object()
        if this is None:
            # Object is destroyed
            return None
        return this.data_set
    
    def get_engine_object(self):
        # Needs to be implemented by Grid and Space Object
        return None
    


Agent.SHARED = Agent()
Agent.SHARED_ID = get_story_id()
Agent.SHARED.id = Agent.SHARED_ID
Agent.SHARED.add()

#
# Needed for testing
#
def clear_shared():
    Agent.SHARED_ID
    Agent.SHARED = Agent()
    Agent.SHARED.id = Agent.SHARED_ID
    Agent.SHARED.add()
