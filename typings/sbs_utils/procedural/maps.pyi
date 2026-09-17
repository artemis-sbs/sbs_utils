from sbs_utils.helpers import FrameContext
def _coerce_like (text, current):
    """Convert a code's string token back to the type of the live variable.
    
    The property shared vars are initialised with their real types before the
    code is applied (ints for sliders, strings for dropdowns / minute inputs),
    so matching the current type round-trips faithfully. Falls back to an
    int->float->str guess when the variable doesn't exist yet."""
def _game_code_presets_file (filename):
    """Where this mission's saved setups live: one file per mission under common_data.
    
    NOT the mission folder. A preset is written by the game, not shipped by the author, so
    putting it in the mission meant untracked state inside a distributed repo - it needed a
    `.gitignore` line and it did not survive a re-extract. `common_data` sits beside the
    missions, so it survives both.
    
    `filename` stays as an injection point for the tests."""
def _loadout_clean (text):
    """Strip the loadout + game-code separators from a free-text field."""
def _loadout_ship_still_alive (ship):
    """True unless this is one of OUR agents and it is known deleted.
    
    The loadout helpers accept duck-typed stand-ins - anything with .id/.name/.art_id -
    and the tests rely on that, so a foreign object is not ours to judge. An Agent (or a
    SpawnData/CloseData wrapping one) IS ours, and a deleted one must be dropped: the
    start-of-game cull strips __player__ from the unused slots and deletes them but never
    removes default_player_ship, and a picker snapshot taken before the cull holds them
    all. `.name`/`.art_id` are cached on the Python object so a dead ship still answers,
    which is what let deleted slots reach an apply (a write straight to the engine
    object) and get baked into a saved preset."""
def _map_is_shown (m):
    """Evaluate a map's ``if`` condition. Unconditional maps, and any map we cannot
    evaluate, are SHOWN.
    
    ``@map/x "X" if COND`` was never evaluated by ``maps_get_list``, so a map hidden by
    its own condition was offered anyway. ``CardLabelBase.test`` answers this, but it
    needs a task, and there is not always one: the headless runner polls this from its
    own loop with no MAST task in context. Missing task therefore means SHOW - hiding
    every map there would stop ``--map`` working at all, which is a far worse failure
    than listing one map too many."""
def _map_property_vars (map):
    """Var names bound in a map's Properties metadata, in declaration order.
    
    Walks the (possibly grouped, e.g. Main/Map) Properties dict and extracts
    every ``var="..."`` / ``var= "..."`` binding from the widget strings."""
def _preset_normalize (entry, position):
    """Coerce a stored preset entry to ``{"name": str, "code": str}``.
    
    New entries are already that dict. A legacy bare-string entry (just the
    code) gets a generated ``"Preset N"`` name from its 1-based ``position``."""
def game_code_decode (code):
    """Apply a game code: set its shared variables and return the matching map.
    
    Resolves the map by path first; if no current map matches, nothing is
    changed and ``None`` is returned (so a code from a different mission is a
    safe no-op). Otherwise each ``VAR=value`` is written to the shared scope,
    coerced to the live variable's type, and the map Label is returned. The
    caller starts the map (e.g. ``task_schedule(map)``).
    
    Args:
        code (str): A code previously produced by :func:`game_code_encode`.
    
    Returns:
        Label | None: The map to start, or ``None`` if the code is empty or
        names a map not present in the current story."""
def game_code_encode (map, with_loadout=False):
    """Build a shareable, human-readable game code for a map.
    
    Format: ``"<map_path>;VAR=value;VAR=value;..."`` where the vars are the
    map's :func:`game_code_vars` read from the shared scope. Reproduces the
    map plus its seed and key option values so another host can recreate the
    same game.
    
    Args:
        map (Label): The map label whose current option values to encode.
        with_loadout (bool): also carry the crew's ship names and hulls. Pass True when
            SAVING (a named preset, the last-used slot); leave False for a code meant to
            be shared, which should not carry another crew's ship names.
    
    Returns:
        str: The game code, or ``""`` if ``map`` is None."""
def game_code_label (code):
    """A short, human-readable label for a game code (for preset menus).
    
    e.g. ``"siege;PLAYER_COUNT=2;DIFFICULTY=5;seed_value=4242"`` -> ``"P2 D5 seed4242"``.
    Falls back to the raw code if it has no value pairs.
    
    ``SHIP_LOADOUT`` is summarized as a ship count rather than spelled out: its value is
    every ship's name and hull joined together, which is longer than the rest of the label
    put together and unreadable in a dropdown."""
def game_code_last_apply (map, filename=None):
    """Apply this mission's remembered setup for ``map``, if there is one.
    
    Safe to call unconditionally: it does nothing when nothing was remembered, when the
    setting that writes them was never on, or when the remembered code names a map this
    story does not have.
    
    Args:
        map (Label|str): the map label (or its path) about to be shown/started.
        filename (str|None): override the store path (tests).
    
    Returns:
        bool: whether a remembered setup was applied."""
def game_code_last_code (map_path, filename=None):
    """The last-used code for one map, or ``""`` when there is none."""
def game_code_last_save (code, filename=None):
    """Remember ``code`` as this mission's last-used setup, keyed by its map.
    
    Called when a game STARTS, not when it ends: that records what was actually played,
    and it survives a crash or a quit that never reaches a results screen.
    
    Args:
        code (str): a code from :func:`game_code_encode`.
        filename (str|None): override the store path (tests).
    
    Returns:
        str|None: the code stored, or ``None`` if it was empty."""
def game_code_presets_for_map (map_path, filename=None):
    """Return one map's saved presets as ``[{"name", "code"}, ...]`` (newest last)."""
def game_code_presets_load (filename=None):
    """Load the saved game-code presets, a dict of ``{map_path: [entry, ...]}``.
    
    Each entry is a ``{"name": str, "code": str}`` dict. Legacy files stored a
    bare code string per entry; those still load (see :func:`_preset_normalize`).
    Returns an empty dict if the file is missing or malformed. Presets are kept
    separated by map so each map only shows its own."""
def game_code_presets_save_code (code, name=None, filename=None):
    """Save a game code as a named preset under its map, de-duplicating on code.
    
    The map is taken from the code's first token, so presets land in the right
    per-map bucket. ``name`` defaults to ``"Preset N"`` (N = the next slot for
    that map). Re-saving an identical code is a no-op (keeps the first name).
    Returns the code saved, or ``None`` if ``code`` is empty."""
def game_code_vars (map, with_loadout=False):
    """Return the var names that make up a map's game code, in order.
    
    By default this is *every* property var the map exposes - the options panel, exactly
    as a person set it. A map can pin the set explicitly with a ``GameCode`` metadata list
    (``GameCode: [PLAYER_COUNT, DIFFICULTY, ...]``), which is then used verbatim.
    
    Args:
        map (Label): The map label object.
        with_loadout (bool): also carry ``SHIP_LOADOUT`` - the crew's ship names and
            hulls. True when SAVING a setup (a preset, or the last-used slot), False when
            producing a code to share. Appended even to an explicit ``GameCode`` list, so
            a map that pins its options still saves its ships.
    
    Returns:
        list[str]: Ordered var names included in the code."""
def label_find_by_spec (labels, spec):
    """Find one label from a loose, human-typed spec - the rule `maps_find` documents,
    factored out so every other "name a label on a command line or in a dropdown" lookup
    resolves IDENTICALLY.
    
    Shared with `media_find` (skybox and music), which is why it lives here rather than
    inside `maps_find`: two copies of a fuzzy matcher drift, and the day they disagree is
    the day `map=siege` and `MUSIC_SELECT=siege` mean different things.
    
    Args:
        labels (list): anything with `.path` and (optionally) `.display_name`.
        spec: an index, a path, a display name, or a unique substring of either.
    
    Returns:
        The label, or None if nothing matched or the spec was AMBIGUOUS."""
def map_apply_crew (map):
    """Publish a map's ``Crew:`` block for :func:`player_roster_apply`, OVERWRITING.
    
    WHY THIS IS NOT PART OF ``Defaults``. ``map_apply_defaults`` is set-if-absent, which
    is exactly right for seeding a control and exactly wrong here: an operator browsing
    the picker would pin whichever map they happened to look at FIRST, and every trial
    after it would be flown in that ship. So this always writes, and CLEARS the variables
    when the selected map declares no crew - leaving a stale hull behind is the same bug
    wearing a different hat.
    
    Reported from the Gamma with a Q playtest as "set the hull at mission select ... after
    Q's intro is too late and confuses people": a map that reshapes its crew from its own
    BODY does it after the console-select screen, so everyone spends that screen looking
    at a ship they are about to stop flying.
    
    Args:
        map (Label | None): The map label object (``None`` clears, so a picker with
            nothing selected does not keep the last map's crew)."""
def map_apply_defaults (map):
    """Apply a map's ``Defaults:`` metadata as SET-IF-ABSENT shared variables.
    
    For each ``VAR: value`` in the map's ``Defaults`` block, set the shared variable to
    ``value`` ONLY if it is not already set - so a value seeded by ``settings.yaml``, the
    story, or a loaded game code always wins (the same semantics as ``default shared``). This
    lets a map give its own Properties controls a starting value without promoting a map-local
    setting (e.g. a ``JOBS_SELECT`` only this map uses) to global settings or scattering
    ``default`` through the map body.
    
    The map's Properties panel renders (and binds its controls to SHARED scope) BEFORE the map
    body runs, so this must be applied at BOTH moments: when the panel is presented, AND again
    whenever the map is started as a task (AUTO_START and a headless ``--map`` runner start the
    map task without ever presenting the panel). It is idempotent - a map with no ``Defaults``
    is a no-op, and an already-set var is left untouched - so calling it at both points is safe.
    
    Args:
        map (Label): The map label object (``None`` is a no-op)."""
def map_get_crew (map):
    """Return the ``Crew`` metadata dict of a map label (fallback ``crew``).
    
    A sibling of ``Properties`` and ``Defaults``. Where ``Defaults`` seeds the map's own
    controls, this says what the CREW FLIES on this map::
    
        metadata:``` yaml
        Crew:
          hull: tng_fed_defiant
          side: federation
        ```
    
    Args:
        map (Label): The map label object.
    
    Returns:
        dict | None: The crew dict, or ``None`` if the map declares none."""
def map_get_defaults (map):
    """Return the ``Defaults`` metadata dict of a map label (fallback ``defaults``).
    
    A sibling of ``Properties`` in a map's ``metadata:`` block: a flat ``{VAR: value}`` map of
    starting values for the variables the map's Properties controls bind to (and any other var
    the map wants defaulted). Read the same way as ``Properties`` / ``GameCode``.
    
    Args:
        map (Label): The map label object.
    
    Returns:
        dict | None: The defaults dict, or ``None`` if the map declares none."""
def map_get_properties (map):
    """Return the ``Properties`` inventory value of a map label.
    
    Checks ``"Properties"`` first, then ``"properties"`` as a fallback.
    
    Args:
        map (Label): The map label object.
    
    Returns:
        any: The properties value, or ``None`` if not set."""
def map_start (map):
    """Start a map: apply its defaults, resume the sim, schedule it, announce it.
    
    The canonical launch sequence. It existed twice before this - in LegendaryMissions'
    server console and in the headless runner - and the two had DRIFTED on things that
    matter: whether the sim resumes before or after scheduling, and ``task_schedule``
    versus ``task_schedule_server``. One implementation ends that.
    
    What it does, in order:
    
      * ``map_apply_defaults`` - set-if-absent shared vars, so a value from settings.yaml,
        the story or a loaded game code still wins. Idempotent, and applied here as well
        as at panel-render time because a map can be started without a panel ever showing.
      * ``sim_resume()`` - the lobby sim is paused; a map body that awaits ``delay_sim``
        would never advance otherwise.
      * ``task_schedule(map, defer=True)`` - deferred so consoles repaint before the map
        body's first tick.
      * ``mission_clock_start()`` - the mission clock the ePADD Status app reads.
      * ``GAME_STARTED`` and the ``game_started`` signal - the contract missions gate on.
    
    What it deliberately does NOT do, because these are LegendaryMissions' own contract
    and are meaningless (or wrong) in a mission that does not load it: the
    ``reconcile_player_roster`` signal, ``sbs.set_beam_damages``, the ``GAME_TIME_LIMIT``
    timer, music selection, and the client/server GUI reroutes. LM does those around its
    own call to this.
    
    Args:
        map (Label | None): The ``@map`` label to start. ``None`` is a no-op, matching
            ``map_apply_defaults``.
    
    Returns:
        Label | None: The map that was started, or ``None``."""
def maps_find (spec):
    """Find one `@map` label from a loose, human-typed spec.
    
    Built for launch arguments - `map=test_shipdata_probe` on the engine command line, or
    `--map 0` under cosmos_dev - where the value is typed by a person or pasted from a
    script and should not have to be exact.
    
    Accepts, in order of preference so an exact hit always wins over a fuzzy one:
    
    * an integer, or a string of digits - an index into the map list
    * the label `path`, case-insensitively
    * the `display_name`, case-insensitively
    * a unique case-insensitive substring of either; AMBIGUOUS matches return None
      rather than picking one, because silently starting the wrong map is worse than
      starting none and saying so.
    
    Returns:
        Label | None: the map, or None if nothing matched or the spec was ambiguous."""
def maps_get_init ():
    """Return the ``__overview__`` map label from the current MAST story, or ``None``.
    
    Returns:
        Label | None: The overview map label, or ``None`` if not defined."""
def maps_get_list (include_hidden=False):
    """Return the ``@map`` labels defined in the current page's story.
    
    If only an ``__overview__`` label exists, it is returned as a single-item
    list. If no map labels are found at all, returns a placeholder list with a
    ``"No maps found"`` entry.
    
    Args:
        include_hidden (bool): When True, return conditional maps whose ``if`` is
            currently false as well. Callers that are RESOLVING A KNOWN MAP rather than
            offering a menu want this - ``game_code_decode`` looks a map up by path, and
            a saved code should not stop resolving because a condition happens to be
            false right now.
    
    Returns:
        list: ``@map`` Label objects, or a fallback list if none are defined."""
def player_loadout_active ():
    """Decode the live ``SHIP_LOADOUT`` shared var into a slot list (``[]`` if unset)."""
def player_loadout_apply_to_ships (ships=None):
    """Write the pending ``SHIP_LOADOUT`` onto the live player ships, then CLEAR it.
    
    This is what makes a RESTORED setup lose to a person. A restored loadout otherwise
    sits in ``SHIP_LOADOUT`` until the game starts, and the roster reconcile applies it
    over whatever is on the ships at that moment - which includes the name and hull helm
    just chose in the lobby. Last session's ships would silently overwrite this session's
    choice, and the person who made it gets no hint that it happened.
    
    Applying it up front inverts that: the restored names and hulls are what helm SEES in
    the picker, and anything helm changes from there is simply the newer value. Clearing
    the var is the other half - it leaves the reconcile nothing to override with.
    
    Ships are matched to slots in id order, the same order :func:`player_loadout_from_ships`
    captured them in.
    
    No player ships yet means the restore is too early to land on anything, so the var is
    left ALONE for the reconcile to apply at start - which is correct, because nobody has
    had the chance to choose anything either.
    
    Args:
        ships (list|None): the player ships, or None to use the ``default_player_ship``
            role.
    
    Returns:
        int: how many slots were applied."""
def player_loadout_capture (ships):
    """Capture ``ships`` into the shared ``SHIP_LOADOUT`` var; return the token.
    
    Call right before encoding a game code so the code carries the current
    crew's hulls + names."""
def player_loadout_decode (token):
    """Inverse of :func:`player_loadout_encode`. Empty/None -> ``[]``."""
def player_loadout_encode (slots):
    """Pack ``[{"name","hull"}, ...]`` into one game-code-safe token (``""`` for none)."""
def player_loadout_from_ships (ships):
    """Build a loadout token from ship objects, reading ``.name`` and ``.art_id``.
    
    ``ships`` is sorted by id first so the slot order is stable and matches the
    rehydrate side (spawn_players walks the player ships in id order too)."""
