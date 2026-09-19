def _escalates (value, stages, key):
    """``Escalates:`` -> ``"deadline"`` | ``"firing"`` | None.
    
    ``with deadline`` (the interesting one) takes the stage from how much of the bound
    quest's clock is left, so the drama curve IS the countdown that already exists - no
    second clock to keep in sync. ``yes`` advances a stage per firing, for an urge with
    no deadline behind it.
    
    Staged lines with no ``Escalates:`` are a warning, not a guess: the author clearly
    meant something by writing ``%%``, and silently flattening it would look like the
    feature was broken. Defaulting it on would be worse - it would change how existing
    flat pools with a stray ``%%`` behave."""
def _every (value):
    """``Every:`` -> seconds, or a ``(low, high)`` range for ``3-5m``.
    
    A range is jitter, and jitter is the difference between a person and a metronome -
    the one shipped nagger in the corpus was written ``random.randint(180, 300)``. The
    unit is read from the WHOLE string, so ``3-5m`` means three-to-five minutes rather
    than three seconds to five minutes."""
def _int (value, default):
    ...
def _urge_pool (desc):
    """Body prose -> ``(pool, stages)``.
    
    Same rules as ``amd_chatter``: one line per entry, ``//`` comments ignored. The
    number of leading ``%`` is the escalation STAGE - ``%`` first asking, ``%%`` more
    insistent, ``%%%`` the last time. A line with no marker sits at stage 1.
    
        % Ambassador Vell is on the docking ring, when convenient.
        %% Vell again. My transport window is closing, captain.
        %%% This is the last time I ask.
    
    ``pool`` is every line flat (what a non-escalating urge uses, unchanged from before);
    ``stages`` is ``{1: [...], 2: [...]}``, present only when the author actually wrote
    more than one stage. So the marker count IS the escalation curve - no second field to
    keep in sync with the words, and the author keeps the dial."""
def amd_duration_seconds (value):
    """`amd_duration_parts` collapsed to seconds, or None if there's no number."""
def amd_parse_facts (text, handler=None, default=<function amd_num at 0x0000026177D728E0>, archetype=None, errors=None):
    """Parse one fact-sheet fence into a dict.
    
    Per label, in order: the caller's `handler` gets first refusal (returns truthy to
    consume it); then the FIELD REGISTRY, when the field is declared for `archetype` -
    which resolves the alias, coerces by the declared type and stores under the runtime
    key; then `default` (historically `amd_num`) for anything undeclared, so an unknown
    field behaves exactly as it does today.
    
    `errors` may be a list - parse problems are appended to it in a writer's terms
    rather than raised, so a typo never takes a mission down; the linter is what makes
    them loud. Returns `data`, carrying the kind line (when present) under `KIND_KEY`."""
def amd_urge_data (text):
    """Parse one urge fence into a data dict (default coercion - all fields are
    strings). Most urges need no fence values beyond these few; the words are the BODY."""
def urge_add (agents, record):
    """Give one urge to one or more agents. Idempotent per (agent, urge key): re-running
    a section does not give an actor the same want twice."""
def urge_record (key=None, whenever='always', every=60, until=None, weight=0, pool=None, action=None, actor=None, stages=None, escalates=None, title=None):
    """One urge, as plain data. ``every`` is seconds; ``pool`` is the flat line list.
    
    ``stages`` is the optional ``{1: [...], 2: [...]}`` map built from ``%`` markers, and
    ``escalates`` is ``"deadline"`` | ``"firing"`` | None. With neither, an urge behaves
    exactly as it did before escalation existed."""
def urges_from_section (section, require_marker=False):
    """Urge records from a section node's children (empty list if None).
    
    A heading with no body is skipped and logged - an urge with nothing to say would
    burn its turn every pass and never be noticed.
    
    ``require_marker`` takes ONLY the children that declared the bare ``Urge`` marker
    (which lands as ``__kind__: urge``). Off by default, because every existing caller
    hands in a section whose children are all urges by construction. A caller that hands
    in a CAST record - where a future nested heading might be anything - passes True, or
    the first person to add a note under a character silently gives them a nagging urge
    that says whatever that note's body happens to be."""
def urges_install (section):
    """Give every authored urge to the agents its ``Actor:`` names. Returns how many
    (record, agent) pairs were installed.
    
    An urge whose actor nobody answers to is LOGGED and skipped, never silently dropped -
    most often it means the AMD was installed before the actor spawned, which the message
    says. Idempotent per (agent, urge key), so re-running a section is safe."""
def urges_install_on (agents, section, key=None, require_marker=False):
    """Install the urges authored under a record onto agents you ALREADY have.
    
    The identity path, next to ``urges_install``'s name-resolution path. A mission that
    is holding the character - it just spawned them, or boarded them - should not have to
    invent a role so a name lookup can find its way back to an agent it already has.
    
    ``key`` picks one record out of ``section`` (a cast entry, say); without it the
    section's own children are the urges. Returns how many were installed; idempotent per
    (agent, urge key), so re-entering a route does not stack a second copy."""
