from sbs_utils.helpers import FrameContext
def _log (message):
    ...
def _move (text):
    """`0,400,-3000 -> 0,120,-600` -> [from, to]. None when it will not parse."""
def _num (v, default=None):
    ...
def _playable (shots):
    """Resolve subjects NOW (the objects exist by the time we play) and drop the
    shots that cannot be resolved, each with a reason."""
def _resolve_subject (name, shot_key=''):
    """Cast first, then a role, else None (and say which shot, and why)."""
def _shot_from (rec):
    """Build a shot dict from an AMD record. Subject stays a NAME here and is
    resolved at play time - the object does not exist at load."""
def _split_transition (body):
    """A shot body -> `(transition, prose)`.
    
    `FADE IN:` / `> CUT TO:` in a shot's body says how the shot ARRIVES, exactly the
    way a screenplay says it. It is structure, not overlay text, so it comes out of
    the prose here - otherwise the words "CUT TO:" would render on screen as the
    shot's title. This is what lets a cutscene file read as a screenplay and still be
    the shot list the engine plays."""
def _truthy (v, default):
    ...
def _vec (text):
    """`0, 900, -4000` -> (0.0, 900.0, -4000.0). None when it will not parse."""
def amd_body_transition (line):
    """The transition a body line names (`CUT TO:`), or None.
    
    Either Fountain's forced form (`> CUT TO:`) or one of the bare spellings every
    screenwriter already types. Returned uppercase so a renderer never has to care
    which was written."""
def amd_cutscene_clear ():
    """Drop every loaded cutscene/rundown/cast - the per-mission reset."""
def amd_cutscenes (section):
    """Load every cutscene, shot and rundown in ``section``.
    
    Returns ``{"cutscenes": {...}, "rundowns": {...}}``. A record with
    A record carrying ``Cutscene:`` or ``Rundown:`` is a SHOT; one carrying neither is
    that cutscene's BED (matched to its shots by key).
    
    NOT ``Scene:``: that field is already a lifeform's dialogue scene, and the schema
    INFERS the lifeform archetype from it (``("scene", "lifeform")``), so a shot
    carrying it would be typed as a character. ``Cutscene:`` also pairs symmetrically
    with ``Rundown:`` - both name the container the shot belongs to."""
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
def cutscene_amd (key, to=None, consoles=None, **overrides):
    """Play a cutscene declared in AMD. Returns the Promise, or None if unknown."""
def cutscene_cast (name, obj=None):
    """Bind (or read) a cast name used by ``Subject:`` in AMD shots.
    
    The film idiom: the script says "hero", the production decides who that is. It
    also means one scene can be replayed with a different ship without touching the
    ``.amd``."""
def cutscene_cast_clear ():
    ...
def cutscene_define (name, shots, letterbox=True, skippable=True, bar=4, release=True):
    """Register a cutscene under ``name``.
    
    Args:
        name (str): what ``cutscene_play`` will look up.
        shots (list[dict]): in order. Per shot:
            ``subject`` (required) - what the shot looks at, and necessarily what
            the lens rides; ``lens`` (world position) OR ``move`` ([from, to]);
            ``seconds`` (default 4); ``ease``; ``overlay`` ({"kind": ..., plus that
            kind's fields}).
        letterbox (bool): black bars for the duration.
        skippable (bool): whether ``cutscene_skip`` ends it.
        bar (float): letterbox bar height in em.
        release (bool): hand the camera back to the engine's director at the end.
            Leave it True unless the next thing the story does is set its own shot -
            a cutscene that ends still holding a dolly will drop to the engine
            default the moment that object is deleted.
    
    Returns:
        dict: the stored cutscene."""
def cutscene_play (name_or_shots, to=None, consoles=None, **overrides):
    """Play a cutscene and return a Promise that resolves when it ends.
    
    Args:
        name_or_shots: a name from ``cutscene_define``, or a list of shots to play
            without registering one.
        to: audience (see ``consoles_of``).
        **overrides: any ``cutscene_define`` field, for this run only.
    
    Returns:
        Promise: resolves with ``{"skipped": bool, "shots": int, "name": str}``."""
def rundown_add (name, subject, lens=None, move=None, seconds=4, ease='in_out', label=None, overlay=None):
    """Add (or replace) a shot in the rundown.
    
    Args:
        name (str): how the director refers to it.
        subject: what the shot looks at - and necessarily what the lens rides.
        lens: world position for a static shot.
        move: ``[from, to]`` world positions for a moving one.
        seconds (float): duration of a ``move`` (a static shot holds until punched away).
        label (str, optional): what the director's tile says. Defaults to ``name``.
        overlay (dict, optional): furniture to show with it, ``{"kind": ..., ...}``.
    
    Returns:
        dict: the stored shot."""
def rundown_amd (key):
    """Load a declared rundown's shots into the live rundown. Returns how many."""
