"""What is still worth exploring, for a crew member on a tile world.

A playtest finding: the map drew everything the crew could SEE, and nothing about which
of it mattered. A crate that had been searched looked like one that had not, a person
nobody had spoken to looked like one who had said everything, and a way out to somewhere
new looked like the way back. So this module answers "what is left here?", and the tile
view and the xESS draw the answer:

``new``   a thing nobody has used yet (a prop with a scene, an item or a lock) or a person
          nobody has talked to.
``lead``  what an open quest held by this crew member (or by the whole party) points at,
          with ``Leads to:`` on the quest - a prop key or a person key, comma separated.
``way``   an exit to an area the party has never set foot in.

The map only ever badges a cell the party has seen: a hint must not leak where something
is before anyone has looked. The lists in the xESS follow the same rule.

A mission draws the badges by naming atlas cells for them (``boarding_hint_style``);
with no sprite for a kind, that kind is simply not drawn.
"""
from ..agent import Agent

_STYLE = {"new": None, "lead": None, "way": None}

#: Compass words for the xESS lists - ASCII, short.
_COMPASS = ["E", "SE", "S", "SW", "W", "NW", "N", "NE"]


def boarding_hint_style(new=None, lead=None, way=None):
    """Name the atlas cells the map draws its hint badges with. ``None`` leaves a kind
    as it was; ``""`` turns it off."""
    for k, v in (("new", new), ("lead", lead), ("way", way)):
        if v is not None:
            _STYLE[k] = v or None


def boarding_hint_sprite(kind):
    return _STYLE.get(kind)


def _norm(s):
    return str(s or "").strip().lower()


# --- what counts as unexplored ------------------------------------------------------

def _prop_worth(rec):
    """A prop nobody has touched yet that has something to it: a scene, an item, a
    lock, or just a description to read."""
    if rec["id"] is None or rec["taken"] or rec["used"] or rec.get("touched") \
            or not rec["shown"]:
        return False
    return bool(rec["scene"] or rec["item"] or (rec["opens"] and not rec["open"])
                or rec.get("desc"))


def _person_worth(rec):
    return bool(rec.get("talk")) and not rec.get("talked") and rec.get("id") is not None \
        and rec.get("state") != "down"


def _leads_of(agent_id):
    """Every ``Leads to:`` key of the ACTIVE quests an agent holds, nested ones too."""
    from .quest import quest_agent_quests, QuestState
    tree = quest_agent_quests(agent_id)
    out = []

    def walk(node):
        for q in (node.get("children", {}) or {}).values():
            if q.get("state") == QuestState.ACTIVE:
                data = q.get("data") or {}
                leads = data.get("leads_to") if hasattr(data, "get") else None
                if isinstance(leads, str):
                    leads = leads.split(",")
                for k in leads or []:
                    k = _norm(k)
                    if k and k not in out:
                        out.append(k)
            walk(q)
    if tree is not None:
        walk(tree)
    return out


def boarding_leads(client_id):
    """The prop and person keys this console's open quests point at, not yet dealt
    with. Its own quests first, then the party's."""
    from .boarding import boarding_me
    from .boarding_props import boarding_prop
    from .boarding_combat import boarding_hostile
    out = []
    me = boarding_me(client_id)
    for holder in ([me] if me is not None else []) + [Agent.SHARED_ID]:
        for key in _leads_of(holder):
            prop = boarding_prop(key)
            person = boarding_hostile(key)
            if prop is not None and (prop["used"] or prop["taken"]):
                continue
            if prop is None and person is not None and person.get("talked"):
                continue
            if (prop or person) is not None and key not in out:
                out.append(key)
    return out


def _where_key(key):
    """(area, x, y) of a prop or person key, or None when it is not on the map."""
    from .boarding_props import boarding_prop
    from .boarding_combat import boarding_hostile
    from .tilemap import tilemap_where
    rec = boarding_prop(key) or boarding_hostile(key)
    if rec is None or rec.get("id") is None:
        return None
    return tilemap_where(rec["id"])


def boarding_hints(client_id, area):
    """``{(x, y): kind}`` for one area, as this console should see it. Only cells the
    party has explored; a lead wins over new, which wins over way."""
    from .boarding_props import _PROPS
    from .boarding_combat import _HOSTILES
    from .tilemap import (tilemap_area, tilemap_where, tilemap_marks, tilemap_mark_cells,
                          tilemap_exit_target)
    rec = tilemap_area(area)
    if rec is None:
        return {}
    area = rec["key"] if "key" in rec else _norm(area)
    explored = rec["explored"]
    out = {}
    for mark in tilemap_marks(area):
        target, _ = tilemap_exit_target(area, mark)
        trec = tilemap_area(target) if target else None
        if trec is not None and not trec["explored"]:
            cells = sorted(c for c in tilemap_mark_cells(area, mark) if c in explored)
            if cells:
                out[cells[0]] = "way"
    for prop in _PROPS.values():
        if prop["area"] == area and _prop_worth(prop):
            at = tilemap_where(prop["id"])
            if at is not None and (at[1], at[2]) in explored:
                out[(at[1], at[2])] = "new"
    for person in _HOSTILES.values():
        if _person_worth(person):
            at = tilemap_where(person["id"])
            if at is not None and at[0] == area and (at[1], at[2]) in explored:
                out[(at[1], at[2])] = "new"
    for key in boarding_leads(client_id):
        at = _where_key(key)
        if at is not None and at[0] == area and (at[1], at[2]) in explored:
            out[(at[1], at[2])] = "lead"
    return out


def boarding_hint_badges(client_id, area):
    """What the tile view draws: ``{(x, y): atlas key}``, kinds with no sprite left
    out. This is what ``gui_tilemap(hints=...)`` is given."""
    return {c: _STYLE[k] for c, k in boarding_hints(client_id, area).items() if _STYLE.get(k)}


# --- words for the lists --------------------------------------------------------------

def boarding_bearing(dx, dy):
    """A compass word for a map offset (y grows down the screen, so -y is north)."""
    import math
    if dx == 0 and dy == 0:
        return "here"
    a = math.degrees(math.atan2(dy, dx)) % 360
    return _COMPASS[int((a + 22.5) // 45) % 8]


def boarding_points_of_interest(client_id, reach=1):
    """What this crew member can see that is worth walking to, nearest first:
    ``[(kind, key, name, distance, bearing, hint)]``. ``kind`` is ``prop`` or ``talk``;
    ``hint`` is ``lead``, ``new`` or ``""``. Things already within ``reach`` are left
    out - the Look app lists those as buttons already."""
    from .boarding import boarding_me
    from .boarding_props import _PROPS
    from .boarding_combat import _HOSTILES
    from .tilemap import tilemap_where, tilemap_visible, tilemap_area
    me = boarding_me(client_id)
    at = tilemap_where(me) if me is not None else None
    if at is None:
        return []
    area, mx, my = at
    rec = tilemap_area(area)
    seen = rec["explored"] if rec else set()
    sight = tilemap_visible(area)
    hints = boarding_hints(client_id, area)
    out = []

    def add(kind, key, name, aid):
        p = tilemap_where(aid)
        if p is None or p[0] != area or (p[1], p[2]) not in seen:
            return
        d = abs(p[1] - mx) + abs(p[2] - my)
        if d <= reach:
            return
        hint = hints.get((p[1], p[2]), "")
        if hint == "way":
            hint = ""
        # A thing out of sight is only listed if it still matters.
        if (p[1], p[2]) not in sight and not hint:
            return
        out.append((kind, key, name, d, boarding_bearing(p[1] - mx, p[2] - my), hint))

    for key, prop in _PROPS.items():
        if prop["id"] is not None and prop["area"] == area and prop["shown"] \
                and not prop["taken"]:
            add("prop", key, prop["name"], prop["id"])
    for key, person in _HOSTILES.items():
        if person.get("talk") and person.get("id") is not None \
                and person.get("state") != "down":
            add("talk", key, person["name"], person["id"])
    rank = {"lead": 0, "new": 1, "": 2}
    out.sort(key=lambda t: (rank[t[5]], t[3]))
    return out


def boarding_lead_places(client_id):
    """``[(key, name, where)]`` for this console's leads: ``where`` is the area's title,
    with a bearing when it is the area the crew member stands in, or a vaguer phrase
    when the party has not found that place yet."""
    from .boarding import boarding_me
    from .boarding_props import boarding_prop
    from .boarding_combat import boarding_hostile
    from .tilemap import tilemap_where, tilemap_title, tilemap_known, tilemap_area
    me = boarding_me(client_id)
    here = tilemap_where(me) if me is not None else None
    out = []
    for key in boarding_leads(client_id):
        rec = boarding_prop(key) or boarding_hostile(key)
        name = rec["name"] if rec else key
        at = _where_key(key)
        area = at[0] if at else (rec.get("area") if rec else None)
        if not area or not tilemap_known(area):
            where = "somewhere not yet found"
        elif here is not None and here[0] == area and at is not None and \
                (at[1], at[2]) in (tilemap_area(area) or {}).get("explored", ()):
            d = abs(at[1] - here[1]) + abs(at[2] - here[2])
            where = "here, %d %s" % (d, boarding_bearing(at[1] - here[1], at[2] - here[2]))
        else:
            where = tilemap_title(area) or area
        out.append((key, name, where))
    return out


def boarding_go_to(client_id, key):
    """Walk to a prop or person and use or talk to it on arrival - the same as clicking
    it on the map. False when it is not in this crew member's area."""
    from .boarding import boarding_me
    from .tilemap import tilemap_where
    at = _where_key(key)
    me = boarding_me(client_id)
    here = tilemap_where(me) if me is not None else None
    if at is None or here is None or here[0] != at[0]:
        return False
    from .boarding_props import boarding_prop, boarding_prop_click
    if boarding_prop(key) is not None:
        return bool(boarding_prop_click(client_id, at[0], at[1], at[2]))
    from .boarding_combat import boarding_hostile_click
    return bool(boarding_hostile_click(client_id, at[0], at[1], at[2]))


def boarding_hints_revision(client_id):
    """Moves when anything these lists show could have changed."""
    from .boarding import boarding_me
    from .tilemap import tilemap_where
    at = tilemap_where(boarding_me(client_id))
    if at is None:
        return None
    return tuple(sorted(boarding_hints(client_id, at[0]).items()))
