"""Multi-file AMD documents: a table-of-contents file whose sections `File:`-splice in
other files.

An AMD document parses to a tree - one level-1 heading (the root) whose children are
`## [Section](key)` nodes, each holding `###` entries. A section's fence may carry
`File: path.amd` (repeat, or a comma `Files:` list) to pull that file's top-level entries
into the section, so the main file stays a slim table of contents and big sections live in
their own files. One level deep: an included file holds entries, not further `File:`s.

This is the generic machinery promoted out of Open Universe (which pioneered it for
universe.amd's Clans/Jobs/Dialogue/Narrative sections). It is content-agnostic - the caller
supplies the per-fence ``data_parser`` (e.g. amd_quest_data, amd_scan_data, or a mission's
own). Pairs with the shared vocabularies (amd_quest / amd_science): those load a single
file; this splits one across many.
"""
import os
from sbs_utils.procedural.quest import document_get_amd_file
from sbs_utils.procedural.media import media_read_relative_file
from sbs_utils.fs import get_mission_dir_filename
from sbs_utils.mast.mast_node import MastDataObject


def amd_read_content(fname):
    """Read an AMD file (or an include) as text. Tries the CONSUMER MISSION folder first
    (``get_mission_dir_filename``) so a mission built on a library can supply its own
    content, then falls back to code/lib-relative (``media_read_relative_file``, which also
    reads from inside a packaged mastlib zip). Returns None if neither resolves."""
    if fname:
        mission_path = get_mission_dir_filename(fname)
        if mission_path is not None and os.path.isfile(mission_path):
            with open(mission_path, "r") as f:
                return f.read()
    return media_read_relative_file(fname)


def amd_document(content, data_parser=None, title="Document"):
    """Parse AMD ``content`` into a document tree (one root heading whose children are the
    sections). ``data_parser`` coerces each ``---`` fence (e.g. amd_quest_data /
    amd_scan_data / a mission's own); ``title`` names the root when the content has none.
    Headings are the link form ``# [Display](key)`` so ``#`` stays STRUCTURAL only."""
    return document_get_amd_file(None, title, content=content, data_parser=data_parser)


def amd_root_node(doc):
    """The single level-1 root heading node (the file's root content), or None."""
    kids = doc.get("children", []) if doc else []
    return kids[0] if kids else None


def amd_root_data(doc):
    """The root heading's ``---`` data dict (``{}`` if none) - where document-wide config
    blocks live (e.g. a ``reputation:`` block)."""
    root = amd_root_node(doc)
    return (root.get("data") if root is not None else None) or {}


def amd_section(doc, key):
    """The named section node under the root, or None when absent (e.g. a legacy flat file
    with no sections -> the caller iterates the root's children instead)."""
    root = amd_root_node(doc)
    if root is None:
        return None
    for n in root.get("children", []):
        if n.get("key") == key:
            return n
    return None


def _amd_file_list(data):
    """Section `File:`/`Files:` values -> a flat list of paths. Robust to any data_parser:
    the key may be any case (a friendly parser lowercases it; the default reader keeps case)
    and a value may be a string (one path, or a comma list) or an already-split list."""
    lower = {str(k).lower(): v for k, v in (data or {}).items()}
    out = []
    for key in ("file", "files"):
        v = lower.get(key)
        if v is None:
            continue
        items = v if isinstance(v, (list, tuple)) else [v]
        for item in items:
            out.extend(p.strip() for p in str(item).split(",") if p.strip())
    return out


def amd_includes(doc):
    """One ``(key, file)`` record (MastDataObject) per file to splice - a section may name
    several (repeat ``File:`` or a comma ``Files:`` list), in order. The caller reads each
    file and calls ``amd_splice``. Parser-agnostic: works whether the fence parser left
    ``file`` as a list, a single string, or a ``files`` comma string."""
    root = amd_root_node(doc)
    out = []
    if root is not None:
        for sec in root.get("children", []):
            for f in _amd_file_list(sec.get("data")):
                out.append(MastDataObject({"key": sec.get("key"), "file": f}))
    return out


def amd_splice(doc, section_key, included_doc):
    """Append an included file's top-level entries as children of the named section."""
    root = amd_root_node(doc)
    if root is None or included_doc is None:
        return
    for sec in root.get("children", []):
        if sec.get("key") == section_key:
            sec.get("children").extend(included_doc.get("children", []))
            return
