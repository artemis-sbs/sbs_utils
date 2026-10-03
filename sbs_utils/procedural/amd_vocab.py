"""Load a mission's OWN AMD vocabulary, so it is declared before anything reads it.

Moved here from sbs_cli's `lint_cmd` so that `sbs lint` and the headless `--test`
gate share ONE implementation. That sharing is the whole point, and the cost of
not sharing is measurable: calling `amd_lint` without this step reports 174
`unknown-field` warnings across the OpenUniverse and LegendaryMissions corpus
that `sbs lint` correctly reports as 2. A gate that cries wolf 174 times is a
gate everybody learns to ignore.

Stdlib only, and never fatal - a module that needs the engine simply does not
contribute its words.
"""
import glob
import json
import os
import sys
import zipfile


# Which of a mission's modules declare AMD vocabulary. Matched by FILENAME, so a
# mission opts in by naming a file rather than by registering anywhere.
_VOCAB_MODULES = ("*_amd.py", "*_dialogue.py")


def load_mission_vocabulary(mission):
    """Import the mission's own AMD field registrations, so its vocabulary is DECLARED
    before anything is linted.

    A mission adds its labels with `amd_register_fields`, which is exactly what stops
    `Disposition:` or `Flies:` failing silently - but the registration runs when the
    mission's Python is imported, and the linter never imported any. So Open Universe
    declared ~30 fields correctly and the linter still called every one of them unknown:
    169 warnings on OU, 46 once its module is loaded. 123 false ones, all telling an
    author their correct file is wrong.

    Convention over configuration: modules named `*_amd.py` or `*_dialogue.py` are the
    ones that declare vocabulary. Narrow on purpose - importing a mission's whole Python
    would run spawn code and drag in the engine.

    `*_dialogue.py` is here because a choice's OUTCOMES are vocabulary too: Open Universe
    registers `costs` and `earns` in `universe_dialogue.py`, and without them the linter
    reads `; costs 200 credits` as a word nobody applies and reports a correct file.
    (Adding the import to `universe_amd.py` instead does not work - these modules are
    imported STANDALONE, with no package context, so a relative import raises and takes
    the whole file's vocabulary down with it.)

    Never fatal. A mission whose module cannot import offline still lints, just without
    its own words - which is exactly today's behaviour, so this can only improve on it.
    """
    root = os.path.abspath(mission)
    import importlib
    loaded = []

    def _try(name, *dirs):
        added = [d for d in dirs if d and d not in sys.path]
        sys.path[:0] = added
        try:
            importlib.import_module(name)
            loaded.append(name)
        except Exception:
            pass          # a module that needs the engine simply does not contribute

    for pattern in _VOCAB_MODULES:
        for path in sorted(glob.glob(os.path.join(root, "**", pattern), recursive=True)):
            _try(os.path.splitext(os.path.basename(path))[0], os.path.dirname(path), root)

    # ...and the mission's ADDONS. A mission authors the vocabulary of what it builds ON:
    # Storm's Beacon writes `Terrain:` and `Skybox:` because it uses the Open Universe
    # engine, and universe_amd.py declares both - but that file lives in the addon, so a
    # mission-only scan called seventeen correct lines unknown. Works for a packaged
    # mastlib too: a zip on sys.path is importable.
    for addon in declared_addon_paths(root):
        if os.path.isdir(addon):
            for pattern in _VOCAB_MODULES:
                for path in sorted(glob.glob(os.path.join(addon, "**", pattern),
                                             recursive=True)):
                    _try(os.path.splitext(os.path.basename(path))[0],
                         os.path.dirname(path), addon)
            continue
        try:
            with zipfile.ZipFile(addon) as z:
                names = [n for n in z.namelist()
                         if any(n.endswith(p[1:]) for p in _VOCAB_MODULES)]
        except Exception:
            continue
        for n in names:
            _try(os.path.splitext(os.path.basename(n))[0],
                 os.path.join(addon, os.path.dirname(n)) if os.path.dirname(n) else addon,
                 addon)
    return loaded


# --- shared folders -----------------------------------------------------------
#
# A mission can read `.amd` files that are NOT in its own folder: an author's own Siege
# bosses live in `<missions>/common_data/bosses`, beside the saves, where an update to the
# mission cannot delete them. Those files are written in the mission's vocabulary and
# point at the mission's keys, so every tool has to treat them as part of the mission -
# and a tool reading a mission folder cannot know the folder exists unless the mission
# says so.

#: What the running process has been told, {name: beside}. Tooling does not read this -
#: it reads the declaration statically (`mission_shared_folders`), so that one mission's
#: folders never leak into another mission linted or served by the same process.
_SHARED_FOLDERS = {}

_COMMON_DATA = "common_data"


def amd_register_shared_folder(name, beside=None):
    """Say that this mission also reads `.amd` files from `common_data/<name>`.

    Call it from the mission's vocabulary file (`*_amd.py`), with LITERAL arguments - the
    tools read the call without running the file:

        amd_register_shared_folder("bosses", beside="maps/bosses")

    `beside` is the mission's own folder those files join. It is what lets a check that
    compares neighbors - two bosses with one name - see both folders as one.

    After this, `sbs lint <mission>` checks the shared files too, `sbs lint
    common_data/<name>` checks them alone, and the editor reads a file opened there with
    the mission's words and keys instead of calling every field unknown.
    """
    _SHARED_FOLDERS[str(name)] = str(beside) if beside else None


def _static_shared_calls(source):
    """Every `amd_register_shared_folder(...)` in `source` with literal arguments, as
    (name, beside). Parsed, never executed."""
    if "amd_register_shared_folder" not in source:
        return []
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "amd_register_shared_folder"):
            continue
        args = [a.value for a in node.args
                if isinstance(a, ast.Constant) and isinstance(a.value, str)]
        if not args:
            continue
        beside = args[1] if len(args) > 1 else None
        for kw in node.keywords:
            if (kw.arg == "beside" and isinstance(kw.value, ast.Constant)
                    and isinstance(kw.value.value, str)):
                beside = kw.value.value
        out.append((args[0], beside))
    return out


def mission_shared_folders(mission):
    """{name: beside} for every shared folder this mission's vocabulary files declare."""
    root = os.path.abspath(mission)
    found = {}
    for pattern in _VOCAB_MODULES:
        for path in sorted(glob.glob(os.path.join(root, "**", pattern), recursive=True)):
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    source = f.read()
            except OSError:
                continue
            for name, beside in _static_shared_calls(source):
                found[name] = beside
    return found


def shared_amd_files(mission):
    """Every `.amd` in the shared folders this mission reads. Sorted, absolute."""
    root = os.path.abspath(mission)
    base = os.path.join(os.path.dirname(root), _COMMON_DATA)
    out = []
    for name in sorted(mission_shared_folders(root)):
        out += glob.glob(os.path.join(base, name, "**", "*.amd"), recursive=True)
    return sorted(os.path.abspath(p) for p in out)


def _shared_parts(path):
    """(missions folder, shared folder name) for a path inside `common_data/<name>`, else
    (None, None). `path` may be the folder itself or anything under it."""
    parts = os.path.abspath(path).replace("\\", "/").split("/")
    low = [p.lower() for p in parts]
    if _COMMON_DATA not in low:
        return None, None
    i = len(low) - 1 - low[::-1].index(_COMMON_DATA)
    if i + 1 >= len(parts) or not parts[i + 1]:
        return None, None
    if os.path.splitext(parts[i + 1])[1] and i + 2 >= len(parts):
        return None, None                     # a FILE directly in common_data
    return os.sep.join(parts[:i]) or os.sep, parts[i + 1]


def shared_folder_owner(path):
    """The mission that reads the shared folder `path` is in, or None.

    A file in `common_data/bosses` belongs to no mission folder, so walking up from it
    finds no `story.json`. The missions beside `common_data` are asked instead: the first
    whose vocabulary file declares that folder is the one whose words the file is in.
    """
    missions, name = _shared_parts(path)
    if not missions:
        return None
    for mission in sorted(glob.glob(os.path.join(missions, "*"))):
        if not os.path.isdir(mission) or os.path.basename(mission) == _COMMON_DATA:
            continue
        if name in mission_shared_folders_shallow(mission):
            return os.path.abspath(mission)
    return None


def mission_shared_folders_shallow(mission):
    """`mission_shared_folders`, looking only at the mission's top two levels - enough
    for a vocabulary file, and cheap enough to ask of every mission on the machine."""
    found = {}
    for pattern in _VOCAB_MODULES:
        for depth in ("", "*"):
            for path in sorted(glob.glob(os.path.join(mission, depth, pattern))):
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        source = f.read()
                except OSError:
                    continue
                for name, beside in _static_shared_calls(source):
                    found[name] = beside
    return found


def shared_neighbor_folders(path):
    """The OTHER folders whose files are read together with the one `path` is in.

    For a file in `common_data/bosses`: the owning mission's `maps/bosses`. For a file in
    a mission's `maps/bosses`: `common_data/bosses`. Empty when the folder is not half of
    such a pair.
    """
    here = os.path.dirname(os.path.abspath(path))
    missions, name = _shared_parts(path)
    if missions:
        owner = shared_folder_owner(path)
        beside = mission_shared_folders_shallow(owner).get(name) if owner else None
        return [os.path.join(owner, *beside.split("/"))] if beside else []
    d = here
    for _ in range(24):
        if any(os.path.isfile(os.path.join(d, m))
               for m in ("story.json", "story.mast", "__lib__.json")):
            out = []
            for name, beside in mission_shared_folders_shallow(d).items():
                if beside and os.path.normcase(os.path.join(d, *beside.split("/"))) \
                        == os.path.normcase(here):
                    out.append(os.path.join(os.path.dirname(d), _COMMON_DATA, name))
            return out
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return []


def declared_addon_paths(mission_root):
    """Each mastlib `story.json` declares, as a source FOLDER (a clone editing its own
    addons) or the `__lib__` zip. Mirrors how the compiler resolves them."""
    out = []
    try:
        story = os.path.join(mission_root, "story.json")
        if not os.path.isfile(story):
            return out
        with open(story) as f:
            data = json.load(f) or {}
        lib_dir = os.path.join(os.path.dirname(mission_root), "__lib__")
        for name in (data.get("mastlib") or []):
            parts = str(name).split(".", 3)
            folder = os.path.join(mission_root, parts[2]) if len(parts) >= 4 else None
            if folder and os.path.isfile(os.path.join(folder, "__init__.mast")):
                out.append(folder)
                continue
            zip_path = os.path.join(lib_dir, name)
            if os.path.isfile(zip_path):
                out.append(zip_path)
    except Exception:
        pass
    return out
