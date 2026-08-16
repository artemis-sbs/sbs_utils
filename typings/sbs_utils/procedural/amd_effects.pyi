def _lerp (a, b, f):
    """Numbers, or tuples element-wise (so `Offset: 0,0,400 -> 0,0,0` closes in)."""
def _num (v, default=None):
    ...
def _parse_descriptor (desc):
    """A descriptor string back to kwargs, so a declared look can be re-emitted.
    
    Only ever consumes strings this module built, so it is a straight split rather
    than a parser - values stay strings, which the descriptor builder renders back
    unchanged."""
def _ramp (text):
    """`A -> B` -> (start, end), else None. Same arrow as a cutscene `Move:`."""
def _register_declared (spec):
    """Teach the charge driver a declared look, once, and return its name.
    
    The driver's table is keyed by name, so an authored record becomes a first-class
    charge look rather than a special case threaded through every call."""
def _spec_from (rec):
    """One AMD record -> the internal spec dict."""
def _truthy (v, default=False):
    ...
def _tuple_or_num (text):
    """`0, 0, 400` -> (0.0, 0.0, 400.0); a bare number -> that number; else the text."""
def amd_effects (section):
    """Load every effect record in ``section`` into ``EFFECT_AMD``. Returns how many."""
def amd_effects_clear ():
    """Forget every declared look. The reset hook."""
def amd_effects_count ():
    """Ledger probe."""
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
def effect_amd (key, obj, slot=None, priority=0, at=1.0):
    """Attach a declared look to an object (at its FULL value by default).
    
    Falls back to a Python preset of the same name when nothing is declared, so a
    caller never has to know which layer a look came from."""
def effect_amd_burst (key, where, at=1.0):
    """One-shot a declared look at an object or a point."""
def effect_amd_charge (key, obj, seconds=None, color=None, slot='warp_charge', priority=10):
    """Run a declared look as a BUILD-UP, ramping to its full value.
    
    A record's own ``Grows over:`` and ``Steps:`` supply the timing unless the caller
    overrides. When the key names no record, this falls through to the built-in
    charge looks (``coil``, ``arc``, ``preburn``, ``implode``, ``pulse``), so
    ``Jump Charge: coil`` works with nothing authored at all."""
def effect_amd_descriptor (key, at=1.0):
    """The descriptor string for a declared look at ramp position ``at`` (0.0-1.0).
    
    PURE - no engine, no objects, no side effects. That is deliberate: it makes the
    ramp arithmetic assertable headlessly, so the only thing left needing the engine
    is what the frame actually looks like.
    
    Returns None if the key is not declared."""
def effect_amd_look (key):
    """What ``key`` resolves to, or None if the name means nothing.
    
    Returns ``"amd"`` (an authored record), ``"preset"`` (an attachable look from
    the built-in table) or ``"charge"`` (a built-in BUILD-UP: coil, arc, preburn,
    implode, pulse). The order is the contract - an authored record shadows a
    shipped look of the same name.
    
    All three are answered because all three are nameable: a side writing
    ``Jump Charge: coil`` names a charge look, and a caller asking "does this
    resolve?" has to get a truthful yes for it."""
def effect_amd_names ():
    """Every declared look key."""
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
def particle_burst (where, preset=None, **kw):
    """Emit a one-shot burst at an object or a point.
    
    ``where`` may be an agent id / Agent / engine object (routed to
    ``sbs.particle_on``) or a ``Vec3`` / ``(x, y, z)`` (routed to
    ``sbs.particle_at``). Callers should not have to know which of the two engine
    calls their subject needs.
    
    Returns:
        bool: True if something was emitted."""
def particle_charge_start (obj, look=None, seconds=None, color=None, slot='warp_charge', priority=10, steps=None):
    """Ramp a build-up on an object's hull, so a jump reads as a wind-up.
    
    Stepped ``add_particle_emittor``, not a per-tick burst loop: a burst is
    one-shot, so driving several seconds of glow with it means hundreds of bursts
    whose appearance depends on the frame rate. This is ~``steps`` engine calls, at
    most ONE live emitter (slot replacement deletes the previous stage for free),
    and every stage is a descriptor string a test can assert on.
    
    SELF-LIMITING: it tears itself down after ``seconds`` whether or not anyone
    calls ``particle_charge_stop``. So an aborted jump, a destroyed ship or a culled
    cell cannot leave it burning, and no caller needs a guard.
    
    If the budget refuses the emitter it falls back to the ``pulse`` look, which
    holds no emitter - going silent would read as a bug rather than as restraint.
    
    Args:
        obj: the ship winding up.
        look (str): a name from ``particle_charge_looks()``. Default ``coil``.
        seconds (float): how long the build-up runs. Default 3.5. **0 disables it**,
            which is the valve that restores a hard cut.
        color (str): tint for looks that use ``{side}`` - pass the side's own color.
        slot (str): the registry slot to occupy.
        priority (int): default 10, so a story beat outranks ambient decoration.
        steps (int): how many stages the ramp is drawn in. Default 6.
    
    Returns:
        bool: True if a build-up is running."""
def particle_charge_stop (obj, slot='warp_charge', flash=True):
    """End a build-up. With ``flash``, snap a ring burst as it lets go.
    
    Safe when nothing is charging, and safe to call twice."""
def particle_descriptor (color=None, lifespan=None, image_cell=None, size=None, speed=None, count=None, align=None, shape=None, offset=None, smoke=None, delay=None, **extra):
    """Build a descriptor string from keyword arguments.
    
    ``None`` values are omitted. Unknown keys in ``extra`` are passed through - the
    grammar is only partly documented and refusing unknowns would freeze it - but
    each unknown name is logged once so a typo is still discoverable.
    
    Args:
        color: named, ``#RGB``, ``#RRGGBB``, or a 2-tuple/comma pair for "random between".
        lifespan (int): frames (30/sec) each particle lives.
        image_cell: sprite cell 0-15, or a pair for a random range.
        size (float): 0.1 - 100.0.
        speed (float): 0.1 - 10.0.
        count: particles per event, or a pair for a random range.
        align (bool): are ``offset`` values relative to the object's front.
        shape (str): ``hull``, ``line_x/y/z``, ``cone_x/y/z``, ``ring_x/y/z``.
        offset: ``(x, y, z)`` from the emit point.
        smoke (bool): True = smoke, False = additive "hot" particles.
        delay (int): frames before the particle appears.
    
    Returns:
        str: e.g. ``"align: True; shape: hull; color: black; lifespan: 60"``"""
def particle_effect (obj, preset=None, slot=None, priority=0, **kw):
    """Attach a persistent emitter to ``obj`` in a named slot.
    
    ``slot`` defaults to the preset name, so ``particle_effect(ship, "smoke")``
    occupies slot ``"smoke"`` and re-issuing it REPLACES rather than doubles. That
    one rule is what makes this safe to call from a loop or a watcher.
    
    ``priority`` decides who wins when the budget is full: a higher-priority effect
    evicts the oldest strictly-lower-priority one. A story beat should outrank
    ambient decoration.
    
    The engine ``lifeSpan`` is always -1 (never expires). Its units are unverified,
    so Python owns the lifetime instead: ``seconds`` then means the same thing on
    every machine and this registry is the single truth.
    
    Returns:
        int | None: the engine emitter id, or None if unknown preset / no engine
        object / the budget refused it."""
def particle_preset_get (name):
    """The raw kwargs dict for a preset, or None. Mission presets shadow built-ins."""
