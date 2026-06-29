"""2.8 ``set_object_property`` -> Cosmos ``data_set`` / ``engine_object``.

2.8 property names differ from Cosmos data-set keys. This maps the high-confidence
subset (see ``docs/property_map.md`` in the arme2cosmos tool) so a port can set them
for real instead of leaving a TODO. Unmapped 2.8 properties return ``False`` so the
caller knows to handle them by hand.

Each entry is either ``("engine", attr)`` (an ``engine_object`` attribute) or
``("data", key, index)`` (a ``data_set`` slot).
"""

_MAP_SIZE = 100_000  # 2.8/Cosmos map size; X and Z mirror about it

# 2.8 property -> Cosmos target. Entry forms:
#   ("engine", attr)        -> engine_object.<attr>
#   ("data", key, index)    -> data_set slot
#   ("pos", axis, flip)     -> engine_object.pos.<axis>; flip=True mirrors (X/Z)
_PROP = {
    # position -> engine_object.pos with the 2.8->Cosmos coordinate flip (X,Z mirror)
    "positionX": ("pos", "x", True),
    "positionY": ("pos", "y", False),
    "positionZ": ("pos", "z", True),
    # spin rates -> engine_object steering (as the HTBM port does)
    "angleDelta": ("engine", "steer_yaw"),
    "rollDelta": ("engine", "steer_roll"),
    "pitchDelta": ("engine", "steer_pitch"),
    # scalar data_set values
    "turnRate": ("data", "turnRate", 0),
    "throttle": ("data", "throttle", 0),
    "artScale": ("data", "local_scale_coeff", 0),
    "energy": ("data", "energy", 0),
    "hasSurrendered": ("data", "surrender_flag", 0),
    "shieldsOn": ("data", "shields_raised_flag", 0),
    # shields (array: 0 = front, 1 = back)
    "shieldStateFront": ("data", "shield_val", 0),
    "shieldStateBack": ("data", "shield_val", 1),
    "shieldMaxStateFront": ("data", "shield_max_val", 0),
    "shieldMaxStateBack": ("data", "shield_max_val", 1),
    # torpedo stores / ammo counts -> <Type>_NUM
    "missileStoresNuke": ("data", "Nuke_NUM", 0),
    "missileStoresHoming": ("data", "Homing_NUM", 0),
    "missileStoresMine": ("data", "Mine_NUM", 0),
    "missileStoresEMP": ("data", "EMP_NUM", 0),
    "countNuke": ("data", "Nuke_NUM", 0),
    "countHoming": ("data", "Homing_NUM", 0),
    "countMine": ("data", "Mine_NUM", 0),
    "countEMP": ("data", "EMP_NUM", 0),
}


# 2.8 global difficulty knobs ("nonPlayer" = all NPC ships) -> per-ship Cosmos
# coefficients, applied across the fleet. Value 100 = baseline, so coeff = value/100.
_FLEET_COEFF = {
    "nonPlayerSpeed": ("__npc__", ["speed_coeff"]),
    "nonPlayerShield": ("__npc__", ["all_shield_upgrade_coeff"]),
    "nonPlayerWeapon": ("__npc__", ["all_beam_upgrade_coeff", "all_tube_upgrade_coeff"]),
    "playerShields": ("__player__", ["all_shield_upgrade_coeff"]),
    "playerWeapon": ("__player__", ["all_beam_upgrade_coeff"]),
}


def fleet_coeff_mapped(prop):
    """True if a 2.8 global difficulty property maps to a fleet coefficient."""
    return prop in _FLEET_COEFF


def set_fleet_coeff(which, value):
    """2.8 global ``nonPlayer*`` / ``player*`` difficulty -> per-ship coefficients.

    Applies ``value/100`` to the matching data_set coeff on every current NPC (or
    player) ship. NOTE: 2.8 applied these globally including to *future* spawns; this
    sets only ships that exist now -- re-apply after later spawns if needed.
    Returns the number of ships updated, or -1 if ``which`` is unknown.
    """
    spec = _FLEET_COEFF.get(which)
    if spec is None:
        return -1
    role_name, keys = spec
    coeff = value / 100.0
    from sbs_utils.procedural.roles import role
    from sbs_utils.procedural.query import to_object_list

    n = 0
    for o in to_object_list(role(role_name)):
        for k in keys:
            o.data_set.set(k, coeff, 0)
        n += 1
    return n


# 2.8 sideValue -> Cosmos side key (0=no side, 1=enemy, 2+=player side).
_SIDE_VALUE = {0: "neutral", 1: "enemy", 2: "friendly"}


def set_side_value(obj, value):
    """2.8 ``set_side_value``: reassign an object's Cosmos side.

    1 -> "enemy", 2(+) -> "friendly", 0 -> "neutral". Swaps the side role (so
    ``role(side)`` queries stay correct) and sets ``.side``; does not require the side
    to be a registered side entity.
    """
    from sbs_utils.procedural.roles import add_role, remove_role
    from sbs_utils.procedural.query import to_object, to_id

    o = to_object(obj)
    if o is None:
        return False
    v = int(value)
    new_side = _SIDE_VALUE.get(v, "friendly" if v >= 2 else "neutral")
    oid = to_id(obj)
    old = o.side
    if old and old != new_side:
        remove_role(oid, old)
    add_role(oid, new_side)
    o.side = new_side
    return True


def object_property_mapped(prop):
    """True if this 2.8 property has a confirmed Cosmos mapping."""
    return prop in _PROP


def object_property_key(prop):
    """Return ``(data_set_key, index)`` for a data-backed 2.8 property, else ``None``.

    Useful for reads (``get_object_property`` / ``if_object_property``).
    """
    m = _PROP.get(prop)
    return (m[1], m[2]) if m and m[0] == "data" else None


def set_relative_position(obj, ref, angle, distance):
    """2.8 ``set_relative_position``: move ``obj`` to a point ``distance`` from ``ref``
    at ``angle`` degrees (XZ plane).

    Approximate: ``angle`` is applied in world XZ; the 2.8 heading-relative nuance is
    left as a refinement. Returns True if both objects resolved.
    """
    import math
    from sbs_utils.procedural.query import to_object

    o, r = to_object(obj), to_object(ref)
    if o is None or r is None:
        return False
    rp = r.engine_object.pos
    rad = math.radians(float(angle))
    o.engine_object.pos.x = rp.x + float(distance) * math.sin(rad)
    o.engine_object.pos.y = rp.y
    o.engine_object.pos.z = rp.z + float(distance) * math.cos(rad)
    return True


def addto_object_property(obj, prop, value, index=None):
    """2.8 ``addto_object_property``: add ``value`` to a mapped property's current value."""
    from sbs_utils.procedural.query import to_object

    m = _PROP.get(prop)
    if m is None:
        return False
    o = to_object(obj)
    if o is None:
        return False
    if m[0] == "engine":
        setattr(o.engine_object, m[1], (getattr(o.engine_object, m[1], 0) or 0) + value)
    elif m[0] == "pos":
        # a 2.8 delta on a mirrored axis is negated in Cosmos space
        delta = -value if m[2] else value
        setattr(o.engine_object.pos, m[1], getattr(o.engine_object.pos, m[1]) + delta)
    else:
        idx = m[2] if index is None else index
        o.data_set.set(m[1], (o.data_set.get(m[1], idx) or 0) + value, idx)
    return True


def copy_object_property(src, dst, prop):
    """2.8 ``copy_object_property``: copy a mapped property from ``src`` to ``dst``."""
    from sbs_utils.procedural.query import to_object

    m = _PROP.get(prop)
    if m is None:
        return False
    so, do = to_object(src), to_object(dst)
    if so is None or do is None:
        return False
    if m[0] == "engine":
        setattr(do.engine_object, m[1], getattr(so.engine_object, m[1], 0))
    elif m[0] == "pos":
        # both already in Cosmos space -> copy the axis directly (no flip)
        setattr(do.engine_object.pos, m[1], getattr(so.engine_object.pos, m[1]))
    else:
        do.data_set.set(m[1], so.data_set.get(m[1], m[2]), m[2])
    return True


# 2.8 set_ship_text field -> Cosmos data_set scan-text key.
_SHIP_TEXT = {
    "name": "name_tag", "race": "hull_origin", "ship_class": "hull_name",
    "desc": "long_description",
}


def set_ship_text(obj, name=None, race=None, ship_class=None, desc=None,
                 scan_desc=None, hail=None):
    """2.8 ``set_ship_text``: set scan / name text on a ship.

    ``name``/``race``/``ship_class``/``desc`` map to ``name_tag`` / ``hull_origin`` /
    ``hull_name`` / ``long_description``. ``scan_desc`` and ``hail`` have no direct
    Cosmos data_set key and are ignored here (handle via science/comms if needed).
    """
    from sbs_utils.procedural.query import to_object

    o = to_object(obj)
    if o is None:
        return False
    for field, val in (("name", name), ("race", race),
                       ("ship_class", ship_class), ("desc", desc)):
        if val is not None:
            o.data_set.set(_SHIP_TEXT[field], val, 0)
    return True


# 2.8 set_special ability -> Cosmos elite_* data_set flag. Only the abilities with a
# Cosmos equivalent are here; combat abilities (Cloak, HET, Warp, Teleport, Tractor,
# ShldDrain, ShldVamp) have no elite_* key and stay unmapped.
_ELITE_ABILITY = {
    "Stealth": "elite_main_scn_invis",   # invisible to main-screen 2d radar
    "LowVis": "elite_low_vis",           # restricted 2d radar visibility
    "Drones": "elite_drone_launcher",
    "AntiMine": "elite_anti_mine",
    "AntiTorp": "elite_anti_torpedo",
}


def special_ability_mapped(ability):
    """True if a 2.8 set_special ability maps to a Cosmos elite flag."""
    return ability in _ELITE_ABILITY


def set_special(obj, ability=None, on=True):
    """2.8 ``set_special`` ability -> the matching Cosmos ``elite_*`` data_set flag.

    Returns the data_set key set, or ``None`` if the ability has no Cosmos
    equivalent. ``on=False`` (2.8 ``clear``) turns the flag off.
    """
    key = _ELITE_ABILITY.get(ability)
    if key is None:
        return None
    from sbs_utils.procedural.query import to_object
    o = to_object(obj)
    if o is not None:
        o.data_set.set(key, 1 if on else 0, 0)
    return key


def set_object_property(obj, prop, value, index=None):
    """Set a 2.8-named property on ``obj`` (id / object / a2x_create_* handle).

    Returns True if the property was mapped and set, False if it has no mapping.
    """
    from sbs_utils.procedural.query import to_object

    m = _PROP.get(prop)
    if m is None:
        return False
    o = to_object(obj)
    if o is None:
        return False
    if m[0] == "engine":
        setattr(o.engine_object, m[1], value)
    elif m[0] == "pos":
        setattr(o.engine_object.pos, m[1], (_MAP_SIZE - value) if m[2] else value)
    else:
        o.data_set.set(m[1], value, m[2] if index is None else index)
    return True
