"""The xESS apps a crew member uses on the ground (a tile world).

LOOK - what is within reach: things to use, pick up or open, and people to talk to. The
       map click does the same thing; this is the same set as a list, so nothing needs
       precise clicking, and it is where the device says what just happened.
PACK - what this crew member is carrying: use a medkit, hand something to whoever is
       standing next to you.

Both only appear on a tile world. On an engine interior the device is what it was.
"""
from .xess import xess_register, gui_xess_head, _esc, DIM
from ..query import to_object, to_id

APP_LOOK = "look"
APP_PACK = "pack"

#: Items with a USE on a person. A mission adds its own with `xess_ground_use`.
_USES = {}


def xess_ground_use(item, fn, label="Use"):
    """Give an item a USE from the Pack: ``fn(client_id, lifeform, target)`` where
    ``target`` is a teammate beside you (or yourself). Return text for the device."""
    _USES[str(item).strip().lower()] = (fn, label)


def _on_ground(client_id):
    from ..boarding_tiles import boarding_tile_on
    return boarding_tile_on(client_id)


def _near(client_id):
    """[(kind, key, name)] within reach: props, then talkable hostiles, then crew."""
    from ..boarding import boarding_me, boarding_team
    from ..boarding_props import boarding_props_near, boarding_prop
    from ..boarding_combat import _BY_ID as HOSTILE_IDS, boarding_hostile
    from ..tilemap import tilemap_actors_near
    me = boarding_me(client_id)
    out = []
    for key in boarding_props_near(me, 1):
        rec = boarding_prop(key)
        out.append(("prop", key, rec["name"]))
    team = set(boarding_team())
    for aid in tilemap_actors_near(me, 1):
        hkey = HOSTILE_IDS.get(aid)
        if hkey:
            rec = boarding_hostile(hkey)
            if rec and rec["talk"]:
                out.append(("talk", hkey, rec["name"]))
        elif aid in team:
            who = to_object(aid)
            out.append(("crew", aid, getattr(who, "name", "crew")))
    return out


def _look_app(client_id):
    from .row import gui_row
    from .text import gui_text, gui_text_area
    from .button import gui_button
    from ..boarding_props import boarding_last_note
    gui_xess_head(client_id, "Look")
    things = [t for t in _near(client_id) if t[0] != "crew"]
    if not things:
        gui_row("row-height: 2em; font:gui-2;")
        gui_text("$text:%s;color:%s;" % (_esc("Nothing within reach."), DIM))
    for kind, key, name in things[:6]:
        gui_row("row-height: 2.2em; font:gui-2;")
        verb = "Talk to" if kind == "talk" else "Use"
        gui_button("%s %s" % (verb, name),
                   on_press=(lambda _c=client_id, _k=kind, _key=key: _use(_c, _k, _key)))
    # THE WAYS OUT. An exit is a few cells of ordinary ground with a mark on them, so a
    # crew member who has walked in has no way to see how to walk out again (playtest:
    # "confused how to exit the ship"). Listed by where they go; pressing walks there.
    for mark, title in _exits(client_id):
        gui_row("row-height: 2.2em; font:gui-2;")
        gui_button("Go to %s" % title,
                   on_press=(lambda _c=client_id, _m=mark: _go_exit(_c, _m)))
    note = boarding_last_note(client_id)
    if note:
        gui_row("row-height: 1fr; padding: 6px, 6px, 6px, 6px;")
        gui_text_area(note)


def _exits(client_id):
    """[(exit mark, destination title)] for the area this console is standing in - only
    to places the party knows about."""
    from ..boarding import boarding_me
    from ..tilemap import (tilemap_where, tilemap_marks, tilemap_exit_target,
                           tilemap_title, tilemap_known)
    at = tilemap_where(boarding_me(client_id))
    if at is None:
        return []
    out = []
    for mark in tilemap_marks(at[0]):
        target, _ = tilemap_exit_target(at[0], mark)
        if target and tilemap_known(target):
            out.append((mark, tilemap_title(target) or target))
    return out


def _go_exit(client_id, mark):
    """Walk to the nearest cell of an exit mark; stopping on it goes through."""
    from ..boarding import boarding_me
    from ..tilemap import tilemap_where, tilemap_mark_cells, tilemap_walk
    me = boarding_me(client_id)
    at = tilemap_where(me)
    if at is None:
        return
    cells = tilemap_mark_cells(at[0], mark)
    if cells:
        x, y = min(cells, key=lambda c: abs(c[0] - at[1]) + abs(c[1] - at[2]))
        tilemap_walk(me, x, y)


def _use(client_id, kind, key):
    if kind == "prop":
        from ..boarding_props import boarding_interact
        boarding_interact(client_id, key)
    elif kind == "talk":
        from ..boarding_combat import boarding_hostile
        from ..boarding_props import _SCENES
        from ..boarding import boarding_encounter
        rec = boarding_hostile(key)
        if rec and rec["talk"] and _SCENES["doc"] is not None:
            boarding_encounter(_SCENES["doc"], rec["talk"], client_id,
                               channel=f"talk:{key}")


def _pack_app(client_id):
    from .row import gui_row
    from .text import gui_text
    from .button import gui_button
    from ..boarding import boarding_me
    from ..boarding_props import boarding_pack
    gui_xess_head(client_id, "Pack")
    me = boarding_me(client_id)
    pack = boarding_pack(me)
    crew = [t for t in _near(client_id) if t[0] == "crew"]
    if not pack:
        gui_row("row-height: 2em; font:gui-2;")
        gui_text("$text:%s;color:%s;" % (_esc("You are not carrying anything."), DIM))
        return
    for item, n in sorted(pack.items()):
        gui_row("row-height: 1.8em; font:gui-2;")
        gui_text("$text:%s;" % _esc("%s x%d" % (item.replace("_", " "), n)))
        use = _USES.get(item)
        if use is not None:
            fn, label = use
            target = crew[0][1] if crew else me
            gui_row("row-height: 2em; font:gui-1;")
            gui_button("%s%s" % (label, "" if target == me else " on " +
                                 getattr(to_object(target), "name", "them")),
                       on_press=(lambda _c=client_id, _f=fn, _t=target:
                                 _apply(_c, _f, _t)))
        for _, aid, name in crew[:2]:
            gui_row("row-height: 2em; font:gui-1;")
            gui_button("Give to %s" % name,
                       on_press=(lambda _c=client_id, _i=item, _a=aid: _give(_c, _i, _a)))


def _apply(client_id, fn, target):
    from ..boarding import boarding_me
    from ..boarding_props import _note
    try:
        text = fn(client_id, boarding_me(client_id), target)
    except Exception as e:                               # noqa: BLE001
        text = "That did not work: %s" % e
    if text:
        _note(client_id, text)


def _give(client_id, item, to):
    from ..boarding import boarding_me
    from ..boarding_props import boarding_hand_over, _note
    if boarding_hand_over(boarding_me(client_id), to, item):
        _note(client_id, "Handed over %s." % item.replace("_", " "))


def _medkit(client_id, me, target):
    """The stock medkit: stand somebody back up, or patch a wound."""
    from ..boarding_combat import boarding_is_down, boarding_revive, boarding_heal
    from ..boarding_props import boarding_take_item
    if not boarding_take_item(me, "medkit"):
        return "No medkit."
    who = getattr(to_object(target), "name", "them")
    if boarding_is_down(target):
        boarding_revive(target, by=me)
        return "%s is back on their feet." % who
    boarding_heal(target, 2)
    return "Patched up %s." % who


xess_ground_use("medkit", _medkit, "Use medkit")


def xess_ground_revision(client_id):
    """What the ground apps show, for the device's revision."""
    from ..boarding import boarding_me
    from ..boarding_props import boarding_pack, boarding_last_note
    if not _on_ground(client_id):
        return None
    me = boarding_me(client_id)
    return (tuple(sorted(boarding_pack(me).items())), boarding_last_note(client_id),
            tuple(_near(client_id)), _tasks_revision(client_id),
            _places(), _in_sight(client_id), tuple(_exits(client_id)))


def _places():
    """Where each crew member is standing, as the Crew app words it. A mark changes
    rarely, so this repaints on arriving somewhere, not on every step."""
    from ..boarding import boarding_team, boarding_client_of
    from .boarding_console import where_text
    out = []
    for lf in sorted(boarding_team()):
        cid = boarding_client_of(lf)
        out.append((lf, where_text(cid) if cid is not None else ""))
    return tuple(out)


def _in_sight(client_id):
    """What Scan lists - only while Scan is the open app, so walking with another app
    open does not rebuild it on every step."""
    from .xess import xess_opened, APP_SCAN
    if xess_opened(client_id) != APP_SCAN:
        return None
    from ..boarding import boarding_me
    from ..tilemap import tilemap_where, tilemap_visible, tilemap_actors, tilemap_actor
    at = tilemap_where(boarding_me(client_id))
    if at is None:
        return None
    seen = tilemap_visible(at[0])
    return tuple(a for a in tilemap_actors(at[0])
                 if (tilemap_actor(a)["x"], tilemap_actor(a)["y"]) in seen)


xess_register(APP_LOOK, title="Look", icon="epadd.status", sort=22,
              blurb="What is within reach", draw=_look_app, available=_on_ground)
xess_register(APP_PACK, title="Pack", icon="epadd.cargo", sort=24,
              blurb="What you are carrying", draw=_pack_app, available=_on_ground)


APP_TASKS = "tasks"
APP_BEAM = "beam"


def _tasks_app(client_id):
    """This crew member's own quests, then the party's."""
    from .row import gui_row
    from .text import gui_text
    from .listbox import gui_list_box
    from ..boarding import boarding_me
    from ..quest import quest_log_build_items, quest_log_template
    from ...agent import Agent
    gui_xess_head(client_id, "Tasks")
    me = boarding_me(client_id)
    name = getattr(to_object(me), "name", "You")
    items = quest_log_build_items([(name, me), ("Party", Agent.SHARED_ID)])
    if not items:
        gui_row("row-height: 2em; font:gui-2;")
        gui_text("$text:%s;color:%s;" % (_esc("Nothing asked of you yet."), DIM))
        return
    gui_row("row-height: 1fr; padding: 4px, 6px, 4px, 6px;")
    gui_list_box(items, "row-height: 2.6em;", item_template=quest_log_template)


def _beam_app(client_id):
    """The transporter: where the ship can put you, and whether it can right now."""
    from .row import gui_row
    from .text import gui_text
    from .button import gui_button
    from ..tilemap import tilemap_title
    from ..boarding_quests import (boarding_transport_targets, boarding_transport_jammed,
                                   _JAM)
    gui_xess_head(client_id, "Beam")
    if boarding_transport_jammed():
        gui_row("row-height: 2.4em; font:gui-2;")
        gui_text("$text:%s;color:#f66;" % _esc(_JAM["why"] or "Transporter jammed"))
        return
    targets = boarding_transport_targets(client_id)
    if not targets:
        gui_row("row-height: 2em; font:gui-2;")
        gui_text("$text:%s;color:%s;" % (_esc("No other site has a lock yet."), DIM))
    for area in targets:
        gui_row("row-height: 2.2em; font:gui-2;")
        gui_button("To %s" % (tilemap_title(area) or area),
                   on_press=(lambda _c=client_id, _a=area: _beam(_c, _a)))


def _beam(client_id, area):
    from ..boarding_quests import boarding_transport
    from ..boarding_props import _note
    ok, text = boarding_transport(client_id, area)
    _note(client_id, text)


def _tasks_revision(client_id):
    from ..quest import quest_generation
    from ..boarding_quests import boarding_transport_jammed, boarding_transport_targets
    return (quest_generation(), boarding_transport_jammed(),
            tuple(boarding_transport_targets(client_id)))


xess_register(APP_TASKS, title="Tasks", icon="epadd.quests", sort=26,
              blurb="What is asked of you", draw=_tasks_app, available=_on_ground)
xess_register(APP_BEAM, title="Beam", icon="epadd.boarding", sort=28,
              blurb="Where the ship can put you", draw=_beam_app, available=_on_ground)
