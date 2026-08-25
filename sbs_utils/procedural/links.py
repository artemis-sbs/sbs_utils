from ..agent import Agent
from .query import (to_set, to_object, to_id_list, to_id,
                    to_agent_list, to_client_object)

# TODO: Consider renaming this function? The name implies that it returns a boolean, which can easily trip people up if they are looking for a `get_links()` or similar.
def has_link(link_name: str):
    """Return the set of agent IDs that have at least one link under a given name.

    Despite the ``has_`` prefix this returns a set, not a bool. Use the result
    to iterate or test membership.

    Args:
        link_name (str): The link key name.

    Returns:
        set[int]: IDs of all agents that own a link entry with this name.
    """
    return Agent.has_links_set(link_name)



def linked_to(link_source, link_name: str):
    """Return the set of IDs that an agent links to under a given name.

    Args:
        link_source (Agent | int): The source agent ID or object.
        link_name (str): The link key name.

    Returns:
        set[int]: IDs of all linked targets, or an empty set if none.
    """
    link_source = Agent.resolve_py_object(link_source)
    if link_source is None:
        return set()
    return link_source.get_link_set(link_name)

def has_link_to(link_source, link_name: str, link_target) -> bool:
    """Return whether a source agent has a specific link to a target.

    Args:
        link_source (Agent | int): The agent ID or object hosting the link.
        link_name (str): The link key name.
        link_target (Agent | int): The target agent ID or object to check.

    Returns:
        bool: ``True`` if the link from source to target exists.
    """
    link_source = Agent.resolve_py_object(link_source)
    if link_source is None:
        return False
    return  link_source.has_link_to(link_name,link_target)

def link(set_holder, link_name: str, set_to):
    """Create a named link from one or more source agents to one or more targets.

    Args:
        set_holder (Agent | int | set[Agent | int]): Source agent(s).
        link_name (str): The link key name.
        set_to (Agent | int | set[Agent | int]): Target agent(s) to link to.
    """
    # to_agent_list, so the SERVER console (client id 0) can be a link SOURCE. It was
    # already a readable one: `linked_to` and `has_link_to` resolve through
    # Agent.resolve_py_object and have always answered for id 0, so a link on the server
    # could be looked for and never made. Same rule as roles.add_role.
    linkers = to_agent_list(to_set(set_holder))
    ids = to_id_list(to_set(set_to))
    for so in linkers:
        for target in ids:
            so.add_link(link_name, target)



def get_dedicated_link(so, link_name: str):
    """Return the single agent ID linked under a dedicated (1-to-1) link.

    A dedicated link stores exactly one target per source. Use ``link`` /
    ``set_dedicated_link`` for many-to-many or 1-to-1 links respectively.

    Args:
        so (Agent | int): The source agent ID or object.
        link_name (str): The link key name.

    Returns:
        int | None: The linked agent ID, or ``None`` if not set.
    """
    # Dedicated links are one-to-one,
    # `or to_client_object(so)` for the SERVER console: to_object refuses id 0 by design.
    so = to_object(so) or to_client_object(so)
    if so is None:
        return None
    return so.get_dedicated_link(link_name)
            
def set_dedicated_link(so, link_name: str, to):
    """Set a dedicated (1-to-1) link from a source agent to a single target.

    Replaces any existing link under ``link_name`` with the new target. Pass
    ``to=None`` to clear the link entirely, so that ``get_dedicated_link``
    returns ``None`` again.

    Args:
        so (Agent | int): The source agent ID or object.
        link_name (str): The link key name.
        to (Agent | int | None): The target agent ID or object, or ``None`` to clear.
    """
    # The server console counts here too - and clear_dedicated_link comes through this
    # function, so both ends of the pair move together.
    so = to_object(so) or to_client_object(so)
    if so is None:
        return
    so.set_dedicated_link(link_name, to_id(to))


def clear_dedicated_link(so, link_name: str):
    """Clear a dedicated (1-to-1) link, leaving the source linked to nothing.

    After this ``get_dedicated_link(so, link_name)`` returns ``None`` and the
    source no longer appears in ``has_link(link_name)``.

    Args:
        so (Agent | int): The source agent ID or object.
        link_name (str): The link key name.
    """
    set_dedicated_link(so, link_name, None)


def unlink(set_holder, link_name: str, set_to):
    """Remove a named link from one or more source agents to one or more targets.

    Args:
        set_holder (Agent | int | set[Agent | int]): Source agent(s).
        link_name (str): The link key name.
        set_to (Agent | int | set[Agent | int]): Target agent(s) to unlink.
    """
    # The same set `link` reaches - a source that can gain a link has to be able to
    # lose one, or the server accumulates every link it was ever given.
    linkers = to_agent_list(to_set(set_holder))
    ids = to_id_list(to_set(set_to))
    for so in linkers:
        for target in ids:
            if so is not None and target is not None:
                so.remove_link(link_name, target)
