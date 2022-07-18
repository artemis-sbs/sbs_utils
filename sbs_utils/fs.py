import os
import sys
import json

def get_mission_dir():
    return os.path.dirname(sys.argv[0])

def get_artemis_data_dir():
    script = sys.argv[0]
    mission = os.path.dirname(script)
    missions = os.path.dirname(mission)
    return os.path.dirname(missions)


def get_artemis_dir():
    script = sys.argv[0]
    mission = os.path.dirname(script)
    missions = os.path.dirname(mission)
    data = os.path.dirname(missions)
    return os.path.dirname(data)


def get_ship_data():
    try:
        file = os.path.join(get_artemis_data_dir(), "shipData.json")
        with open(file, 'r') as f:
            contents = ''.join(line for line in f if not line.startswith('//'))
            #return contents
            return json.loads(contents)
    except:
        pass
    return None

