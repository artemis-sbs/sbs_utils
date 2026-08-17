from sbs_utils.mast.mast_node import MastDataObject
def _amd_relic_numbers (value):
    """Every number in a value, comma or space separated. Non-numeric words are skipped,
    so `hub 300` yields [300.0] and the word survives for the caller to read."""
def _amd_relic_pairs (value):
    """`hub 300, gallery 240` -> [("hub", 300.0), ("gallery", 240.0)].
    
    Comma-separated groups, each a name plus a radius. A group with no radius yields
    None for it, so the caller can fall back to a default rather than guess here."""
def _amd_relic_words (value):
    """Every non-numeric word in a value - the names in `hub 300, gallery 240`."""
def _relic_arm_tick ():
    """Start the shared tick, once, and only while something is waiting on it."""
def _relic_contents_tick (t=None):
    """Place every armed record whose trigger has now fired, and light up the places the
    crew has reached."""
def _relic_mark_placed (obj, c):
    """Give a placed thing the ROLES of the place it was placed, and its relic's key.
    
    An author already says what a spot is for - `Roles: vault_door, relic_piece` - and
    saying it twice, once for the marker and once for the thing sitting there, is how the
    two drift apart. So the roles carry over, and the object knows which ruin it is in.
    
    That second half is what makes "carry it OUT" answerable at all: the containment latch
    tracks ships, and a thing on the end of a tether is not one, so the only way to ask
    whether the treasure has left is to ask the treasure which ruin to measure against."""
def _relic_part_pos (rec, name, base=None):
    """Where a named part is, in world coordinates - point, chamber or box."""
def _relic_place_contents (c):
    """Put one content record in the world: its item, then its spawns.
    
    Failures are logged and stepped over rather than raised. Half a placed ruin beats a
    tick that dies on the first unregistered key and silently places nothing after it."""
def _relic_place_role_markers (rec, relic_key, reveal=None):
    """Put a measuring post at every point carrying `Roles:`.
    
    This is the plumbing behind `Starts when: reach <role>`. The quest driver's reach test
    measures a player against OBJECTS HOLDING A ROLE, so a role written on a point is only
    half the sentence until something is standing there. An author should never have to
    know that, so arming supplies the other half.
    
    IT STARTS INVISIBLE AND EARNS ITS PLACE ON THE RADAR. These were `marker_object`s at
    first - selectable, radar-gold - which put a blip on every room, every cache and every
    trigger the moment the ruin was built. A dungeon that draws its own floor plan is not a
    dungeon; the crew arrives already knowing which rooms matter and where the treasure is.
    
    Invisible for good is no better - the crew has no record of where they have been, in a
    structure whose whole problem is that it all looks alike. So a post is dark until a
    ship reaches it, and then it lights up and stays lit: the ruin draws its own map, in
    the order you fly it. `_relic_reveal_tick` is the other half.
    
    Marked with `relic_marker` and keyed by (relic, part) so a reload replaces rather than
    accumulates - the same identity rule the contents use."""
def _relic_reached (rec, args):
    """The same test quest_tick_reach runs: any player within radius of any object
    holding the role."""
def _relic_reveal_tick ():
    """Light up the markers the crew has reached. The ruin drawing its own map.
    
    Runs on the same shared tick as the contents triggers, and for the same reason: one
    tick for every relic beats a watcher per point.
    
    A revealed marker STAYS revealed - it is a record of where the crew has been, which is
    the whole value of it in a structure where every room looks like the last one."""
def _relic_signal_observer (name, data=None):
    ...
def _relic_spawn_phrase (phrase, pos, c):
    """`raider x2`, `skaraan 4`, `raider` - the `Guards:` grammar, one entry.
    
    Scattered rather than stacked: several NPCs on one point would spawn inside each
    other. The spread is small on purpose - they should read as being IN the room the
    author put them in, not near it."""
def _relic_timer_done (rec, args):
    """`5 minutes` - measured from the moment the record was ARMED, not from mission
    start, so a relic armed late still gives its full delay."""
def _relic_trigger (phrase):
    """Parse a `Starts when:` phrase, or None when there is none.
    
    Uses the quest layer's own parser, so the vocabulary is the one the author already
    knows. An unevaluable phrase is NOT silently swallowed - `relic_contents_can_trigger`
    is what lint calls to say so before the mission ever runs."""
def _relic_trigger_fired (rec):
    ...
def amd_coords (s, n=2):
    """'6, 4' -> [6, 4] (the first `n` signed-integer tokens)."""
def amd_parse_facts (text, handler=None, default=<function amd_num at 0x0000028640FEBF60>, archetype=None, errors=None):
    """Parse one fact-sheet fence into a dict.
    
    Per label, in order: the caller's `handler` gets first refusal (returns truthy to
    consume it); then the FIELD REGISTRY, when the field is declared for `archetype` -
    which resolves the alias, coerces by the declared type and stores under the runtime
    key; then `default` (historically `amd_num`) for anything undeclared, so an unknown
    field behaves exactly as it does today.
    
    `errors` may be a list - parse problems are appended to it in a writer's terms
    rather than raised, so a typo never takes a mission down; the linter is what makes
    them loud. Returns `data`, carrying the kind line (when present) under `KIND_KEY`."""
def amd_relic_data (text):
    """Parse one relic fence into a data dict."""
def amd_relic_facts ():
    """``amd_parse_facts`` handler for relic fences.
    
    Unknown labels return None so they chain to the field registry and then to the
    default coercion - the same contract ``amd_landmark_facts`` follows."""
def amd_section (doc, key):
    """The named section node under the root, or None when absent (e.g. a legacy flat file
    with no sections -> the caller iterates the root's children instead)."""
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
def relic_contain (record, name=None):
    """Start containment for a built relic, honoring its authored fields.
    
    Returns the watcher, or None if the volume has not been built yet."""
def relic_contents (relic_key):
    """Every authored content record for a relic, with its world position resolved.
    
    `[{part, item, qty, spawn, starts_when, pos}]`. The position comes from whichever part
    carries it - a point marks a spot, a chamber means "somewhere in this room" and
    resolves to its centre."""
def relic_contents_arm (relic_key, radius_default=900.0, reveal=1200.0):
    """Arm a relic's authored contents. Returns how many are waiting on a trigger.
    
    Three things happen, in this order:
    
    1. Every point carrying `Roles:` gets a **role marker** - an invisible, selectable
       object at that spot holding those roles. That is what makes `Starts when: reach
       <role>` work at all, since the quest driver's reach test measures against OBJECTS
       holding a role, and it is the plumbing an author should never have to think about.
    2. Contents with no trigger are placed now. That is the common case - a ruin with
       things in it - and it needs no word in the file.
    3. The rest are armed and checked by ONE shared tick, in the pattern
       `quest_tick_reach` established: a watcher per item would be the same work done
       many times.
    
    Idempotent by (relic, part): re-arming, or a live reload, places nothing twice."""
def relic_contents_can_trigger (phrase):
    """True when `phrase` is one this can actually evaluate. What lint asks."""
def relic_contents_clear (relic_key=None):
    """Forget what has been armed and placed. Does not delete objects.
    
    With no key this is the mission reset: everything, including the signal observer and
    the shared tick, since the world is going away anyway.
    
    With a KEY it forgets one relic - the galaxy case, where a system is torn down while
    other systems are still live. The observer and the tick stay, because the relics that
    are still standing are still waiting on them."""
def relic_contents_count ():
    """How many content records are armed. The reset-ledger probe - an armed record that
    survives a mission reset would place loot in the NEXT mission."""
def relic_contents_state (relic_key, part):
    """`"placed"`, `"waiting"` or `"unarmed"` for one content record.
    
    What a report or a test asks. Distinguishing WAITING from UNARMED matters: both look
    like "the loot is not there", and only one of them is a bug."""
def relic_keys ():
    """Every registered relic key."""
def relic_place (record, x, y, z):
    """Put a relic somewhere at RUNTIME, overriding its authored `Loc:`.
    
    An `.amd` cannot know where a relic will stand when the world decides that late. An
    Open Universe cell has a transient world origin - the same system lands at a different
    slot on a different visit - so a galaxy relic has to be placed when the cell is built,
    not when the file is read.
    
    Every reader goes through `relic_pos`, so setting `loc` here moves the geometry, the
    points, the contents and the containment together. Anything already built keeps the
    position it was built at: place BEFORE `relic_volume`.
    
    Takes the record (or a key) and returns it, so it reads as one step in a build."""
def relic_point (relic_key, name):
    """The WORLD position of a named point in a relic, or None.
    
    Points are authored RELATIVE to the relic's `Loc:`, like every other part, so this
    shifts them - which is the whole reason a point belongs in the relic rather than being
    a landmark of its own. Move the relic and its cache, its entrance and its ambush move
    with it; a landmark's `Loc:` is absolute and would stay behind.
    
    What goes there is the mission's business::
    
        item_spawn("relic_core", *relic_point("ossuary", "cache"), qty=2)
        npc_spawn(*relic_point("ossuary", "picket"), "Sentry", "raider", ...)
        marker_point(*relic_point("ossuary", "mouth"), "The Ossuary")"""
def relic_point_roles (relic_key, name):
    """The roles authored on one point, lowercased. Empty when it has none."""
def relic_points (relic_key, role=None):
    """Every point in a relic as `{name: (x, y, z)}` in world coordinates.
    
    `role` narrows to one purpose - `relic_points("ossuary", "spawn")` for every place an
    NPC may appear, `"entrance"` for the ways in. Roles are matched lowercased, the way
    they are authored."""
def relic_pos (record):
    """A relic's world [x, y, z] - its ``Loc:``, else the origin.
    
    Deliberately simpler than ``landmark_pos``: relics have no galaxy placer, because
    the landmark one has never been used by a shipped mission (Open Universe rolls its
    own). If a galaxy mission needs one, add it the way landmarks did rather than
    assuming this hook exists."""
def relic_record (key):
    """The registered record for ``key``, or None."""
def relic_release (key):
    """Tear ONE relic down: stop its containment, drop its volume, forget what was armed.
    
    The counterpart to building a relic into a world that comes and goes. A galaxy tears a
    system down while the next one is already being built, so the whole-registry verbs
    (`volume_clear`, `relics_clear`) are the wrong tools there - they would take the relic
    the crew is currently inside.
    
    The RECORD stays registered: the relic is a thing the mission still knows about and
    may rebuild on the next visit. Objects are not deleted either - whoever tore the world
    down did that, and a relic outliving its props is not this function's business."""
def relic_reload (key):
    """Re-read one relic's `.amd` and rebuild its volume in place. Returns a summary dict.
    
    THE POINT: this is what a live preview needs, and until now every mission had to write
    it. The editor's Preview button can only ring a doorbell over the debug channel; the
    rebuild has to happen inside the running mission, so it belongs here rather than in
    the tool. See `cosmos_dev.mission_runner`'s `relic_reload` debug action, which calls
    this and needs no mission code at all.
    
    Geometry only. The props a mission scatters over the walls are its own art, and this
    cannot know what they are - so it emits `relic_rebuilt` afterwards and a mission that
    draws walls re-dresses on that signal.
    
    Rebuilds UNDER THE SAME VOLUME NAME, so a watcher, a brain, or a stored id that
    addresses the relic keeps addressing it. Containment is re-applied from the AUTHORED
    fields (`relic_contain`), so an edit to `Margin:` or `Containment:` takes effect on
    the same Preview as an edit to a chamber - which is the whole promise of authoring it
    declaratively.
    
    Returns `{"key", "volume", "source", "chambers", "passages", "boxes", "solids"}`, or
    `None` if the key is unknown or the record has no source (built in code, not read
    from a file - there is nothing to re-read)."""
def relic_volume (record, name=None):
    """Build the navigable volume for a record and return it.
    
    The layout is authored RELATIVE to the relic's Loc, so the record's position becomes
    the volume's origin - which is what lets the same layout be placed twice."""
def relic_volume_name (record, name=None):
    """Which volume a record's geometry lives in: an explicit name, else the one the
    record actually BUILT, else its key.
    
    The middle term is the one that matters. A mission is free to build a relic under a
    name of its own (`relics_build(..., name="relic")`), and when it does, anything that
    guesses the record's key instead - containment, reload - silently addresses a volume
    that does not exist and does nothing at all. That is not hypothetical: it is why the
    Ossuary's authored `Scrape band: 120` never once reached its watcher."""
def relics_build (file_path, section_key='relics', name=None):
    """Load a file, build the first relic's volume, and return (record, volume).
    
    The whole declarative path in one call, for the common case of a mission with one
    relic. `name` overrides the volume's name; it defaults to the relic's own key."""
def relics_clear ():
    """Drop every registered relic record. Called by reset_mission_state()."""
def relics_count ():
    """Number of registered relic records. The reset-ledger probe."""
def relics_from_section (section, source=None, section_key=None):
    """Relic records from a section node's children, each with its parts attached.
    
    Grouping mirrors the cutscene reader: a record naming a relic is a part of it,
    collected in DOCUMENT ORDER; a record naming none is the relic itself.
    
    `source` and `section_key` are carried onto every record so the relic can be REBUILT
    from its file later - see `relic_reload`. They are the reader's own arguments, not
    anything the author writes; without them a record is a snapshot with no way back to
    the text it came from, and a live preview has to be written per mission."""
def relics_load (file_path, section_key='relics', content=None):
    """Read relics straight from an `.amd` file. The verb a mission actually wants.
    
    Without this every mission repeats the same three lines - load the document with the
    relic fence handler wired in, find the section, walk it - and the fence handler is
    the part that is easy to forget. Miss it and every field silently falls through to
    the default coercion, so `Chamber: 0, 0, 0, 900` becomes a string and the relic
    builds as nothing.
    
    Returns the records; they are registered too, so `relic_record(key)` finds them
    later on a story cue.
    
    `content` is the text, for a caller that has already read it - an addon inside a
    packaged `.mastlib` cannot open its own files by path, so it resolves them with its
    own reader and hands the text over. `file_path` is still recorded as the source, so a
    live editor reload knows what to re-read."""
def relics_register (section, source=None, section_key=None):
    """Remember every relic record in ``section`` by key, without building any.
    
    Separate from ``relics_build`` for the same reason landmarks are: a mission builds
    most of its relics at setup, but a story beat reveals one on cue, and both need the
    same record."""
def relics_reload_all ():
    """Re-read every relic that came from a file. Returns a list of summaries.
    
    What the editor's Preview posts when it does not name one - the common case of a
    mission with a single relic, where naming it would only be a way to get it wrong."""
def signal_emit (name, data=None):
    """Emit a named signal, running all registered ``//signal/<name>`` routes.
    
    Safe to call when no MAST context is active — returns immediately with no
    side effects.
    
    Args:
        name (str): The signal name.
        data (dict, optional): Arbitrary data passed to each signal handler.
            Defaults to None."""
def volume_define (name, chambers=None, passages=None, boxes=None, solids=None, origin=None):
    """Create (or replace) a named volume.
    
    Declarative form - `chambers` maps a name to (x, y, z, radius), `passages` is a
    sequence of (a, b, radius) where a and b are chamber names or explicit points:
    
        volume_define("relic",
                      chambers={"hub": (0, 0, 0, 1200)},
                      passages=[("hub", "spine", 300)])
    
    `origin` PLACES the whole layout: every coordinate is treated as relative to it.
    That is what lets one authored layout be dropped at two different points in a
    system - without it a layout is welded to the absolute coordinates it was written
    at, and a second copy means editing every number. Radii and half-extents are
    sizes, not positions, so they are never shifted; a passage naming a chamber needs
    no shift either, since the chamber it names has already moved."""
def volume_get (name):
    """The named volume, or None."""
def volume_watch (volume, agents=None, scrape_band=120.0, margin=0.0, govern=True, clamp=True, seconds=0, hold='tractor', speed_limit=None, block_jump=False, engage='entered'):
    """Start enforcing containment for a volume. Replaces any existing watch.
    
    ENGAGEMENT - who this applies to, which is not the same question as who is watched.
    
    A tier is a pure depth test, so a ship that has never been near the relic reads
    BREACH exactly like one that just punched through a wall: measured, a ship 80,000
    units away came back BREACH and, under the default agent set of every player, was
    tractored toward the relic. That is not containment, it is a fishing net.
    
    So a ship is contained ONCE IT HAS BEEN INSIDE, and released when it leaves the
    bounding sphere. Fly in through a mouth - a chamber or passage that reaches out past
    the hull - and you are inside the volume before you are deep in it, so the latch
    catches without a breach ever happening. Fly out and away and it lets go. A ship that
    never entered is never touched, which is what makes an entrance possible at all and
    what stops a relic in one corner of a system grabbing everything in it.
    
    `engage="always"` restores the old behaviour for a volume that IS the playfield.
    
    Args:
        volume: Volume or its name.
        agents: None for players+fighters (the default set), a CALLABLE returning a
            set - re-evaluated every tick, so arrivals and departures need no
            wiring - or a static set.
        scrape_band (float): how far past the wall a scrape becomes a breach.
        margin (float): how far inside the wall the clamp puts a breached ship.
        govern (bool): cap `playerThrottle` to impulse while breached.
        clamp (bool): project a breached ship back inside.
        seconds (int): tick interval; 0 = every tick, which is what containment
            wants - it is a handful of float ops per agent.
    
    Signals fire on tier CHANGE only, never per tick, each carrying
    ``{"volume": name, "id": agent_id, "depth": float}``:
        ``volume_scrape``    - entered the wall
        ``volume_breach``    - went past the scrape band
        ``volume_recovered`` - back inside
    
    Route the consequences: ``//shared/signal/volume_scrape`` for damage or scoring
    (server-once), ``//signal/volume_scrape`` only for per-console display."""
def volume_watching (name):
    """True if a volume is currently enforced."""
