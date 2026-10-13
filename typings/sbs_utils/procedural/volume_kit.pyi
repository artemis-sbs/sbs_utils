def _debug (message):
    """log() has no handler in the engine; DEBUG reaches debug.log there. Both, because
    a kit that silently did not load looks exactly like a relic dressed in plates."""
def _kit_ships (name, manifest, folder):
    """Tell the engine about the pack's art - only if every piece's art is really there."""
def _manifest_path (name, path=None):
    """Where `ships/<name>_kit.json` is: an explicit folder, else the mission's media,
    else a pinned pack - the order `media_shared` already searches."""
def log (message: str, name: str = None, level: str = None, use_mast_scope=False) -> None:
    """Emit a log message using Python's ``logging`` module.
    
    When ``use_mast_scope=True`` the message is formatted through the current
    MAST task's string formatter first (MAST exposes this as ``log``).
    
    Args:
        message (str): The message to log. May contain MAST format strings when
            ``use_mast_scope=True``.
        name (str, optional): Logger name. Defaults to None (``__base_logger__``).
        level (str, optional): Logging level string, e.g. ``"DEBUG"``, ``"INFO"``.
            Defaults to None (``DEBUG``).
        use_mast_scope (bool, optional): Format the message via the current
            MAST task. Defaults to False."""
def volume_kit (name):
    """A registered kit's record, or None."""
def volume_kit_load (name, path=None, ships=True):
    """Load an art pack's kits. Returns the kit names registered - [] when nothing was.
    
    `name` is the pack (`"ruins"`); `path` an explicit folder holding its manifest, for a
    tool or a test. `ships=False` skips telling the engine about the art - only for a
    caller that already did, or a test with no engine.
    
    Idempotent: loading a pack twice registers it once."""
def volume_kit_names ():
    """Every registered kit."""
def volume_kit_piece (key):
    """A piece's record - kind, kit, size - or None for a key no kit knows."""
def volume_kit_pieces (kit, kind):
    """The piece keys a kit has for one kind - a surface kind with none borrows `wall`."""
def volume_kit_register (manifest):
    """Register a manifest's pieces and kits (already-loaded art). Returns kit names.
    
    The half of `volume_kit_load` that needs no files - what a test, or a mission that
    builds its own manifest, calls."""
def volume_kit_size (key, default=None):
    """A piece's world size at scale 1, `(x, y, z)`, or `default`."""
def volume_kits_clear ():
    """Forget every kit - the per-mission reset. The styles they added go too."""
def volume_kits_count ():
    """Reset-ledger probe. Must not create anything by asking."""
