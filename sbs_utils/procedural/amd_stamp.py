"""A build-time record of which .amd files linted clean, and their bytes.

`sbs lib` writes one `__amd_stamp__.json` into each mastlib it builds; the
headless `--test` gate reads it. The stamp is the GATE'S CACHE, not a second
opinion -- which is what stops it from being redundant with the linter:

  * a file whose sha256 matches a stamped entry with `errors: 0` is skipped,
    so the gate costs nothing for the packaged content a mission did not touch;
  * anything else is linted, which is exactly right for the case a stamp
    structurally CANNOT cover -- a mission-folder .amd shadowing an addon's copy
    (amd_read_content step 1 beats step 3), which is the file an author is
    editing and the one most likely to be broken.

Hashing file BODIES, not the zip listing. media_cmd's `.stamp.json` hashes the
listing because its question is "did these bytes change"; the question here is
"are these the bytes that linted clean", and only the content answers it.

Reader and writer live together on purpose. They are the two halves of one
format, and the CLI half is in a different repo -- keeping them apart is how the
two would come to disagree about their own file.
"""
import hashlib
import json
import os
import zipfile

STAMP_NAME = "__amd_stamp__.json"


def amd_digest(data):
    """The stamp's identity for one .amd, as bytes or text.

    Line endings are NORMALIZED first. A mastlib holds whatever bytes the build
    machine had, `core.autocrlf` rewrites a working tree's, and the two are the
    same document -- so a raw hash would call every file dirty on the other
    platform and quietly turn the cache off. (This is the same one-file-two-forms
    trap RE_HEADING carries a comment about.)
    """
    if isinstance(data, bytes):
        try:
            data = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            data = data.decode("utf-8", "replace")
    text = data.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def amd_stamp_build(entries, linter_version=""):
    """`entries` is [(arcname, text, findings)] -> the stamp dict to store."""
    files = {}
    for arcname, text, findings in entries:
        errors = sum(1 for f in findings if getattr(f, "is_error", bool)())
        files[arcname.replace("\\", "/")] = {
            "sha256": amd_digest(text),
            "errors": errors,
            "warnings": len(findings) - errors,
        }
    return {"linter": str(linter_version or ""), "files": files}


def amd_stamp_read_zip(zip_path):
    """The stamp inside a mastlib, or {} when it has none (an older build, or a
    zip that holds no .amd at all). Never raises -- a missing stamp means "lint
    it", which is the safe direction."""
    try:
        with zipfile.ZipFile(zip_path) as z:
            with z.open(STAMP_NAME) as f:
                return json.loads(f.read().decode("utf-8")) or {}
    except Exception:
        return {}


def amd_clean_digests(addon_paths):
    """The set of sha256s that some addon's stamp says linted CLEAN.

    A folder-form addon (a clone editing its own source) has no stamp and
    contributes nothing, so its files get linted -- again the safe direction.
    """
    clean = set()
    for path in addon_paths or ():
        if not os.path.isfile(path):
            continue
        for rec in (amd_stamp_read_zip(path).get("files") or {}).values():
            if isinstance(rec, dict) and not rec.get("errors") and rec.get("sha256"):
                clean.add(rec["sha256"])
    return clean


def amd_stamp_for_folder(folder, mission_root=None, linter_version=""):
    """Lint every .amd under `folder` and return (stamp_dict, [(path, finding)]).

    Called by `sbs lib` for each mastlib it builds. Two details make the result
    match what the runtime gate would compute, which is the only way the stamp can
    be trusted as that gate's cache:

    * the MISSION's vocabulary is loaded (and put back afterwards), because an
      addon's fields are declared by the mission it belongs to;
    * `known_keys` spans the WHOLE mission, not just this folder, because a record
      in one addon legitimately references one in another.
    """
    import glob
    from sbs_utils.procedural.amd import amd_read_text
    from sbs_utils.procedural.amd_core import parse as _core_parse
    from sbs_utils.procedural.amd_lint import amd_lint
    from sbs_utils.procedural.amd_vocab import load_mission_vocabulary
    from sbs_utils.procedural.amd_schema import (amd_vocabulary_snapshot,
                                                 amd_vocabulary_restore)

    folder = os.path.abspath(folder)
    root = os.path.abspath(mission_root or folder)
    paths = sorted(glob.glob(os.path.join(folder, "**", "*.amd"), recursive=True))
    if not paths:
        return None, []

    snap = amd_vocabulary_snapshot()
    try:
        try:
            load_mission_vocabulary(root)
        except Exception:
            pass
        known = set()
        for q in glob.glob(os.path.join(root, "**", "*.amd"), recursive=True):
            try:
                known |= _core_parse(amd_read_text(q)).keys
            except Exception:
                pass
        entries, findings = [], []
        for q in paths:
            try:
                text = amd_read_text(q)
            except Exception:
                continue
            found = list(amd_lint(file_path=q, content=text, cross_file=False,
                                  known_keys=known))
            entries.append((os.path.relpath(q, folder), text, found))
            findings.extend((q, f) for f in found)
        return amd_stamp_build(entries, linter_version), findings
    finally:
        amd_vocabulary_restore(snap)
