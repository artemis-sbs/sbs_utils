from sbs_utils import scatter
import random
from sbs_utils.procedural.ship_data import plain_asteroid_keys
from sbs_utils.procedural.spawn import terrain_spawn, npc_spawn
from sbs_utils.procedural.query import to_id, to_object, to_data_set
from sbs_utils.procedural.inventory import set_inventory_value

from sbs_utils.scatter import ring as scatter_ring
from sbs_utils.faces import set_face, random_terran
from sbs_utils.vec import Vec3
from sbs_utils.procedural.prefab import prefab_spawn

import math

NEB_MAX_SIZE = 3000

def terrain_spawn_stations(DIFFICULTY, lethal_value, x_min=-32500, x_max=32500, center=None, min_num=0):
    """
    Spawn stations throughout the map, weighted by the game difficutly, and wrap minefields around them as applicable based on the lethal terrain value.
    Args:
        DIFFICULTY (int): The game difficulty.
        lethal_value (int): The lethal terrain value.
        x_min (int, optional): The minimum X value on the map
        x_max (int, optional): The maximum X value on the map
        center (Vec3, optional): The center of the map. Default is None (0,0,0).
    """
    if center is None:
        center = Vec3(0,0,0)

    _station_weights  = {"starbase_industry": 5,"starbase_command": 3,"starbase_civil": 1,"starbase_science": 1}
    # make the list of stations we will create -----------------------------------------------
    station_type_list = []
    total_weight = (12-DIFFICULTY) *2

    while total_weight > 0:
        station_type = random.choice(list(_station_weights.keys()))
        station_weight = _station_weights[station_type]

        # Force big stations first
        if total_weight > 8 and station_weight==1:
            continue

        total_weight -= station_weight
        station_type_list.append(station_type)
    
    while len(station_type_list) < min_num:
        station_type_list.append("starbase_civil")

    pos = Vec3(center)
    startZ = -50000
    num_stations = len(station_type_list)
    station_step = 100000/num_stations

    
    # for each station
    for index in range(num_stations):
        stat_type = station_type_list[index]
        pos.x = center.x + random.uniform(x_min, x_max)
        pos.y = center.y + random.random()*500-250
        pos.z = center.z + startZ #+ random.random()*station_step/3  -   station_step/6
    #    _spawned_pos.append(pos)
        startZ += station_step

        #make the station ----------------------------------
        name = f"DS {index+1}"
        s_roles = f"tsn, station"
        station_object = npc_spawn(*pos, name, s_roles, stat_type, "behav_station")
        ds = to_id(station_object)
        set_face(ds, random_terran(civilian=True))

        # wrap a minefield around the station ----------------------------
        if lethal_value > 0:
            startAngle = random.randrange(0,359)
            angle = random.randrange(90,170)
            angle = 170
            endAngle = startAngle + angle
            
            
            depth = 1   #random.randrange(2,3)
            width = int(5 * lethal_value)
            widthArray = [int(angle / 5.0)]
            inner = random.randrange(1200,1500)
            cluster_spawn_points = scatter_ring(width, depth, pos.x,pos.y,pos.z, inner, inner, startAngle, endAngle)
            
            # Random type, but same for cluster
            for v2 in cluster_spawn_points:
                #keep value between -500 and 500??
                mine_obj = terrain_spawn( v2.x, v2.y + random.randrange(-300,300), v2.z,None, "#,mine", "danger_1a", "behav_mine")
                mine_obj.blob.set("damage_done", 5)
                mine_obj.blob.set("blast_radius", 1000)
                mine_obj.engine_object.blink_state = -5


# make a few random clusters of Asteroids
def terrain_asteroid_clusters(terrain_value, center=None, selectable=False):
    """
    Spawn clusters of asteroids around the map.
    Args:
        terrain_value (int): Scales how many asteroid clusters are spawned, and how many asteroids per cluster.
        center (Vec3, optional): The center of the map. Default is None (0,0,0).
        selectable (bool, optional): Should the asteroids be selectable on a 2D radar widget? Default is False.
    """
    if center is None:
        center = Vec3(0,0,0)

    #t_min = terrain_value * 7
    #t_max = t_min * 3
    t_max_pick = [0,8,10, 12,16]
    t_min = t_max_pick[terrain_value]
    t_max = t_min * 2
    spawn_points = scatter.box(random.randint(t_min,t_max), center.x, center.y, center.z, 100000, 1000, 100000, centered=True)
    for v in spawn_points:
        
        amount = random.randint(t_min,t_max)//2
        size = amount *3
        # the more you have give a bit more space
        ax = random.randint(-20,20)
        ay = random.randint(-150,150)
        az = random.randint(-20,20)
        #cluster_spawn_points = scatter_box(amount, v.x, 0,v.z, amount*50, amount*20,amount*200, centered=True, ax, ay, az )
        cluster_spawn_points = scatter.box(amount,  v.x, 0,v.z, size*150, size*50,size*200, True, 0, ay, 0 )

        terrain_spawn_asteroid_scatter(cluster_spawn_points, 1000, selectable=selectable)

def terrain_spawn_asteroid_box(x,y,z, size_x=10000,size_z=None, density_scale=1.0, density=1, height=1000, selectable=False, is_tiled=False):
    """
    Spawn asteroid clusters within the box. Density is per 1000.
    Args:
        x (int): The x position of the starting point.
        y (int): The y position of the starting point. (Not currently used)
        z (int): The z position of the starting point.
        size_x (int, optional): The size of the box in the x dimension. Default is 10,000.
        size_z (int, optional): The size of the box in the z dimension. Default is None, in which case it is equal to size_x.
        density_scale (float, optional): The density of the asteroid clusters. Default is 1.0.
        density (int, optional): The density of the asteroid spawns. Default is 1.
        height (int, optional): The size of the box in the y dimension. Default is 1000.
        selectable (bool, optional): Should the spawned asteroids be selectable on the 2D radar widgets? Default is False.
        is_tiled (bool, optional): Is the spawn position data tiled (using the map editor)? Default is False.
    """
    if density_scale==0:
        return
    if size_z is None:
        size_z = size_x
    
    grid = size_x/1000 + abs(size_z/1000)
    grid = grid * density_scale
    amount = max(int(grid * density), 1)
    amount = random.randrange(amount//2, amount)

    # Tiled send top, left and z are flipped
    if is_tiled:
        cz = z+size_z/2
        # Map editor send size_z as negative for flipping
        if size_z <0:
            cz = (z-size_z/2)
            size_z = -size_z
        
        cluster_spawn_points = scatter.box(amount,  x + size_x/2, -height/2, cz, size_x, height/2, size_z, True, 0, 0, 0 )
    else:
        cluster_spawn_points = scatter.box(amount,  x, -height/2, z, size_x, height/2, size_z, True, 0, 0, 0 )
    terrain_spawn_asteroid_scatter(cluster_spawn_points, height, selectable=selectable)


def terrain_spawn_asteroid_sphere(x,y,z, radius=10000, density_scale=1.0, density=1, height=1000, selectable=False):
    """
    Spawn asteroid clusters within the sphere. Density is per 1000.
    Args:
        x (int): The x position of the starting point.
        y (int): The y position of the starting point.
        z (int): The z position of the starting point.
        radius (int, optional): The radius of the spawn sphere. Default is 10,000.
        density_scale (float, optional): The density of the asteroid clusters. Default is 1.0.
        density (int, optional): The density of the asteroid spawns. Default is 1.
        height (int, optional): The size of the box in the y dimension. Default is 1000.
        selectable (bool, optional): Should the spawned asteroids be selectable on the 2D radar widgets? Default is False.
    """
    if density_scale==0:
        return
    grid = radius/1000
    grid = grid * density_scale
    amount = max(int(grid * density), 1)
    amount = random.randrange(amount//2, amount)
    
    cluster_spawn_points = scatter.sphere(amount,  x, y,z, radius)
    terrain_spawn_asteroid_scatter(cluster_spawn_points, height, selectable=selectable)

def terrain_spawn_asteroid_points(x,y,z, points, radius=10000, density_scale=1.0, density=1, height=1000, selectable=False):
    """
    Spawn asteroid clusters within the box. Density is per 1000.
    Args:
        x (int): The x position of the starting point.
        y (int): The y position of the starting point. Not currently used.
        z (int): The z position of the starting point.
        radius (int, optional): The size of the box in the x dimension. Default is 10,000. Not currently used.
        density_scale (float, optional): The density of the asteroid clusters. Default is 1.0.
        density (int, optional): The density of the asteroid spawns. Default is 1.
        height (int, optional): The size of the box in the y dimension. Default is 1000.
        selectable (bool, optional): Should the spawned asteroids be selectable on the 2D radar widgets? Default is False.
    """
    if density_scale==0:
        return
    if density==0:
        return
    if len(points)==0:
        return
    # grid = radius/1000
    # grid = grid + grid

    # amount = max(int(grid * density), 1)
    # amount = random.randrange(int(amount* density_scale))
    my_iter = iter(points)
    pt1 = next(my_iter)
    
    # Z- was already flipped by map export
    for pt2 in my_iter:
        x1 = pt1[0] + x
        y1 = height
        z1 = (z + pt1[1])

        x2 = pt2[0] + x
        y2 = height
        z2 = (z + pt2[1])
        pt1 = pt2

        length = math.sqrt((x2-x1)**2 + (z2-z1)**2)
        length = 20

        amount = random.randrange(int(length* density_scale))
        amount = length

        #print(f"POLYLINE {x1},{z1} {x2},{z2} {length} {amount}" )

        cluster_spawn_points = scatter.line(amount, x1, y1, z1, x2,y2, z2, True)
        terrain_spawn_asteroid_scatter(cluster_spawn_points, height, selectable=selectable)

def terrain_spawn_asteroid_scatter(cluster_spawn_points, height, selectable=False):
    """
    Spawn asteroids at the specified spawn points.
    Args:
        cluster_spawn_points (Iterable[Vec3]): The spawn points.
        height (int): Scales where the asteroids should spawn in the y dimension.
        selectable (bool, optional): Should the asteroids be selectable on the 2D radar widget? Default is False.
    """
    asteroid_types = plain_asteroid_keys()
    a_type = random.choice(asteroid_types)

    er = 1
    scatter_pass = 0
    for v2 in cluster_spawn_points:
        #v2.y = v2.y % (height/2)
        v2.y = random.random() * (height/2)-(height/4)
        a_type = random.choice(asteroid_types)

        asteroid = terrain_spawn(v2.x, v2.y, v2.z,None, "#,asteroid", a_type, "behav_asteroid")
        asteroid.engine_object.steer_yaw = random.uniform(0.0001, 0.003)
        asteroid.engine_object.steer_pitch = -random.uniform(0.0001, 0.003)
        asteroid.engine_object.steer_roll = random.uniform(0.0001, 0.003)
        asteroid.blob.set("unselectable", 0 if selectable else 1)

        # Some big, some small
        # big are more spherical
        # 1 in 4 big
        er = asteroid.engine_object.exclusion_radius
        moons = False
        if scatter_pass%4 != 0:
            sx = random.uniform(7.0, 15.0)
            sy = sx + random.uniform(-1.2, 1.2)
            sz = sx + random.uniform(-1.2, 1.2)
            sm = min(sx, sy)
            sm = min(sm, sz)
            er *= sm/2
            asteroid.engine_object.exclusion_radius = er
            moons = True
        else:
            sx = random.uniform(2.5, 5)
            sy = random.uniform(2.5, 5)
            sz = random.uniform(2.5, 5)
            sm = min(sx, sy)
            sm = min(sm, sz)
            moons = random.randint(0,4)!=2
            

        scatter_pass += 1
        #er = asteroid.blob.get("exclusionradius",0)
        #er *= sm

        asteroid.blob.set("local_scale_x_coeff", sx)
        asteroid.blob.set("local_scale_y_coeff", sy)
        asteroid.blob.set("local_scale_z_coeff", sz)
        
        # Big asteroids
        if not moons:
            continue
            # #
        # else:
        #     continue

        # #
        # # Sphere od smaller asteroids
        # #
        this_amount = random.randint(4,8)
        
        little = scatter.sphere(this_amount,  v2.x, 0,v2.z, er + 50, er + 100 )
        #little = scatter.sphere(random.randint(2,6), v2.x, v2.y, v2.z, 300, 800)
        # little = scatter.sphere(random.randint(12,26), v2.x, v2.y, v2.z, 800)
        
        for v3 in little: 
            a_type = random.choice(asteroid_types)

            asteroid = terrain_spawn(v3.x, v3.y, v3.z,None, "#,asteroid", a_type, "behav_asteroid")
            asteroid.engine_object.steer_yaw = random.uniform(0.0001, 0.003)
            asteroid.engine_object.steer_pitch = -random.uniform(0.0001, 0.003)
            asteroid.engine_object.steer_roll = random.uniform(0.0001, 0.003)
            asteroid.blob.set("unselectable", 0 if selectable else 1)

            sx1 = random.uniform(0.3, 1.0)
            sy1 = random.uniform(0.3, 1.0)
            sz1 = random.uniform(0.3, 1.0)
            sm1 = max(sx, sy)
            sm1 = max(sm, sz)
            # er = asteroid.engine_object.exclusion_radius
            # er *= sm1
            asteroid.engine_object.exclusion_radius = 1
            

            asteroid.blob.set("local_scale_x_coeff", sx1)
            asteroid.blob.set("local_scale_y_coeff", sy1)
            asteroid.blob.set("local_scale_z_coeff", sz1)




def terrain_to_value(dropdown_select, default=0):
    """
    Convert a string representation of the terrain density (shown to the players) to an integer.
    Args:
        dropdown_select (str): The string representation of the terrain density.
        default (int, optional): The default integer value, if `dropdown_select` is not a valid value. Default is 0.
    Returns:
        int: The integer value that corresponds to the string. (0 - 4)
    """
    if "few" == dropdown_select:
        return 1

    if "some" == dropdown_select:
        return 2

    if "lots" == dropdown_select:
        return 3

    if "max" == dropdown_select:
        return 4
    
    if "many" == dropdown_select:
        return 4
    
    return default


def terrain_spawn_nebula_clusters(terrain_value, center=None, selectable=False):
    """
    Spawn clusters of nebulae around the map.
    Args:
        terrain_value (int): Scales how many nebulae clusters are spawned, and how many nebulae per cluster.
        center (Vec3, optional): The center of the map. Default is None (0,0,0).
        selectable (bool, optional): Should the nebulae be selectable on a 2D radar widget? Default is False.
    """
    if center is None:
        center = Vec3(0,0,0)

    t_min = terrain_value * 6
    t_max = t_min * 2
    spawn_points = scatter.box(random.randint(t_min,t_max), center.x, center.y, center.z, 100000, 1000, 100000, centered=True)
    
    for v in spawn_points:
        #cluster_spawn_points = scatter.sphere(random.randint(terrain_value*6,terrain_value*10), v.x, 0,v.z, 1000, 10000, ring=False)
        cluster_color = random.randrange(3)
        #terrain_spawn_nebula_scatter(cluster_spawn_points, 1000, cluster_color)
        # 10000 = radius 5000
        terrain_spawn_nebula_sphere(v.x,v.y, v.z, 5000,terrain_value, cluster_color=cluster_color, selectable=selectable)

def terrain_spawn_nebula_scatter(cluster_spawn_points, height, cluster_color=None, diameter=4000, density=1.0, selectable=False):
    """
    Spawn asteroids at the specified spawn points.
    Args:
        cluster_spawn_points (Iterable[Vec3]): The spawn points.
        height (int): Scales where the asteroids should spawn in the y dimension.
        cluster_color (int, optional): The color the nebulae should spawn as. Default is 0.
        * 0: purple
        * 1: red
        * 2: blue
        * 3: yellow
        diameter (int, optional): The diameter of the nebulae.
        density (float, optional): The density of the nebulae (3D view). Default is 1.0.
        selectable (bool, optional): Should the asteroids be selectable on the 2D radar widget? Default is False.
    """
    ret = []
    if cluster_color is None:
            cluster_color = random.randint(0,2)

    for v2 in cluster_spawn_points:
        # v2.y = v2.y % 500.0 Mod doesn't work like you think
        v2.y = random.random() * (height/2)-(height/4)

        # This should be a set of prefabs
        nebula = terrain_spawn(v2.x, v2.y, v2.z,None, "#, nebula", "nebula", "behav_nebula")
        
        # nebula.blob.set("local_scale_x_coeff", random.uniform(1.0, 5.5))
        # nebula.blob.set("local_scale_y_coeff", random.uniform(2.0, 5.5))
        # nebula.blob.set("local_scale_z_coeff", random.uniform(1.0, 5.5))
        nebula.blob.set("unselectable", 0 if selectable else 1)
        diameter += ((random.random()*2)-1) * diameter *0.10
        diameter = min(diameter,NEB_MAX_SIZE)
        #print(f"NEBULA {cluster_color} {density} {diameter} {in_dia}")
        #terrain_setup_nebula(nebula, diameter, density, "yellow")
        if cluster_color == 1:
            terrain_setup_nebula(nebula, diameter, density, "red")
        elif cluster_color == 2:
            terrain_setup_nebula(nebula, diameter, density, "blue")
        else:
            terrain_setup_nebula(nebula, diameter, density, "yellow")
        ret.append(nebula)
    return ret

def terrain_spawn_nebula_box(x,y,z, size_x=10000, size_z=None, density_scale=1.0, density= 1, height=1000, cluster_color=None, selectable=False, is_tiled=False):
    """
    Spawn asteroids throughout a box.
    Args:
        x (int): The X position.
        y (int): The Y position. (Not currently used).
        z (int): The Z position.
        size_x (int, optional): The width of the box in the x dimension. Default is 10,000.
        size_z (int, optional): The width of the box in the z dimension. If None, equal to `size_x`. Default is None.
        density_scale(float, optional): How dense the nebulae spawn. Default is 1.0.
        density (int, optional): The density of the nebulae (3D view). Default is 1.
        height (int): Scales where the asteroids should spawn in the y dimension.
        cluster_color (int, optional): The color the nebulae should spawn as. Default is 0.
        * 0: purple
        * 1: red
        * 2: blue
        * 3: yellow
        selectable (bool, optional): Should the asteroids be selectable on the 2D radar widget? Default is False.
        is_tiled (bool, optional): Is the spawn position data tiled (using the map editor)? Default is False.
    """
    if density_scale==0:
        return
    if size_z is None:
        size_z = size_x
    
    grid = (size_x/5000 + size_z/5000) * density_scale
    raw_amount = max(int(grid), 1)
    min_amount = max(raw_amount//2, 1)
    if raw_amount == min_amount:
        amount = raw_amount
    else:
        # if density is already 1 or 2, then randomize whether 
        # a nebula is spawned
        if raw_amount<=2 and random.randrange(0,5)==3:
            return
        amount = random.randrange(min(raw_amount, min_amount), max(raw_amount, min_amount))

    if is_tiled:
        cluster_spawn_points = scatter.box(amount,  x + size_x/2, -height/2, z+size_z/2, size_x, height/2, size_z, True, 0, 0, 0 )
    else:
        cluster_spawn_points = scatter.box(amount,  x, -height/2, z, size_x, height/2, size_z, True, 0, 0, 0 )
    return terrain_spawn_nebula_scatter(cluster_spawn_points, height, cluster_color, diameter=size_x*2, density=density, selectable=selectable)

def terrain_spawn_nebula_sphere(x,y,z, radius=10000, density_scale=1.0, density=1.0, height=1000, cluster_color=None, selectable=False):
    """
    Spawn nebula clusters within the sphere. Density is per 1000.
    Args:
        x (int): The x position of the starting point.
        y (int): The y position of the starting point.
        z (int): The z position of the starting point.
        radius (int, optional): The radius of the spawn sphere. Default is 10,000.
        density_scale (float, optional): The density of the nebulae clusters. Default is 1.0.
        density (int, optional): The density of the nebulae spawns. Default is 1.
        height (int, optional): The size of the box in the y dimension. Default is 1000.
        cluster_colors (int, optional): The color the nebulae should spawn as. Default is 0.
        * 0: purple
        * 1: red
        * 2: blue
        * 3: yellow
        selectable (bool, optional): Should the spawned nebulae be selectable on the 2D radar widgets? Default is False.
    """
    if density_scale==0:
        return
    
    grid = (radius)/2000
    grid = grid * density_scale

    raw_amount = max(int(grid * density), 1)
    min_amount = max(raw_amount//2, 1)
    if raw_amount == min_amount:
        amount = raw_amount
    else:
        # if density is already 1 or 2, then randomize whether 
        # a nebula is spawned
        if raw_amount<=2 and random.randrange(0,5)==3:
            return
        amount = random.randrange(min(raw_amount, min_amount), max(raw_amount, min_amount))
    
    dia = min(radius*2 / amount, NEB_MAX_SIZE)
    # print(f"TER SPHERE {amount} {radius} {grid} {raw_amount}")
    cluster_spawn_points = scatter.sphere(amount, x, y, z, radius)
    return terrain_spawn_nebula_scatter(cluster_spawn_points, height, cluster_color, diameter=dia, density=density, selectable=selectable)
 
            

def terrain_spawn_monsters(monster_value, center=None):
    """
    Spawn monsters based on the monster value of the game.
    Args:
        monster_value (int): Scales the numnber of monsters to spawn.
        center (Vec3): The center of the spawn area. Defaults to None (0,0,0).
    """
    if center is None:
        center = Vec3(0,0,0)

    spawn_points = scatter.box(monster_value, center.x,center.y, center.z, 75000, 1000, 75000, centered=True)
    for v in spawn_points:
        prefab_spawn("prefab_typhon_classic", None, *v.xyz)


call_signs = []
enemy_name_number = 0
call_signs.extend(range(1,100))

random.shuffle(call_signs)


def terrain_spawn_black_hole(x,y,z, gravity_radius= 1500, gravity_strength=1.0, turbulence_strength= 1.0, collision_damage=200):
    """
    Spawn a black hole.
    Args:
        x (int): The x position.
        y (int): The y position.
        z (int): The z position.
        gravity_radius (int, optional): The radius in which objects will be pulled towards the black hole. Default is 1500.
        gravity_strength (float, optional): How fast the black hole pulls objects. Default is 1.0.
        turbulence_strength (float, optional): The turbulence of the black hole. Default is 1.0.
        collision_damage (int, optional): The damage to apply to objects that fall into the black hole. Default is 200.
    """
    global enemy_name_number

    _prefix = "XEA"
    r_name = f"{random.choice(_prefix)} {str(call_signs[enemy_name_number]).zfill(2)}"
    enemy_name_number = (enemy_name_number+1)%99

    bh = to_object(terrain_spawn(x,y,z, r_name, "#,black_hole", "maelstrom", "behav_maelstrom"))
    bh.engine_object.exclusion_radius = 100 # event horizon
    blob = bh.data_set
    blob.set("gravity_radius", gravity_radius, 0)
    blob.set("gravity_strength", gravity_strength, 0)
    blob.set("turbulence_strength", turbulence_strength, 0)
    blob.set("collision_damage", collision_damage, 0)
    # Note this returns the object, not spawn data. SpawnData is deprecated 
    return bh


def terrain_spawn_black_holes(lethal_value, center=None):
    """
    Spawn black holes based on the game's lethal terrain value.
    Args:
        lethal_value (int): The integer value representing how much lethal terrain should spawn.
        center (Vec3): The center of the spawn points. Default is None (0,0,0).
    """
    if center is None:
        center = Vec3(0,0,0)

    spawn_points = scatter.box(lethal_value, center.x,center.y, center.z, 75000, 500, 75000, centered=True)
    for v in spawn_points:
        terrain_spawn_black_hole(*v.xyz, 5000, 4.0, 2.0)

def color_noise(r_min, r_max, g_min,g_max, b_min, b_max, a_min=0xff, a_max=0xff):
    r = random.randrange(r_min,r_max)
    g = random.randrange(g_min,g_max)
    b = random.randrange(b_min,b_max)
    if a_min != 0xff:
        a = random.randrange(a_min,a_max)
        return f"#{r:02x}{g:02x}{b:02x}{a:02x}"

    return f"#{r:02x}{g:02x}{b:02x}"

_neb_colors = {
    "blue": {
        "radar_color_override"  : color_noise(0,0x10, 0x40, 0x50,0x40, 0x50),    
        "absorption_red": 1.6,  
        "absorption_green": 1.3,    
        "absorption_blue": 0.01,
        "emission_red": 0.01,   
        "emission_green": 2.0,
        "emission_blue": 2.0,   
        "scattering_red": 0.0,  
        "scattering_green": 2., 
        "scattering_blue": 0.5, 
        "anisotropy": random.uniform(-0.25, 0.1),
        "base_frequency":3.5,   
        "base_amplitude": 1.87, 
        "detail_frequency": 1.3055, 
        "detail_amplitude": 0.900,
        "detail_lacunarity": 2.43,  
        "domain_warp":   random.random(),
        "swirl": random.random() * 10
    },
    "red":{
        "radar_color_override"  : color_noise(0x40, 0x50, 0,0x10, 0x40, 0x50),    
        "absorption_red": 0.11,  
        "absorption_green": 0.2,    
        "absorption_blue": 0.2,
        "emission_red": 0.11,   
        "emission_green": 0.06   ,
        "emission_blue": 0.04,   
        "scattering_red": 0.14,  
        "scattering_green": 0.01, 
        "scattering_blue": 0.01, 
        "anisotropy": random.uniform(-0.25, 0.1),
        "base_frequency":0.56,   
        "base_amplitude": 0.87, 
        "detail_frequency": 1.3055, 
        "detail_amplitude": 0.900,
        "detail_lacunarity": 2.43,  
        "domain_warp":   random.random(),
        "swirl":  random.random() * 10
    }, "yellow":{
        "radar_color_override"  : color_noise(0x40, 0x50,0x40, 0x50,0, 0x10),    
        "absorption_red": 0.1,  
        "absorption_green": 0.61,    
        "absorption_blue": 1.3,
        "emission_red": 0.8,   
        "emission_green": 2.0,
        "emission_blue": 0.6,   
        "scattering_red": 0.66,  
        "scattering_green": 0.76, 
        "scattering_blue": 0.65, 
        "anisotropy": random.uniform(-0.25, 0.1),
        "base_frequency":1.4,   
        "base_amplitude": 1.87, 
        "detail_frequency": 1.3055, 
        "detail_amplitude": 1.6,
        "detail_lacunarity": 2.43,  
        "domain_warp":   random.random(),
        "swirl":  random.random() * 10
    }
}


    

def terrain_setup_nebula(nebula, diameter=4000, density_coef=1.0, color="yellow"):
    """
    Set up the nebulae to use the default blue values.
    Args:
        nebula (set[Agent]): The nebulae
        diameter (int, optional): The diameter of the nebula.
        density_coef (float, optional): Scales the visual nebula density (3D view)
    """
    blob = to_data_set(nebula)
    
    # size = 1000 * random.uniform(1.0, 5.5)
    size = min(diameter,  NEB_MAX_SIZE)
    blob.set("size", size)
    blob.set("display_size", size)
    blob.set("effect_size", size)
    blob.set("max_throttle", 2.0)

    density = min(max(8.23 * density_coef,1.95), 20)
    blob.set("density", density)
    # 0 to 10000
    seed = random.randint(2,99999)
    blob.set("random_seed", seed)

    neb_properties = _neb_colors.get(color, _neb_colors.get("yellow"))

    for k,v in neb_properties.items():
        blob.set(k,v)
    # Need to tell the engine we changed the values
    blob.set("nebula_data_change", 1)






    