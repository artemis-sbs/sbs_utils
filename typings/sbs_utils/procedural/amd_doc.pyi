from sbs_utils.mast.mast_node import MastDataObject
def _amd_file_list (data):
    """Section `File:`/`Files:` values -> a flat list of paths. Robust to any data_parser:
    the key may be any case (a friendly parser lowercases it; the default reader keeps case)
    and a value may be a string (one path, or a comma list) or an already-split list."""
def _read_from_addon (path, fname):
    """`fname` out of one addon - a folder on disk or a mastlib zip - or None."""
def amd_declared_addons ():
    """Every addon this story declares, as a path to a source FOLDER or a mastlib ZIP.
    
    Resolved the same way the compiler does (`story.json` -> a mission-local folder if it
    has an `__init__.mast`, else `__lib__/<lib>`), reusing the compiler's own
    `addon_source_folder` so the two cannot drift - a second copy of that rule is exactly
    the class of bug this session spent its time on. Cached per mission; empty and
    harmless when there is no story.json (tests, tools)."""
def amd_declared_addons_clear ():
    """Drop the cached addon list - the per-mission reset."""
def amd_document (content, data_parser=None, title='Document'):
    """Parse AMD ``content`` into a document tree (one root heading whose children are the
    sections). ``data_parser`` coerces each ``---`` fence (e.g. amd_quest_data /
    amd_scan_data / a mission's own); ``title`` names the root when the content has none.
    Headings are the link form ``# [Display](key)`` so ``#`` stays STRUCTURAL only."""
def amd_fill (template, values):
    """Fill a template's ``{slot}`` placeholders from ``values`` via ``format_map``, leaving
    UNKNOWN slots literal (missing-key-safe). Returns ``""`` for an empty/None template. Pairs
    with amd_text_map: load prose templates once, fill their slots per use."""
def amd_has_content (fname):
    """True when `amd_read_content` would find something - the consumer mission's own
    copy, or one inside the addon that asks.
    
    For gating a TAB on whether there is anything to put in it. An addon registers its
    tab at module level, just by being listed in story.json, so a mission that loads the
    addon for its MACHINERY gets an empty tab it never asked for - Storm's Beacon got an
    empty codex the moment Open Universe's lore moved out of universe_core.
    
    Deliberately QUIET: `amd_read_content` warns when a file resolves nowhere, which is
    right when something is trying to READ it and wrong when something is only asking
    whether to offer it at all."""
def amd_includes (doc):
    """One ``(key, file)`` record (MastDataObject) per file to splice - a section may name
    several (repeat ``File:`` or a comma ``Files:`` list), in order. The caller reads each
    file and calls ``amd_splice``. Parser-agnostic: works whether the fence parser left
    ``file`` as a list, a single string, or a ``files`` comma string."""
def amd_read_content (fname):
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
    
    Returns None when nothing resolves."""
def amd_records (section):
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
def amd_root_data (doc):
    """Document-wide config (``{}`` if none).
    
    There are two places this can be written and they used to mean different things:
    the FRONT-MATTER fence (before any heading, which the parser attaches to the
    synthetic document root) and the first ``#`` heading's own fence. `amd_core`
    called the first one "root"; this module called the second one "root".
    
    Front matter now wins, because it is the only one that works for the flat files -
    nine of the corpus's files are a bare list of records with no title heading to
    hang config on. The title heading's fence is still merged underneath it, so every
    existing file keeps working; front matter simply takes precedence on a clash."""
def amd_root_node (doc):
    """The single level-1 root heading node (the file's root content), or None."""
def amd_section (doc, key):
    """The named section node under the root, or None when absent (e.g. a legacy flat file
    with no sections -> the caller iterates the root's children instead)."""
def amd_splice (doc, section_key, included_doc):
    """Append an included file's top-level entries as children of the named section."""
def amd_text_map (section):
    """A section's per-heading prose as a ``{key: text}`` lookup: each child's ``key`` mapped
    to its stripped ``description``. Built as plain data (not interpolated at load) so a mission
    can load a section of prose TEMPLATES once and fill their ``{slots}`` later (see amd_fill).
    Returns ``{}`` when ``section`` is None."""
def document_get_amd_file (file_path, root_display_text='', strip_comments=True, content=None, data_parser=None, allow_bare_headings=False):
    """Parse an AMD markdown file into a nested quest/document structure.
    
    AMD files use ``# [Display Name](key)`` headings to define hierarchical
    sections. The heading level controls depth (``#`` = level 1, ``##`` = level
    2, etc.). Lines between headings are accumulated as the section's
    ``description``. Lines starting with ``//`` are stripped when
    ``strip_comments`` is ``True``. Query-string parameters in the key URI
    (``key?param=value&…``) are parsed as extra attributes on the section.
    
    Returns a dict with keys ``"key"``, ``"display_text"``, ``"description"``,
    and ``"children"`` (list of the same structure). On parse error the
    exception message is returned as the root ``"display_text"``.
    
    Args:
        file_path (str | None): Path to the ``.amd`` file to read. Ignored if
            ``content`` is provided.
        root_display_text (str, optional): Label for the root node.
            Defaults to ``""``.
        strip_comments (bool, optional): Skip ``//`` lines. Defaults to
            ``True``.
        content (str | None, optional): Raw AMD text to parse instead of
            reading ``file_path``. Defaults to ``None``.
    
    Returns:
        dict: Nested document tree rooted at ``"__root__"``.
    
    Example:
        doc = document_get_amd_file("consoles/quest.amd", "Quests")
        items = document_flatten(doc)"""
def get_mission_dir_filename (filename):
    """Get the full path to a file in the current mission directory.
    
    Args:
        filename (str): The relative path from the mission directory.
    
    Returns:
        str: The full path to the file in the mission directory."""
def lore_available ():
    """True when at least one registered source actually resolves to content.
    
    What the Library tab gates on. A source that registers but whose file is missing must
    not conjure a tab - that is the empty-shelf bug in its other form."""
def lore_clear ():
    """Drop every registered source - the per-mission reset."""
def lore_document (title='Library'):
    """Every registered source merged into ONE document tree.
    
    Each source becomes a top-level section holding that file's own sections, so the
    Library reads as one book with a chapter per contributor rather than as several
    documents wearing different tab names. Sources that resolve to nothing are skipped
    silently - `lore_available` is where "there is nothing at all" is answered."""
def lore_register (key, display, fname, domain=None):
    """Offer a document to the shared Library.
    
    `fname` is resolved by `amd_read_content` AT RENDER TIME, not now - a source may be
    declared before the mission that supplies the file is known, and resolving late is
    what lets a mission override a library's copy with its own.
    
    Registering the same key twice REPLACES it, so a mission can substitute a library's
    section wholesale by re-registering the key with its own file."""
def lore_sources ():
    """Registered sources, in registration order."""
def media_read_relative_file (file):
    """Read a file sitting beside the .mast that is running - from the addon's zip when
    that .mast came from a mastlib, else from its folder.
    
    EVERY failure is logged and named. It returns None on failure, and a None flows
    straight into `document_get_amd_file(content=None)`, which yields an empty tree that
    renders as a flat, contentless page - a screen that looks broken while saying
    nothing about why. Reported as: a document whose headings "stopped being
    recognized", running a mission that gets this addon from a mastlib."""
class _AmdFormatDict(dict):
    """format_map helper: an unfilled ``{slot}`` is left LITERAL rather than raising."""
    def __class_getitem__(*argv):
        """See PEP 585"""
    def __missing__ (self, key):
        ...
