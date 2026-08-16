def _alias_index (archetype, traits=()):
    """`{alias -> canonical label}` for one archetype (plus its traits, plus GLOBAL).
    
    TRAITS GO IN FIRST, which means LOWEST priority - later tables overwrite earlier
    ones. That is the opposite of _declared's order (archetype, traits, GLOBAL) and it
    is deliberate: an alias that resolves today must keep resolving to the same field,
    so a trait can only fill in a name nothing else claims. Traits were absent from
    this index entirely, which is why a trait's `aka` never resolved at all."""
def _as_lines (raw):
    """A stage-direction block -> a list of lines. A single-line value is still a list of
    one, so a caller never has to test which shape it got."""
def _d (kind, **kw):
    ...
def _declared (label, archetype=None, traits=()):
    """The declared descriptor for `label`, or None when nothing declares it.
    
    Order is archetype -> its TRAITS (as written) -> GLOBAL, so what a record IS always
    wins a name collision and a trait only fills in what the archetype left unsaid.
    
    Lookup is normalized on BOTH sides, so a table may spell a key `fail on signal`
    while the author writes `Fail on signal` / `fail_on_signal` and all three land
    together. Aliases are tried after canonical names."""
def _declared_under (norm_key, archetype, traits=()):
    """True when `norm_key` is itself a declared (canonical) label, alias aside.
    
    Trait tables are consulted too, and LAST - a trait's own field must count as
    canonical or its aliases could never resolve to it."""
def _install_core_parsers ():
    """Wire the generic value grammars from `amd` (stdlib-only, no engine)."""
def _kind_to_archetype (noun):
    """A bare-noun kind line -> an archetype. Singular or plural both work, so an
    author writes `Character` over one record and `Characters` over a section
    without being told there is a difference."""
def _labels_of (archetype, traits=()):
    """Every declared label in play for an archetype, most specific table first - the
    same precedence `_declared` resolves with.
    
    Labels come back exactly as the tables spell them (`at start`, not `at_start`), so
    this composes with `template_fields`. Matching is still done on the normalized form
    everywhere else; only what is HANDED BACK keeps the authored shape."""
def _norm_label (label):
    """Field labels normalize like `amd_norm`: lowercase, hyphens/spaces -> `_`.
    Inlined (not imported) to keep this module's import graph empty."""
def _schema_changed ():
    """Every table mutation lands HERE, and every memo over those tables is
    cleared HERE. One function on purpose: the previous shape had each registrar
    clearing _ALIAS_CACHE by hand, and two of the three forgot - which is why a
    trait registered after a lookup stayed invisible."""
def _trait_tables (archetype, traits):
    """The trait field tables in play: what the archetype ALWAYS has, then what this
    record says it ALSO does. Same order _declared uses."""
def _traits_key (traits):
    """Traits arrive as a tuple from one caller and a list from another. Normalize
    to a hashable tuple here rather than reaching for lru_cache, which would raise
    TypeError on the list form - at parse time, on an author's file."""
def amd_authored_label (runtime_key, archetype=None, traits=()):
    """The canonical AUTHORED label for a key found in a parsed record's `data` -
    the inverse of `amd_field_key`, and `None` when nothing declares it.
    
    WHY THIS IS NEEDED. A record parsed from `Done when:` / `Part of:` stores `goal` /
    `parent`, because renaming the authored word must never move the stored key. So
    anything that PUBLISHES a parsed record - a fact table, a web page - and titles the
    stored keys prints `Goal` and `Parent`: the exact retired spellings the rename
    existed to remove, taught back to authors by the tooling. Go through here instead."""
def amd_canonical_label (label, archetype=None, traits=()):
    """The canonical spelling of `label` - itself when it is already canonical (or
    unknown), else the field it is an alias of. Underscore/space/hyphen tolerant, so
    `fail_on_signal`, `Fail on signal` and `fail-on-signal` all land together."""
def amd_coerce (descriptor, value):
    """Parse one authored value according to its declared type.
    
    Replaces the per-label `elif` chains: the table says what the field IS, and this
    turns the written text into it. Unknown types fall back to the historical default
    (int -> float -> the trimmed string), so an undeclared field behaves exactly as
    it does today."""
def amd_field_aliases (archetype=None, traits=()):
    """`{canonical label -> [other spellings]}` for one archetype.
    
    The alias index runs alias -> canonical because that is the direction a PARSER
    needs. Anything explaining a field to a human needs the other direction: which
    older words still work. Both are the same table, read two ways."""
def amd_field_doc (label, archetype=None, traits=()):
    """The one-sentence meaning of a field, or `None` when it has none yet.
    
    Callers should degrade to the `hint` rather than inventing prose: a generated field
    table with a blank cell says "nobody has explained this yet", which is true and
    fixable in one line. Prose invented at the point of display is how the last set of
    hand-written tables drifted."""
def amd_field_key (label, archetype=None, traits=()):
    """The name the RUNTIME should store this field under: the descriptor's `key`
    when it declares one, else the canonical label. This is the one place the
    authored word and the stored word are allowed to differ."""
def amd_is_declared (label, archetype=None, traits=()):
    """True when some table declares this field. The reader needs this to tell a
    declared `text` field (stays a string) from an UNDECLARED one, which must keep
    the historical `amd_num` default - else `Time: 30` silently becomes "30"."""
def amd_is_internal (label, archetype=None):
    """True when a field still parses but should not be OFFERED (picker, completion,
    new-record template)."""
def amd_kind_defaults (noun):
    """Every field a kind noun implies, as {field: value}. Singular / plural both work,
    matching `_kind_to_archetype` - an author writes `Beat` over one record and `Beats`
    over a section without being told there is a difference.
    
    `Quest` carries none - it is the neutral word, for a record that is neither a story
    moment nor clearly one of the two. `Job` restates today's defaults (per ship, waiting
    to be accepted) rather than changing them, so peacetime's board - which says none of
    this - keeps working exactly as written."""
def amd_kind_menu ():
    """The nouns to OFFER, in order, with their group and what each implies.
    
    Everything in `amd_known_kinds` still parses - this only decides what is put in
    front of someone choosing."""
def amd_kind_show_default (noun):
    """The `Show:` a kind noun implies, or None."""
def amd_known_kinds ():
    """Every noun an author may legally write as a kind line - what the error
    message offers when they write something else."""
def amd_read_field (label, value, archetype=None, traits=()):
    """One authored `Label: value` -> `(runtime_key, parsed_value)`.
    
    The whole point of the registry in one call: alias resolved, type coerced, stored
    under the runtime key - so the reader, the linter and the editor cannot disagree
    about what a line means."""
def amd_register_archetype_traits (archetype, traits, domain=None):
    """Give an archetype traits it always has (see ARCHETYPE_TRAITS)."""
def amd_register_fields (archetype, table, domain=None):
    """Declare (or extend) an archetype's field table.
    
    A mission or addon calls this so its own labels get the same typed widget, the same
    lint and the same coercion as core fields - today OU's ~30 labels are invisible to
    every tool because there is nowhere to say what they are.
    
    Collisions are LOUD ON PURPOSE: re-declaring a core field with a different
    descriptor raises at registration (startup), rather than silently shadowing it and
    drifting. Re-registering an IDENTICAL descriptor is a no-op, so reloading is safe."""
def amd_register_parser (type_name, fn):
    """Register the parser for a value type. Domain types (`trigger`, `reward`) call
    this at import time so `amd_schema` never has to depend on the domain module."""
def amd_register_section_names (names, archetype, domain=None):
    """Teach the section-name table that sections called any of `names` hold records of
    `archetype` - so authors name a section the way their story names it (`Contracts`,
    `Bounties`) and never have to write a kind line."""
def amd_register_trait (name, table, domain=None):
    """Declare (or extend) a trait's field table - the same contract as
    `amd_register_fields`, for a concern rather than a kind of thing."""
def amd_resolve_kind (own_kind=None, ancestor_kinds=(), section_key=None, field_labels=(), ancestor_sections=()):
    """Which kind of record this is, in the order the author would expect.
    
    1. the record's OWN kind line (`Characters` at the top of its fence)
    2. the nearest ancestor that declared one - sections inherit downward
    3. a document-level kind line
    4. the section-name table - `## Jobs` holds quests, and the table is
       extensible so a story can call them `Contracts` or `Bounties`
    5. the discriminating-field fallback
    
    Step 4 is the common path: most files declare nothing, because the section is
    already NAMED for what it holds. The kind line exists for the files where the
    name does not say it.
    
    `ancestor_kinds` / `ancestor_sections` are ordered NEAREST FIRST."""
def amd_resolve_kind_chain (own_kind=None, ancestors=(), field_labels=(), own_section=None):
    """Which kind of record this is, asking each ancestor IN TURN, closest first.
    
    `ancestors` is `[(kind_line, section_key), ...]` ordered **nearest first** - one pair
    per ancestor, so an ancestor's kind line and its section name stay at the same
    distance. `own_section` is the record's own key, used ONLY when it has no real
    ancestor (the flat-file shape, where nothing else can name its kind).
    
    THIS IS THE ONE IMPLEMENTATION. `amd_resolve_kind` keeps the old shape - two
    separate lists - and that shape is the bug: every ancestor KIND was tried before any
    section NAME, so a kind line on the document root reached past every section beneath
    it and typed a whole file. Both readers (`amd_core` for the tooling, `quest.py` for
    the game) call this now, because two copies of this grammar is exactly how the
    tooling and the game came to disagree about the same file."""
def amd_trait_names ():
    """Every trait a record may claim in `Also:`."""
def amd_traits_of (data):
    """The traits a record claims, from its `Also:` value (a comma list)."""
def amd_vocabulary_restore (snap):
    """Put back an `amd_vocabulary_snapshot`, and drop every memo over it."""
def amd_vocabulary_snapshot ():
    """Everything `amd_register_*` can change, copied deeply enough to put back.
    
    For a caller that has to LOAD a mission's vocabulary without KEEPING it. The
    pre-flight lint gate is the reason this exists: it imports the mission's
    `*_amd.py` so its words are declared before linting, and it runs in the same
    process that is about to run the mission - so without a restore it pre-registers
    fields the mission then re-registers, and any pair that disagrees raises at
    startup on a mission that was fine a moment ago. (Measured: linting
    LegendaryMissions in-process turned a passing run into `AMD field 'call sign'
    is already declared ... with a different meaning`, because loading `lm_amd.py`
    early let it collide with `casino/bar_content.py`, which the gate does not load.)
    
    It also stops one mission's words leaking into the next one linted in the same
    process, which is how OpenUniverse briefly inherited LegendaryMissions' fields."""
def archetype_for_section (section_key):
    """The archetype a conventionally-named `## section` key maps to, or None.
    Case/trailing-`s` tolerant (`Items`, `items`, `Item` all -> item)."""
def boolean ():
    """A yes/no flag. Stays `type: enum` so the editor keeps rendering a two-value
    dropdown, but carries `bool` so `amd_coerce` returns a real bool - `Required: false`
    used to coerce to the STRING "false", which is truthy."""
def color (hint='#rgb or #rrggbb'):
    """A hex color - the editor shows a swatch/picker (LSP already has one)."""
def compound (verbs, hint=None):
    """A verb-led field whose operand type depends on the verb: `When: reach i,j`
    vs `When: signal X`. `verbs` maps verb -> operand descriptor. The editor may
    render a verb dropdown + a typed operand, or fall back to text."""
def coord2 (hint='i, j'):
    """A grid cell `i, j` - the map view's draggable landmark/region coordinate."""
def counted (hint='salvage x5, bio_sample x1'):
    """A shopping list - `key xN, key xM` (a bare key counts 1)."""
def csv (hint='comma, separated'):
    """A free comma list (roles, races, targets) - not resolved against a symbol
    table, so distinct from `ref(csv=True)`."""
def enum (*values, **kw):
    """A closed set of string values (dropdown). `open=True` lets the author type
    a value outside the set (the editor keeps it, the linter still warns).
    
    `aka={old: new}` renames a VALUE without breaking existing files: the old
    spelling still parses and coerces to the new one, but only the new one is
    offered. This is the value-level twin of `field(aka=...)` - `State: idle`
    keeps working while `available` (the word the player actually sees) becomes
    the one an author is shown."""
def enum_accepts (label, archetype=None):
    """Every value the linter should ACCEPT for an enum field - the current values
    plus any retired spelling kept alive by `aka`. `enum_values` stays the list an
    author is OFFERED, so a rename shows only the new word but never flags the old."""
def enum_values (label, archetype=None):
    """The allowed values for an enum field, or None if the field isn't a closed
    enum (so the linter only value-checks genuine enums). An `open` enum returns
    None here too - its values are suggestions, not a closed set."""
def field (descriptor, key=None, aka=None, internal=None, doc=None):
    """Wrap a type descriptor with the things a table entry also has to own:
    `key` - the name the RUNTIME stores it under, when that differs from the authored
    label (`Pays:` -> `reward`), `aka` - every other spelling that means this field,
    and `doc` - one sentence saying what the field MEANS.
    
    WHY `doc` LIVES HERE. `hint` is example values; it never says what a field does. So
    every consumer that had to explain a field wrote its own prose, by hand, on a
    documentation page - and those pages drifted from the table until one of them taught
    `When:` as the COMPLETION trigger when it is an alias of `Starts when:`, the START
    one. Prose kept beside the type cannot drift from it. Keep it link-free: the schema
    owns what a field means, each page owns its own cross-references.
    
    Owning aliases here is what makes renaming safe forever: a rename is one line in
    this table and no `.amd` file in the world has to change.
    
    RULE: renaming the AUTHORED name must not move the STORED key. When a canonical
    label is introduced for an existing field (`When:` -> `Starts when:`), pin `key=`
    to what the data was already stored under, so every reader keeps working. The two
    are independent on purpose - one is what a writer types, the other is an
    implementation detail. Descriptors stay plain
    JSON-able dicts, so they still cross the LSP boundary untouched."""
def field_schema (label, archetype=None, traits=()):
    """The descriptor for one field `label` within `archetype` (falling back to
    the GLOBAL type-stable fields, then plain text). Never returns None - an
    unknown field is `text`, so the editor always has a widget."""
def infer_archetype (field_labels, section_key=None):
    """Resolve a record's archetype: its section key if conventionally named,
    else the first discriminating field it carries. `field_labels` is any
    iterable of the record's fence labels. Returns an archetype name or None."""
def integer (hint=None):
    ...
def kv (hint='kind=bio, range=medium'):
    """`k=v, k=v` settings stamped onto whatever the record produces."""
def lines (hint='Kidnapper becomes a pirate'):
    """A block of stage directions, one per list item - the ``Action:`` form. Distinct
    from `csv` because a direction contains commas and must not be split on them."""
def makeup (hint='60% Kralien, 40% Arvonian'):
    """A percentage mix, a plain list, or a single value - whichever was written."""
def multiline (hint=None):
    """Multi-line prose (rendered as a textarea)."""
def pct (hint='40%'):
    """`40%` -> 0.4 (a bare number passes through)."""
def record_schema (field_labels, section_key=None):
    """`{archetype, fields: {label: descriptor}}` for a whole record - the payload
    the Inspector needs to render every field with the right widget. Resolves the
    archetype, then maps each present label through `field_schema`."""
def ref (kind='node', csv=False, hint=None):
    """A reference to a named symbol: `node` (any AMD node key / MAST label),
    `side` (a side key), or `role`. `csv=True` for a comma list of them."""
def reward (hint='200 credits, 2 torpedoes, earns tsn honest +10'):
    """What a job pays: comma-separated credits / items / `earns <faction> <pole> <n>`.
    A reputation clause is only meaningful on a player-held quest (DESIGN_RECORD.md s4)."""
def signal ():
    """A signal name (`Then: signal X`, `Fail on signal: Y`) - dropdown of the
    mission's emitted / routed signals."""
def starter_fields (archetype):
    """The short set a new record of this archetype opens with (see STARTERS), falling
    back to the first few offered fields for an archetype with no opinion."""
def template_fields (archetype, include_internal=False):
    """The ordered field labels a 'new <archetype>' skeleton should offer, or []
    for an unknown archetype. Preserves the table's authoring order (dict order).
    
    `internal` fields are LEFT OUT: they are implementation forms (`on kill`, what
    `Done when:` compiles to) or shapes a newer field absorbed (`Fail after:` ->
    `Fails when:`). Both must keep parsing; neither should be offered to an author or
    land in a new-record skeleton."""
def text (hint=None):
    """Free single-line text (the default when a field isn't in the schema)."""
def trigger (hint='5 drone_down  |  reach 6, 4  |  destroy 4 raiders'):
    """A game event to wait for. A bare token IS a signal name; verb-led forms
    (`reach`, `destroy`, `dock`, ...) name a different shape."""
def weighted (hint='by-the-book 40, fearsome 30'):
    """A weighted vocabulary - `name N, name N` (a bare name weighs 0)."""
