import os
import sys
import json
import re

# the script module should be the startup script
script_dir = None
def get_script_dir():
    global script_dir
    if script_dir is None:
        if sys.modules.get('script') is not None:
            script_dir = os.path.dirname(sys.modules['script'].__file__)
        else:
            script_dir =sys.path[0]

    return script_dir

def get_mission_dir():
    return get_script_dir()

def get_artemis_data_dir():
    mission = get_script_dir()
    missions = os.path.dirname(mission)
    return os.path.dirname(missions)


def get_artemis_dir():
    mission = get_script_dir()
    missions = os.path.dirname(mission)
    data = os.path.dirname(missions)
    return os.path.dirname(data)

def get_mission_dir_filename(filename):
    return get_script_dir()+"\\"+filename        


def get_json_data(file):
    try:
        with open(file, 'r') as f:
            # remove comments
            contents = ''.join(line.strip() for line in f if not line.strip().startswith('//'))
            
            # remove trailing commas
            contents = re.sub(r',(\s*(?=[]}]|$))|("(?:[^\\"]|\\.)*"|[^"])', r'\1\2', contents)
           
            return json.loads(contents)
    except Exception as e:
        return str(e)

ship_data_cache = get_json_data( os.path.join(get_artemis_data_dir(), "shipData.json"))
def get_ship_data():
    return ship_data_cache
