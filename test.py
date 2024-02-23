from typing import Any
from test_label import label, prev_label, python_labels
import test_label1
import test_label2

for l in python_labels:
    
    lb = python_labels[l].next_label
    if lb:
        print(f"{l} >> {lb.__name__}")
    else:
        print(l)

player_list = [
    {"name": "Artemis", "id": None, "side": "tsn", "ship": "tsn_battle_cruiser", "face":"terran"},
    {"name": "Intrepid", "id": None, "side": "tsn", "ship": "tsn_battle_cruiser", "face":"terran"},
    {"name": "Aegis", "id": None, "side": "tsn", "ship": "tsn_battle_cruiser" ,  "face":"terran"},
    {"name": "Horatio", "id": None, "side": "tsn", "ship": "tsn_battle_cruiser" , "spawn_point": (700,0, -300), "face":"terran"},
    {"name": "Excalibur", "id": None, "side": "tsn", "ship": "tsn_battle_cruiser", "spawn_point": (-200,0,0) , "face":"terran"},
    {"name": "Hera", "id": None, "side": "tsn", "ship": "tsn_battle_cruiser", "spawn_point":  (-300,0,-100), "face":"terran"},
    {"name": "Ceres", "id": None, "side": "tsn", "ship": "tsn_battle_cruiser", "spawn_point": (-500,0, -200) , "face":"terran"},
    {"name": "Diana", "id": None , "side": "tsn", "ship": "tsn_battle_cruiser", "spawn_point": (-700,0, -300), "face":"terran"},
]

