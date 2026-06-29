"""2.8 ``set_object_property`` -> Cosmos ``data_set`` / ``engine_object``.

2.8 property names differ from Cosmos data-set keys. This maps the high-confidence
subset (see ``docs/property_map.md`` in the arme2cosmos tool) so a port can set them
for real instead of leaving a TODO. Unmapped 2.8 properties return ``False`` so the
caller knows to handle them by hand.

Each entry is either ``("engine", attr)`` (an ``engine_object`` attribute) or
``("data", key, index)`` (a ``data_set`` slot).
"""

# 2.8 property -> Cosmos target. Only the confirmed mappings live here.
_PROP = {
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


def object_property_mapped(prop):
    """True if this 2.8 property has a confirmed Cosmos mapping."""
    return prop in _PROP


def object_property_key(prop):
    """Return ``(data_set_key, index)`` for a data-backed 2.8 property, else ``None``.

    Useful for reads (``get_object_property`` / ``if_object_property``).
    """
    m = _PROP.get(prop)
    return (m[1], m[2]) if m and m[0] == "data" else None


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
    else:
        o.data_set.set(m[1], value, m[2] if index is None else index)
    return True
