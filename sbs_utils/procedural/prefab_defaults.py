"""The library's DEFAULT prefabs for everything AMD creates that is not a landmark.

Each is what that path spawned before prefabs were the way in - the same call, the same
roles, the same behavior - so a mission with no prefab labels of its own sees nothing
change. A mission overrides any of them with a MAST label of the same type:

    === prefab_my_pickup
    metadata: ``` yaml
    type: prefab/pickup
    ```
        obj = terrain_spawn(START_X, START_Y, START_Z, name, "#,item,crate", "container_2a", "behav_pickup")
        yield result to_id(obj)

The argument tables live in ``amd_schema.PREFAB_DEFAULTS`` (stdlib-only, so lint and the
editor read the same table); the landmark defaults are registered by amd_landmarks.
Loaded on first prefab lookup (prefab._DEFAULT_OWNERS), never by hand.
"""
from sbs_utils.procedural.prefab import prefab_register
from sbs_utils.procedural.amd_schema import PREFAB_DEFAULTS as _DECLARED


def _args(t):
    return _DECLARED[t]["args"]


def _side(data):
    """`amd/side` - an AMD side record: `side_create` with what the record says. Its
    relations are applied by sides_declare afterwards, for every side at once."""
    from sbs_utils.procedural.sides import side_create
    return side_create(data.get("key"), data.get("name"), data.get("desc"),
                       data.get("color"), data.get("icon_index"), data.get("races"))


def _lifeform(data):
    """`amd/lifeform` - a cast character: `lifeform_spawn` with its face, roles, host,
    comms path and card color. The record's scene/key/side are stamped on afterwards by
    lifeform_from_record, whatever prefab made the body."""
    from sbs_utils.procedural.lifeform import lifeform_spawn
    return lifeform_spawn(data.get("name") or data.get("NAME"), data.get("face"),
                          data.get("roles_value") or "", data.get("host_id"),
                          path=data.get("path"),
                          title_color=data.get("title_color") or "green")


def _crew(data):
    """`amd/crew` - one crew post as a body on the ground: an UNHOSTED lifeform (a hosted
    one loses ultra_beam). Jobs and skills are stamped on afterwards by the boarding code."""
    from sbs_utils.procedural.lifeform import lifeform_spawn
    return lifeform_spawn(data.get("name") or data.get("NAME"), data.get("face") or "",
                          data.get("roles_value") or "")


def _boarding_host(data):
    """`boarding/host` - the hidden ship a boarding zone's interior is cut from, parked far
    below the play plane. Hidden by DISTANCE, not art: the floor plan is read from the
    hull's silhouette, so swapping the art for "invisible" would take the floor away."""
    from sbs_utils.procedural.spawn import npc_spawn
    roles = data.get("roles_value") or ""
    return npc_spawn(data.get("START_X", 0), data.get("START_Y", 0), data.get("START_Z", 0),
                     data.get("NAME"), "#" + ("," + roles if roles else ""),
                     data.get("art") or "starbase_civil",
                     data.get("behavior") or "behav_station")


def _boarding_figure(data):
    """`grid/boarding_figure` - a character's body on an interior: one grid object."""
    from sbs_utils.procedural.spawn import grid_spawn
    return grid_spawn(data.get("site_id"), data.get("name") or data.get("NAME"), "boarding",
                      int(data.get("START_X", 0)), int(data.get("START_Y", 0)),
                      data.get("icon_index", 100), data.get("color") or "#4cf",
                      data.get("roles_value") or "boarding_figure")


def _pickup(data):
    """`pickup` - an item lying in space, as `item_spawn` always made it: a spinning,
    blinking terrain object with behav_pickup. item_spawn stamps the item key and the
    quantity on afterwards, whatever prefab made the body."""
    import random
    from sbs_utils.procedural.spawn import terrain_spawn
    key = data.get("item_key") or ""
    obj = terrain_spawn(data.get("START_X", 0), data.get("START_Y", 0), data.get("START_Z", 0),
                        data.get("name") or data.get("NAME"), f"#,item,upgrade,{key}",
                        data.get("art") or key, "behav_pickup")
    blink = data.get("blink")
    yaw = data.get("yaw")
    obj.engine_object.steer_yaw = yaw if yaw is not None else random.uniform(0.03, 0.08)
    obj.engine_object.blink_state = int(blink if blink is not None else random.randint(1, 2))
    return obj


def _npc_ship(data):
    """`npc/ship` - one ship of a side. Art from `Art:`, else a random hull that side
    flies (the role is `ship`). LM's prefab_single_ship (type npc/ship) overrides this
    with its brain, faces and fleet."""
    from sbs_utils.procedural.spawn import npc_spawn
    side = str(data.get("side_value") or "").strip()
    art = data.get("art")
    if not art and side:
        try:
            from sbs_utils.procedural.ship_data import filter_ship_data_by_side
            import random
            hulls = filter_ship_data_by_side(None, side, "ship", ret_key_only=True)
            art = random.choice(hulls) if hulls else None
        except Exception:                          # noqa: BLE001
            art = None
    if not art:
        from sbs_utils.procedural.execution import log
        log(f"npc/ship: no Art: and no hull for side '{side}' - nothing spawned",
            "prefab", "warning")
        return None
    roles = data.get("roles_value") or ""
    return npc_spawn(data.get("START_X", 0), data.get("START_Y", 0), data.get("START_Z", 0),
                     data.get("NAME") or "", (side or "#") + (", " + roles if roles else ""),
                     art, data.get("behavior") or "behav_npcship")


def _relic_piece(default_art, behavior):
    """A relic part's body: one terrain object the relic code then fits - scales,
    rotates, makes unselectable - to the part it stands for."""
    def create(data):
        from sbs_utils.procedural.spawn import terrain_spawn
        roles = data.get("roles_value") or ""
        return terrain_spawn(data.get("START_X", 0), data.get("START_Y", 0),
                             data.get("START_Z", 0), data.get("NAME") or "",
                             "#" + ("," + roles if roles else ""),
                             data.get("art") or default_art,
                             data.get("behavior") or behavior)
    return create


prefab_register("amd/side", _side, args=_args("amd/side"), display_text="Side (AMD)")
prefab_register("amd/lifeform", _lifeform, args=_args("amd/lifeform"),
                display_text="Lifeform (AMD)")
prefab_register("amd/crew", _crew, args=_args("amd/crew"), display_text="Crew body (AMD)")
prefab_register("boarding/host", _boarding_host, args=_args("boarding/host"),
                display_text="Boarding zone host")
prefab_register("grid/boarding_figure", _boarding_figure,
                args=_args("grid/boarding_figure"), display_text="Boarding figure")
prefab_register("pickup", _pickup, args=_args("pickup"), display_text="Pickup")
prefab_register("npc/ship", _npc_ship, args=_args("npc/ship"), display_text="NPC ship")
prefab_register("relic/setpiece", _relic_piece(None, "behav_asteroid"),
                args=_args("relic/setpiece"), display_text="Relic set piece")
prefab_register("relic/barrier", _relic_piece("generic-sphere", "behav_selection"),
                args=_args("relic/barrier"), display_text="Relic barrier")
prefab_register("relic/repair", _relic_piece("generic-sphere", "behav_selection"),
                args=_args("relic/repair"), display_text="Relic repair point")
prefab_register("relic/marker", _relic_piece("generic-sphere", "behav_selection"),
                args=_args("relic/marker"), display_text="Relic marker")
