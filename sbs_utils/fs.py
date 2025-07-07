import os
import sys
import json
from . import yaml
import re

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
            script_dir = os.path.dirname(os.path.abspath(sys.modules['script'].__file__))
            script_dir = script_dir.replace("/", "\\")
        else:
            script_dir =sys.path[0]
            script_dir = script_dir.replace("/", "\\")

    return script_dir

mission_name = None
def get_mission_name():
    global mission_name
    if mission_name is None:
        sdir = get_script_dir()
        mission_name = os.path.basename(sdir)
    return mission_name

def get_startup_mission_name():
    # TODO: get the preference data
    from .helpers import FrameContext
    return FrameContext.context.sbs.get_preference_string("default_mission_folder")

def get_missions_dir():
    return get_artemis_data_dir()+"/missions"


def get_mod_file(mod, file):
    return f"{get_artemis_data_dir()}/missions/{mod}/{file}"

def get_mod_dir(mod):
    return f"{get_artemis_data_dir()}/missions/{mod}"


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


def load_yaml_data(file):
    try:
        import ryaml
        with open(file, 'r') as f:
            return ryaml.load(f)
    except Exception as e:
        pass

    try:
        with open(file, 'r') as f:
            # remove comments
            return yaml.safe_load(f)
    except Exception as e:
        return None

def load_yaml_string(s):
    try:
        import ryaml
        return ryaml.loads(s)
    except Exception as e:
        pass

    try:
        # remove comments
        return yaml.safe_load(s)
    except Exception as e:
        return None


def load_json_data(file):
    try:
        import ryaml
        with open(file, 'r') as f:
            return ryaml.load(f)
    except Exception as e:
        pass
    
    try:
        with open(file, 'r') as f:
            # remove comments
            contents = ''.join(line.strip() for line in f if not (line.strip().startswith('#') or line.strip().startswith('//')))
            
            # remove trailing commas
            contents = re.sub(r',(\s*(?=[]}]|$))|("(?:[^\\"]|\\.)*"|[^"])', r'\1\2', contents)
            return json.loads(contents)
    except Exception as e:
        return None
    
def load_json_string(contents):
    d = load_yaml_string(contents)
    if d:
        return d
    try:
        #f = contents.split("\n")
        # remove comments
        # contents = ''.join(line.strip() for line in f if not line.strip().startswith('//'))
        
        # # remove trailing commas
        # contents = re.sub(r',(\s*(?=[]}]|$))|("(?:[^\\"]|\\.)*"|[^"])', r'\1\2', contents)
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



import zipfile
def expand_zip(zip_filepath, extract_to_path, overwrite=False):
    """
    Expands a zip file to a specified directory.

    Args:
        zip_filepath (str): The path to the zip file.
        extract_to_path (str): The directory to extract the contents to.
                           If the directory does not exist, it will be created.
    """
    try:
        with zipfile.ZipFile(zip_filepath, 'r') as zip_ref:
            for member in zip_ref.infolist():
                file_path = os.path.join(extract_to_path, member.filename)
                if not os.path.exists(file_path) or overwrite:
                    zip_ref.extract(member, extract_to_path)
    except FileNotFoundError:
        print(f"Error: Zip file '{zip_filepath}' not found.")
    except zipfile.BadZipFile:
         print(f"Error: '{zip_filepath}' is not a valid zip file.")
    except Exception as e:
        print(f"An error occurred: {e}")
    