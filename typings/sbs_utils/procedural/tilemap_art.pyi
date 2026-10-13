def _dress (spec, look):
    """Copy an art set's look onto one tileset kind (never its walk/see rules)."""
def _fill_facings ():
    """Give a figure the side it lacks: its east looks mirrored for west, or the
    reverse. Only a figure - something with south or north looks too - and never over a
    look a set or the mission drew. A look derived before is derived again, so it
    follows whatever set now draws the side it comes from."""
def _forget (key):
    ...
def _log (text, level='warning'):
    ...
def _twin_key (key):
    ...
def tilemap_art_clear ():
    """Forget everything the sets registered - footprints, origins, AND their atlas keys.
    
    The keys matter: ``ImageAtlas.all`` is process-wide, and a pack's facing frames left
    in it would still be found by ``tilemap_sprite_look`` for the next mission in the
    same interpreter (the dev runner reuses one), even one that never loads the pack."""
def tilemap_art_count ():
    """For the reset ledger."""
def tilemap_art_find (name):
    """The folder of an art set, relative to the mission, or None when no mission
    folder or pinned pack has one."""
def tilemap_art_ground (tileset, ground):
    """Give a tileset's kinds their looks from an art set. Kinds the tileset does not
    have are ignored; whether a kind can be walked or seen through is never touched."""
def tilemap_art_load (manifest, folder, name='set', tileset=None):
    """Register one manifest. ``folder`` is where its sheets are (relative to the
    mission, the way image paths are). Returns the sprite keys it registered."""
def tilemap_art_loaded ():
    ...
def tilemap_art_mirror (key, as_key, origin=None):
    """Register ``as_key`` as ``key`` mirrored left to right: the picture, the point that
    stands on the cell, and the ground it covers all flipped. False when ``key`` is not
    a registered atlas key."""
def tilemap_art_mirror_pairs (real, mirror=(), present=None):
    """The looks mirroring DERIVES, as ``[(source, key)]`` - pure, so a tool that reads
    the manifests itself (``tilemap_preview``) derives exactly what the game does.
    
    - A figure - something with south or north looks - that has one side's looks, east
      or west, but not the other's: each missing look, from the one it mirrors.
    - Each key in ``mirror`` (``"mirror": true``): its twin, ``<key>_mirror``.
    
    Args:
        real: the keys a set really draws - never a derived one.
        mirror: the keys marked ``"mirror": true``.
        present: every key drawn for real, sets or not (a mission's own); defaults to
            ``real``. A look already present is never replaced."""
def tilemap_art_origin (key):
    """Which set supplied a sprite key, or None - for a debug line and for tests."""
def tilemap_art_sets (default=None):
    """The sets a mission should load, in order: ``builtin`` and then whatever the
    ``TILE_ART`` setting names (a list, or a comma separated string).
    
    Args:
        default (str | list, optional): what to use when the setting says nothing."""
def tilemap_art_use (*sets, tileset=None):
    """Load art sets in order, later ones overriding earlier ones key by key.
    
    Args:
        *sets (str): set names - ``tileart/<name>`` in this mission or a pinned pack.
            With none, ``tilemap_art_sets()``: ``builtin`` plus the ``TILE_ART`` setting.
        tileset (str | list, optional): the tileset - or tilesets - whose kinds the
            sets' ``ground`` dresses.
    
    Returns:
        list: the sets that were found and loaded."""
def tilemap_sprite_base (key, rect=None):
    """Say how much GROUND a sprite stands on, so a big prop blocks all of it.
    
    Args:
        key (str): the atlas key.
        rect: ``(left, top, right, bottom)`` in tiles, from the centre of the actor's cell
            (x east, y south). A parked car three tiles long, nose east, is about
            ``(-1.6, -0.55, 1.6, 0.55)``. ``None`` forgets it: one cell, the old way."""
def tilemap_sprite_cells (key):
    """The cells a sprite covers, as ``(dx, dy)`` offsets from its actor's own cell.
    
    Always holds ``(0, 0)``; a sprite with no ``base`` covers just that. Every other
    cell is covered when more than half of it is under the base, each way."""
def tilemap_sprite_footprint (key):
    """``(w, h, anchor x, anchor y)`` for a sprite - one flat cell unless told."""
def tilemap_sprite_size (key, w=1.0, h=1.0, anchor=(0.5, 1.0)):
    """Say how big a sprite is drawn, in tiles, and which point of it stands on the
    actor's cell (fractions of the sprite; the default is its bottom-center)."""
def tilemap_sprite_twin (key):
    """The mirrored twin a still prop may be drawn with (``"mirror": true``), or None."""
