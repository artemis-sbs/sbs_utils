import os
import sys
import json
import re

# the script module should be the startup script
script_dir = os.path.dirname(sys.modules['script'].__file__)

def get_mission_dir():
    return script_dir

def get_artemis_data_dir():
    mission = script_dir
    missions = os.path.dirname(mission)
    return os.path.dirname(missions)


def get_artemis_dir():
    mission = script_dir
    missions = os.path.dirname(mission)
    data = os.path.dirname(missions)
    return os.path.dirname(data)


def get_ship_data():
    return get_json_data( os.path.join(get_artemis_data_dir(), "shipData.json"))
        


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

