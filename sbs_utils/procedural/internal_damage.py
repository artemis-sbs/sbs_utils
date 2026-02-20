from .query import to_id, to_blob, to_object, to_list, to_set
from .roles import role, add_role, remove_role, all_roles,has_role
from .links import link,unlink
from .inventory import get_inventory_value, set_inventory_value
from .grid import grid_objects, grid_objects_at, grid_closest, grid_get_grid_data, grid_get_item_theme_data, grid_get_grid_current_theme
from .spawn import grid_spawn
from .comms import comms_broadcast
from .settings import settings_get_defaults
from .prefab import prefab_spawn

from .space_objects import get_pos
from .signal import signal_emit
from ..helpers import FrameContext
from ..agent import Agent
from ..fs import is_dev_build

import random


_MAX_HP = 6
def grid_set_max_hp(max_hp):
    global _MAX_HP
    _MAX_HP = max_hp

def grid_get_max_hp():
    global _MAX_HP
    return _MAX_HP

"""
Future use hero Damcon name

Anushka
Brickwell
Cowbell
Fergus
Helga
Jenkins
Lumpy
Moose
Pliskin
Wally
"""


def grid_rebuild_grid_objects(id_or_obj, grid_data=None):
    SBS = FrameContext.context.sbs
    if grid_data is None:
        grid_data = grid_get_grid_data()

    ship_id = to_id(id_or_obj)
    so = to_object(ship_id)
    if so is None: return 
    blob = to_blob(ship_id)
    if blob is None: return

    ship_grid  = grid_data.get(so.art_id)
    if ship_grid is None: return
    internal_items = ship_grid.get("grid_objects")
    if internal_items is None: return
    theme = grid_get_grid_current_theme()


    #
    # Setup theme
    #
    blob.set("internal_color_ship_sillouette", theme["colors"]["silhouette"],0)
    blob.set("internal_color_ship_lines", theme["colors"]["lines"],0)
    blob.set("internal_color_ship_nodes", theme["colors"]["nodes"],0)


    # Delete all grid objects
    items =grid_objects(ship_id)
    for k in items:
        # delete by id
        SBS.delete_grid_object(ship_id, k)
        Agent.remove_id(k)


    #
    # Got data build grid objects
    #
    i=0 # used to create unique tag
    sensors = 0 # used to calculate max damage
    engines = 0
    weapons = 0
    shields = 0
    for g in internal_items:
        loc_x = int(g["x"])
        loc_y = int(g["y"])
        coords = f"{loc_x},{loc_y}"
        name_tag = f"{g['name']}:{coords}"

        item_theme_data = grid_get_item_theme_data(g["roles"])

        color = item_theme_data.color
        icon = item_theme_data.icon
        scale = item_theme_data.scale
        r = "#,"+g["roles"]
        go =  grid_spawn(ship_id,  name_tag, name_tag, loc_x, loc_y, icon, color, r)
        if go is None: return
        #
        go.engine_object.layer = 0
        go.blob.set("icon_scale", scale/2, 0)
        # save color so it cn be restored
        set_inventory_value(go.id, "color", color)
        set_inventory_value(go.id, "icon_index", icon)
        set_inventory_value(go.id, "icon_scale", scale)
        # set_inventory_value(go.id, "simple_icon_index", 12 for system, 97 for room)

        #
        # Add link so query can find this relationship
        #       e.g. query to find engine grid objects on a ship
        #       linked_to(player_id, "grid_objects") & role("engine")
        #
        link(so, "grid_objects",go)
        add_role(go, "__undamaged__")
        i+=1

        #
        # Update max damage counts
        #
        roles = g["roles"].lower()
        if "sensor" in roles:
            sensors += 1
        if "engine" in roles:
            engines += 1
        if "shield" in roles:
            shields += 1
        if "weapon" in roles:
            weapons += 1

    blob.set('system_max_damage', weapons, SBS.SHPSYS.WEAPONS)
    blob.set('system_max_damage', engines, SBS.SHPSYS.ENGINES)
    blob.set('system_max_damage', sensors, SBS.SHPSYS.SENSORS)
    blob.set('system_max_damage', shields, SBS.SHPSYS.SHIELDS)
    blob.set('system_damage', 0, SBS.SHPSYS.WEAPONS)
    blob.set('system_damage', 0, SBS.SHPSYS.ENGINES)
    blob.set('system_damage', 0, SBS.SHPSYS.SENSORS)
    blob.set('system_damage', 0, SBS.SHPSYS.SHIELDS)

    #
    # This is needed to reset the coefficients after an explosion
    # set_damage_coefficients is in internal_damage
    #
    set_damage_coefficients(ship_id)
    grid_restore_damcons(ship_id)

    #
    # Create marker
    #
    v = SBS.vec3(0.5,0,0.5)
    loc = SBS.find_valid_grid_point_for_vector3(ship_id, v, 5)
    if len(loc)==0:
        return
    loc_x = loc[0]
    loc_y = loc[1]
    ship = ship_id & 0xFFFFFFFF
    marker_tag = f"marker:{ship}"
    # marker is named hallway
    # 23 flag, 101-filled square, 111
    marker_go = grid_spawn(ship_id, "marker", marker_tag, int(loc_x),int(loc_y), 101, "#9994", "#,marker") 
    marker_go.blob.set("icon_scale",1.5,0)
    marker_go.engine_object.layer = 6
    marker_go_id =  to_id(marker_go)
    set_inventory_value(ship_id, "marker_id", marker_go_id)
    # Create EPAD
    v = SBS.vec3(0.5,0,0.5)
    loc = SBS.find_valid_grid_point_for_vector3(ship_id, v, 5)
    if len(loc)==0:
        return
    loc_x = loc[0]
    loc_y = loc[1]
    ship = ship_id & 0xFFFFFFFF
    epad_tag = f"epad:{ship}"
    # marker is named hallway
    # 23 flag, 101-filled square, 111
    epad_go = grid_spawn(ship_id, "EPad", epad_tag, int(loc_x),int(loc_y), 134, "#9994", "tools,epad") 
    epad_go.engine_object.layer = 0
    epad_go.blob.set("icon_scale",0.01,0)
    set_inventory_value(ship_id, "epad_id", epad_go.id)


def grid_restore_damcons(id_or_obj):
    """
    Restore all damcon teams for the specified ship to full health.
    Args:
        id_or_obj (Agent | int): The agent or id of the ship
    """
    SBS = FrameContext.context.sbs
    ship_id = to_id(id_or_obj)
    if has_role(ship_id, "cockpit"):
        return

    hm = SBS.get_hull_map(ship_id)
    if hm is None: return

    item_theme_data = grid_get_item_theme_data("damcons")
    rally_theme_data = grid_get_item_theme_data("rally_point")
    #
    # Get Colors from theme
    # 
    colors  = item_theme_data.color
    damage_colors  = item_theme_data.damage_color
    #
    #TODO: REMOVE When Grid AI is proven
    settings = settings_get_defaults()
    interns = settings.get("NEW_DAMCONS", is_dev_build())

    prefab_label = get_inventory_value(ship_id, "PREFAB_DAMCONS", "prefab_lifeform_damcons")
    #
    # Create damcons/lifeforms
    #
    color_count = len(colors)
    for i in range(3):
        # See if damcon exists
        _name = f"DC{i+1}"
        _test_go = hm.get_grid_object_by_name(_name)
        if _test_go is not None:
            _id = _test_go.unique_ID # _test_go is an object from the engine
            _blob = to_blob(_test_go.unique_ID)
            _blob.set("icon_color", colors[i%color_count], 0)
            # Hit points == MAX_HP
            set_inventory_value(_id, "HP", grid_get_max_hp() )
        else:
            v = SBS.vec3(0.5,0,0.5)
            point = SBS.find_valid_unoccupied_grid_point_for_vector3(ship_id, v, 5)
            # Allow it to spawn somewhere
            if len(point) == 0:
                point = SBS.find_valid_grid_point_for_vector3(ship_id, v, 5)
                
            if len(point) == 0:
                break
            icon = item_theme_data.icon
            scale = item_theme_data.scale

            dc = None
            color = colors[i%color_count]
            damage_color = damage_colors[i%color_count]


            if interns:
                dc_task = prefab_spawn(prefab_label, {"ship_id": ship_id, "NAME":_name, "START_X": point[0], "START_Y": point[1], "COLOR": color, "DAMAGE_COLOR":damage_color})
                if dc_task.done():
                    dc = dc_task.result()
                if dc is not None:
                    continue
                
#region TODO: Old Damcons remove
            if not interns and dc is None:
                icon = 2
                color = colors[i%color_count]
                dc = grid_spawn(ship_id, _name, _name, point[0],point[1],icon, color, "crew,damcons,lifeform")
                #
                # Create idle/rally point
                #
                _id = to_id(dc)
                _go = to_object(dc)
                marker_tag = f"{_go.name} rally point"
                
                icon =  rally_theme_data.icon
                rally_scale = rally_theme_data.scale

                idle_marker = grid_spawn(ship_id, marker_tag, marker_tag, point[0],point[1], icon, color, "#,rally_point") 
                _blob = to_blob(idle_marker)
                _blob.set("icon_scale", rally_scale, 0)
                set_inventory_value(_id, "idle_marker", to_id(idle_marker))
#endregion


            dc.engine_object.layer = 4
            dc.blob.set("icon_scale", scale,0 )
            _id = to_id(dc)
            _go = to_object(dc)
            set_inventory_value(_id, "color", colors[i%color_count])
            set_inventory_value(_id, "damage_color", damage_colors[i%color_count])
            set_inventory_value(_id, "idle_pos", (point[0], point[1]) )
            # Hit points == MAX_HP
            set_inventory_value(_id, "HP", grid_get_max_hp() )
            
def grid_apply_system_damage(id_or_obj):
    """
    Damage a random system node on the specified ship.
    Args:
        id_or_obj (Agent | int): The agent or id of the specified ship.
    """
    SBS = FrameContext.context.sbs

    ship_id = to_id(id_or_obj)
    if has_role(ship_id, "exploded"):
        return
    blob = to_blob(ship_id)

    undamaged_grid_objects = grid_objects(ship_id) & role("__undamaged__")
    damaged_grid_objects = grid_objects(ship_id) & role("__damaged__")
    the_roles =  ["weapon", "engine", "sensor", "shield"]


    for x in range(SBS.SHPSYS.MAX):
        # system_damaged = damaged_grid_objects & role(the_roles[x])
        system_damage = damaged_grid_objects & role(the_roles[x])
        cur = len(system_damage)
        blob.set('system_damage',cur, x)

    #should explode if len(undamaged_grid_objects)==0

    undamaged = undamaged_grid_objects & (role("weapon") | role("sensor") | role("shield") | role("engine")) 
    should_explode = len(undamaged) == 0
    set_damage_coefficients(ship_id)

    if should_explode:
        explode_player_ship(ship_id)


        # def _delete_ship(t):
        #     if get_shared_inventory_value("GAME_ENDED", False):
        #         return
        #     for cid in linked_to(ship_id, "consoles") -  role("mainscreen"):
        #         gui_reroute_client(cid, "show_hangar")

        #     so = to_object(t.ship_id)
        #     if so is not None:
        #         sbs.delete_object(t.ship_id)

        # t = TickDispatcher.do_once(_delete_ship, 3)
        # t.ship_id = ship_id



        # respawn_seconds = get_inventory_value(ship_id, "respawn_time", None)
        # if respawn_seconds is not None:
        #     def _do_respawn(t):
        #         respawn_player_ship(t.ship_id)    
        #         grid_rebuild_grid_objects(t.ship_id)

        #     t = TickDispatcher.do_once(_do_respawn, respawn_seconds)
        #     t.ship_id = ship_id

    return should_explode

def explode_player_ship(id_or_obj):
    """
    The specified ship will be destroyed, but not immediately. This will trigger the `player_ship_destroyed` signal, which will allow things to happen prior to the ship being deleted.
    Args:
        id_or_obj (Agent | int): The agent or id of the ship.
    """
    ship_id = to_id(id_or_obj)
    if has_role(ship_id, "exploded"):
        return
    blob = to_blob(ship_id)
    so = to_object(ship_id)
    
    pos = get_pos(ship_id)
    # if pos:
    #     sbs.create_transient(1, 0, ship_id, 0, 0, pos.x, pos.y, pos.z, "")  
    #
    # Need to replace transient

    add_role(ship_id, "exploded")
    
    art_id = so.art_id
    set_inventory_value(ship_id, "art_id", art_id)
    so.set_art_id("invisible")
    # Reset the systems to no damage
    for sys in range(4):
        blob.set('system_damage', 0, sys)
    # Send Signal that the ship has been destroyed
    signal_emit("player_ship_destroyed", {"DESTROYED_ID": ship_id})


def respawn_player_ship(id_or_obj):
    """
    Cause the specified player ship to respawn after 'destruction'.
    Args:
        id_or_obj (Agent | int): The agent or id of the player ship.
    """
    ship_id = to_id(id_or_obj)
    art_id = get_inventory_value(ship_id, "art_id")
    so = to_object(ship_id)
    engine_obj = so.space_object()
    FrameContext.context.sim.reposition_space_object(engine_obj, so.spawn_pos.x, so.spawn_pos.y, so.spawn_pos.z)
    so.set_art_id(art_id)
    remove_role(ship_id, "exploded")


def grid_damage_hallway(id_or_obj, loc_x, loc_y, damage_color):
    """
    Damage a grid location that is not already a grid object.
    Args:
        id_or_obj (Agent | int): The agent or id of the ship.
        loc_x (int): The x position of the hallway
        loc_y (int): The y position of the hallway
        damage_color (str): The color that should be applied to the grid object icon.
    """
    ship_id = to_id(id_or_obj)
    icon = 45 #fire   # 113 - Door

    name_tag = f"hallway:{loc_x},{loc_y}"
    dam_go = grid_spawn(ship_id, name_tag, name_tag, loc_x,loc_y, icon, damage_color, "#,hallway,__damaged__") 
    link(ship_id, "damage", to_id(dam_go))


def set_damage_coefficients(id_or_obj):
    """
    Update the damage coefficients of the ship based on the number of damaged nodes for each system.
    Assumes the standard system roles.
    Args:
        id_or_obj (Agent | int): The agent or id of the ship.
    """
    # TODO: Update this to use a more robust system of determining what systems exist and can be damaged.
    ship_id = to_id(id_or_obj)
    blob = to_blob(ship_id)
    if blob is None:
        return

    ship_gos = grid_objects(ship_id)
    # This ship's undamaged
    undamaged = ship_gos & role("__undamaged__")
    # This ships damaged
    damaged = ship_gos & role("__damaged__")
    #
    # get all eight systems damaged and undamaged
    #
    # arrays, Beam, Tube, Shield
    systems = [
        ("beam", "all_beam_damage_coeff",0), 
        ("torpedo", "all_tube_damage_coeff",0), 
        ("impulse", "impulse_damage_coeff",0), 
        ("warp", "warp_damage_coeff",0), 
        ("maneuver", "turn_damage_coeff",0),
        ("sensors", "sensor_damage_coeff",0),
        ("shield,fwd", "shield_damage_coeff",0), 
        ("shield,aft", "shield_damage_coeff",1)
        ]


    for system in systems:
        sys_role = system[0]
        _blob_name = system[1]
        _idx = system[2]

        _undam = undamaged & all_roles(sys_role)
        _dam = damaged & all_roles(sys_role)
        _total = max(1, len(_dam)+len(_undam))
        if (len(_undam) + len(_dam)) == 0:
            _coef = 1.0
        else:
            _coef = len(_undam) / _total
        # do print(f"damage {_coef} {_blob_name}")
        blob.set(_blob_name, _coef, _idx)

def grid_damage_grid_object(ship_id, grid_id, damage_color):
    """
    Damage the specified grid object associated with the specified ship, and give it a color.
    Args:
        ship_id (Agent | int): The agent or id of the ship
        grid_id (Agent | int): The agent or id of the grid object
        damage_color (str): The color of the damage grid object
    """
    # Note that ship_id and grid_id CAN be Agents; the functions that use these values convert them as needed.
    if has_role(grid_id, "tools"):
        return
    if has_role(grid_id, "marker"):
        return
    blob = to_blob(grid_id)
    blob.set("icon_color", damage_color, 0)
    link(ship_id, "damage", grid_id) 
    add_role(grid_id, "__damaged__")
    remove_role(grid_id, "__undamaged__")

# def grid_mark_repaired_grid_object(ship_id, grid_id, repair_color):
#     blob = to_blob(grid_id)
#     blob.set("icon_color", repair_color, 0)
#     unlink(ship_id, "damage", grid_id) 
#     remove_role(grid_id, "__damaged__")
#     add_role(grid_id, "__undamaged__")

    


def convert_system_to_string(the_system):
    """
    Convert the SBS.SHIPSYS enum value or string to a string.
    Args:
        the_system (SYS.SHIPSYSTEM | string): The enum value or string
    Returns:
        str: The string representation of the system, e.g. `weapon`.
    """
    SBS = FrameContext.context.sbs
    if isinstance(the_system, str):
        return the_system
    elif isinstance(the_system, SBS.SHPSYS):
        the_system = the_system.value
    
    the_roles =  ["weapon", "engine", "sensor", "shield"]
    hit_system = int(the_system)
    return the_roles[hit_system]

    
    

def grid_damage_system(id_or_obj, the_system=None):
    """ grid_damage_system

    Damage a system using the grid objects of the ship
    Args:
        id_or_obj (Agent | int | CloseData | SpawnData): the ship to damage
        the_system (SBS.SHIPSYS | int | str | None, optional): The system to damage, None picks random
    Returns:
        bool: True if the system is damaged, otherwise False
    """
    ship_id = to_id(id_or_obj)
    if has_role(ship_id, "exploded"):
        return False
    if the_system is None:
        the_system = convert_system_to_string(random.randrange(4))

    the_system = convert_system_to_string(the_system)
    hittable = to_list(grid_objects(ship_id) & role("__undamaged__") & role(the_system))
    if len(hittable) == 0:
        return False
    go_id = random.choice(hittable)
    # TODO: Maybe this should be inventory like the damcons
    damage_color = grid_get_grid_current_theme()["damage_colors"]["default"]

    grid_damage_grid_object(ship_id, go_id, damage_color)
    add_role(go_id, "__damaged__")
    grid_apply_system_damage(ship_id)
    return True


###################
def grid_damage_pos(id_or_obj, loc_x, loc_y):
    """
    Damage the ship's grid at the specified coordinates.
    Args:
        id_or_obj (Agent | int): The agent or id of the ship
        loc_x (int): The x coordinate of the grid position
        loc_y (int): The y coordinate of the grid position
    """
    ship_id = to_id(id_or_obj)
    go_set_at_loc = grid_objects_at(ship_id, loc_x, loc_y)
    #
    # If empty hallway hit, Drop damage down 
    #
    if len(go_set_at_loc) == 0:
        grid_damage_hallway(ship_id, loc_x,loc_y)
        return




def grid_take_internal_damage_at(id_or_obj, source_point, system_hit=None, damage_amount=None):
    """
    Damage the ship's grid at the specified point in 3D.
    Args:
        id_or_obj (Agent | int): The agent or id
        source_point (Vec3): The point at which damage should be applied.
        system_hit (SBS.SHIPSYS | int | str | None, optional): The system to which damage should be applied. Unused.
        damage_amount (int | None, optional): The damage to apply. Unused.
    """
    SBS = FrameContext.context.sbs
    ship_id = to_id(id_or_obj)
    # Make sure you don't take further damage
    if has_role(ship_id, "exploded"): return
    # Host is no more 
    hm = SBS.get_hull_map(ship_id)
    if hm is None: return

    loc_x = 0
    loc_y = 0
    damage_radius = int(((hm.w+hm.h) / 2 / 2) + 2) # Average halved + 2

    loc = SBS.find_valid_grid_point_for_vector3(ship_id, source_point, damage_radius)
    # Nothing to do END
    if len(loc)== 0: return
    #
    # pick a random system 
    # this can get overridden by finding a grid object in the hit location
    #
    blob = to_blob(ship_id)

    loc_x = loc[0]
    loc_y = loc[1]
    # do print(f"{loc_x} {loc_y} {EVENT.source_point.x} {EVENT.source_point.y} {EVENT.source_point.z}")
    go_set_at_loc = grid_objects_at(ship_id, loc_x, loc_y)
    #
    # If empty hallway hit, Drop damage down 
    #
    damage_color = grid_get_grid_current_theme()["damage_colors"]["default"]
    if len(go_set_at_loc) == 0:

        grid_damage_hallway(ship_id, loc_x, loc_y, damage_color)
        return grid_apply_system_damage(ship_id)
#
    # there are things here
    #
    #
    # Try several times to apply damage
    # if damage is applied just do it once
    #
    num_retry = 3
    injured_dc = set()
    for retry in range(num_retry):
        already_damaged = False
        
        for go_id in go_set_at_loc:
            #
            # track hit lifeforms
            #
            if has_role(go_id, "marker"): continue
            if has_role(go_id, "tools"): continue
            if has_role(go_id, "rally_point"): continue
            if has_role(go_id, "lifeform"):
                injured_dc.add(go_id)
                # don't mark lifeforms as damaged
                continue

            if has_role(go_id, "__damaged__"):
                already_damaged = True
                continue

            go = to_object(go_id)
            blob = to_blob(go_id)
            blob.set("icon_color", damage_color, 0)
            link(ship_id, "damage", go_id) 
            add_role(go_id, "__damaged__")
            remove_role(go_id, "__undamaged__")
        #
        # I all damage was new, we are done
        #
        if not already_damaged: break
        
        #
        # otherwise
        # find closest undamaged thing, not hallways
        # Using it's x,y as the new place to try
        #
        a_go = next(iter(go_set_at_loc))
        undam = grid_closest(a_go, role("__undamaged__") & grid_objects(ship_id))
        #
        # Just need one item to get x,y
        #
        if undam is not None:
            go_blob = to_blob(undam)
            loc_x = int(go_blob.get("curx", 0))
            loc_y = int(go_blob.get("cury", 0))

            #do print(f"{loc_x} {loc_y}")
            go_set_at_loc = grid_objects_at(ship_id, loc_x, loc_y)


    for d in injured_dc:
        hp =  get_inventory_value(d, "HP", 0)
        hp -= 1
        set_inventory_value(d, "HP", hp)
        go = to_object(d)
        blob = to_blob(d)
        dc_damage_color = get_inventory_value(d, "damage_color")
        dc_damage_color = damage_color if damage_color else damage_color

        blob.set("icon_color", dc_damage_color, 0)
        if hp <= 0:
            SBS.delete_grid_object(go.host_id, d)
            comms_broadcast(ship_id, f"{go.name} has perished", dc_damage_color)
            if go is not None:
                go.destroyed()
        else:
            comms_broadcast(ship_id, f"{go.name} has been hurt hp={hp}","yellow")


    return grid_apply_system_damage(ship_id)


def grid_repair_system_damage(id_or_obj, the_system=None):
    """
    Repair damage for the specified system. If None, a random node is repaired.
    Args:
        id_or_obj (Agent | int): The agent or id.
        the_system (SBS.SHIPSYS | str | int | None, optional): The system to repair.
    """
    ship_id = to_id(id_or_obj)
    
    if the_system is None:
        the_system = convert_system_to_string(random.randrange(4))

    the_system = convert_system_to_string(the_system)
    fixable = to_list(grid_objects(ship_id) & role("__damaged__") & role(the_system))
    if len(fixable) == 0:
        return False
    go_id = random.choice(fixable)
    grid_repair_grid_objects(ship_id, go_id)
    grid_apply_system_damage(ship_id)
    return True



def grid_repair_grid_objects(player_ship, id_or_set, who_repaired=None):
    """
    Repair the provided grid objects.
    Note: More details on the use of this function required.
    Args:
        player_ship (Agent | int): The agent or id of the ship
        id_or_set (Agent | int | set[Agent | int]): The grid object or set of grid objects to repair
        who_repaired (Agent | int): The agent (damcon team) that did the work.
    """
    SBS = FrameContext.context.sbs
    at_point = to_set(id_or_set)
    damcon_repairer = to_id(who_repaired)
    player_ship_id = to_id(player_ship)

    something_healed = False
    for id in at_point:
        #
        # Remove work order, even if no longer damaged
        # 
        if damcon_repairer is not None:
            unlink(damcon_repairer, "work-order", id)

        # Only deal with Damage
        if not has_role(id, "__damaged__"): continue 
        if has_role(id, "damcons"): continue
        go = to_object(id)
        if go is None: continue


        # Have to unlink this so it is no longer seen
        unlink(go.host_id, "damage", id)
        remove_role(id, "__damaged__")
        add_role(id, "__undamaged__")


        # If hallway damage delete
        # else restore color and repair system
        system_heal = None
        if has_role(id, "hallway"):
            SBS.delete_grid_object(go.host_id, id)
            go.destroyed()
        #
        # This is a room, fix
        #
        else:
            blob = to_blob(id)
            color = get_inventory_value(id, "color")

            if color is None:
                color = "purple"
            blob.set("icon_color", color, 0)
            if has_role(id, "sensor"):
                system_heal = SBS.SHPSYS.SENSORS
            elif has_role(id, "weapon"):
                system_heal = SBS.SHPSYS.WEAPONS
            elif has_role(id, "engine"):
                system_heal = SBS.SHPSYS.ENGINES
            elif has_role(id, "shield"):
                system_heal = SBS.SHPSYS.SHIELDS
        #
        # 
        #
        if system_heal is not None:
            ship_blob = to_blob(player_ship_id)
            something_healed = True
        
            current = ship_blob.get('system_damage', system_heal)
            if current >0:
                ship_blob.set('system_damage', current-1 , system_heal)
            else:
                ship_blob.set('system_damage', 0 ,  system_heal)

    #
    # Update the damage coefficients if a system was healed
    # Label is in internal_damage, Expects DAMAGE_ORIGIN_ID
    #

    if something_healed:
        set_damage_coefficients(player_ship_id )
    
def grid_count_grid_data(ship_key, role, default=0):
    """
    Count the amount of grid items with the give role(from the json data)
    for the given ship.
    Args:
        ship_key (str): The ship key to use to find the grid items
        role (str): A comma-separated list of roles for which to check
        default (int, optional): If the data for the grid key specified is not found, this number will be returned. Default is 0.
    """
    grid_data = grid_get_grid_data()
    ship_data = grid_data.get(ship_key)
    if ship_data is None:
        return default
    
    internal_items = ship_data.get("grid_objects")
    if internal_items is None:
        return default
    count = 0
    for item in internal_items:
        role_set = set([x.strip() for x in item["roles"].split(',')])
        if role in role_set:
            count += 1
    
    return count
