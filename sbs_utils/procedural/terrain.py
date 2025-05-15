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


def terrain_spawn_stations(DIFFICULTY, lethal_value, x_min=-32500, x_max=32500, center=None, min_num=0):
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
def terrain_asteroid_clusters(terrain_value, center=None):
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

        terrain_spawn_asteroid_scatter(cluster_spawn_points, 1000)

def terrain_spawn_asteroid_box(x,y,z, size_x=10000,size_z=None, density_scale=1.0, density=1, height=1000, is_tiled=False):
    """
        density is per 1000. Defaults to 0.5.
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
    terrain_spawn_asteroid_scatter(cluster_spawn_points, height)


def terrain_spawn_asteroid_sphere(x,y,z, radius=10000, density_scale=1.0, density=1, height=1000):
    if density_scale==0:
        return
    grid = radius/1000
    grid = grid * density_scale
    amount = max(int(grid * density), 1)
    amount = random.randrange(amount//2, amount)
    
    cluster_spawn_points = scatter.sphere(amount,  x, y,z, radius)
    terrain_spawn_asteroid_scatter(cluster_spawn_points, height)

def terrain_spawn_asteroid_points(x,y,z, points, radius=10000, density_scale=1.0, density=1, height=1000):
    
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
        terrain_spawn_asteroid_scatter(cluster_spawn_points, height)

def terrain_spawn_asteroid_scatter(cluster_spawn_points, height):
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
    if "few" == dropdown_select:
        return 1

    if "some" == dropdown_select:
        return 2

    if "lots" == dropdown_select:
        return 3

    if "many" == dropdown_select:
        return 4
    return default


def terrain_spawn_nebula_clusters(terrain_value, center=None):
    if center is None:
        center = Vec3(0,0,0)

    t_min = terrain_value * 6
    t_max = t_min * 2
    spawn_points = scatter.box(random.randint(t_min,t_max), center.x, center.y, center.z, 100000, 1000, 100000, centered=True)
    
    for v in spawn_points:
        cluster_spawn_points = scatter.sphere(random.randint(terrain_value*2,terrain_value*4), v.x, 0,v.z, 1000, 10000, ring=False)
        cluster_color = random.randrange(3)
        terrain_spawn_nebula_scatter(cluster_spawn_points, 1000, cluster_color)

def terrain_spawn_nebula_scatter(cluster_spawn_points, height, cluster_color=None):
    for v2 in cluster_spawn_points:
        # v2.y = v2.y % 500.0 Mod doesn't work like you think
        v2.y = random.random() * (height/2)-(height/4)

        # This should be a set of prefabs
        nebula = terrain_spawn(v2.x, v2.y, v2.z,None, "#, nebula", "nebula", "behav_nebula")
        nebula.blob.set("local_scale_x_coeff", random.uniform(1.0, 5.5))
        nebula.blob.set("local_scale_y_coeff", random.uniform(2.0, 5.5))
        nebula.blob.set("local_scale_z_coeff", random.uniform(1.0, 5.5))

        if cluster_color is None:
            cluster_color = random.randint(0,2)

        #terrain_setup_nebula_blue(nebula)
        if cluster_color == 1:
            terrain_setup_nebula_red(nebula)
        elif cluster_color == 2:
            terrain_setup_nebula_blue(nebula)
        else:
            terrain_setup_nebula_yellow(nebula)

def terrain_spawn_nebula_box(x,y,z, size_x=10000, size_z=None, density_scale=1.0, density= 0.25, height=1000, is_tiled=False):
    if density_scale==0:
        return
    if size_z is None:
        size_z = size_x
    
    grid = size_x/100 + size_z/100
    grid = grid * density_scale

    amount = max(int(grid * density), 1)
    amount = random.randrange(amount//2, amount)

    if is_tiled:
        cluster_spawn_points = scatter.box(amount,  x + size_x/2, -height/2, z+size_z/2, size_x, height/2, size_z, True, 0, 0, 0 )
    else:
        cluster_spawn_points = scatter.box(amount,  x, -height/2, z, size_x, height/2, size_z, True, 0, 0, 0 )
    terrain_spawn_nebula_scatter(cluster_spawn_points, height)

def terrain_spawn_nebula_sphere(x,y,z, radius=10000, density_scale=1.0, density=0.25, height=1000):
    if density_scale==0:
        return
    
    grid = radius/100
    grid = grid * density_scale

    amount = max(int(grid * density), 1)
    amount = random.randrange(amount//2, amount)

    cluster_spawn_points = scatter.sphere(amount, x, y, z, radius)
    terrain_spawn_nebula_scatter(cluster_spawn_points, height)


            
            
            

def terrain_spawn_monsters(monster_value, center=None):
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
    if center is None:
        center = Vec3(0,0,0)

    spawn_points = scatter.box(lethal_value, center.x,center.y, center.z, 75000, 500, 75000, centered=True)
    for v in spawn_points:
        terrain_spawn_black_hole(*v.xyz)


def terrain_setup_nebula_red(nebula):
    blob = to_data_set(nebula)
    blob.set("radar_color_override", "#e0e")    
    #blob.set("radar_color_override", "#0ff")    
    size = 1000 * random.uniform(1.0, 5.5)
    size = 4000.0
    blob.set("size", size)
    density = 9.24
    blob.set("density", density)
    # 0 to 10000
    seed = random.randint(2,99999)
    blob.set("random_seed", seed)


    blob.set("absorption_red", 0.11)
    blob.set("absorption_green", 0.2)
    blob.set("absorption_blue", 0.2)

    blob.set("emission_red", 0.11)
    blob.set("emission_green", 0.06)
    blob.set("emission_blue", 0.04)

    blob.set("scattering_red", 0.14)
    blob.set("scattering_green", .01)
    blob.set("scattering_blue", 0.01)

    blob.set("anisotropy", random.uniform(-0.25, 0.1))

    blob.set("base_frequency",0.56)
    blob.set("base_amplitude", 0.87)
    blob.set("detail_frequency", 1.3055)
    blob.set("detail_amplitude", 0.900299)
    blob.set("detail_lacunarity", 2.43)

    blob.set("domain_warp", random.random())
    swirl = random.random() * 2
    blob.set("swirl", swirl)
    # Need to tell the engine we changed the values
    blob.set("nebula_data_change", 1)


def terrain_setup_nebula_yellow(nebula):
    blob = to_data_set(nebula)
    blob.set("radar_color_override", "#aa0")    
    size = 1000 * random.uniform(1.0, 5.5)
    size = 4000.0
    blob.set("size", size)
    density = 9.24
    blob.set("density", density)
    # 0 to 10000
    seed = random.randint(2,99999)
    blob.set("random_seed", seed)


    blob.set("absorption_red", 0.1)
    blob.set("absorption_green", 0.1)
    blob.set("absorption_blue", 0.2)

    blob.set("emission_red", 0.05)
    blob.set("emission_green", 0.05)
    blob.set("emission_blue", 0.01)

    blob.set("scattering_red", 0.2)
    blob.set("scattering_green", 0.2)
    blob.set("scattering_blue", 0.01)

    blob.set("anisotropy", random.uniform(-0.25, 0.1))

    blob.set("base_frequency",0.56)
    blob.set("base_amplitude", 1.87)
    blob.set("detail_frequency", 1.3055)
    blob.set("detail_amplitude", 0.900299)
    blob.set("detail_lacunarity", 2.43)

    blob.set("domain_warp", random.random())
    swirl = random.random() * 2
    blob.set("swirl", swirl)
    # Need to tell the engine we changed the values
    blob.set("nebula_data_change", 1)

def terrain_setup_nebula_blue(nebula):
    blob = to_data_set(nebula)
    blob.set("radar_color_override", "#0ff")    
    size = 1000 * random.uniform(1.0, 5.5)
    size = 4000.0
    blob.set("size", size)
    density = 9.24
    blob.set("density", density)
    # 0 to 10000
    seed = random.randint(2,99999)
    blob.set("random_seed", seed)


    blob.set("absorption_red", 0.2)
    blob.set("absorption_green", 0.1)
    blob.set("absorption_blue", 0.1)

    blob.set("emission_red", 0.01)
    blob.set("emission_green", 0.03)
    blob.set("emission_blue", 0.05)

    blob.set("scattering_red", 0.01)
    blob.set("scattering_green", 0.2)
    blob.set("scattering_blue", 0.2)

    blob.set("anisotropy", random.uniform(-0.25, 0.1))

    blob.set("base_frequency",0.56)
    blob.set("base_amplitude", 1.87)
    blob.set("detail_frequency", 1.3055)
    blob.set("detail_amplitude", 0.900299)
    blob.set("detail_lacunarity", 2.43)

    blob.set("domain_warp", random.random())
    swirl = random.random() * 2
    blob.set("swirl", swirl)
    # Need to tell the engine we changed the values
    blob.set("nebula_data_change", 1)

