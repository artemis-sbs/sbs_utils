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


def load_mission_vocabulary(mission):
    """Import the mission's own AMD field registrations, so its vocabulary is DECLARED
    before anything is linted.

    A mission adds its labels with `amd_register_fields`, which is exactly what stops
    `Disposition:` or `Flies:` failing silently - but the registration runs when the
    mission's Python is imported, and the linter never imported any. So Open Universe
    declared ~30 fields correctly and the linter still called every one of them unknown:
    169 warnings on OU, 46 once its module is loaded. 123 false ones, all telling an
    author their correct file is wrong.

    Convention over configuration: modules named `*_amd.py` are the ones that declare
    vocabulary (`universe_amd.py`). Narrow on purpose - importing a mission's whole
    Python would run spawn code and drag in the engine.

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

    for path in sorted(glob.glob(os.path.join(root, "**", "*_amd.py"), recursive=True)):
        _try(os.path.splitext(os.path.basename(path))[0], os.path.dirname(path), root)

    # ...and the mission's ADDONS. A mission authors the vocabulary of what it builds ON:
    # Storm's Beacon writes `Terrain:` and `Skybox:` because it uses the Open Universe
    # engine, and universe_amd.py declares both - but that file lives in the addon, so a
    # mission-only scan called seventeen correct lines unknown. Works for a packaged
    # mastlib too: a zip on sys.path is importable.
    for addon in declared_addon_paths(root):
        if os.path.isdir(addon):
            for path in sorted(glob.glob(os.path.join(addon, "**", "*_amd.py"),
                                         recursive=True)):
                _try(os.path.splitext(os.path.basename(path))[0],
                     os.path.dirname(path), addon)
            continue
        try:
            with zipfile.ZipFile(addon) as z:
                names = [n for n in z.namelist() if n.endswith("_amd.py")]
        except Exception:
            continue
        for n in names:
            _try(os.path.splitext(os.path.basename(n))[0],
                 os.path.join(addon, os.path.dirname(n)) if os.path.dirname(n) else addon,
                 addon)
    return loaded


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
