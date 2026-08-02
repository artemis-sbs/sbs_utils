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


# Addons this story declares, resolved to a source folder or a mastlib zip. Per-mission,
# so it is on the reset ledger in handlerhooks.
_DECLARED_ADDONS = []


def amd_declared_addons():
    """Every addon this story declares, as a path to a source FOLDER or a mastlib ZIP.

    Resolved the same way the compiler does (`story.json` -> a mission-local folder if it
    has an `__init__.mast`, else `__lib__/<lib>`), reusing the compiler's own
    `addon_source_folder` so the two cannot drift - a second copy of that rule is exactly
    the class of bug this session spent its time on. Cached per mission; empty and
    harmless when there is no story.json (tests, tools)."""
    if _DECLARED_ADDONS:
        return _DECLARED_ADDONS
    try:
        import json
        from sbs_utils import fs
        from sbs_utils.mast.mast import Mast
        script_dir = fs.get_script_dir()
        story = os.path.join(script_dir, "story.json")
        if not os.path.isfile(story):
            return _DECLARED_ADDONS
        with open(story, "r") as f:
            data = json.load(f) or {}
        lib_dir = os.path.join(fs.get_missions_dir(), "__lib__")
        for name in (data.get("mastlib") or []):
            src = Mast.addon_source_folder(script_dir, name)
            path = src if src is not None else os.path.join(lib_dir, name)
            if os.path.exists(path):
                _DECLARED_ADDONS.append(path)
    except Exception:
        pass
    return _DECLARED_ADDONS


def amd_declared_addons_clear():
    """Drop the cached addon list - the per-mission reset."""
    _DECLARED_ADDONS.clear()


def _read_from_addon(path, fname):
    """`fname` out of one addon - a folder on disk or a mastlib zip - or None."""
    try:
        if os.path.isdir(path):
            full = os.path.join(path, fname)
            if os.path.isfile(full):
                with open(full, "r") as f:
                    return f.read()
            return None
        import zipfile
        with zipfile.ZipFile(path, "r") as z:
            with z.open(fname.replace("\\", "/")) as f:
                return f.read().decode("utf-8")
    except Exception:
        return None


def amd_read_content(fname):
    """Read an AMD file (or an include) as text, in three steps:

    1. the CONSUMER MISSION folder, so a mission built on a library supplies its own;
    2. the addon the CALLING label came from (``media_read_relative_file``, which reads
       inside a packaged mastlib zip);
    3. any other addon this story DECLARES.

    Step 3 is what lets content live in an addon of its own. `media_read_relative_file`
    resolves relative to the calling label's source, so an addon holding only content is
    invisible to a renderer living in a different addon - which is why Open Universe's
    universes had to move to its mission root instead of becoming the opt-in addon they
    wanted to be. With step 3, a mission adds a content addon and the renderer finds it.

    Returns None when nothing resolves.
    """
    if not fname:
        return None
    mission_path = get_mission_dir_filename(fname)
    if mission_path is not None and os.path.isfile(mission_path):
        with open(mission_path, "r") as f:
            return f.read()
    found = media_read_relative_file(fname)
    if found is not None:
        return found
    for path in amd_declared_addons():
        found = _read_from_addon(path, fname)
        if found is not None:
            return found
    return None


def amd_has_content(fname):
    """True when `amd_read_content` would find something - the consumer mission's own
    copy, or one inside the addon that asks.

    For gating a TAB on whether there is anything to put in it. An addon registers its
    tab at module level, just by being listed in story.json, so a mission that loads the
    addon for its MACHINERY gets an empty tab it never asked for - Storm's Beacon got an
    empty codex the moment Open Universe's lore moved out of universe_core.

    Deliberately QUIET: `amd_read_content` warns when a file resolves nowhere, which is
    right when something is trying to READ it and wrong when something is only asking
    whether to offer it at all.
    """
    if not fname:
        return False
    mission_path = get_mission_dir_filename(fname)
    if mission_path is not None and os.path.isfile(mission_path):
        return True
    try:
        if media_read_relative_file(fname) is not None:
            return True
    except Exception:
        pass
    return any(_read_from_addon(p, fname) is not None for p in amd_declared_addons())


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


# --- the LORE registry -------------------------------------------------------
# Codex and Library were the same idea twice: an in-game readable document, rendered by
# the SAME `document_screen`, differing only in which .amd each tab hard-coded. Two tabs
# meant two chances to show an empty one, and no way for a third source to join.
#
# Now anything with lore registers it and ONE tab renders them merged, a top-level
# section per source. What follows from that, rather than being special-cased:
#   * nothing registered -> no tab, so a mission that loads the machinery without the
#     content does not get an empty shelf;
#   * a mission adds a lore addon and its section simply appears;
#   * a mission's own lore sits beside the libraries' as an equal.
_LORE_SOURCES = []


def lore_register(key, display, fname, domain=None):
    """Offer a document to the shared Library.

    `fname` is resolved by `amd_read_content` AT RENDER TIME, not now - a source may be
    declared before the mission that supplies the file is known, and resolving late is
    what lets a mission override a library's copy with its own.

    Registering the same key twice REPLACES it, so a mission can substitute a library's
    section wholesale by re-registering the key with its own file.
    """
    key = str(key).strip()
    if not key:
        return
    entry = {"key": key, "display": display, "file": fname, "domain": domain}
    for i, src in enumerate(_LORE_SOURCES):
        if src["key"] == key:
            _LORE_SOURCES[i] = entry
            break
    else:
        _LORE_SOURCES.append(entry)
    # Registering lore THAT RESOLVES is what makes there be a Library.
    #
    # The tab is not declared separately and then gated on "is there any lore yet?" -
    # that races, because addons load in a non-deterministic order and the answer would
    # depend on which ran first. Each registrant instead answers about its OWN file,
    # which cannot be asked too early: the file is on disk or in a zip either way.
    #
    # The `if` matters. universe_core registers its Codex unconditionally, so without it
    # every mission loading the universe ENGINE got a Library tab - Storm's Beacon has no
    # lore.amd and got an empty one, which is the empty-shelf bug wearing a new hat. The
    # source stays registered either way; it just does not conjure a tab it cannot fill.
    if not amd_has_content(fname):
        return
    try:
        from sbs_utils.procedural.gui.console_tab import gui_tab_add_top
        gui_tab_add_top("library")
    except Exception:
        pass          # no GUI context (tests, tools) - the registry still works


def lore_sources():
    """Registered sources, in registration order."""
    return list(_LORE_SOURCES)


def lore_clear():
    """Drop every registered source - the per-mission reset."""
    _LORE_SOURCES.clear()


def lore_available():
    """True when at least one registered source actually resolves to content.

    What the Library tab gates on. A source that registers but whose file is missing must
    not conjure a tab - that is the empty-shelf bug in its other form.
    """
    return any(amd_has_content(s["file"]) for s in _LORE_SOURCES)


def lore_document(title="Library"):
    """Every registered source merged into ONE document tree.

    Each source becomes a top-level section holding that file's own sections, so the
    Library reads as one book with a chapter per contributor rather than as several
    documents wearing different tab names. Sources that resolve to nothing are skipped
    silently - `lore_available` is where "there is nothing at all" is answered.
    """
    root = {"key": "__root__", "children": [], "description": "",
            "display_text": title}
    for src in _LORE_SOURCES:
        content = amd_read_content(src["file"])
        if not content:
            continue
        doc = document_get_amd_file(None, src["display"] or src["key"], content=content)
        kids = doc.get("children") or []
        kids = list(kids.values()) if hasattr(kids, "values") else list(kids)
        # A file with ONE root heading contributes that heading; a flat file contributes
        # a section of its own, so both shapes land as one chapter either way.
        if len(kids) == 1:
            node = kids[0]
            node["display_text"] = src["display"] or node.get("display_text")
            root["children"].append(node)
        elif kids:
            root["children"].append({"key": src["key"],
                                     "display_text": src["display"] or src["key"],
                                     "description": doc.get("description", ""),
                                     "children": kids})
    return root
