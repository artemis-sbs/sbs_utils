def _deck_only (docs):
    """True when everything the documents put on the ground is aboard `Area: deck` - a
    boarding mission with no ground of its own, which needs no .tiles file."""
def _default_looks ():
    """The looks the loaded art can draw, where the mission chose none of its own."""
def _load_art (tilesets):
    """Load the art sets that are installed. Returns ``(loaded, missing)``."""
def _only_new (section, known):
    """The section's records nothing has declared yet, as a section."""
def _read (path):
    ...
def _say (message, once=None, loud=False):
    """Tell the author. ``loud`` also writes ``mast.runtime``, which a headless test
    fails on - for a mistake in the mission's own files, never for art that is merely
    not installed on this machine."""
def _sections (docs, keys):
    """Every section, across the documents, whose key is one of ``keys``."""
def _why_unplaced (key):
    ...
def boarding_ground_clear ():
    """The per-mission reset: nothing loaded, nothing said, and the default looks this
    module chose are handed back so the next mission's art decides its own."""
def boarding_ground_count ():
    """Reset-ledger probe."""
def boarding_ground_files (folder=None):
    """The tileset and area files of a mission: ``(tilesets, areas)``, sorted paths.
    
    The same recursive ``*.tileset`` / ``*.tiles`` search ``tilemap_world`` makes for the
    linter, less anything under a folder whose name starts ``__`` or ``.`` - a built
    ``__site__``, a ``.git`` - which hold copies, not the mission."""
def boarding_ground_load (doc=None, folder=None):
    """Load a mission's ground: its tile files, its art, and what stands on it.
    
    Args:
        doc (optional): the parsed mission document - what
            ``document_get_amd_file(..., data_parser=amd_mission_data)`` returns - or a
            list of them when the world and its scenes are separate files. Without one
            only the tile files and the art are loaded.
        folder (str, optional): where to look for ``*.tileset`` / ``*.tiles``. The
            mission folder by default.
    
    Returns:
        dict: what was done - ``tilesets``, ``areas``, ``props``, ``people``, ``scenes``,
        ``skills`` (counts), ``art`` (the sets loaded),
        ``art_missing`` (the sets named and not installed), and ``unplaced`` (the keys of
        props and people that could not be put on the map: an ``Area:`` that is no area,
        a ``Mark:`` the area file does not have). Each of those is also said in
        ``mast.runtime.log``."""
def boarding_ground_loaded ():
    """What the last ``boarding_ground_load`` reported, or None before the first."""
def boarding_ground_scenes ():
    """The scenes the loaded documents hold, ``{key: scene}`` - what a prop's ``Scene:``
    and a person's ``Talk scene:`` name, and what ``boarding_visit`` is handed."""
def boarding_ground_unplaced ():
    """The keys of props and people that should be on the map and are not, sorted.
    
    Not the ones that are meant to be absent: hidden until a signal, picked up, down."""
