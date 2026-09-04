"""The reel manifest: which takes make up the finished cut, and in what order.

A reel is not one recording. Missions cannot share an engine session - the Control
Gallery is its own mission, ePADD lives in LegendaryMissions, Peacetime is a third -
so the reel is shot as several takes and assembled afterwards. Even inside ONE mission
a scene change is a fresh take, because the staging differs.

The manifest is data rather than flags so the running order is reviewable in one place,
and so a re-cut can drop or reorder a take without re-shooting anything.
"""
import os
import json


# Each entry: the take's name (also its directory), the mission that stages it, the
# @map to start, and the cutscene key in that mission's shots.amd.
DEFAULT_REEL = [
    {"name": "open",  "mission": "SizzleReel", "map": "sz_open", "scene": "open"},
    {"name": "fight", "mission": "SizzleReel", "map": "sz_open", "scene": "fight"},
]


def load(path=None):
    """The manifest, from a JSON file or the built-in default."""
    if path and os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
        return doc.get("takes") or doc
    return list(DEFAULT_REEL)


def save(takes, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"takes": takes}, f, indent=2)
    return path


def take_dirs(root, takes):
    """Where each take's recording lives, in reel order."""
    return [os.path.join(root, "takes", t["name"]) for t in takes]


def group_by_session(takes):
    """Takes grouped so each group can share ONE engine session.

    Two takes can share a session only if they are the same mission AND the same map -
    a different map means different staging, and restaging inside a live session is
    exactly the kind of state carry-over that makes take 2 differ from take 1.
    """
    groups, cur, key = [], [], None
    for t in takes:
        k = (t.get("mission"), t.get("map"))
        if key is not None and k != key:
            groups.append(cur)
            cur = []
        cur.append(t)
        key = k
    if cur:
        groups.append(cur)
    return groups
