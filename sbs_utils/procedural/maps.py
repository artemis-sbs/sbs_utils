from ..helpers import FrameContext
#from .gui import text_sanitize


def maps_get_list():
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
    page = FrameContext.page
    if page is None:
        return []
    #
    # Walk all labels looking for map Labels
    #
    all_labels = page.story.labels
    init_label = None
    for l in all_labels:
        if not l.startswith("map/"):
            continue
        if all_labels[l].path == "__overview__":
            init_label = all_labels[l]
            break

    return init_label


def map_get_properties(map):
    meta_data = getattr(map, "meta_data", None)
    if meta_data is None:
        return None
    # Try Properties and properties
    ret = meta_data.get("Properties", meta_data.get("properties"))

    return ret



