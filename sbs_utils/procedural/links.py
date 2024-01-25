from ..agent import Agent
from .query import to_object_list, to_set, to_object, to_id_list, to_id

def has_link(key: str):
    """ has_link

        get the object that have a link item with the given key

        :param key: The key/name of the inventory item
        :type key: str
        :rtype: set of ids
        """
    return Agent.has_links_set(key)



def linked_to(link_source, link_name: str):
    """ linked_to

        get the set that inventor the source is linked to for the given key

        :param link_source: The id object to check
        :type link_source: int / id
        :param link_name: The key/name of the inventory item
        :type link_name: str
        :rtype: set of ids
        """


    link_source = Agent.resolve_py_object(link_source)
    return link_source.get_link_set(link_name)

def has_link_to(link_source, link_name: str, link_target):
    """ has_linked_to

        check if target and source are linked to for the given key

        :param link_source: The id object to check
        :type link_source: int / id
        :param link_name: The key/name of the inventory item
        :type link_name: str
        :rtype: set of ids
        """


    link_source = Agent.resolve_py_object(link_source)
    return  link_source.has_link_to(link_name,link_target)

def link(set_holder, link, set_to):
    linkers = to_object_list(to_set(set_holder))
    ids = to_id_list(to_set(set_to))
    for so in linkers:
        for target in ids:
            so.add_link(link, target)



def get_dedicated_link(so, link):
    # Dedicated links are one-to-one, 
    so = to_object(so)
    return so.get_dedicated_link(link)
            
def set_dedicated_link(so, link, to):
    # Dedicated links are one-to-one
    so = to_object(so)
    to = to_id(to)
    so.set_dedicated_link(link, to)


def unlink(set_holder, link, set_to):
    linkers = to_object_list(to_set(set_holder))
    ids = to_id_list(to_set(set_to))
    for so in linkers:
        for target in ids:
            if so is not None and target is not None:
                so.remove_link(link, target)
