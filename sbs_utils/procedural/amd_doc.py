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
    """Document-wide config (``{}`` if none).

    There are two places this can be written and they used to mean different things:
    the FRONT-MATTER fence (before any heading, which the parser attaches to the
    synthetic document root) and the first ``#`` heading's own fence. `amd_core`
    called the first one "root"; this module called the second one "root".

    Front matter now wins, because it is the only one that works for the flat files -
    nine of the corpus's files are a bare list of records with no title heading to
    hang config on. The title heading's fence is still merged underneath it, so every
    existing file keeps working; front matter simply takes precedence on a clash."""
    data = dict(doc.get("data") or {}) if doc else {}
    kids = doc.get("children", []) if doc else []
    # Merge the title heading's fence ONLY when there genuinely is a title: exactly
    # one top-level heading, and it contains others. On a FLAT file (nine in the
    # corpus - jobs.amd is 12 bare records) `children[0]` is a RECORD, and treating
    # it as the root would publish one character's fields as document config.
    if len(kids) == 1 and kids[0].get("children"):
        merged = dict(kids[0].get("data") or {})
        merged.update(data)         # front matter wins
        data = merged
    return {k: v for k, v in data.items() if not str(k).startswith("__")}


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


def amd_text_map(section):
    """A section's per-heading prose as a ``{key: text}`` lookup: each child's ``key`` mapped
    to its stripped ``description``. Built as plain data (not interpolated at load) so a mission
    can load a section of prose TEMPLATES once and fill their ``{slots}`` later (see amd_fill).
    Returns ``{}`` when ``section`` is None."""
    out = {}
    if section is not None:
        for n in section.get("children", []):
            out[n.get("key")] = (n.get("description") or "").strip()
    return out


def amd_records(section):
    """A section's children as GENERIC records - the raw AMD atom, before any domain lens.

    Every AMD heading (``# [Display](key)`` + an optional ``---`` fence + body prose) carries
    exactly four things; this returns one ``MastDataObject`` per child exposing them verbatim:

        key      : the ``(slug)``            -> ``rec.get("key")``
        display  : the ``[Display]`` text    -> ``rec.get("display")``
        body     : the prose under it        -> ``rec.get("body")`` (stripped)
        data     : the ``---`` fence dict    -> ``rec.get("data")`` (keys lower-cased, ``{}`` if none)

    The domain loaders (amd_lifeforms / amd_items / amd_chatter) are each a projection of this
    same node; ``amd_records`` is that substrate exposed directly, for content that IS just a
    labelled line of prose and needs no domain shape. Canonical example: a mystery clue authored as
    ``# [Container Name](slug)`` + the clue text as body -> ``{display: container, body: clue}``.
    Returns ``[]`` when ``section`` is None."""
    out = []
    if section is not None:
        for n in section.get("children", []):
            data = {str(k).lower(): v for k, v in (n.get("data") or {}).items()}
            out.append(MastDataObject({
                "key": n.get("key"),
                "display": n.get("display_text"),
                "body": (n.get("description") or "").strip(),
                "data": data,
            }))
    return out


class _AmdFormatDict(dict):
    """format_map helper: an unfilled ``{slot}`` is left LITERAL rather than raising."""
    def __missing__(self, key):
        return "{" + key + "}"


def amd_fill(template, values):
    """Fill a template's ``{slot}`` placeholders from ``values`` via ``format_map``, leaving
    UNKNOWN slots literal (missing-key-safe). Returns ``""`` for an empty/None template. Pairs
    with amd_text_map: load prose templates once, fill their slots per use."""
    if not template:
        return ""
    try:
        return template.format_map(_AmdFormatDict(values))
    except Exception:
        return template
