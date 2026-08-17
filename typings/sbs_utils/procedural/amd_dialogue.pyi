from sbs_utils.mast.mast_node import MastDataObject
def _dlg_norm (s):
    ...
def _dlg_parse_choice (line):
    """A `- [label](target) if guard ; outcomes` line -> dict, or None.
    
    Returns `{"label", "target", "guard", "outcomes"}`. `guard` is None when the
    choice is unconditional; `outcomes` is `amd_outcomes`' list of tuples.
    
    The `; outcomes` tail splits FIRST, before the `if` guard is read, because a
    guard is free text and would otherwise swallow the whole tail - `if standing >
    10 ; earns kind 5` would become the guard `standing > 10 ; earns kind 5`,
    which no evaluator can answer and which loses the outcome without a word."""
def _dlg_parse_outcomes (s):
    """`'costs 200 credits, earns vex kind 5, signal paid'` -> `[(verb, *tokens), ...]`.
    
    Tokens are interpreted by the mission's registered outcome handler (only
    `signal` is built in), so the grammar of costs/earns/etc. lives with the
    mission rather than here."""
def _dlg_split_extension (ext):
    """A cue's `(...)` -> `(surface, direction)`. A registered word is the surface;
    anything else is a direction."""
def amd_body_variant (line):
    """A `%` speech-variant line -> `(text, gate)`, or None when it is not one.
    
    `gate` is the condition in `%{...}` / `{...}`, or None. The leading `%` is
    optional in a dialogue body, so this returns a pair for ANY line once the
    caller has decided it is in speech position - it is the shared *stripping and
    gate* rule, not the decision that a line is speech. Callers that require the
    sigil test `line.startswith("%")` themselves."""
def amd_choice (line):
    """A `- [label](target) if guard ; outcomes` line -> dict, or None.
    
    Returns `{"label", "target", "guard", "outcomes"}`. `guard` is None when the
    choice is unconditional; `outcomes` is `amd_outcomes`' list of tuples.
    
    The `; outcomes` tail splits FIRST, before the `if` guard is read, because a
    guard is free text and would otherwise swallow the whole tail - `if standing >
    10 ; earns kind 5` would become the guard `standing > 10 ; earns kind 5`,
    which no evaluator can answer and which loses the outcome without a word."""
def amd_direction_names ():
    """Every registered direction. NOT the set an author is limited to - a direction
    may be any words at all; these are the ones that carry extra meaning."""
def amd_outcomes (s):
    """`'costs 200 credits, earns vex kind 5, signal paid'` -> `[(verb, *tokens), ...]`.
    
    Tokens are interpreted by the mission's registered outcome handler (only
    `signal` is built in), so the grammar of costs/earns/etc. lives with the
    mission rather than here."""
def amd_register_directions (domain, table):
    """Register delivery directions: `{name: payload}`, where payload is whatever the
    mission's renderer understands (a face mood, a style string, a delay). Mirrors
    `amd_register_fields`: a clash with an existing name is a startup failure, not
    silent drift."""
def amd_register_surfaces (domain, names):
    """Register delivery surfaces a cue may name (`@Vell (comms)`). `domain` is the
    registering mission/addon, kept for error messages on a clash."""
def amd_surface_names ():
    """Every registered delivery surface, for completion and lint."""
def dialogue_apply (agent_id, speaker, outcomes):
    """Apply a chosen line's outcomes: built-in `signal`, plus any registered verbs. Returns
    False if a handler refuses (e.g. a cost can't be afforded) - the pick is rejected."""
def dialogue_beats (scene, agent_id, speaker=None):
    """One playable beat per `@cue`, in script order.
    
    Each is a MastDataObject `{speaker, surface, direction, text}` where `text` is a
    random eligible variant for that beat (gates use the same metric resolver as
    everything else) and `direction` is the beat's own, or the one written directly
    above the chosen line. A beat with no eligible line is dropped, so a fully gated
    beat disappears rather than playing silence.
    
    `speaker` here is the resolved CARD for guard evaluation (the mission's own
    record), not the beat's cue key - a beat names its speaker in `.speaker`, which
    the caller resolves per beat via `lifeform_speaker`."""
def dialogue_choices (scene, agent_id, speaker):
    """Choices whose guard passes, as MastDataObject (label/target/outcomes) so a mast comms
    route can render one button each."""
def dialogue_direction (name):
    """The registered payload for a direction, or None when it is free-form flavor."""
def dialogue_entry_for (scenes, speaker_key, when='comms'):
    """The entry scene key whose Speaker == speaker_key and When == `when`, or None.
    
    `when=None` means "either" - a caller that just wants this speaker's entry scene
    and does not care which door it is.
    
    Both sides of the speaker test are normalized, because everything else in this
    module goes through `_dlg_norm` and this did not: `Speaker: DS 1` did not match
    an actor written `DS-1` or `ds_1`, and a scene that is there reads as missing.
    (`DS1` remains a DIFFERENT key from `DS 1` - normalization settles case, dashes
    and spaces, not whether a name has one.)"""
def dialogue_fill_slots (text, agent_id=None, speaker=None, values=None):
    """Fill `{name}` in `text` from `values` first, then the registered resolvers.
    
    Unknown braces are LEFT ALONE. A writer may have meant them literally, and a
    half-substituted line is easier to recognize than one silently emptied."""
def dialogue_get (scenes, key):
    ...
def dialogue_guard_ok (guard, agent_id, speaker):
    """Evaluate a simple `lhs op number` guard (no guard -> True). Safe: only a resolved
    metric, a comparison operator, and an integer - never arbitrary code."""
def dialogue_outcome_verbs ():
    """Every verb a choice's `; ...` can use right now.
    
    Read by the linter rather than a copy, so a mission that registers its own word is
    lint-known for free - the same rule `amd_action_verbs` follows. `signal` is built
    into `dialogue_apply` and so is not in the handler table; it is added here because
    a linter asking "may an author write this" needs the answer to include it."""
def dialogue_parse (node):
    """Parse one scene node into a plain dict. Pure - no engine calls.
    
    Returns `speaker`, `when`, `lines` [(text, gate)], `choices`, and `beats` - one
    speech block per `@cue`, each `{speaker, surface, direction, lines}` where a
    line is `(text, gate, direction)`.
    
    `lines` is the FLAT list of every spoken variant in the scene, unchanged from
    before cues existed. That is what keeps the shipped single-speaker corpus
    working: `raider_hails.amd` is 8 scenes of bare `%` lines with the speaker in
    the fence, and `dialogue_pick_line` still sees exactly what it always saw. A
    scene with no `@` at all parses to one beat whose speaker is the fence's."""
def dialogue_pick_line (scene, agent_id, speaker):
    """A random NPC line whose gate passes (gates reuse the metric resolver). '' if the
    scene has no eligible line."""
def dialogue_register_outcome (verb, fn):
    """Register an outcome handler: fn(agent_id, speaker, tokens) - tokens are the words
    after the verb. Returning False refuses the pick. (`signal` is built in.)"""
def dialogue_register_scenes (source, domain=None):
    """Register a mission's scenes by key, and RETURN them.
    
    `source` may be a dialogue section node, a whole document, or an already-built
    `{key: node}` dict - `enemy_taunt.mast` hands `dialogue_scenes()` a whole document
    today, so all three shapes are already in use.
    
    Returning the dict is what makes this a one-word edit at every existing call site:
    `SCENES = dialogue_register_scenes(amd_section(doc, "messages"))` keeps the MAST
    variable and adds the registry.
    
    Last registration wins, quietly. A document cache miss legitimately re-parses and
    re-registers different node objects for the same keys, so a collision is normal
    rather than an error."""
def dialogue_register_slot (name, fn):
    """Declare a `{name}` a scene body may use. `fn(agent_id, speaker) -> str`.
    
    Collisions are loud, the same contract as `amd_action_register`: re-registering a
    name with a different function raises, re-registering the same one is a no-op so
    reloading is safe."""
def dialogue_registered_scenes ():
    """Every registered scene, keyed. The dict `hail_offer` falls back to."""
def dialogue_scene (key):
    """A registered scene node by key, or None."""
def dialogue_scenes (section):
    """key -> scene node for every scene in a dialogue SECTION node (empty if None). The
    caller resolves the section (e.g. amd_section(doc, "dialogue"))."""
def dialogue_scenes_registry_clear ():
    """Drop the registry - the per-mission reset."""
def dialogue_set_metric_resolver (fn):
    """Set the guard metric resolver: fn(name, agent_id, speaker) -> number."""
def dialogue_slot_names ():
    """Every registered slot name, for lint and completion."""
def dialogue_slots_clear ():
    """Drop the registry - the per-mission reset."""
def dialogue_speakers (scene):
    """Every distinct speaker key a scene cues, in first-appearance order."""
def signal_emit (name, data=None):
    """Emit a named signal, running all registered ``//signal/<name>`` routes.
    
    Safe to call when no MAST context is active — returns immediately with no
    side effects.
    
    Args:
        name (str): The signal name.
        data (dict, optional): Arbitrary data passed to each signal handler.
            Defaults to None."""
