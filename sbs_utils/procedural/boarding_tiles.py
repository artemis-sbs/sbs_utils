"""A boarding party on a TILE WORLD - the ground as data rather than a ship interior.

`boarding_site.py` puts a crew member's body on an engine interior as a grid object.
This is the other body model for the same party: the body is an actor in
``procedural/tilemap.py``, standing at ``(area, x, y)``, and the console draws it with
``gui_tilemap``. Everything above the body - the team, the scenes, the channels, the xESS
- is the same party either way.

What a crew member does with a map click is policy, and it lives here (`boarding_tile_click`):
fire when the device is armed, use the thing on the cell when there is one within reach,
walk up to it when it is further, and otherwise walk there.

Stdlib only.
"""
from .inventory import get_inventory_value, set_inventory_value
from .query import to_id

#: On the CLIENT: the tile area this console is standing in, while it is.
KEY_AREA = "BOARDING_AREA"

#: Default look for a crew body. A mission sets its own with `boarding_tile_style`.
_STYLE = {"sprite": None, "colors": ["#4cf", "#fc4", "#f66", "#8f8", "#c8f", "#fa8"]}

#: Who handles a click on a cell that holds something: ``fn(client_id, area, x, y)``
#: returning True when it dealt with the click. Props (and hostiles) register here, so
#: this module does not need to know what either of them is.
_CLICK_HANDLERS = []


def boarding_tile_style(sprite=None, colors=None):
    """How crew bodies are drawn: an atlas key, and a color per crew member in turn."""
    if sprite is not None:
        _STYLE["sprite"] = sprite
    if colors:
        _STYLE["colors"] = list(colors)


def boarding_tile_click_handler(fn):
    """Let something else claim a map click first (a prop, a hostile). Idempotent."""
    if fn not in _CLICK_HANDLERS:
        _CLICK_HANDLERS.append(fn)


def boarding_tile_on(client_id):
    """Whether this console's body is standing on a tile world."""
    from .boarding import boarding_me
    from .tilemap import tilemap_where
    me = boarding_me(client_id)
    return me is not None and tilemap_where(me) is not None


def boarding_tile_where(client_id):
    """``(area, x, y)`` for this console's body, or None."""
    from .boarding import boarding_me
    from .tilemap import tilemap_where
    me = boarding_me(client_id)
    return tilemap_where(me) if me is not None else None


def boarding_tile_put(client_id, area, at=None):
    """Stand this console's character in a tile area. Returns its actor record."""
    from .boarding import boarding_me, boarding_team
    from .tilemap import tilemap_place, tilemap_actor
    me = boarding_me(client_id)
    if me is None:
        return None
    rec = tilemap_actor(me)
    color = rec.get("color") if rec else None
    if color is None:
        colors = _STYLE["colors"] or ["#4cf"]
        color = colors[len([m for m in boarding_team() if tilemap_actor(m)]) % len(colors)]
    x, y = at if at else (None, None)
    rec = tilemap_place(me, area, x, y, sprite=_STYLE["sprite"], color=color, party=True,
                        blocks=False)
    set_inventory_value(me, "BOARDING_COLOR", color)
    set_inventory_value(client_id, KEY_AREA, area)
    from .signal import signal_observe
    signal_observe(_on_signal)
    # Their quest screens show THEIR quests while they are down here.
    from .boarding_quests import boarding_quest_holder
    boarding_quest_holder(client_id)
    return rec


def boarding_tile_leave(client_id):
    """Take this console's character off the tile world."""
    from .boarding import boarding_me
    from .tilemap import tilemap_remove
    me = boarding_me(client_id)
    set_inventory_value(client_id, KEY_AREA, None)
    from .quest_driver import quest_holder_clear
    quest_holder_clear(client_id)
    return tilemap_remove(me) if me is not None else False


def _on_signal(name, data):
    """A crew member who changes area leaves the conversation they were in: a side scene
    happens SOMEWHERE."""
    if name != "tilemap_moved" or not isinstance(data, dict):
        return
    from .boarding import (boarding_client_of, boarding_channel_of,
                           boarding_channel_leave, PARTY)
    cid = boarding_client_of(data.get("TILEMAP_AGENT"))
    if cid is not None and boarding_channel_of(cid) != PARTY:
        boarding_channel_leave(cid)


def boarding_tile_click(client_id, area, x, y):
    """One map click, as policy. What ``gui_tilemap(on_click=...)`` should be given.

    Order: an armed device fires; then anything registered with
    ``boarding_tile_click_handler`` may claim the cell (a prop to use, somebody to talk
    to); otherwise the character walks there.
    """
    from .boarding import boarding_me
    from .boarding_site import boarding_armed
    from .tilemap import tilemap_where, tilemap_walk
    me = boarding_me(client_id)
    at = tilemap_where(me) if me is not None else None
    if at is None or at[0] != area:
        return False
    from .boarding_combat import boarding_can_act
    if not boarding_can_act(me):
        return False                     # down, or stunned: nobody moves
    if boarding_armed(client_id):
        from .boarding_combat import boarding_tile_fire
        return boarding_tile_fire(client_id, x, y)
    for fn in list(_CLICK_HANDLERS):
        try:
            if fn(client_id, area, x, y):
                return True
        except Exception as e:                           # noqa: BLE001
            from .execution import log
            log(f"tile click handler failed: {e}", "boarding", "warning")
    return tilemap_walk(me, x, y) >= 0


def boarding_tile_area_of(client_id):
    """The tile area this console is in, or None."""
    at = boarding_tile_where(client_id)
    return at[0] if at else None


def boarding_tile_clear():
    from .signal import signal_unobserve
    signal_unobserve(_on_signal)
    _CLICK_HANDLERS.clear()
    _STYLE["sprite"] = None


def _discover_outcome(agent_id, speaker, tokens):
    """`discover caves` - the party now knows an area exists (a map, a survivor's word)."""
    from .tilemap import tilemap_reveal_area
    for key in tokens:
        tilemap_reveal_area(key)
    return None


from .amd_dialogue import dialogue_register_outcome  # noqa: E402
dialogue_register_outcome("discover", _discover_outcome)
