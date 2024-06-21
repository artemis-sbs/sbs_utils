from ..helpers import FrameContext
from .gui import text_sanitize


def maps_get_list():
    ret = []
    page = FrameContext.page
    if page is None:
        return []
    #
    # Walk all labels looking for map Labels
    #
    all_labels = page.story.labels
    for l in all_labels:
        if l.startswith("map/"):
            m = all_labels[l]
            ret.append(m)
#                {"name": m.display_name, "description": text_sanitize(m.desc), "label": m},
#            )

    if len(ret)==0:
        return  [
            {"name": "No maps found", "description": "No maps were found when searching all mast/python labels."},
        ]
    return ret


