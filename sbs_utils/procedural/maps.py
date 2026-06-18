from ..helpers import FrameContext
#from .gui import text_sanitize


def maps_get_list():
    """Return all ``@map`` labels defined in the current page's story.

    If only an ``__overview__`` label exists, it is returned as a single-item
    list. If no map labels are found at all, returns a placeholder list with a
    ``"No maps found"`` entry.

    Returns:
        list: ``@map`` Label objects, or a fallback list if none are defined.
    """
    ret = []
    page = FrameContext.page
    if page is None:
        return []
    #
    # Walk all labels looking for map Labels
    #
    init_label = None
    all_labels = page.story.labels
    for l in all_labels:
        if not l.startswith("map/"):
            continue
        m = all_labels[l]
        if m.path == "__overview__":
            init_label = m
        else:
            ret.append(m)
#                {"name": m.display_name, "description": text_sanitize(m.desc), "label": m},
#            )
    #
    # If there is just the one i.e. the init return that
    #
    if len(ret)==0 and init_label is not None:
        return [init_label]
    elif len(ret)==0:
        return  [
            {"name": "No maps found", "description": "No maps were found when searching all mast/python labels."},
        ]
    return ret


def maps_get_init():
    """Return the ``__overview__`` map label from the current MAST story, or ``None``.

    Returns:
        Label | None: The overview map label, or ``None`` if not defined.
    """
    mast = FrameContext.mast
    if mast is None:
        return []
    #
    # Walk all labels looking for map Labels
    #
    all_labels = mast.labels
    init_label = None
    for l in all_labels:
        if not l.startswith("map/"):
            continue
        if all_labels[l].path == "__overview__":
            init_label = all_labels[l]
            break

    return init_label


def map_get_properties(map):
    """Return the ``Properties`` inventory value of a map label.

    Checks ``"Properties"`` first, then ``"properties"`` as a fallback.

    Args:
        map (Label): The map label object.

    Returns:
        any: The properties value, or ``None`` if not set.
    """
    # Try Properties and properties
    return map.get_inventory_value("Properties", map.get_inventory_value("properties"))




