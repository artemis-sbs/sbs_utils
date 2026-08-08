"""`Drops:` - what a kill leaves behind, authored instead of coded.

What drops today is spread across hand-written routes: a hostile ship drops a random
trade good, a wreck rolls an upgrade by race. That is a reasonable DEFAULT and stays the
default - a mission that authors nothing behaves exactly as it always has. What it cannot
do is be looked at, or changed by an author, or answer "why did a practice target leave
contraband" (PRM-14) without reading MAST.

A drop table is keyed by ROLE, because loot follows from what a ship IS:

    ## [Drops](drops)

    ### [Target Drone](target_drone)
    ---
    Drops: none
    ---
    Condemned hulks squawking hostile IFF. Practice targets carry nothing.

    ### [Raider](raider)
    ---
    Drops: salvage x2-4, contraband 20%
    ---

The record KEY is the role it applies to. First matching role wins, so a specific role
(`target_drone`) overrides a general one (`raider`) as long as it is registered first -
which is the order the author wrote them in.
"""
import random

from ..agent import Agent
from .amd import amd_drop_table
from .query import to_object, to_id


# role -> [ {key, low, high, chance}, ... ]. Per-mission; cleared by the reset.
_DROPS = {}
_ORDER = []          # roles in the order they were authored - first match wins


def drops_clear():
    """Forget every authored table. Part of the per-mission reset."""
    _DROPS.clear()
    _ORDER.clear()


def drops_size():
    return len(_DROPS)


def drop_table_parse(value):
    """`salvage x2-4, contraband 20%` -> [{key, low, high, chance}].

    The grammar itself lives in `amd.amd_drop_table`, alongside the other authored value
    types and reachable from the stdlib-only half of the toolchain - the parser turns
    these keys into references and `sbs lint` checks them, and neither may import this
    module. This name stays because it is what the mission-facing code calls.
    """
    return amd_drop_table(value)


def drops_register(role, value):
    """Register one role's table. Re-registering a role REPLACES it."""
    role = str(role or "").strip()
    if not role:
        return
    if role not in _DROPS:
        _ORDER.append(role)
    _DROPS[role] = drop_table_parse(value)


def amd_drops(section):
    """Register every record in a `## [Drops]` section. The record key is the role.

    `children` comes back as a LIST from some readers and a DICT from others, so both are
    accepted rather than assuming whichever one this caller happens to hold.
    """
    if section is None:
        return {}
    kids = section.get("children") or []
    records = kids.values() if hasattr(kids, "values") else kids
    for rec in records:
        key = rec.get("key")
        data = {str(k).lower(): v for k, v in (rec.get("data") or {}).items()}
        if key and "drops" in data:
            drops_register(key, data.get("drops"))
    return dict(_DROPS)


def drops_table_for(agent_or_id):
    """The authored table for this object, or None when nothing was authored.

    None and [] are DIFFERENT and the difference is the whole feature: None means "no
    author had an opinion, do whatever you did before", [] means "this one drops nothing"
    (`Drops: none`). Collapsing them would make `Drops: none` a no-op.
    """
    obj = to_object(agent_or_id)
    if obj is None:
        return None
    for role in _ORDER:
        if obj.has_role(role):
            return _DROPS[role]
    return None


def drops_roll(agent_or_id):
    """(key, count) pairs this object's table actually yields on THIS kill - chances
    rolled, counts picked. Empty when the table is empty or absent."""
    table = drops_table_for(agent_or_id)
    if not table:
        return []
    out = []
    for entry in table:
        if entry["chance"] < 1.0 and random.random() > entry["chance"]:
            continue
        n = random.randint(entry["low"], entry["high"])
        if n > 0:
            out.append((entry["key"], n))
    return out


def drops_spawn(agent_or_id, x=None, y=None, z=None):
    """Spawn this object's authored drops at its position (or an explicit point).

    Returns the number of pickups spawned. Read the position BEFORE the caller deletes
    the object, or pass the point in - a destroyed object cannot be asked where it was.
    """
    from .items import item_spawn
    rolls = drops_roll(agent_or_id)
    if not rolls:
        return 0
    if x is None:
        obj = to_object(agent_or_id)
        if obj is None:
            return 0
        pos = obj.pos
        x, y, z = pos.x, pos.y, pos.z
    count = 0
    for key, n in rolls:
        # One pickup carrying n, not n pickups - a cache, not a litter of objects.
        item_spawn(key, x, y, z, qty=n)
        count += 1
    return count
