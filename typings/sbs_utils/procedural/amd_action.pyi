def _action_lines (value):
    """A fence value that may be a list (the nested form) or one string."""
def _action_log (message):
    ...
def _action_norm (text):
    ...
def _action_slug (text):
    ...
def _amd_action_run (value, where=''):
    ...
def _arrives (actor, operand, line):
    """`Kessel Station arrives` - place a declared landmark.
    
    Idempotent by construction: ``landmark_spawn`` returns the existing object when the
    key is already placed, so a beat entered twice does not duplicate it, and a landmark
    that was destroyed IS re-placed. That is why an event verb needs no `once` flag - the
    identity is the landmark key, checked against the live world."""
def _becomes (actor, operand, line):
    """`Kidnapper becomes a pirate` - add a role."""
def _departs (actor, operand, line):
    """`The freighter departs` - remove it from the world.
    
    Handles a NON-space actor too. `delete_object` needs a SpaceObject; a cast
    character (a lifeform, a side) is a bare Agent and has no `delete_object`, so this
    used to raise AttributeError - swallowed by `amd_action_run`, which meant the
    direction silently did nothing. Invisible until urges put `Action:` on lifeforms and
    stations, at which point "the ambassador gives up and leaves" quietly never happened.
    
    A lifeform is unhosted first, so its host does not keep a link to someone who left."""
def _hails (actor, operand, line):
    """`DS 1 hails ds1_brief` - open an incoming hail.
    
    The scene carries everything the hail looks like (`Title:`, `Presentation:`,
    `Audio:`, `Backdrop:`, `Subject:`, `Priority:`, `Face:`, `Color:`) and everything
    it says, so this only has to answer two questions: WHICH scene, and WHO gets
    called.
    
    Which scene: the operand, or - written bare - the scene whose `Speaker:` is this
    actor and whose `When:` is `hail`. The registry answers, so the beat needs no
    `scenes` dict in hand.
    
    Who: the block's own actor. A `Scope: ship` quest runs its block once per holder,
    so the beat calls that ship; a `Scope: shared` quest runs once on the story agent,
    so it calls every player. An urge's actor is the character speaking, which is not a
    ship, so that calls everyone too.
    
    Idempotent per scene within a queue (`hail_offer(key=...)`), so a beat entered
    twice in a frame does not stack two identical calls - the same identity rule
    `arrives` uses. A hail already ANSWERED and archived can be offered again, also
    deliberately: re-entering a beat means it is happening again."""
def _install_builtins ():
    ...
def _joins (actor, operand, line):
    """`Xorn joins tsn` - change side. Distinct from `becomes` because a side is not a
    role: it drives diplomacy, and conflating the two hid that.
    
    Goes through `side_set_object_side` rather than assigning `.side`. Assigning direct
    leaves `side_display` pointing at the OLD side's name (so the GUI keeps showing the
    faction it just left) and skips the warning gate that reports an unknown side key.
    Found by migrating LM's `kidnapper_discovered`, which had it right."""
def _no_longer (actor, operand, line):
    """`Kidnapper is no longer a suspect` - remove a role."""
def _parse_line (line):
    ...
def _role_list (operand):
    """`a pirate` / `pirate, discovered` -> role tokens."""
def amd_action_actor ():
    """Whose block is running - the id "self" resolves to, or None.
    
    A verb needs this when the ACTOR is not the target: `X hails Y` has to know
    whether the block belongs to one player ship (hail that ship) or to the shared
    story agent (hail everyone), and the actor is the only thing that says which."""
def amd_action_actors (name):
    """The live agent ids a direction's actor names, as a set (possibly empty).
    
    Resolution order: ``self`` (the actor this run belongs to, when there is one), then
    a declared AMD **landmark** key (the specific thing an author named in this
    mission), then a **role** (which covers a group - "Raiders become hostile" acts on
    all of them). Both are role lookups underneath, so this stays O(1) and self-cleans
    when an object dies."""
def amd_action_clear_verbs ():
    """Test-only: drop every registered verb (then re-install the built-ins)."""
def amd_action_parse (value):
    """``Action:`` -> ``[{actor, verb, operand, raw, error}]``, in written order.
    
    Pure and engine-free, so it unit-tests offline and the linter can call it. A line
    that matches no verb still comes back, carrying ``error`` - the caller decides
    whether that is a warning (runtime) or a diagnostic (lint), and neither has to
    re-parse."""
def amd_action_register (phrase, fn, operand='required', operand_ref=None, domain=None):
    """Declare a stage-direction verb.
    
    ``fn(actor, operand, line)`` applies it and returns False if it could not. ``actor``
    is the raw name as written (resolution is the verb's business - ``becomes`` wants a
    live object, ``arrives`` wants a landmark record). ``operand`` is
    ``required`` / ``optional`` / ``none``.
    
    ``operand_ref`` says what KIND of thing the operand names, so the tooling can check
    it. ``"node"`` means an AMD record key, which is the only kind so far - it is what
    lets a mistyped ``DS1 hails ds1_breif`` be a lint finding and an editor completion
    rather than a silence at runtime. The runtime ignores it entirely.
    
    Collisions are loud: re-registering a phrase with a different function raises, the
    same contract as ``amd_register_fields``. Re-registering the identical function is a
    no-op so reloading is safe."""
def amd_action_run (value, where='', actor_id=None):
    """Apply every direction in an ``Action:`` block. Returns how many applied.
    
    One bad line never stops the others: a beat that half-fires is bad, but a beat that
    stops at the first dead actor is worse, and the log names which line went wrong.
    
    ``actor_id`` is who "self" means for the duration - an urge's own actor. Without it
    a direction can only name a role or a landmark, so a character wanting to act on
    ITSELF ("the ambassador gives up and leaves") had to be given a role purely so a
    line could point at it. Nested runs restore the previous actor, so an action that
    triggers another cannot leave the wrong "self" behind."""
def amd_action_run_record (record):
    """Run the ``Action:`` block of a parsed AMD record (nothing to do without one)."""
def amd_action_verb_spec (phrase):
    """What a registered verb declares: ``{fn, operand, operand_ref}``, or None."""
def amd_action_verbs ():
    """Every registered phrase, longest first - the order the parser matches in, and
    what an error message offers."""
