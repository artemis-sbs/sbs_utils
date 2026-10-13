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
def _persist_provider_register (name, snapshot_fn, restore_fn, library=False):
    """Register a state provider under `name`. Re-registering a name replaces it.
    
    If a save was already restored this mission and it held a blob under this name,
    the new provider is handed it at once - so a provider that registers late (an
    addon that loads after the campaign was opened) is not left empty.
    
    `library=True` is for sbs_utils' own modules, which register once as they
    import: the per-mission reset keeps those and drops the rest."""
def _relic_arm_barriers (rec, relic_key):
    """Arm every `Barrier:` that has an `Opens when:`. Returns how many are waiting.
    
    A barrier with no trigger is a hard block: it opens when somebody CUTS it, and that is
    the weapons app's business, not a clock's. One with a trigger is armed on the same
    shared tick as the contents, using the same `amd_trigger` grammar - so an author has
    one vocabulary for "when does this happen", not two."""
def _relic_arm_tick ():
    """Start the shared tick, once, and only while something is waiting on it."""
def _relic_attach_content (c, pos):
    """Put a placed thing ON THE RAIL WEB, so it is somewhere you can be SENT.
    
    This is what makes a cache a destination rather than something you happen to fly past.
    A relic's contents do not all exist when the ruin is built - `Starts when: reach ...`
    places one the first time somebody gets near the room - so the web is joined to rather
    than resolved again.
    
    A content hanging off a POINT is already a node under the author's own key; only one
    on a chamber or a box needs its own."""
def _relic_contents_tick (t=None):
    """Place every armed record whose trigger has now fired, and light up the places the
    crew has reached."""
def _relic_dress_pick (dress):
    """The first `(art, size)` in a `Dress:` list the engine knows, or (None, 1.0)."""
def _relic_facing (rec, relic_key, spec, pos, base):
    """Which way a set piece looks, flattened so it stays upright: `Facing:` a named
    place, or `Facing: x, y, z` as a direction; else the middle of the room it stands in."""
def _relic_ledger_has (relic_key, kind):
    """The part names of one kind remembered for a relic. An empty set when none."""
def _relic_ledger_note (relic_key, kind, name):
    ...
def _relic_ledger_open_web (relic_key, volume):
    """Open, on a freshly solved web, every barrier the ledger says was opened."""
def _relic_light (key, rec, by=None):
    """Light one armed marker, find its place on the web, and say so. Idempotent.
    
    `key` is the armed ("marker", relic, point) tuple. `by` is whoever came near enough -
    a ship, a suit, or None when a story beat revealed it (`relic_reveal_point`)."""
def _relic_mark_placed (obj, c):
    """Give a placed thing the ROLES of the place it was placed, and its relic's key.
    
    An author already says what a spot is for - `Roles: vault_door, relic_piece` - and
    saying it twice, once for the marker and once for the thing sitting there, is how the
    two drift apart. So the roles carry over, and the object knows which ruin it is in.
    
    That second half is what makes "carry it OUT" answerable at all: the containment latch
    tracks ships, and a thing on the end of a tether is not one, so the only way to ask
    whether the treasure has left is to ask the treasure which ruin to measure against."""
def _relic_of (thing):
    """The relic a suit - or the person in it, or the console flying it - is inside."""
def _relic_open_barrier (rec):
    """Open one barrier and say so, so a suit holding for a shut way re-plans at once."""
def _relic_part_pos (rec, name, base=None):
    """Where a named part is, in world coordinates - point, chamber or box."""
def _relic_piece_taken (rec):
    """One watched piece is out of its ruin: say so, once, and stop watching it."""
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
def _relic_register_dialogue (file_path, content=None):
    """Register a relic file's `## Dialogue` scenes. Never raises; returns how many."""
def _relic_reveal_tick ():
    """Light up the markers the crew has reached. The ruin drawing its own map.
    
    Runs on the same shared tick as the contents triggers, and for the same reason: one
    tick for every relic beats a watcher per point.
    
    A revealed marker STAYS revealed - it is a record of where the crew has been, which is
    the whole value of it in a structure where every room looks like the last one."""
def _relic_say (message):
    """Say that a ruin was not built as written, where the author will see it.
    
    A named log category has no handler unless the mission attached one, so the same line
    goes to `mast.runtime` - the log a headless test fails on and the first one anybody
    opens."""
def _relic_section_any (doc):
    """(section, its key) for the first top-level section the schema calls a relic
    section, else (None, "relics")."""
def _relic_signal_observer (name, data=None):
    ...
def _relic_spawn_marker (relic_key, rec):
    ...
def _relic_spawn_phrase (phrase, pos, c):
    """`raider x2`, `skaraan 4`, `raider` - the `Guards:` grammar, one entry.
    
    Scattered rather than stacked: several NPCs on one point would spawn inside each
    other. The spread is small on purpose - they should read as being IN the room the
    author put them in, not near it."""
def _relic_state_restore (blob):
    """REPLACE the ledger with what a save says. Lazy: no ruin is touched, and the next
    one armed reads it. Announces nothing."""
def _relic_state_snapshot ():
    """The state provider's half: the ledger, and the quest signals already sent."""
def _relic_taken_tick ():
    """Send `<relic>_taken` for every piece that has LEFT its ruin.
    
    Asked of the piece, not of the ship towing it: see `relic_holds`. A piece whose
    object is gone is NOT taken by that alone - it may have been destroyed, or torn down
    with its system - so it is only marked as gone, and `relic_piece_collected` is what
    says it was picked up. A relic whose space is not standing is skipped rather than
    read as "outside": `relic_holds` answers False for both, and only one is an exit."""
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
def amd_parse_facts (text, handler=None, default=<function amd_num at 0x0000022F81E7E3E0>, archetype=None, errors=None):
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
def relic_atmos_role (key):
    """The role one relic's nebula carries: `relic_atmos:<key>`."""
def relic_atmosphere (relic_key, roles=None, default=None, name=None):
    """Fill a built relic with ONE nebula, in the color its `Atmosphere:` names.
    Returns how many nebula objects were made.
    
    The point is not the look: the engine caps warp for a ship inside a nebula by itself,
    so the interior needs no script governor.
    
    `Atmosphere: none` - and, here, no `Atmosphere:` line at all - makes none. `default`
    is the color for a relic that does not say (Open Universe passes `purple`).
    
    Identity, not a once-flag: a relic that already has its nebula gets no second one."""
def relic_atmosphere_colors ():
    """The words `Atmosphere:` accepts, sorted. Empty when the color table cannot be
    read, which callers treat as "do not judge"."""
def relic_barrier_destroyed (obj_id):
    """A destroyed barrier object opens its barrier. What a `//damage/destroy` route calls.
    
    Returns the barrier key it opened, or None when the object was not a barrier - so a
    route can hand it every destruction without asking first.
    
    A REPAIR JOB IS NOT DONE BY BEING SHOT. Handed the marker of a `Repair:` job this
    repairs nothing and returns None: the job is read from the record, so it is still
    there to do. It only FORGETS the marker's id - ids are recycled, and
    `relic_repair_done` puts the plain marker away by id, so a remembered id of a marker
    that is gone would one day delete whatever the engine gave that number to next."""
def relic_barriers (relic_key):
    """``{name: [x, y, z, radius, opens_when, clear_with, display]}`` as AUTHORED.
    
    Positions are relic-relative, like every other authored part. For the live state - is
    it open, which edges is it severing - ask the web with `rail_barriers`."""
def relic_barriers_spawn (relic_key, name=None):
    """Give every SHUT barrier a space object, so a beam has something to hit.
    
    A barrier is a sphere in the rail web, and nothing in the engine can shoot a sphere -
    which is the whole reason cutting one used to be a scripted timer with no beam on
    screen. A real object makes it an ordinary weapons problem: point at it, fire, and the
    thing dies. `relic_barrier_destroyed` is the other end.
    
    Idempotent per (relic, barrier): a reload replaces rather than accumulates, the same
    identity rule the markers and contents use. Returns how many were placed."""
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
def relic_entrance (relic_key):
    """Where a relic is entered: its first point carrying `Roles: entrance`, else its
    own `Loc:`. World (x, y, z), or None for an unknown relic."""
def relic_find_part (name, near=None):
    """Which relic has a barrier or point called `name`, or None.
    
    `near` is anything a suit can be traced from - a lifeform, a suit, or a console - and
    that suit's relic is asked first, because two relics may well both have a `door`."""
def relic_finds (relic_key):
    """The things a relic put in the world that are still there, as `{part: [ids]}`.
    
    Matched by the `relic_key` / `relic_part` stamp `_relic_mark_placed` puts on everything
    it places, so a find is traced to its spot without guessing from names or positions."""
def relic_holds (relic_key, pos):
    """Is this position inside relic `relic_key`? The extraction test.
    
    Hauling a thing OUT of a ruin is the one question containment cannot answer: the
    containment latch tracks ships, and the thing on the end of a tether is cargo. So the
    cargo is asked instead - `pos` is an (x, y, z), a Vec3, or anything with a position.
    
    False for a relic that is not registered or whose space is not built, which is the
    same answer as "it is not in there"."""
def relic_items (relic_key=None):
    """Declare the `Items` section of a relic's own file. Returns the item keys.
    
    A relic file is self-contained - the ruin, what is in it, and what those things ARE,
    in one document. `Item:` on a room only names an item; this is what makes the name
    mean something. With no key, every registered relic's file is read, once each.
    Nothing to do, and no error, for a file with no `Items` section."""
def relic_keys ():
    """Every registered relic key."""
def relic_ledger (relic_key=None):
    """What has happened in a ruin - or in every ruin - as plain sorted lists.
    
    `{"opened": [...], "repaired": [...], "taken": [...], "placed": [...]}` for one
    relic, `{relic key: {...}}` for all of them. `taken` and `placed` name the PART a
    content record hangs off. What a report, a test or a mission asks; the ruin does
    not have to be standing."""
def relic_ledger_count ():
    """Reset-ledger probe: how many things ruins are remembering."""
def relic_ledger_forget (relic_key=None):
    """Forget what happened in one ruin - or in all of them, with no key.
    
    For a ruin that RESETS: one that is meant to be a different ruin each time it is
    found. The next build is from the file. The quest signals it sent stay sent."""
def relic_open_barrier (relic_key, barrier, name=None):
    """Open one of a relic's barriers - what a cutting beam or a haul ends in.
    
    Emits `rail_opened` so a suit holding for a shut way re-plans at once rather than
    waiting out its stall counter. False when there is no such barrier, or it was already
    open."""
def relic_part_at (relic_key, pos):
    """The room (chamber or box) a world position is in, else the nearest one, else None.
    
    Boxes count - `volume_chamber_at` only knows chambers, and four of Storm's Beacon's
    seven ruins are built from boxes, so it answered "open space" in the middle of a hall."""
def relic_part_info (relic_key, name):
    """The non-geometry facts of one part - `scene`, `scan`, `dress`, `facing`, `kind`,
    `display`. An empty dict for an unknown part."""
def relic_part_scan (relic_key, name):
    """What the xESS Scan app says about a place, or None.
    
    Never the part's prose: in a shipped relic that is written for the AUTHOR ("the
    cradle is a box solid so the rails skirt it") and must never reach a player."""
def relic_part_scene (relic_key, name):
    """The scene key a place opens when a suit arrives there, or None."""
def relic_piece_collected (item_key, item_id=None):
    """A pickup was collected: if it was a relic's piece, send `<relic>_taken`.
    
    What an `item_collected` route calls, with the signal's `key` and - when the sender
    carries it - the id of the pickup itself. REELING A PIECE IN from a suit collects and
    deletes it while it is still inside the ruin, so it never "leaves the volume"; without
    this the crew would hold the piece and the quest would wait forever.
    
    Matched by id when there is one, else by the item key against pieces not yet taken.
    Returns the relic key whose piece it was, or None - so a route can hand it every
    pickup without asking first."""
def relic_pieces (relic_key=None, taken=None):
    """The ids of the pieces relics have placed - one relic's, or every one's.
    
    `taken=True` / `taken=False` narrows to the ones already out, or still inside."""
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
def relic_plate_size (value):
    """An authored `Plate:` as the size the dresser will use. 0 means "work it out"."""
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
def relic_point_display (relic_key, name):
    """What a point is CALLED - the authored label, else its key.
    
    The same string `_relic_place_role_markers` names the marker with, so a list of places
    to go and the label that lights up on the radar cannot disagree."""
def relic_point_has_marker (relic_key, name):
    """Whether this point was armed with a marker at all.
    
    The companion `relic_point_revealed` answers TRUE for a point with no marker, which
    is right for its own job - it gates destinations, and a relic that does not use the
    reveal mechanism must not have every destination hidden. It makes it useless as a
    record of where the crew has BEEN, though: without this test, every place in an
    unarmed relic reads as already seen."""
def relic_point_hidden (relic_key, name):
    """Whether a point is authored `Hidden:` - off the destination list until found.
    
    Hidden is a property of the LIST, never of the graph: a route still passes THROUGH a
    hidden place, because stumbling into a secret on the way somewhere else is the point
    of having one."""
def relic_point_revealed (relic_key, name):
    """Whether the crew has been close enough to light this point's marker.
    
    TRUE WHEN THERE IS NO MARKER, which is the case that matters: a point without
    `Roles:` is never armed, and a relic whose contents were never armed has no markers at
    all. Answering False for those would hide every destination in a relic that simply
    does not use the reveal mechanism."""
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
def relic_quest_signal (name):
    """Send a quest signal on a relic's behalf, once per mission. True when it was sent.
    
    `signal_emit("quest_signal", {"SIGNAL_NAME": name})` - the line a quest's
    `Done when: signal <name>` hears. Called from a tick or from another signal's
    handler, which is always the server, so it is sent once whatever the console count."""
def relic_quest_signal_count ():
    """Reset-ledger probe: quest signals relics have sent this mission."""
def relic_quest_signal_sent (name):
    """Whether a relic already sent this quest signal. What a test or a report asks."""
def relic_rails (record, name=None, margin=None):
    """Solve this relic's rail web. Called by `relic_volume`; returns the stats dict.
    
    ONCE PER RELIC, HERE, rather than once per trip. Every destination a console picks
    used to re-derive the ruin's connectivity from the geometry - doorways, skirts and an
    N-squared visibility graph, measured at 96ms for the first pick and 17ms for every one
    after, per console, on a bridge. Connectivity is a property of the RUIN, so it is
    solved when the ruin is built.
    
    Nothing about it is authored. The relic's own `Point:` records become named
    destinations; everything else - the stations through each room, the doorways, the way
    round a pillar - is derived. `Rail step:` is the one dial, and `Barrier:` parts are
    registered here so a shut way is shut from the first route anybody asks for."""
def relic_rails_ensure (relic_key, name=None):
    """The relic's rail web name, solving the web now if it has not been solved yet.
    
    `relic_volume` builds it, which covers every relic read from an `.amd`. A mission - or
    a test - that defines the volume itself and registers the points by hand never goes
    through that, and a route with no web to walk would simply refuse. So the first route
    asked for is what builds it, once, and everything after that walks the cache.
    
    Returns the volume name, or None when there is no such relic or its volume has not
    been built."""
def relic_record (key):
    """The registered record for ``key``, or None."""
def relic_redress (relic_key):
    """Tear a spawned relic's walls down and dress it again. Returns how many were made.
    
    What a live edit needs: `relic_reload` moves the SPACE, and walls left where the old
    space was are worse than no walls. A no-op for a relic `relic_spawn` did not dress -
    a mission that dresses its own answers `relic_rebuilt` itself."""
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
def relic_repair_done (relic_key, repair):
    """A repair job is finished - what a suit's tool, or a story beat, ends in.
    
    Emits `relic_repaired` (RELIC_KEY, RELIC_REPAIR) and sends the quest signal
    `<repair key>_repaired`. False when there is no such job or it was already done.
    
    The plain marker goes: it marked a fault, and the fault is gone. A DRESSED job - a
    panel, a coupling - stays where it is and wears `relic_repaired` instead."""
def relic_repair_fixed (relic_key, repair):
    """Whether a repair job has been done - now, or on an earlier visit."""
def relic_repair_jobs (relic_key, open_only=False):
    """``[(name, job)]`` with the live state: ``{"pos", "radius", "display",
    "clear_with", "fixed", "object"}``, `pos` in WORLD coordinates.
    
    What the suit's Fire app lists. Read from the record, not from the objects standing
    in for the jobs - so a job whose marker was never placed, or was destroyed, is still
    a job that can be done."""
def relic_repairs (relic_key):
    """``{name: [x, y, z, radius, None, clear_with, display]}`` as AUTHORED - the shape
    `relic_barriers` returns, so one reader serves both. Positions are relic-relative."""
def relic_repairs_spawn (relic_key, name=None):
    """Give every repair job a marker in the world, and somewhere to fly to.
    
    The marker is what the crew sees and selects - dressed with the part's `Dress:` art
    when it has any, else the plain sphere a barrier uses. It has no exclusion radius and
    is NOT what makes the job doable: `relic_repair_jobs` reads the record.
    
    The job also joins the rail web as a DESTINATION (`rail_attach`), so the Nav app can
    send a suit to it. That adds a node and its own legs; it severs nothing.
    
    Idempotent per (relic, job). Returns how many were placed."""
def relic_reveal_point (relic_key, name):
    """Reveal a place on cue - what a scene's `reveal <point>` does, and a mission's
    story beat can too. Lights its marker when it has one, and puts a `Hidden:` place on
    the destination list either way. True when anything changed."""
def relic_section (relic_key, section_key):
    """Another section of the file a relic came from - its `side_stories`, its `items`.
    
    A relic file is self-contained: the space, what is in it, what is said in it and the
    stories told in it open as one document. This is how a mission reaches the parts the
    library does not read itself - `boarding_quests_grant(relic_section(key,
    "side_stories"))` gives the crew who go inside the stories that belong to that ruin.
    None when the relic or the section is unknown."""
def relic_setpieces (relic_key):
    """Every part carrying `Dress:`, as `[{part, kind, dress, facing, solid_index}]`."""
def relic_setpieces_place (relic_key, roles='', name=None):
    """Place a relic's set pieces. Returns `(made, solid_indices_dressed)`.
    
    A POINT or a PROP gets its piece standing upright on the spot, facing its `Facing:`
    (else the middle of its room). A SOLID gets its piece fitted to the solid's size, so
    the cradle a route already skirts is drawn as the cradle rather than as a grey cube -
    turned the same way, and fitted AFTER the turn. Size is the kit's scale for a kit
    piece, times the optional number after the key."""
def relic_spawn (relic_key, walls=True, atmosphere=True, contents=True, marker=True, contain=False, props=None):
    """Put one registered relic in the game: space, walls, nebula, contents, map marker.
    Returns the record, or None when it could not be built - and says why.
    
        relics_load(get_mission_dir_filename("mission.amd"))
        relic_spawn("hollow")
    
    | part | from the file | turned off with |
    |---|---|---|
    | the space | `Chamber:`, `Box:`, `Passage to:`, `Solid:` | - |
    | walls | `Walls:`, `Art:`, `Seed:`, `Gaps:`, `Debris:`, `Dress:` | `walls=False` |
    | nebula | `Atmosphere: <color>`; none when the line is absent | `atmosphere=False` |
    | what is inside | `Item:`, `Spawn:`, `Starts when:`, points and their markers | `contents=False` |
    | a name on the map | the `Roles: entrance` point, else `Loc:` | `marker=False` |
    
    CONTAINMENT IS OFF unless asked for. `contain=True` applies the authored
    `Containment:` - and a ship held inside a ruin has no way out of one that is not also
    a galaxy cell, because containment lets go only a whole relic clear of the walls and a
    held ship never gets there. Open Universe leaves by jumping. Until a ruin can say
    where its door is, walls in a plain mission are scenery.
    
    IDENTITY, not a once-flag: a relic whose space is already built is left alone, so
    calling this twice - a route that fires again, a late joiner - builds nothing twice.
    
    NEVER RAISES. A passage naming a room that does not exist used to raise out of the map
    label, and a map label that dies spawns no players either. The reason is logged and
    the rest of the mission carries on.
    
    Emits `relic_built` with RELIC_KEY, RELIC_VOLUME and RELIC_NAME."""
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
def relic_wall_role (key):
    """The role one relic's wall props carry: `relic_wall:<key>`.
    
    Scoped to the relic, so that tearing one ruin down - or re-dressing it after a live
    edit - cannot take another ruin's walls with it."""
def relic_walls (relic_key, n=600, roles='', wall_depth=40.0, seed=None, name=None, setpieces=True):
    """Dress a built relic: its walls in the authored style, and its set pieces.
    Returns how many objects were made.
    
    The AMD-to-`volume_dress` mapping every mission was about to write for itself:
    `Walls:` (a fallback chain - `torgoth, plates`), `Art:`, per-part looks, `Plate:`,
    `Gaps:`, `Debris:`, `Seed:`. Then every part carrying `Dress:` gets its set piece, and
    a solid dressed that way is not ALSO dressed as a generic primitive.
    
    `roles` go on everything made, and are how the caller tears it down again. Not
    idempotent on its own - a caller guards on its role, the way Open Universe does."""
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
def relics_load (file_path, section_key='relics', content=None, scenes=True):
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
def relics_spawn (file_path, section_key='relics', **spawn):
    """Build EVERY relic written in a file. Returns the records that were built.
    
        relics_spawn(get_mission_dir_filename("mission.amd"))
    
    The one line a mission needs. A file with no `relics` section is not an error - it
    returns an empty list - so the line can sit in a template whether the mission has a
    ruin or not. Keyword arguments go to `relic_spawn` (`contain=True`, `walls=False`...)."""
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
class _RelicNothingToPlace(Exception):
    """A repair that was done on an earlier visit and has no furniture to stand as."""
