import os
import sys
import json
import re
import sbs

# the script module should be the startup script
exe_dir = os.path.dirname(sys.executable)
def test_set_exe_dir():
    global exe_dir
    d = get_script_dir()
    d = os.path.dirname(d)
    d = os.path.dirname(d)
    d = os.path.dirname(d)

    exe_dir = d



script_dir = None
def get_script_dir():
    global script_dir
    if script_dir is None:
        if sys.modules.get('script') is not None:
            script_dir = os.path.dirname(sys.modules['script'].__file__)
        else:
            script_dir =sys.path[0]

    return script_dir.replace("/", "\\")

mission_name = None
def get_mission_name():
    global mission_name
    if mission_name is None:
        sdir = get_script_dir()
        mission_name = os.path.basename(sdir)
    return mission_name

def get_startup_mission_name():
    # TODO: get the preference data
    return sbs.get_preference_string("default_mission_folder")

def get_missions_dir():
    return get_artemis_data_dir()+"/missions"

def get_mission_dir():
    return get_script_dir()

def is_dev_build():
    mission = get_script_dir()
    return os.path.isdir(mission+"\\.git")

def get_artemis_data_dir():
    return exe_dir+"/data"
    

def get_artemis_data_dir_filename(filename):
    return get_artemis_data_dir()+"\\"+filename        


def get_artemis_graphics_dir():
    data = get_artemis_data_dir()
    return data+"\\graphics"        

def get_mission_graphics_file(file):
    start = get_artemis_graphics_dir()
    mission = get_mission_dir()
    rel = os.path.relpath(mission, start)
    return f"{rel}/{file}"

def get_mission_audio_file(file):
    start = get_artemis_audio_dir()
    mission = get_mission_dir()
    rel = os.path.relpath(mission, start)
    return f"{rel}/{file}"
    



def get_artemis_audio_dir():
    data = get_artemis_data_dir()
    return data+"\\audio"        



def get_artemis_dir():
    data = get_artemis_data_dir()
    return os.path.dirname(data)

def get_mission_dir_filename(filename):
    return get_script_dir()+"\\"+filename        


def load_json_data(file):
    try:
        with open(file, 'r') as f:
            # remove comments
            contents = ''.join(line.strip() for line in f if not line.strip().startswith('//'))
            
            # remove trailing commas
            contents = re.sub(r',(\s*(?=[]}]|$))|("(?:[^\\"]|\\.)*"|[^"])', r'\1\2', contents)
            return json.loads(contents)
    except Exception as e:
        return None
    
def save_json_data(file, data):
    with open(file, 'w') as f:
        #f.write(json.dumps(data).replace("},", "},\n"))
        #f.write(json.dumps(data, indent=1).replace(r',[ \t]*[\n\r]+"', ',"'))
        j = json.dumps(data, indent=1)
        # Make more human readable
        j = re.sub(r',\n\s+"', ',"', j)
        j = re.sub(r'{\n\s+"', '{"', j )
        j = re.sub(r'\n\s+\},', '},', j)
        j = re.sub(r'\n\s+\}', '}', j)
        j = re.sub(r': {', ':\n {', j)
        j = re.sub(r'},"', '},\n"', j)
        #j = re.sub(r',[\n\r]+[ \t]*"', ',"', j )
        #j = re.sub(r'\n[\s]+},\n[\s]+', '},', j )
        f.write(j)

def add_to_path(dir):
    sys.path.insert(0, dir) 