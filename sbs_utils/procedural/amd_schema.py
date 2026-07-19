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
    return _d("enum", values=["true", "false"])

def enum(*values, **kw):
    """A closed set of string values (dropdown). `open=True` lets the author type
    a value outside the set (the editor keeps it, the linter still warns)."""
    return _d("enum", values=list(values), open=kw.get("open", False))

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
    "state": enum("active", "secret", "idle", "complete", "failed"),
    "parent": ref("node"),
    "when": compound({"reach": coord2(), "travel": coord2(), "signal": signal()},
                     hint="reach i,j  |  signal NAME"),
    "then": compound({"reveal": ref("node"), "signal": signal()},
                     hint="reveal KEY  |  signal NAME"),
    "fail on signal": signal(),
    "required": boolean(),
    "critical": boolean(),
    "win": boolean(),
    "lose": boolean(),
    "fail after": text(hint="seconds, or mm:ss"),
    "reward": text(),
    "accept on": csv(hint="comms, admiral"),
    "engage on": csv(hint="helm"),
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
}

# Type-stable everywhere: if a field isn't in the resolved archetype, fall back
# to these before defaulting to plain text.
GLOBAL = {
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
}

# When there's no conventional section key, the FIRST discriminating field a
# record carries identifies its archetype. Order = specificity (most telling
# first), since a record may legitimately carry several.
_DISCRIMINATORS = (
    ("scan of", "scan"),
    ("scan_of", "scan"),
    ("enemies", "side"), ("allies", "side"), ("neutral", "side"),
    ("modifiers", "item"),
    ("center", "region"), ("radius", "region"),
    ("face", "lifeform"), ("scene", "lifeform"),
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
    key = str(label).strip().lower()
    table = ARCHETYPES.get(archetype) if archetype else None
    if table and key in table:
        return table[key]
    if key in GLOBAL:
        return GLOBAL[key]
    return text()


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


def template_fields(archetype):
    """The ordered field labels a 'new <archetype>' skeleton should offer, or []
    for an unknown archetype. Preserves the table's authoring order (dict order)."""
    table = ARCHETYPES.get(archetype)
    return list(table.keys()) if table else []
