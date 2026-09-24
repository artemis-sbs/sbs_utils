"""Hand a shot reel to Blender's Video Sequence Editor as an editable .blend.

The ffmpeg path (`assemble.py`) bakes the cut. This one builds a timeline instead:
each take is a movie strip trimmed at its marks, so the edit can be finished by hand
in Blender - retime a cut, add a transition, drop in music - and rendered from there.

Host side only. The Blender side is `vse_build.py`, run with `blender --background`.
"""
import os
import glob
import json
import shutil
import subprocess


BUILDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vse_build.py")


def blender_exe():
    """The newest installed Blender, or None. PATH first, then the default installs."""
    p = shutil.which("blender")
    if p:
        return p
    roots = [os.environ.get("ProgramFiles", r"C:\Program Files"),
             os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")]
    found = []
    for r in roots:
        found += glob.glob(os.path.join(r, "Blender Foundation", "Blender *", "blender.exe"))
    def ver(p):
        v = os.path.basename(os.path.dirname(p)).split()[-1]
        return tuple(int(x) for x in v.split(".") if x.isdigit())
    return max(found, key=ver) if found else None


def resolve_take(take_dir, named):
    """The recording a marks.json means.

    The recorded path is absolute, so it goes stale when the output folder moves.
    Try it, then the same file name in the take's own directory, then the only
    recording there. More than one candidate and no match is an error - picking one
    would put the marks on the wrong tape.
    """
    if named and os.path.isfile(named):
        return named
    if named:
        local = os.path.join(take_dir, os.path.basename(named))
        if os.path.isfile(local):
            return local
    cand = sorted(glob.glob(os.path.join(take_dir, "*.mkv")) +
                  glob.glob(os.path.join(take_dir, "*.mp4")))
    if len(cand) == 1:
        return cand[0]
    return None


def shots_from(path):
    """(shots, source_size, problems) from a reel root or a single take directory.

    A reel root has reel.json and takes/<name>/; its running order comes from
    reel.json. A take directory has marks.json.
    """
    problems = []
    if os.path.isfile(os.path.join(path, "marks.json")):
        take_dirs = [path]
    else:
        order = []
        rj = os.path.join(path, "reel.json")
        if os.path.isfile(rj):
            with open(rj, encoding="utf-8") as f:
                doc = json.load(f)
            order = [t["name"] for t in (doc.get("takes") or doc)]
        take_dirs = [os.path.join(path, "takes", n) for n in order]
        if not take_dirs:
            take_dirs = sorted(glob.glob(os.path.join(path, "takes", "*")))

    shots, size = [], None
    for d in take_dirs:
        mp = os.path.join(d, "marks.json")
        if not os.path.isfile(mp):
            problems.append("%s: no marks.json (take not recorded?)" % d)
            continue
        with open(mp, encoding="utf-8") as f:
            doc = json.load(f)
        take = resolve_take(d, doc.get("take"))
        if not take:
            problems.append("%s: cannot tell which recording the marks belong to" % d)
            continue
        size = size or doc.get("source_size")
        name = doc.get("name") or os.path.basename(d)
        for m in doc.get("marks") or []:
            shots.append({"take": os.path.abspath(take), "group": name,
                          "t": float(m.get("t") or 0.0),
                          "t_end": float(m.get("t_end") or 0.0),
                          "label": m.get("label") or ""})
    return shots, size, problems


def build(blender, plan, plan_path, timeout=3600):
    """Run the Blender side. Returns (ok, output)."""
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2)
    r = subprocess.run([blender, "--background", "--factory-startup",
                        "--python-exit-code", "1",
                        "--python", BUILDER, "--", plan_path],
                       capture_output=True, text=True, timeout=timeout)
    out = (r.stdout or "") + (r.stderr or "")
    return r.returncode == 0 and "SIZZLE blend" in out, out
