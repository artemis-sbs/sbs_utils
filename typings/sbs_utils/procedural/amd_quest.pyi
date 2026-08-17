def _is_duration (text):
    """`5 minutes` / `30 seconds` - a time is a trigger like any other."""
def _norm (label):
    ...
def _quest_log (message):
    """Warn about an authored line that did not parse (never raise - a bad reward must
    not take the mission down with it). Mirrors ``amd_action``'s ``_action_log``."""
def _rep_clause (toks):
    """``earns <faction> <pole...> <n>`` -> ``(faction, pole, delta)``, else None.
    
    Deliberately the SAME shape as the dialogue outcome verb already in production
    (``earns ashfang selfish +5``, OU ``_ou_earns``): number last, pole possibly several
    words. One grammar for shifting standing, not two spellings of it."""
def _resolve_role (target, aliases=None):
    """A friendly role name -> its real role: apply an alias, else singularize
    ('raiders' -> 'raider') but keep 'ss' words ('boss' stays 'boss')."""
def _signal_name (value):
    """A signal name, lowercased with spaces -> underscores (matched exactly).
    Kept as a local alias; the rule itself lives in `amd.amd_signal_name` so the
    editor's signal join matches exactly what the driver matches."""
def amd_console_list (value):
    """'comms, admiral' / 'comms admiral' -> ['comms', 'admiral'] (lowercased). Used by
    the Quests-tab `Accept On:` / `Engage On:` labels to restrict WHICH consoles may
    accept/abandon or engage this quest (a job specific to one station)."""
def amd_coords (s, n=2):
    """'6, 4' -> [6, 4] (the first `n` signed-integer tokens)."""
def amd_duration_parts (value):
    """`6 minutes` -> `(6, "minutes")`, `90 seconds` -> `(90, "seconds")`, `2` ->
    `(2, "minutes")`. `(None, unit)` when there's no number.
    
    The unit is MINUTES unless the text says "second" - the rule `Fail after:` and
    `Complete after:` have always used. Shared so a view can't disagree with the clock
    the engine actually runs. Returns the AUTHORED unit (not just seconds) because the
    quest data keeps what was written.
    
    The COMPACT form parses too - `20m`, `30s`, `2h`. It reads naturally and everyone
    writes it, but the digit-token scan never saw it: `20m` is not `isdigit()`, so
    `Fails when: after 20m` came back `(None, "minutes")` -> `{minutes: 0}` -> `secs <=
    0` -> the watcher skipped the quest and **the deadline silently never fired**. An
    unrecognized suffix still falls through to minutes, as before."""
def amd_norm (name):
    """Canonicalize a token: lowercase, hyphens/spaces -> underscores."""
def amd_num (s):
    """int -> float -> the trimmed string, whichever parses first."""
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
def amd_quest_data (text, aliases=None):
    """Parse one quest fact-sheet fence into a quest-data dict using the shared
    vocabulary only. A mission with extra labels should compose ``amd_quest_facts``
    with its own handler and call ``amd_parse_facts`` directly instead."""
def amd_quest_facts (aliases=None):
    """Return an ``amd_parse_facts`` handler for the shared quest vocabulary.
    
    Objective/flow labels: Scope / State / Goal / When / Then / Pays / Tier / Display.
    Quests-tab action gating: Accept On (consoles that may Accept/Abandon) and Engage On
    (consoles that may Engage) restrict a job to specific stations.
    End-game + mission-tree labels: Win / Lose (bare flag -> end_win/end_lose; prose ->
    also the win_text/lose_text reason), Parent, Required, Critical, and the fail
    triggers Fail on signal / Fail on all dead / Fail after, plus the timed-completion
    trigger Complete after (symmetric to Fail after; drives a reveal chain). These map to
    the data keys the LM quest end-game driver reads (parent aggregation, end_win/end_lose
    game-over, fail_on_signal/fail_on_all_dead/fail_after, complete_after).
    
    Unknown labels return None, so a mission with extra vocabulary chains its own
    handler after this one (or falls to amd_parse_facts's default coercion).
    ``aliases`` is forwarded to ``amd_trigger`` / role resolution."""
def amd_reward (value):
    """A reward/penalty block -> ``{credits, items, reputation}``. Clauses are
    comma-separated::
    
        Pays: 300 credits, 2 torpedoes, earns tsn honest +10
        Penalty: 200 credits, earns tsn diplomatic -15
    
    * ``<n> credits``  -> ``{"credits": n}``
    * ``<n> <item>``   -> ``{"items": {<amd_norm(item)>: n}}``, keyed exactly the way
      ``recover 2 torpedoes`` keys its goal, so a reward and the goal that collects it
      cannot disagree.
    * ``earns <faction> <pole...> <n>`` -> ``{"reputation": {faction: {pole: n}}}``.
    
    ``earns`` applies its delta **literally in both blocks** - a `Penalty:` does not
    silently flip the sign, so an author writing ``-15`` gets ``-15``. (Credits differ:
    a bare quantity takes its direction from the block, which is why the sign is written
    on the one that could be ambiguous and omitted on the one that cannot.)
    
    Prose carrying no number is a FLAVOR reward and stays ``{"credits": 0}`` silently -
    "a favor" is a legitimate thing to write. A clause that DOES carry a number but
    matches no form is logged: this used to be the ``Pays: 300 credits, 2 torpedoes``
    case, which returned the credits and dropped the torpedoes without telling anyone,
    while ``quest_grant_reward`` had supported ``items`` the whole time.
    
    ``items`` and ``reputation`` are present only when non-empty, so the common
    ``{"credits": n}`` shape is unchanged for every existing caller."""
def amd_signal_name (value):
    """A signal name, lowercased with spaces -> underscores (matched exactly).
    
    Lives here, not in a caller, because it IS the matching contract: the quest driver
    matches on it at runtime and the editor's signal join matches on it statically. Two
    copies held in agreement by a comment would silently stop agreeing the first time
    the rule widened."""
def amd_trigger (value, aliases=None):
    """'destroy 4 raiders' -> ('on_kill', {role: raider, count: 4}); 'reach 6, 4' ->
    ('on_reach', {sector: [6,4]}); 'signal x' -> ('on_signal', {name: x}). Returns
    None if the leading word isn't a known verb. ``aliases`` optionally maps a
    friendly role name to its real role (e.g. {'derelict': 'universe_derelict'})."""
