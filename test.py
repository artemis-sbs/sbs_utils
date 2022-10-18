from sbs_utils.mast.mast import Mast, PY_EXP_REGEX, IF_EXP_REGEX
from sbs_utils.mast.mastsbs import MastSbs



print(r"""((button\s+["'](?P<message>.+?)["'])(\s*data\s*=\s*(?P<data>"""+PY_EXP_REGEX+r"""))?"""+IF_EXP_REGEX+r")|(?P<end>end_button)")



player_ships =  [ 
        PlayerShip().spawn(sim, 500,0,0, "Artemis", "tsn", "Battle Cruiser").py_object,
        PlayerShip().spawn(sim, 200,0,0, "Hera", "tsn", "Missile Cruiser").py_object,
        PlayerShip().spawn(sim, 900,0,0, "Atlas", "tsn", "Missile Cruiser").py_object
    ]
sbs.assign_player_ship(player_ships[0].id)
for player in player_ships:
    faces.set_face(player.id, faces.random_terran())

stations = [
    Npc().spawn(sim,0,0,0, "Alpha", "tsn", "Starbase", "behav_station").py_object,
    Npc().spawn(sim,2400,0,100, "Beta", "tsn", "Starbase", "behav_station").py_object
]
for ds in stations:
    faces.set_face(ds.id, faces.random_terran(civilian=True))
    ds.add_role('Station')

enemyTypeNameList = ["Dreadnaught","Battleship","Hunter","Cargo","ARV Carrier","Behemoth"]
enemy_prefix = "KLMNQ"

enemy = 0
spawn_points = scatter.sphere(enemy_count, 0,0,0, 3000, 6000, ring=True)
for v in spawn_points:
    r_type = random.choice(enemyTypeNameList)
    r_name = f"{random.choice(enemy_prefix)}_{enemy}"
    spawn_data = Npc().spawn_v(sim,v, r_name, "RAIDER", r_type, "behav_npcship")
    faces.set_face(spawn_data.id, faces.random_kralien())
    enemy += 1
