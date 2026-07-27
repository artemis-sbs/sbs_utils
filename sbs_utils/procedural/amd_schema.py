"""Declarative AMD FIELD SCHEMA - the single source of truth for what each fence
field *means*, so three consumers stop each re-deriving it from scratch:

  * the **linter** (`amd_lint`) can validate a field's VALUE, not just its
    references - e.g. `State: activ` (typo) becomes a warning instead of silently
    doing nothing;
  * the **editor** (`amd_lsp` -> the VS Code Inspector) can render a typed widget
    per field - a dropdown for an enum, a key-picker for a node reference, a
    swatch for a colour - instead of a plain text box; and
  * a **"new record" template** can emit the right empty fence skeleton for a
    given kind of record.

Today that knowledge is scattered and duplicated: `amd_core._extract_data_refs`
knows the reference-bearing fields (Scene/Parent/Then/When/At/...), `amd_lint`
hardcodes the scan-tab vocabulary, and `inspectorForm.js` hardcodes its own
`FIELD_ENUMS`. This module consolidates it.

WHY ARCHETYPE-KEYED, NOT A FLAT LABEL MAP. Most field labels are globally
unambiguous (`Color` is always a colour, `At` is always a cell), but at least one
is NOT: `Mode` is `consumable|install|resource` on an ITEM and
`story|sandbox|skirmish|war|campaign` on a MAP. So the schema is keyed by record
*archetype* (quest / lifeform / item / side / scan / landmark / region / map),
with a small set of type-stable GLOBAL fields as a fallback layer.

An archetype is resolved from a section's key when the mission names it
conventionally (`## Items` -> item), else inferred from which discriminating
field the record carries (`Scan of:` -> scan, `Enemies:` -> side, ...).

Descriptors are plain JSON-able dicts so they cross the LSP boundary untouched.
Stdlib-only (like `amd_lint`) so it ships in `sbs.pyz` and unit-tests offline.
"""

# --- field-type descriptor constructors -------------------------------------
# Each returns a plain dict the editor/linter consume. `type` is the widget kind;
# extra keys parameterise it. `hint` is placeholder / help text.

def text(hint=None):
    """Free single-line text (the default when a field isn't in the schema)."""
    return _d("text", hint=hint)

def multiline(hint=None):
    """Multi-line prose (rendered as a textarea)."""
    return _d("multiline", hint=hint)

def integer(hint=None):
    return _d("int", hint=hint)

def boolean():
    """A yes/no flag. Stays `type: enum` so the editor keeps rendering a two-value
    dropdown, but carries `bool` so `amd_coerce` returns a real bool - `Required: false`
    used to coerce to the STRING "false", which is truthy."""
    return _d("enum", values=["true", "false"], bool=True)

def enum(*values, **kw):
    """A closed set of string values (dropdown). `open=True` lets the author type
    a value outside the set (the editor keeps it, the linter still warns).

    `aka={old: new}` renames a VALUE without breaking existing files: the old
    spelling still parses and coerces to the new one, but only the new one is
    offered. This is the value-level twin of `field(aka=...)` - `State: idle`
    keeps working while `available` (the word the player actually sees) becomes
    the one an author is shown."""
    return _d("enum", values=list(values), open=kw.get("open", False),
              value_aka={str(k).lower(): v for k, v in (kw.get("aka") or {}).items()} or None)

def ref(kind="node", csv=False, hint=None):
    """A reference to a named symbol: `node` (any AMD node key / MAST label),
    `side` (a side key), or `role`. `csv=True` for a comma list of them."""
    return _d("ref", ref=kind, csv=csv, hint=hint)

def coord2(hint="i, j"):
    """A grid cell `i, j` - the map view's draggable landmark/region coordinate."""
    return _d("coord2", hint=hint)

def color(hint="#rgb or #rrggbb"):
    """A hex colour - the editor shows a swatch/picker (LSP already has one)."""
    return _d("color", hint=hint)

def face(hint="terran / male / female / <face string>"):
    """A face keyword or raw face string - the editor's Face Builder + preview."""
    return _d("face", hint=hint)

def signal():
    """A signal name (`Then: signal X`, `Fail on signal: Y`) - dropdown of the
    mission's emitted / routed signals."""
    return _d("signal")

def csv(hint="comma, separated"):
    """A free comma list (roles, races, targets) - not resolved against a symbol
    table, so distinct from `ref(csv=True)`."""
    return _d("csv", hint=hint)

def compound(verbs, hint=None):
    """A verb-led field whose operand type depends on the verb: `When: reach i,j`
    vs `When: signal X`. `verbs` maps verb -> operand descriptor. The editor may
    render a verb dropdown + a typed operand, or fall back to text."""
    return _d("compound", verbs=verbs, hint=hint)


# --- author-shaped value types ----------------------------------------------
# These name the little grammars authors were already writing by hand. Each had a
# private parser somewhere (amd.py, amd_quest.py, LM's recipes.py); naming them as
# TYPES is what lets the Inspector render a real widget and the linter check a real
# value, instead of every one of them being an unvalidated text box.

def duration(hint="6 minutes / 90 seconds"):
    """`6 minutes` / `90 seconds` / a bare number (minutes)."""
    return _d("duration", hint=hint)

def pct(hint="40%"):
    """`40%` -> 0.4 (a bare number passes through)."""
    return _d("pct", hint=hint)

def weighted(hint="by-the-book 40, fearsome 30"):
    """A weighted vocabulary - `name N, name N` (a bare name weighs 0)."""
    return _d("weighted", hint=hint)

def makeup(hint="60% Kralien, 40% Arvonian"):
    """A percentage mix, a plain list, or a single value - whichever was written."""
    return _d("makeup", hint=hint)

def counted(hint="salvage x5, bio_sample x1"):
    """A shopping list - `key xN, key xM` (a bare key counts 1)."""
    return _d("counted", hint=hint)

def kv(hint="kind=bio, range=medium"):
    """`k=v, k=v` settings stamped onto whatever the record produces."""
    return _d("kv", hint=hint)

def reward(hint="200 credits"):
    """What a job pays."""
    return _d("reward", hint=hint)

def trigger(hint="5 drone_down  |  reach 6, 4  |  destroy 4 raiders"):
    """A game event to wait for. A bare token IS a signal name; verb-led forms
    (`reach`, `destroy`, `dock`, ...) name a different shape."""
    return _d("trigger", hint=hint)


# --- field descriptors: type + alias + runtime key ---------------------------
def field(descriptor, key=None, aka=None):
    """Wrap a type descriptor with the two things a table entry also has to own:
    `key` - the name the RUNTIME stores it under, when that differs from the authored
    label (`Pays:` -> `reward`), and `aka` - every other spelling that means this field.

    Owning aliases here is what makes renaming safe forever: a rename is one line in
    this table and no `.amd` file in the world has to change.

    RULE: renaming the AUTHORED name must not move the STORED key. When a canonical
    label is introduced for an existing field (`When:` -> `Starts when:`), pin `key=`
    to what the data was already stored under, so every reader keeps working. The two
    are independent on purpose - one is what a writer types, the other is an
    implementation detail. Descriptors stay plain
    JSON-able dicts, so they still cross the LSP boundary untouched."""
    d = dict(descriptor)
    if key:
        d["key"] = key
    if aka:
        d["aka"] = [str(a).strip().lower() for a in aka]
    return d


def _d(kind, **kw):
    d = {"type": kind}
    for k, v in kw.items():
        if v is not None and v is not False:
            d[k] = v
    return d


# --- archetype field tables -------------------------------------------------
# Each maps a NORMALISED (lower-cased) field label -> descriptor. Labels match
# the loaders in procedural.amd_* and the parser in amd_core._extract_data_refs.

QUEST = {
    # `available` is the word the PLAYER already sees - QuestState.IDLE renders as
    # "Available" - so it is the word the author writes. `idle` stays as an alias.
    "state": enum("available", "active", "secret", "posting", "complete", "failed",
                  aka={"idle": "available"}),
    "objective": text(hint="the sentence the player reads"),
    # `Goal:` used to set BOTH the completion trigger and the objective TEXT, so a
    # job's quest log read "Signal 5 drone_down". Split: Objective is the prose,
    # Done when is the trigger.
    "done when": field(trigger(), key="goal", aka=("goal",)),
    "starts when": field(compound({"reach": coord2(), "travel": coord2(),
                                   "signal": signal()},
                                  hint="reach i, j  |  5 drone_down"),
                         key="when", aka=("when",)),
    "then": compound({"reveal": ref("node"), "signal": signal()},
                     hint="reveal KEY  |  signal NAME"),
    "parent": ref("node"),
    "scope": enum("shared", "ship"),
    "pays": field(reward(), key="pays", aka=("reward",)),
    "earns": reward(),
    "tier": integer(),
    "fail on signal": signal(),
    "fail on all dead": ref("role"),
    "fail after": duration(),
    "complete after": duration(),
    "on accept": text(hint="toast <message>"),
    "on complete": text(hint="toast <message>"),
    "required": boolean(),
    "critical": boolean(),
    "win": boolean(),
    "lose": boolean(),
    "win text": text(hint="the end-screen line"),
    "lose text": text(hint="the end-screen line"),
    "citation": multiline(hint="the commendation read out at the end"),
    "reveals": field(multiline(hint="what a scan of the target returns"),
                     key="reveals", aka=("scan text",)),
    "accept on": csv(hint="comms, admiral"),
    "engage on": csv(hint="helm"),
}

DIALOGUE = {
    "speaker": ref("node", hint="who says it"),
    "when": text(hint="the condition this line plays under"),
    "file": text(hint="a sibling .amd to pull lines from"),
}

LIFEFORM = {
    "face": face(),
    "roles": csv(),
    "host": ref("node", hint="a ship/node key to host the character on"),
    "color": color(),
    "title color": color(),
    "path": ref("node", hint="a //comms route = the character's voice"),
    "scene": ref("node"),
    "speaker": ref("node"),
}

ITEM = {
    "type": text(hint="item/<category>/<sub>"),
    "art": text(hint="pickup art_id"),
    "mode": enum("consumable", "install", "resource"),
    "targets": csv(hint="ship, cockpit, ..."),
    "consoles": enum("helm", "weapons", "science", "engineering", "comms",
                     open=True),
    "duration": integer(hint="seconds"),
    "tier": integer(),
    "price": integer(),
    "modifiers": text(hint="blob_key value, blob_key2 value2"),
}

SIDE = {
    "color": color(),
    "icon index": integer(),
    "icon": integer(),
    "races": csv(),
    "enemies": ref("side", csv=True),
    "allies": ref("side", csv=True),
    "neutral": ref("side", csv=True),
}

SCAN = {
    "scan of": ref("role", hint="the role/hull this scan describes"),
    "tab": enum("scan", "status", "intel", "mat", "bio"),
}

LANDMARK = {
    # Open: real missions use derelict/station/worldlet plus npc/antimatter and
    # mission-specific prefab kinds - suggest, don't reject.
    "kind": enum("derelict", "station", "worldlet", "npc", "antimatter", open=True),
    "side": ref("side"),
    "roles": csv(),
    "art": text(),
    "behavior": text(hint="behav_station / behav_npcship / ..."),
    "at": coord2(),
    "loc": coord2(),
    "system": text(),
}

REGION = {
    "center": coord2(),
    "radius": integer(),
    "color": color(),
    "kind": text(),
}

MAP = {
    "mode": enum("story", "sandbox", "skirmish", "war", "campaign"),
    "scope": enum("shared", "ship"),
}

ARCHETYPES = {
    "quest": QUEST, "lifeform": LIFEFORM, "item": ITEM, "side": SIDE,
    "scan": SCAN, "landmark": LANDMARK, "region": REGION, "map": MAP,
    "dialogue": DIALOGUE,
}

# Type-stable everywhere: if a field isn't in the resolved archetype, fall back
# to these before defaulting to plain text.
GLOBAL = {
    "display": text(hint="the name shown in game, when it differs from the heading"),
    "weight": integer(hint="relative chance when one of a set is picked"),
    "color": color(),
    "title color": color(),
    "face": face(),
    "at": coord2(),
    "loc": coord2(),
}


# --- archetype resolution ---------------------------------------------------
# A conventional section key names its archetype directly (## Items -> item).
_SECTION_ALIASES = {
    "quests": "quest", "quest": "quest", "objectives": "quest",
    "lifeforms": "lifeform", "lifeform": "lifeform", "cast": "lifeform",
    "characters": "lifeform", "crew": "lifeform",
    "items": "item", "item": "item",
    "sides": "side", "side": "side", "factions": "side",
    "scans": "scan", "scan": "scan", "science": "scan",
    "landmarks": "landmark", "landmark": "landmark",
    "regions": "region", "region": "region",
    "maps": "map", "map": "map",
    "dialogue": "dialogue", "lines": "dialogue",
    # Names real missions already use for a group of quests. Before these, 5108 of
    # the corpus's 5273 field uses resolved to NO archetype, so the busiest part of
    # the language had no typing, no lint and no widgets.
    "jobs": "quest", "job": "quest", "goals": "quest", "goal": "quest",
    "narrative": "quest", "missions": "quest", "mission": "quest",
    "contracts": "quest", "bounties": "quest", "scenario": "map",
}

# When there's no conventional section key, the FIRST discriminating field a
# record carries identifies its archetype. Order = specificity (most telling
# first), since a record may legitimately carry several.
_DISCRIMINATORS = (
    ("scan of", "scan"),
    ("scan_of", "scan"),
    # quest-only fields, checked early: the FLAT a2x files (1444 records directly
    # under the document root) have no section to be named by, so a discriminating
    # field is the only thing that can classify them.
    ("goal", "quest"), ("done when", "quest"), ("done_when", "quest"),
    ("objective", "quest"), ("pays", "quest"),
    ("complete after", "quest"), ("complete_after", "quest"),
    ("fail on all dead", "quest"), ("fail_on_all_dead", "quest"),
    ("on accept", "quest"), ("on_accept", "quest"),
    ("enemies", "side"), ("allies", "side"), ("neutral", "side"),
    ("modifiers", "item"),
    ("center", "region"), ("radius", "region"),
    ("face", "lifeform"), ("scene", "lifeform"),
    ("speaker", "dialogue"),
    ("at", "landmark"), ("kind", "landmark"),
    ("state", "quest"), ("when", "quest"), ("then", "quest"),
    ("parent", "quest"), ("fail on signal", "quest"),
)


def archetype_for_section(section_key):
    """The archetype a conventionally-named `## section` key maps to, or None.
    Case/trailing-`s` tolerant (`Items`, `items`, `Item` all -> item)."""
    if not section_key:
        return None
    k = str(section_key).strip().lower()
    return _SECTION_ALIASES.get(k) or _SECTION_ALIASES.get(k.rstrip("s"))


def amd_resolve_kind(own_kind=None, ancestor_kinds=(), section_key=None,
                     field_labels=(), ancestor_sections=()):
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
    for candidate in (own_kind,) + tuple(ancestor_kinds):
        if candidate:
            arch = _kind_to_archetype(candidate)
            if arch:
                return arch
    for key in (section_key,) + tuple(ancestor_sections):
        arch = archetype_for_section(key)
        if arch:
            return arch
    return infer_archetype(field_labels)


def _kind_to_archetype(noun):
    """A bare-noun kind line -> an archetype. Singular or plural both work, so an
    author writes `Character` over one record and `Characters` over a section
    without being told there is a difference."""
    if not noun:
        return None
    n = str(noun).strip().lower().replace("-", "_").replace(" ", "_")
    return (_SECTION_ALIASES.get(n) or _SECTION_ALIASES.get(n.rstrip("s"))
            or (n if n in ARCHETYPES else None))


def amd_known_kinds():
    """Every noun an author may legally write as a kind line - what the error
    message offers when they write something else."""
    return sorted(set(_SECTION_ALIASES) | set(ARCHETYPES))


def infer_archetype(field_labels, section_key=None):
    """Resolve a record's archetype: its section key if conventionally named,
    else the first discriminating field it carries. `field_labels` is any
    iterable of the record's fence labels. Returns an archetype name or None."""
    by_section = archetype_for_section(section_key)
    if by_section:
        return by_section
    present = {str(l).strip().lower() for l in (field_labels or ())}
    for label, arch in _DISCRIMINATORS:
        if label in present:
            return arch
    # 'type: item/...' is a weaker signal than the item-specific 'modifiers'.
    return None


# --- lookup API (what the LSP / linter call) --------------------------------
def field_schema(label, archetype=None):
    """The descriptor for one field `label` within `archetype` (falling back to
    the GLOBAL type-stable fields, then plain text). Never returns None - an
    unknown field is `text`, so the editor always has a widget."""
    d = _declared(label, archetype)
    return d if d is not None else text()


def _declared(label, archetype=None):
    """The declared descriptor for `label`, or None when nothing declares it.

    Lookup is normalised on BOTH sides, so a table may spell a key `fail on signal`
    while the author writes `Fail on signal` / `fail_on_signal` and all three land
    together. Aliases are tried after canonical names."""
    key = _norm_label(label)
    tables = [t for t in (ARCHETYPES.get(archetype) if archetype else None, GLOBAL) if t]
    canonical = _alias_index(archetype).get(key, key)
    for want in (key, canonical):
        for table in tables:
            for declared_label, descriptor in table.items():
                if _norm_label(declared_label) == want:
                    return descriptor
    return None


def amd_is_declared(label, archetype=None):
    """True when some table declares this field. The reader needs this to tell a
    declared `text` field (stays a string) from an UNDECLARED one, which must keep
    the historical `amd_num` default - else `Time: 30` silently becomes "30"."""
    return _declared(label, archetype) is not None


def record_schema(field_labels, section_key=None):
    """`{archetype, fields: {label: descriptor}}` for a whole record - the payload
    the Inspector needs to render every field with the right widget. Resolves the
    archetype, then maps each present label through `field_schema`."""
    arch = infer_archetype(field_labels, section_key)
    fields = {str(l): field_schema(l, arch) for l in (field_labels or ())}
    return {"archetype": arch, "fields": fields}


def enum_values(label, archetype=None):
    """The allowed values for an enum field, or None if the field isn't a closed
    enum (so the linter only value-checks genuine enums). An `open` enum returns
    None here too - its values are suggestions, not a closed set."""
    d = field_schema(label, archetype)
    if d.get("type") == "enum" and not d.get("open"):
        return list(d.get("values", ()))
    return None


def enum_accepts(label, archetype=None):
    """Every value the linter should ACCEPT for an enum field - the current values
    plus any retired spelling kept alive by `aka`. `enum_values` stays the list an
    author is OFFERED, so a rename shows only the new word but never flags the old."""
    d = field_schema(label, archetype)
    if d.get("type") != "enum" or d.get("open"):
        return None
    return list(d.get("values", ())) + list(d.get("value_aka") or {})


def template_fields(archetype):
    """The ordered field labels a 'new <archetype>' skeleton should offer, or []
    for an unknown archetype. Preserves the table's authoring order (dict order)."""
    table = ARCHETYPES.get(archetype)
    return list(table.keys()) if table else []


# --- aliases: one field, many spellings -------------------------------------
_ALIAS_CACHE = {}


def _alias_index(archetype):
    """`{alias -> canonical label}` for one archetype (plus GLOBAL), built on demand."""
    cached = _ALIAS_CACHE.get(archetype)
    if cached is not None:
        return cached
    index = {}
    for table in (GLOBAL, ARCHETYPES.get(archetype) or {}):
        for canonical, d in table.items():
            for a in d.get("aka", ()):
                index[_norm_label(a)] = _norm_label(canonical)
    _ALIAS_CACHE[archetype] = index
    return index


def amd_canonical_label(label, archetype=None):
    """The canonical spelling of `label` - itself when it is already canonical (or
    unknown), else the field it is an alias of. Underscore/space/hyphen tolerant, so
    `fail_on_signal`, `Fail on signal` and `fail-on-signal` all land together."""
    key = _norm_label(label)
    if _declared_under(key, archetype):
        return key
    return _alias_index(archetype).get(key, key)


def _declared_under(norm_key, archetype):
    """True when `norm_key` is itself a declared (canonical) label, alias aside."""
    for table in (t for t in (ARCHETYPES.get(archetype) if archetype else None, GLOBAL) if t):
        if any(_norm_label(l) == norm_key for l in table):
            return True
    return False


def amd_field_key(label, archetype=None):
    """The name the RUNTIME should store this field under: the descriptor's `key`
    when it declares one, else the canonical label. This is the one place the
    authored word and the stored word are allowed to differ."""
    canonical = amd_canonical_label(label, archetype)
    return field_schema(canonical, archetype).get("key", canonical)


def _norm_label(label):
    """Field labels normalise like `amd_norm`: lowercase, hyphens/spaces -> `_`.
    Inlined (not imported) to keep this module's import graph empty."""
    return str(label).strip().lower().replace("-", "_").replace(" ", "_")


# --- coercion: the declared type parses the value ---------------------------
# Parsers are keyed by descriptor `type` and held OUTSIDE the descriptors, so a
# descriptor stays a plain JSON-able dict that crosses the LSP boundary untouched.
# Domains register their own (`trigger`, `reward`) rather than this module reaching
# up into them.
_PARSERS = {}


def amd_register_parser(type_name, fn):
    """Register the parser for a value type. Domain types (`trigger`, `reward`) call
    this at import time so `amd_schema` never has to depend on the domain module."""
    _PARSERS[str(type_name)] = fn


def _install_core_parsers():
    """Wire the generic value grammars from `amd` (stdlib-only, no engine)."""
    from sbs_utils.procedural.amd import (amd_num, amd_pct, amd_list, amd_weighted,
                                          amd_makeup, amd_coords, amd_counted, amd_kv,
                                          amd_signal_name, amd_duration_seconds)
    for name, fn in (("int", amd_num), ("pct", amd_pct), ("csv", amd_list),
                     ("weighted", amd_weighted), ("makeup", amd_makeup),
                     ("coord2", amd_coords), ("counted", amd_counted), ("kv", amd_kv),
                     ("signal", amd_signal_name), ("duration", amd_duration_seconds)):
        _PARSERS.setdefault(name, fn)


_TRUE = ("true", "yes", "on", "1", "")


def amd_coerce(descriptor, value):
    """Parse one authored value according to its declared type.

    Replaces the per-label `elif` chains: the table says what the field IS, and this
    turns the written text into it. Unknown types fall back to the historical default
    (int -> float -> the trimmed string), so an undeclared field behaves exactly as
    it does today."""
    if not _PARSERS:
        _install_core_parsers()
    d = descriptor or {}
    # NO default type: a descriptor that declares nothing falls through to amd_num,
    # which is exactly what an undeclared field does today. A descriptor that DOES
    # say `text` keeps its string.
    kind = d.get("type")
    raw = value
    if d.get("bool"):
        return str(raw).strip().lower() in _TRUE
    if kind == "enum":
        # match case-insensitively but STORE the declared spelling
        s = str(raw).strip()
        for v in d.get("values", ()):
            if s.lower() == str(v).lower():
                return v
        renamed = (d.get("value_aka") or {}).get(s.lower())
        if renamed is not None:
            return renamed
        return s
    if kind == "ref":
        # a csv ref (`Enemies: tsn, civ`) is a LIST of references, not one string
        if d.get("csv") and isinstance(raw, str):
            return _PARSERS["csv"](raw)
        return str(raw).strip() if isinstance(raw, str) else raw
    if kind in ("text", "multiline", "color", "face"):
        return str(raw).strip() if isinstance(raw, str) else raw
    fn = _PARSERS.get(kind)
    if fn is not None and isinstance(raw, str):
        return fn(raw)
    if isinstance(raw, str):
        return _PARSERS["int"](raw)      # historical default (amd_num)
    return raw


def amd_read_field(label, value, archetype=None):
    """One authored `Label: value` -> `(runtime_key, parsed_value)`.

    The whole point of the registry in one call: alias resolved, type coerced, stored
    under the runtime key - so the reader, the linter and the editor cannot disagree
    about what a line means."""
    canonical = amd_canonical_label(label, archetype)
    d = _declared(canonical, archetype)
    if d is None:
        # undeclared: keep today's behaviour exactly (amd_num), and let the linter
        # be the one that says "I don't know this field".
        return canonical, amd_coerce({}, value)
    return d.get("key", canonical), amd_coerce(d, value)


# --- extension: a mission/addon adds vocabulary ------------------------------
def amd_register_fields(archetype, table, domain=None):
    """Declare (or extend) an archetype's field table.

    A mission or addon calls this so its own labels get the same typed widget, the same
    lint and the same coercion as core fields - today OU's ~30 labels are invisible to
    every tool because there is nowhere to say what they are.

    Collisions are LOUD ON PURPOSE: re-declaring a core field with a different
    descriptor raises at registration (startup), rather than silently shadowing it and
    drifting. Re-registering an IDENTICAL descriptor is a no-op, so reloading is safe."""
    who = f" (from {domain})" if domain else ""
    existing = ARCHETYPES.setdefault(archetype, {})
    for label, descriptor in (table or {}).items():
        key = _norm_label(label)
        prior = existing.get(key) or GLOBAL.get(key)
        if prior is not None and prior != descriptor:
            where = "a global type-stable field" if key in GLOBAL else f"archetype '{archetype}'"
            raise ValueError(
                f"AMD field '{label}'{who} is already declared by {where} with a different "
                f"meaning. Pick another name, or register it on your own archetype.")
        existing[key] = descriptor
    _ALIAS_CACHE.clear()
    return existing


def amd_register_section_names(names, archetype, domain=None):
    """Teach the section-name table that sections called any of `names` hold records of
    `archetype` - so authors name a section the way their story names it (`Contracts`,
    `Bounties`) and never have to write a kind line."""
    for n in names:
        key = str(n).strip().lower()
        prior = _SECTION_ALIASES.get(key)
        if prior is not None and prior != archetype:
            who = f" (from {domain})" if domain else ""
            raise ValueError(
                f"AMD section name '{n}'{who} already means '{prior}', not '{archetype}'.")
        _SECTION_ALIASES[key] = archetype
