import os
import sys
import json
import re

# the script module should be the startup script
exe_dir = os.path.dirname(sys.executable)

def test_set_exe_dir():
    """Set path globals using this file's known location.

    Used in test environments to override the default path detection.
    fs.py lives at <game_root>/data/missions/sbs_utils/sbs_utils/fs.py,
    so all paths are derived from __file__ and are reliable regardless
    of CWD, sys.path[0], or how tests are invoked (discover vs explicit
    vs IDE runner).

    Sets:
      exe_dir    — game root (<game_root>)
      script_dir — project root (<game_root>/data/missions/sbs_utils),
                   used by get_mission_dir() to resolve relative MAST
                   import/file paths in tests
    """
    global exe_dir, script_dir
    pkg_dir = os.path.dirname(os.path.abspath(__file__))   # sbs_utils package
    project_dir = os.path.dirname(pkg_dir)                  # sbs_utils project root
    missions_dir = os.path.dirname(project_dir)             # missions
    data_dir = os.path.dirname(missions_dir)                 # data
    game_root = os.path.dirname(data_dir)                    # game root
    exe_dir = game_root
    script_dir = project_dir



script_dir = None

def get_script_dir():
    """Get the directory where the main script is located.
    
    Returns the cached script directory from sys.modules['script'] or sys.path[0].
    Paths are normalized to use backslashes on Windows.
    
    Returns:
        str: The absolute path to the script directory.
    """
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
    """Get the name of the current mission.
    
    Returns the name derived from the script directory basename.
    Cached after first call.
    
    Returns:
        str: The mission folder name.
    """
    global mission_name
    if mission_name is None:
        sdir = get_script_dir()
        mission_name = os.path.basename(sdir)
    return mission_name

def get_startup_mission_name():
    """Get the default mission name from preferences.
    
    Returns:
        str: The default mission folder name from game preferences.
    """
    # TODO: get the preference data
    from .helpers import FrameContext
    return FrameContext.context.sbs.get_preference_string("default_mission_folder")

def get_missions_dir():
    """Get the path to the missions directory.
    
    Returns:
        str: Path to the artemis data missions folder.
    """
    return get_artemis_data_dir()+"/missions"


def get_mod_file(mod, file):
    """Get the full path to a file within a mission module.
    
    Args:
        mod (str): The module/mission name.
        file (str): The relative file path within the module.
    
    Returns:
        str: The full path to the file.
    """
    return f"{get_artemis_data_dir()}/missions/{mod}/{file}"

def get_mod_dir(mod):
    """Get the directory path for a mission module.
    
    Args:
        mod (str): The module/mission name.
    
    Returns:
        str: The full directory path for the module.
    """
    return f"{get_artemis_data_dir()}/missions/{mod}"


def get_mission_dir():
    """Get the directory of the current mission.
    
    Returns:
        str: The script directory path.
    """
    return get_script_dir()

_is_dev_build = None
def is_dev_build():
    """Check if the current mission is a development build.
    
    Returns True if a .git directory exists in the mission folder.
    
    Returns:
        bool: True if running in development mode, False otherwise.
    """
    global _is_dev_build
    if _is_dev_build is None:
        mission = get_script_dir()
        _is_dev_build = os.path.isdir(mission+"\\.git")

    return _is_dev_build

def set_dev_build(v):
    global _is_dev_build
    _is_dev_build = v
    
def get_artemis_data_dir():
    """Get the path to the Artemis Cosmos data directory.
    
    Returns:
        str: The data folder path (executable directory + "/data").
    """
    return exe_dir+"/data"
    

def get_artemis_data_dir_filename(filename):
    """Get the full path to a file in the data directory.
    
    Args:
        filename (str): The relative path from the data directory.
    
    Returns:
        str: The full path to the file in the data directory.
    """
    return get_artemis_data_dir()+"\\"+filename        


def get_artemis_graphics_dir():
    """Get the path to the Artemis Cosmos graphics directory.
    
    Returns:
        str: The graphics folder path (data directory + "\\graphics").
    """
    data = get_artemis_data_dir()
    return data+"\\graphics"        

def engine_file(path):
    """A path in the shape the ENGINE resolves: relative to the Cosmos root.

    THE ONE PATH HELPER. Every asset class used to compute its own shape against its own
    base - audio against `data/audio`, images against `data/graphics`, a skybox as an
    absolute path for a mission asset but a bare name for a stock one, ship data already
    root-relative. Five spellings of the same idea, and only a run of the game could say
    which of them a given engine would open.

    The 2026-08-15 engine resolves ONE shape for all of them, measured against it
    (`data/missions/mediapath_probe`): a path from the Cosmos root, or an absolute path.
    Both open. What does NOT open is a bare name, or a path relative to the asset's own
    old base - `../missions/<m>/<file>` against `data/audio` is what this library built
    for audio until now, and on this engine it silently plays nothing.

    NOTE ON EXTENSIONS, because it is the opposite of what the shape suggests: the engine
    appends the extension itself, and passing one can make the lookup FAIL. A `.wav` on an
    audio path was measured not to open while the same path without it did. So callers
    name assets the way they always have - without a suffix - and this does not add one.

    An absolute path outside the install is passed through unchanged: it is still a path
    the engine accepts, and rewriting it to `../../..` would only make it fragile.
    """
    text = str(path)
    if not os.path.isabs(text):
        # Already relative - a caller who wrote one already knew what it meant.
        return text.replace("\\", "/")
    try:
        rel = os.path.relpath(text, get_artemis_dir())
    except (ValueError, OSError):
        return text.replace("\\", "/")      # different drive - absolute is still valid
    if rel.startswith(".."):
        return text.replace("\\", "/")      # outside the install - leave it alone
    return rel.replace(os.sep, "/").replace("\\", "/")


def get_mission_graphics_file(file):
    """The path the engine wants for a graphics file kept in this mission.

    Now the same shape as everything else - see :func:`engine_file`. It was safe to move
    only once two things were measured on engine 1.3.6: that images open from an
    exe-relative path (the `image_probe` mission, judged by eye - an image is loaded when
    it is DRAWN, so an access-time probe on the server screen answers nothing), and that
    `ImageAtlas` no longer routes through this function, so changing it cannot disturb
    the fallback chain that finds the art in the first place.

    Args:
        file (str): The file, relative to the mission folder, WITHOUT its extension.

    Returns:
        str: A Cosmos-root-relative path.
    """
    return engine_file(os.path.join(get_mission_dir(), file))

def get_mission_audio_file(file):
    """The path the engine wants for an audio file kept in this mission.

    Args:
        file (str): The file, relative to the mission folder, WITHOUT its extension.

    Returns:
        str: A Cosmos-root-relative path - see :func:`engine_file`.
    """
    return engine_file(os.path.join(get_mission_dir(), file))




def get_artemis_audio_dir():
    """Get the path to the Artemis Cosmos audio directory.
    
    Returns:
        str: The audio folder path (data directory + "\\audio").
    """
    data = get_artemis_data_dir()
    return data+"\\audio"        



def get_artemis_dir():
    """Get the path to the root Artemis Cosmos installation directory.
    
    Returns:
        str: The parent directory of the data folder.
    """
    data = get_artemis_data_dir()
    return os.path.dirname(data)

def get_mission_dir_filename(filename):
    """Get the full path to a file in the current mission directory.
    
    Args:
        filename (str): The relative path from the mission directory.
    
    Returns:
        str: The full path to the file in the mission directory.
    """
    # os.path.join, not a hardcoded backslash. On Windows the two are identical,
    # so nothing the engine sees changes. On POSIX they are not: a hardcoded "\\"
    # is an ordinary character, so `os.path.dirname` of the result silently
    # returns the mission's PARENT - which is how a media pack went undiscovered
    # and a lookup fell back to the wrong folder, on CI only, where this library's
    # host-side tooling and tests actually run.
    return os.path.join(get_script_dir(), filename)


#
# ryaml (the engine's PyAddons/ryaml.pyd) parses roughly 34x faster than the
# bundled pure-Python yaml: 9ms against 308ms on shipData, which is most of a
# second of mission start once the metadata blocks and data files are added up.
#
# Resolve it ONCE. A FAILED import walks the whole of sys.path, and this used to
# run on every call, for every file - so the machine without it paid the search
# over and over, and said so, over and over.
#
# The import is kept separate from the PARSE on purpose. They used to share one
# try/except, so ryaml refusing a single file (it is a stricter parser than
# pyyaml) surfaced as "ryaml not found" and every later load quietly took the
# slow path. That is what "the fast parser only works once" looks like from the
# outside, and the message sent anyone who investigated to the wrong place.
#
_RYAML = None            # the module once resolved; False once known absent
_RYAML_REJECTED = set()  # things it refused, so we complain once each


def ryaml_module():
    """The fast YAML parser, or None where it is not installed.

    Absent is NORMAL and silent: the mock and any host-side tooling run on a
    plain Python that has no PyAddons on its path, and they must not be noisy
    about a thing they were never going to have.
    """
    global _RYAML
    if _RYAML is None:
        try:
            import ryaml
            _RYAML = ryaml
        except ImportError:
            _RYAML = False
    return _RYAML or None


def _ryaml_rejected(what, err):
    """ryaml is PRESENT and refused this content - a different fact entirely.

    Worth saying once, with the name of the offending file: the fallback keeps
    the mission running, so nothing else will ever mention that this file is
    being parsed the slow way, or that it may be malformed.
    """
    if what in _RYAML_REJECTED:
        return
    _RYAML_REJECTED.add(what)
    import logging
    logging.getLogger("mast.runtime").warning(
        f"ryaml refused {what} ({type(err).__name__}: {err}) - falling back to "
        "the bundled parser for it. The fast path is otherwise still in use.")


def load_yaml_data(file, multi=False):
    """Load and parse a YAML file.

    Uses the fast ryaml parser when the engine provides it, and the bundled
    pure-Python yaml otherwise (or when ryaml refuses the file).

    Args:
        file (str): Path to the YAML file to load.
        multi (bool): return a generator of all documents

    Returns:
        dict or generator or None: Parsed YAML data, or None if loading fails.
    """
    ry = ryaml_module()
    if ry is not None:
        try:
            with open(file, 'r') as f:
                if multi:
                    return ry.load_all(f)
                else:
                    return ry.load(f)
        except OSError:
            # Missing or unreadable is NOT a parser refusal. Optional data files
            # are looked up speculatively all over the place, so reporting this
            # would cry wolf on every one of them - and did.
            pass
        except Exception as e:
            _ryaml_rejected(file, e)

    try:
        from . import yaml
        with open(file, 'r') as f:
            # remove comments
            if multi:
                return yaml.safe_load_all(f)
            else:
                return yaml.safe_load(f)
    except Exception as e:
        return None

def load_data(file):
    """Load a data file as YAML or JSON, dispatching on the extension.

    ``.yaml``/``.yml`` are parsed as YAML; ``.json`` as JSON (comment- and
    trailing-comma-tolerant). When ``file`` has no recognised extension it is
    treated as a BASE path and the ``.yaml``, ``.yml`` then ``.json`` siblings are
    tried in turn -- so a caller can pass ``"shipData"`` (no extension) and get
    whichever form is present, YAML preferred.

    Args:
        file (str): Path to the data file, with or without a
            ``.yaml``/``.yml``/``.json`` extension.

    Returns:
        dict | list | None: The parsed data, or ``None`` if nothing loaded.
    """
    ext = os.path.splitext(file)[1].lower()
    if ext in (".yaml", ".yml"):
        return load_yaml_data(file)
    if ext == ".json":
        return load_json_data(file)
    # No recognised extension: treat as a base, preferring YAML then JSON.
    for cand, loader in ((file + ".yaml", load_yaml_data), (file + ".yml", load_yaml_data), (file + ".json", load_json_data)):
        if os.path.exists(cand):
            return loader(cand)
    return None


def load_yaml_string(s):
    """Parse a YAML string.
    
    Attempts to parse using ryaml first for better comment handling,
    falls back to standard yaml.safe_load if ryaml is unavailable.
    
    Args:
        s (str): YAML content as a string.
    
    Returns:
        dict or None: Parsed YAML data, or None if parsing fails.
    """
    # JSON FIRST - for ROBUSTNESS, not for speed. Measured on Cosmos-TNG-Mod's 119 KB
    # ship-data file:
    #
    #     ryaml (PyAddons, what the engine uses)   0.007 s
    #     json.loads                               0.001 s
    #     bundled yaml (the FALLBACK)              0.220 s
    #
    # So against the normal path this saves 6ms and is not worth arguing about - YAML is
    # the preferred authoring format and ryaml is fast. What it does buy is the case where
    # ryaml is NOT on the path: PyAddons is resolved from the Cosmos install, and anything
    # running outside it (a bare python, a tool, a CI box) falls back to the bundled parser
    # and pays 220ms per file. A mod that ships .json then costs 1ms instead.
    #
    # Gated on the first character rather than a bare try, because this is called for EVERY
    # `metadata:` block in every story - an exception per block would cost more than it
    # saves. A YAML flow document also opens with `{`; it simply fails and falls through.
    head = s.lstrip()[:1] if s else ""
    if head in ("{", "["):
        try:
            import json
            return json.loads(s)
        except Exception:
            pass

    ry = ryaml_module()
    if ry is not None:
        try:
            return ry.loads(s)
        except Exception as e:
            # Keyed by content, not by name: this is called for every metadata:
            # block, and one bad block should not mute the report for the rest.
            _ryaml_rejected(f"yaml string {s[:60]!r}", e)

    try:
        from . import yaml
        # remove comments
        return yaml.safe_load(s)
    except Exception as e:
        return None

def save_yaml_data(file, data):
    """Save an object as a YAML file.
    
    Attempts to dump using ryaml first for better comment handling, 
    falls back to standard yaml.safe_dump if ryaml is unavailable.
    
    Args:
        file (str): Path to the YAML file to load.
        data (dict): Dict or object to save
    """
    ry = ryaml_module()
    if ry is not None:
        try:
            with open(file, 'w') as f:
                return ry.dump(f, data)
        except OSError:
            pass
        except Exception as e:
            _ryaml_rejected(f"dump of {file}", e)

    try:
        from . import yaml
        with open(file, 'w') as f:
            # safe_dump(data, stream) - a single document. (The old call passed the
            # file as 'documents' and the dict as 'stream', which wrote nothing.)
            return yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
    except Exception as e:
        return None


def load_json_data(file):
    """Load and parse a JSON file with comment support.
    
    Strips comments (# and //) and trailing commas before parsing.
    Attempts to load using ryaml first, falls back to json.loads with preprocessing.
    
    Args:
        file (str): Path to the JSON file to load.
    
    Returns:
        dict or None: Parsed JSON data, or None if loading fails.
    """
    ry = ryaml_module()
    if ry is not None:
        try:
            with open(file, 'r') as f:
                return ry.load(f)
        except OSError:
            pass
        except Exception as e:
            _ryaml_rejected(file, e)

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
    """Parse a JSON string with comment and trailing comma support.
    
    First attempts YAML parsing (which handles more formats), then falls back
    to JSON parsing. Supports comments (# and //) and trailing commas.
    
    Args:
        contents (str): JSON content as a string.
    
    Returns:
        dict or None: Parsed data, or None if parsing fails.
    """
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
    """Save data to a JSON file with human-readable formatting.
    
    Applies regex transformations to make the JSON output more readable with
    logical line breaks and consistent spacing.
    
    Args:
        file (str): Path to the output JSON file.
        data (dict): The data structure to serialize.
    """
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



def file_get_time(filename):
    try:
        return os.stat(filename).st_mtime
    except Exception:
        return 0

def file_get_stats(filename):
    try:
        return os.stat(filename)
    except Exception:
        return None


def add_to_path(dir):
    """Add a directory to the Python module search path.
    
    Inserts the directory at the beginning of sys.path.
    
    Args:
        dir (str): The directory path to add.
    """
    sys.path.insert(0, dir) 



import zipfile
def expand_zip(zip_filepath, extract_to_path, overwrite=False):
    """Extract the contents of a zip file to a specified directory.

    Creates the target directory if it does not exist. Handles zip extraction
    errors gracefully with informative error messages.

    Args:
        zip_filepath (str): The path to the zip file to extract.
        extract_to_path (str): The directory where contents will be extracted.
            Created automatically if it does not exist.
        overwrite (bool): If True, overwrite existing files. Defaults to False.
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
    