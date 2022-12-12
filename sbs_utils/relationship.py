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
