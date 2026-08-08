"""Declarative AMD FIELD SCHEMA - the single source of truth for what each fence
field *means*, so three consumers stop each re-deriving it from scratch:

  * the **linter** (`amd_lint`) can validate a field's VALUE, not just its
    references - e.g. `State: activ` (typo) becomes a warning instead of silently
    doing nothing;
  * the **editor** (`amd_lsp` -> the VS Code Inspector) can render a typed widget
    per field - a dropdown for an enum, a key-picker for a node reference, a
    swatch for a color - instead of a plain text box; and
  * a **"new record" template** can emit the right empty fence skeleton for a
    given kind of record.

Today that knowledge is scattered and duplicated: `amd_core._extract_data_refs`
knows the reference-bearing fields (Scene/Parent/Then/When/At/...), `amd_lint`
hardcodes the scan-tab vocabulary, and `inspectorForm.js` hardcodes its own
`FIELD_ENUMS`. This module consolidates it.

WHY ARCHETYPE-KEYED, NOT A FLAT LABEL MAP. Most field labels are globally
unambiguous (`Color` is always a color, `At` is always a cell), but at least one
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
    """A hex color - the editor shows a swatch/picker (LSP already has one)."""
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

def reward(hint="200 credits, 2 torpedoes, earns tsn honest +10"):
    """What a job pays: comma-separated credits / items / `earns <faction> <pole> <n>`.
    A reputation clause is only meaningful on a player-held quest (URGE_PLAN.md s7.1)."""
    return _d("reward", hint=hint)

def lines(hint="Kidnapper becomes a pirate"):
    """A block of stage directions, one per list item - the ``Action:`` form. Distinct
    from `csv` because a direction contains commas and must not be split on them."""
    return _d("lines", hint=hint)

def trigger(hint="5 drone_down  |  reach 6, 4  |  destroy 4 raiders"):
    """A game event to wait for. A bare token IS a signal name; verb-led forms
    (`reach`, `destroy`, `dock`, ...) name a different shape."""
    return _d("trigger", hint=hint)


# --- field descriptors: type + alias + runtime key ---------------------------
def field(descriptor, key=None, aka=None, internal=True if False else None):
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
    if internal:
        # Valid to write, never OFFERED. Either the implementation form of an author
        # word (`on kill` under `Done when:`) or a shape a newer field absorbed - both
        # have to keep parsing, and neither belongs in a picker or a new-record template.
        d["internal"] = True
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
    # What this record's condition is when the mission BEGINS - which is what the
    # field always meant, said in words an author would use. `hidden` is a story
    # word for "not revealed yet"; `offered` is what the player is shown for a job
    # waiting to be accepted (QuestState.IDLE renders as "Available"). Every older
    # spelling still parses.
    # `Starts when: accepted` / `Starts when: revealed` say this for the pure cases, and
    # are the better words. This field SURVIVES because 306 converted records need to say
    # two things at once - "hidden until something reveals me" AND "then fire on gate 62"
    # - and one `Starts when:` cannot carry both. The reason is that SECRET currently
    # means BOTH "not listed" and "triggers off"; when `Show:` takes the listing half,
    # this field can finally go.
    "at start": field(enum("running", "offered", "hidden", "posting", "done", "failed",
                           aka={"active": "running", "idle": "offered",
                                "available": "offered", "secret": "hidden",
                                "complete": "done"}),
                      key="state", aka=("state",)),
    "objective": text(hint="the sentence the player reads"),
    # `Goal:` used to set BOTH the completion trigger and the objective TEXT, so a
    # job's quest log read "Signal 5 drone_down". Split: Objective is the prose,
    # Done when is the trigger.
    # THE LIFE CYCLE - three questions, one trigger grammar:
    #   `signal X` | `destroy 6 raiders` | `reach 6, 4` | `dock station` |
    #   `5 minutes` | `all dead convoy` | `accepted` | `revealed`
    # This replaces seven differently-shaped fields (At start / Complete after /
    # Fail after / Fail on signal / Fail on all dead, and the two spellings of the
    # first two). An author learns one grammar and can answer all three.
    "done when": field(trigger(), key="goal", aka=("goal",)),
    "starts when": field(trigger(hint="signal X | accepted | revealed | destroy 6 raiders"),
                         key="when", aka=("when",)),
    "fails when": field(trigger(hint="signal X | all dead convoy | 5 minutes"),
                        key="fails_when"),
    "then": compound({"reveal": ref("node"), "signal": signal()},
                     hint="reveal KEY  |  signal NAME"),
    # What happens the MOMENT this record starts. `Then:` is the other end - it fires on
    # completion - and the two were being conflated because there was no entry slot.
    # Lines are simultaneous; see procedural/amd_action.py.
    "action": lines(),
    "part of": field(ref("node"), key="parent", aka=("parent",)),
    "scope": enum("shared", "ship"),
    # WHO owns the quest, named outright - `Scope:` generalized from "the crew or this
    # ship" to any actor, so a station's resupply job is held by the station and its
    # deadline and penalty land on the world rather than on a passing crew. Resolved the
    # same way an `Action:` actor is (landmark key, then role); `shared` names the story
    # agent. URGE_PLAN.md s7.2.
    "held by": field(text(hint="ds1"), key="held_by"),
    # `Reward:` over `Pays:`. Its partner is free - the failure side already exists in
    # code (quest_grant_penalty) with no authored word yet, and `Reward:`/`Penalty:`
    # mirrors the two functions, while `Pays:`/`Costs:` collides with what you spend to
    # BUILD something in research and recipes. `Pays:` also presumes an employer, which
    # is wrong for a rescue or a story beat that simply hands you salvage. `Pays:` still
    # parses. (A record speaks in the JOB's voice - a job pays, a crew earns - so
    # `Earns:` is the wrong voice whichever word wins.)
    "reward": field(reward(), key="reward", aka=("pays",)),
    # The failure side has had code since the beginning (quest_grant_penalty) and no
    # word. `Reward:` / `Penalty:` is the pair.
    "penalty": field(reward(hint="100 credits, earns tsn diplomatic -15"), key="penalty"),
    "tier": integer(),
    # WHO speaks for this quest. Same word DIALOGUE and LIFEFORM already use, extended
    # to a quest rather than a new one invented for it - the vocabulary is meant to be
    # one language. Today it names the voice for deadline reminders (the shuttle crew
    # calling in on their own rescue, the client chasing a delivery); anything else the
    # quest needs to SAY should use it too rather than growing a second field.
    #
    # Optional by design. Unset falls back to `Held by:` when that resolves to a real
    # agent - a station's job speaks with the station's face for nothing - and then to
    # whatever voice the mission registered for dispatch.
    "speaker": ref("node", hint="who says it - falls back to Held by:, then dispatch"),
    # What the SIGNAL reads out, the way `Scan says:` is what a scan reads out. The line
    # sent as a deadline closes in, so an automated distress beacon sounds like one
    # instead of like a person reporting the time. `{time}` interpolates the remaining
    # clock; without it the line is sent as written.
    #
    # NOT to be confused with `Done when: signal <name>` - that "signal" is an event
    # name, this one is the thing transmitting. Same word, and the only reason it is safe
    # is that one is a field LABEL and the other a field VALUE.
    "signal says": field(multiline(hint="LIFE SUPPORT CRITICAL. {time} TO FAILURE."),
                         key="reminder"),
    "fail on signal": field(signal(), internal=True),
    "fail on all dead": field(ref("role"), internal=True),
    "fail after": field(duration(), internal=True),
    "complete after": field(duration(), internal=True),
    "on accept": text(hint="toast <message>"),
    "on complete": text(hint="toast <message>"),
    "required": boolean(),
    # Failing this ENDS the mission - "critical" said how much it mattered, not what
    # happens.
    "fatal": field(boolean(), key="critical", aka=("critical",)),
    "win": boolean(),
    "lose": boolean(),
    # `Win:` / `Lose:` carry their own prose; these are what that prose is STORED as.
    "win text": field(text(hint="the end-screen line"), internal=True),
    "lose text": field(text(hint="the end-screen line"), internal=True),
    "citation": multiline(hint="the commendation read out at the end"),
    # `Then: reveal <quest>` UNLOCKS; this is what a scan READS OUT. Same word, two
    # concepts - the author-facing one says which.
    "scan says": field(multiline(hint="what a scan of the target returns"),
                       key="reveals", aka=("reveals", "scan text")),
    # WHEN this quest is listed in the log. `when done` runs it unseen and shows it
    # once it resolves (complete OR failed) - a story beat is history, not a to-do.
    # `with children` is for a pure GROUPING heading: it earns a row only while
    # something under it is listed, so it never names a thread that has not started.
    # A job that HAS steps but is a quest in its own right (accept it, it pays) stays
    # `always` - which is why this is declared, not guessed from the shape of the tree.
    # NOT the same as State: secret, which also stops the triggers.
    "show": enum("always", "when done", "with children", "never",
                 aka={"when children": "with children"}),
    "accept on": csv(hint="comms, admiral"),
    "engage on": csv(hint="helm"),
    # The quest driver's own advancement triggers. Authored as a flow value
    # (`on_kill: { role: raider, count: 5 }`), so the reader has already parsed
    # them by the time anything reads the descriptor.
    # What `Done when:` COMPILES TO. Declared so a hand-written one still validates,
    # never offered - an author should not be typing flow mappings into a form.
    "on kill": field(text(), internal=True),
    "on collect": field(text(), internal=True),
    "on scan": field(text(), internal=True),
    "on dock": field(text(), internal=True),
    "reveal": field(ref("node"), internal=True),   # what `Then: reveal X` stores
    "cockpit": text(hint="the craft a sortie is flown in"),
}

DIALOGUE = {
    "speaker": ref("node", hint="who says it"),
    "when": text(hint="the condition this line plays under"),
    "file": text(hint="a sibling .amd to pull lines from"),
    # A scene the whole run shares. `Title:` is the comms title bar (2.8 called it the
    # message `type` - ALERT / FRIEND / STATION), `Side:` is who the hail is addressed
    # to. Both are per-message in 2.8 and per-SCENE here, which is exactly why a run
    # whose tags disagree about either is never lifted into a scene.
    "title": text(hint="the comms title bar - ALERT / FRIEND / STATION"),
    # An INTEGER, not text: 2.8's sideValue is a faction index (`a2x.sides.side_key`
    # does `int(...)` on it). Declaring it as text made the fence hand back "2" where
    # the direct call passed 2 - harmless downstream, but it is a type change and the
    # conversion is supposed to be exact.
    "side": integer(hint="the 2.8 sideValue this is addressed to"),
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

# A cell of a sheet: where the art is, and which key names it. `Sheet`/`Cell`/`Grid`/
# `Domain` are usually written ONCE on the section and inherited, so an entry is one
# `At:` line - which is what makes moving a glyph an edit rather than an arithmetic
# exercise. An `icons` section registers into the icon domain, so its keys are the LOOKS
# `gui_icon_name` resolves; anything else registers ordinary atlas keys.
IMAGE = {
    "sheet": text(hint="icons/quest-sheet - inside a media pack, or a mission path"),
    "at": coord2(hint="col, row"),
    "cell": text(hint="64, or 190, 280 - the cell size in PIXELS"),
    "grid": coord2(hint="8, 8 - cells across and down, to measure a cell instead"),
    "rect": text(hint="left, top, right, bottom in pixels - for an irregular cell"),
    "color": color(),
    "domain": text(hint="a namespace, so two addons cannot claim one key"),
}

# A cutscene BED. The shots that belong to it are separate records carrying
# `Scene:` - one heading per shot, so a shot is an ordinary record and lint, schema
# and the typed widgets all work on it unchanged.
CUTSCENE = {
    # --- the BED ---
    "letterbox": boolean(),
    "skippable": boolean(),
    "release": boolean(),
    "bar": integer(hint="letterbox bar height in em"),
    # --- a SHOT ---
    # One archetype, not two, because a SECTION resolves to a single archetype and
    # beds and shots live in the same section - splitting them left half of every
    # cinematics file untyped and lint calling its fields unknown.
    "cutscene": text(hint="the cutscene this shot belongs to"),
    "rundown": text(hint="the rundown this shot belongs to"),
    # Resolved LATE: a cast name bound by the mission, else a role. The object does
    # not exist when the .amd loads.
    "subject": text(hint="cast name (cutscene_cast) or a role"),
    "lens": text(hint="x, y, z - where the lens sits"),
    "move": text(hint="x,y,z -> x,y,z - where the lens travels"),
    "seconds": integer(),
    "ease": enum("in_out", "in", "out", "linear"),
    "order": integer(hint="optional - document order is used without it"),
    "overlay": text(hint="an overlay kind to show with this shot"),
    "label": text(hint="what a director's tile says"),
    # --- the shot's OVERLAY, authored inline ---
    # A shot carries its overlay's own fields right beside it (`Overlay: lower_third`
    # + `Name:`), rather than nesting them, so the record reads as one thing. They
    # therefore belong in this schema: without them lint calls a correct file wrong,
    # which teaches authors to ignore it.
    "name": text(hint="overlay: the speaker's name plate"),
    "line": text(hint="overlay: the subtitle line"),
    "title": text(hint="overlay: hero/credits title"),
    "subtitle": text(hint="overlay: hero subtitle"),
    "align": enum("left", "right", hint="overlay: which side the portrait sits on"),
    "face": face(hint="overlay: a face string, or a cast name"),
    "ship": text(hint="overlay: a ship-type key"),
    "icon": text(hint="overlay: an icon spec"),
    "image": text(hint="overlay: an image key"),
    "color": color(hint="overlay: name-plate color"),
    "background": color(hint="overlay: fill behind the strip"),
    "slot": text(hint="overlay: override the kind's default slot"),
}
SHOT = CUTSCENE     # one schema; "shot" and "cutscene" are two words for it

# An URGE: what an actor keeps asking for. A condition, a cadence, a pool of lines in
# the BODY, and optionally an `Action:`. It declares no stakes of its own - the
# consequence belongs to the quest it watches (URGE_PLAN.md).
URGE = {
    "actor": ref("node", hint="ds1  (a landmark key or a role)"),
    "whenever": text(hint="quest ds1_resupply active"),
    "every": duration(hint="5m, or 3-5m to jitter"),
    "until": text(hint="quest passenger_vell active  (retires it for good)"),
    "weight": integer(hint="20  (which of THIS actor's urges wins; 90+ is urgent)"),
    # Open: the vocabulary is a registry, so a mission can add a mode. The linter still
    # warns on anything it does not know, which is the point of `open` rather than text.
    "escalates": enum("with deadline", "yes", open=True),
    "title": text(hint="Passenger Request  (the card header; default is the speaker)"),
    "action": lines(hint="self departs"),
}

ARCHETYPES = {
    "quest": QUEST, "lifeform": LIFEFORM, "item": ITEM, "side": SIDE,
    "scan": SCAN, "landmark": LANDMARK, "region": REGION, "map": MAP,
    "dialogue": DIALOGUE, "image": IMAGE,
    "cutscene": CUTSCENE, "urge": URGE,
}

# TRAITS: a concern a record ALSO has, on top of what it is.
#
# A worldlet is a Landmark that yields ore; a captain is a Character with standing.
# Neither is a new kind of thing, and inventing an archetype for the second half is
# what produced `worldlet`, `clan` and `captain` as private types. A trait names that
# second half once and lends its words to anything that says `Also:`.
#
# The archetype still answers "what IS this" and still WINS a name collision - traits
# only fill in what it does not declare, in the order they are written.
TRAITS = {
    "economy": {
        "yields": text(hint="ore 12  (per minute, per extractor)"),
        "reserve": text(hint="4000, or `unlimited`"),
        "price": integer(),
        "costs": counted(hint="ore 120, gas 40"),
        "time": duration(),
    },
    # How someone is REGARDED, and what they regard. One concern that four different
    # records had each spelled their own way: a side's `Values`, a captain's `Values`
    # and `Rival when`, a bar patron's `Reliability`, a quest's `Standing`.
    "reputation": {
        "values": weighted(hint="by-the-book 40, fearsome 30"),
        "standing": text(hint="iron honest 20, iron fearsome 10"),
        "reliability": pct(hint="0.55 - how often they are right"),
        "rival when": text(hint="the standing that turns them against you"),
    },
}


# Traits an archetype ALWAYS has, so no record has to say the obvious. A side is always
# regarded some way; so is a person. `Also:` is for the concerns that are OPTIONAL - a
# landmark that happens to yield - and writing `Also: reputation` on every side would be
# ceremony, not clarity.
ARCHETYPE_TRAITS = {
    "side": ("reputation",),
    "lifeform": ("reputation",),
}


def amd_register_archetype_traits(archetype, traits, domain=None):
    """Give an archetype traits it always has (see ARCHETYPE_TRAITS)."""
    key = str(archetype).strip().lower()
    have = tuple(ARCHETYPE_TRAITS.get(key, ()))
    ARCHETYPE_TRAITS[key] = have + tuple(t for t in traits if t not in have)


def amd_register_trait(name, table, domain=None):
    """Declare (or extend) a trait's field table - the same contract as
    `amd_register_fields`, for a concern rather than a kind of thing."""
    key = str(name).strip().lower()
    existing = TRAITS.setdefault(key, {})
    for label, descriptor in (table or {}).items():
        lk = _norm_label(label)
        prior = existing.get(lk)
        if prior is not None and prior != descriptor:
            who = " (from %s)" % domain if domain else ""
            raise ValueError("trait %r already declares %r differently%s" % (key, label, who))
        existing[lk] = descriptor


def amd_trait_names():
    """Every trait a record may claim in `Also:`."""
    return sorted(TRAITS)


def amd_traits_of(data):
    """The traits a record claims, from its `Also:` value (a comma list)."""
    if not data:
        return ()
    raw = data.get("also") if hasattr(data, "get") else None
    if not raw:
        return ()
    if isinstance(raw, (list, tuple)):
        parts = raw
    else:
        parts = str(raw).replace(",", " ").split()
    return tuple(p.strip().lower() for p in parts if str(p).strip())


# Type-stable everywhere: if a field isn't in the resolved archetype, fall back
# to these before defaulting to plain text.
GLOBAL = {
    # What this record ALSO does, beyond what it is (see TRAITS).
    "also": csv(hint="economy"),
    # What else this record ANSWERS TO. Obsidian's note aliases: other names that
    # resolve here, so a reference written before a rename - or an a2x-generated key
    # nobody wants to keep - still finds its target. Distinct from `Also:`, which is
    # traits; the two are a syllable apart on purpose and must not be conflated.
    "aka": csv(hint="The Florbin Job, florbin_case"),
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
    "characters": "lifeform", "character": "lifeform", "crew": "lifeform",
    "items": "item", "item": "item",
    "sides": "side", "side": "side", "factions": "side",
    "scans": "scan", "scan": "scan", "science": "scan",
    "landmarks": "landmark", "landmark": "landmark",
    "regions": "region", "region": "region",
    "maps": "map", "map": "map",
    "dialogue": "dialogue", "lines": "dialogue",
    "urges": "urge", "urge": "urge",
    # An icon IS an atlas cell that resolves in the icon domain - one archetype, two
    # section words, so a mission's card deck and its icon sheet read the same way.
    "images": "image", "image": "image", "art": "image", "atlas": "image",
    "icons": "image", "icon": "image", "sheet": "image", "sheets": "image",
    # The ROOT record of a file names the whole document - a universe, a scenario, a
    # siege. That is what a map record is, so these read as one without a new word.
    "universe": "map", "scenario": "map", "siege": "map", "boss": "map",
    # Names real missions already use for a group of quests. Before these, 5108 of
    # the corpus's 5273 field uses resolved to NO archetype, so the busiest part of
    # the language had no typing, no lint and no widgets.
    # Cinematic sections. A cutscene bed and its shots share one archetype, so any
    # of these words types a whole cinematics file.
    "cinematic": "cutscene", "cinematics": "cutscene", "cutscene": "cutscene",
    "cutscenes": "cutscene", "shot": "cutscene", "shots": "cutscene",
    "rundown": "cutscene", "rundowns": "cutscene",
    "jobs": "quest", "job": "quest", "goals": "quest", "goal": "quest",
    "narrative": "quest", "missions": "quest", "mission": "quest",
    "contracts": "quest", "bounties": "quest", "scenario": "map",
    # SCREENPLAY WORDS for the same archetype. A beat and an objective are the same
    # machinery playing different parts, and the part is what an author knows: a beat
    # is a moment the crew lives through, an arc is the heading over a run of them.
    # Nouns are vocabulary; ARCHETYPES are field schemas - these add no schema.
    "beat": "quest", "beats": "quest", "cue": "quest", "cues": "quest",
    "arc": "quest", "arcs": "quest", "chapter": "quest", "chapters": "quest",
    "act": "quest", "acts": "quest", "sequence": "quest", "sequences": "quest",
    "thread": "quest", "threads": "quest",
}

# What a KIND NOUN already implies. Over HALF of every field line in the converted
# corpus (2574 of 4657) was a record restating what it had just called itself:
# `Scope: shared` on all 1375, `State: active` on 988, `Show: never` on 211. A story
# moment belongs to the whole crew and is already running - saying so again is
# ceremony. An explicit field always wins, so a `Beat` that differs just says so.
_KIND_DEFAULTS = {
    # A JOB is taken by a ship; an OBJECTIVE is the crew's. That is the difference
    # between the two words, and it is the whole of `Scope:` and `At start:` for them.
    "job":       {"scope": "ship",   "state": "offered"},
    "objective": {"scope": "shared", "state": "running"},
    "beat":     {"show": "when done",     "scope": "shared", "state": "running"},
    "cue":      {"show": "never",         "scope": "shared", "state": "running"},
    "arc":      {"show": "with children", "scope": "shared", "state": "running"},
    "chapter":  {"show": "with children", "scope": "shared", "state": "running"},
    "act":      {"show": "with children", "scope": "shared", "state": "running"},
    "sequence": {"show": "with children", "scope": "shared", "state": "running"},
    "thread":   {"show": "with children", "scope": "shared", "state": "running"},
}


def amd_kind_defaults(noun):
    """Every field a kind noun implies, as {field: value}. Singular / plural both work,
    matching `_kind_to_archetype` - an author writes `Beat` over one record and `Beats`
    over a section without being told there is a difference.

    `Quest` carries none - it is the neutral word, for a record that is neither a story
    moment nor clearly one of the two. `Job` restates today's defaults (per ship, waiting
    to be accepted) rather than changing them, so peacetime's board - which says none of
    this - keeps working exactly as written."""
    if not noun:
        return {}
    n = str(noun).strip().lower().replace("-", "_").replace(" ", "_")
    return _KIND_DEFAULTS.get(n) or _KIND_DEFAULTS.get(n.rstrip("s")) or {}


def amd_kind_show_default(noun):
    """The `Show:` a kind noun implies, or None."""
    return amd_kind_defaults(noun).get("show")

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
    # A failure DEADLINE is quest-only, and it has to be listed here now that `Speaker:`
    # is legal on a quest: without it, a job carrying a speaker and a deadline but no
    # `Done when:` would hit ("speaker", "dialogue") below and be classified as dialogue.
    # Real jobs declare `Job` outright so inference never runs on them, but the flat a2x
    # records have no section to be named by and rely on exactly this.
    ("fails when", "quest"), ("fails_when", "quest"),
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


def amd_resolve_kind_chain(own_kind=None, ancestors=(), field_labels=(),
                           own_section=None):
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
    tooling and the game came to disagree about the same file.
    """
    if own_kind:
        arch = _kind_to_archetype(own_kind)
        if arch:
            return arch
    pairs = [p for p in ancestors if p and (p[0] or p[1])]
    if not pairs and own_section:
        arch = archetype_for_section(own_section)
        if arch:
            return arch
    for kind, section in pairs:
        if kind:
            arch = _kind_to_archetype(kind)
            if arch:
                return arch
        if section:
            arch = archetype_for_section(section)
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


# What a picker OFFERS, which is not the same as what the reader ACCEPTS. `amd_known_kinds`
# is the validation vocabulary - 48 entries counting every plural and every alias a mission
# might use for a section (`cast`, `crew`, `bounties`, `scenario`). Handing that to an
# author as a menu is not a choice, it is a wall. This is the curated list: canonical,
# singular, one word per meaning, grouped the way an author thinks about them.
KIND_MENU = (
    ("Story", ("beat", "cue", "arc")),
    ("Work", ("objective", "job", "quest")),
    ("Content", ("character", "item", "side", "scan", "landmark", "region", "map",
                 "dialogue")),
)


def amd_kind_menu():
    """The nouns to OFFER, in order, with their group and what each implies.

    Everything in `amd_known_kinds` still parses - this only decides what is put in
    front of someone choosing."""
    out = []
    for group, nouns in KIND_MENU:
        for n in nouns:
            implied = amd_kind_defaults(n)
            out.append({"noun": n[:1].upper() + n[1:], "group": group,
                        "implies": ", ".join("%s: %s" % kv for kv in sorted(implied.items()))})
    return out


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
def field_schema(label, archetype=None, traits=()):
    """The descriptor for one field `label` within `archetype` (falling back to
    the GLOBAL type-stable fields, then plain text). Never returns None - an
    unknown field is `text`, so the editor always has a widget."""
    d = _declared(label, archetype, traits)
    return d if d is not None else text()


def _declared(label, archetype=None, traits=()):
    """The declared descriptor for `label`, or None when nothing declares it.

    Order is archetype -> its TRAITS (as written) -> GLOBAL, so what a record IS always
    wins a name collision and a trait only fills in what the archetype left unsaid.

    Lookup is normalized on BOTH sides, so a table may spell a key `fail on signal`
    while the author writes `Fail on signal` / `fail_on_signal` and all three land
    together. Aliases are tried after canonical names."""
    key = _norm_label(label)
    tables = [ARCHETYPES.get(archetype) if archetype else None]
    # what it always is, then what this record says it ALSO does
    implicit = ARCHETYPE_TRAITS.get(str(archetype).strip().lower(), ()) if archetype else ()
    tables += [TRAITS.get(str(t).strip().lower()) for t in implicit]
    tables += [TRAITS.get(str(t).strip().lower()) for t in (traits or ())]
    tables.append(GLOBAL)
    tables = [t for t in tables if t]
    canonical = _alias_index(archetype).get(key, key)
    for want in (key, canonical):
        for table in tables:
            for declared_label, descriptor in table.items():
                if _norm_label(declared_label) == want:
                    return descriptor
    return None


def amd_is_declared(label, archetype=None, traits=()):
    """True when some table declares this field. The reader needs this to tell a
    declared `text` field (stays a string) from an UNDECLARED one, which must keep
    the historical `amd_num` default - else `Time: 30` silently becomes "30"."""
    return _declared(label, archetype, traits) is not None


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


def template_fields(archetype, include_internal=False):
    """The ordered field labels a 'new <archetype>' skeleton should offer, or []
    for an unknown archetype. Preserves the table's authoring order (dict order).

    `internal` fields are LEFT OUT: they are implementation forms (`on kill`, what
    `Done when:` compiles to) or shapes a newer field absorbed (`Fail after:` ->
    `Fails when:`). Both must keep parsing; neither should be offered to an author or
    land in a new-record skeleton."""
    table = ARCHETYPES.get(archetype)
    if not table:
        return []
    return [k for k, d in table.items()
            if include_internal or not (isinstance(d, dict) and d.get("internal"))]


# The handful of fields a NEW record of each kind actually starts with. Offering the
# whole table instead put 33 blank lines in front of an author writing their first
# quest, which reads as "all of this is required" - the opposite of what a fact sheet
# should feel like. Everything else is still one `+ add field` away.
STARTERS = {
    "quest": ("objective", "done when", "reward"),
    "lifeform": ("display", "face", "roles"),
    "item": ("display", "mode", "price"),
    "side": ("display", "color", "enemies"),
    "scan": ("scan of", "tab"),
    "landmark": ("at", "art", "roles"),
    "region": ("at", "color"),
    "map": ("display", "mode"),
    "dialogue": ("speaker",),
}


def starter_fields(archetype):
    """The short set a new record of this archetype opens with (see STARTERS), falling
    back to the first few offered fields for an archetype with no opinion."""
    known = [f for f in template_fields(archetype)]
    picked = [f for f in STARTERS.get(archetype, ()) if f in known]
    return picked or known[:4]


def amd_is_internal(label, archetype=None):
    """True when a field still parses but should not be OFFERED (picker, completion,
    new-record template)."""
    d = _declared(label, archetype)
    return bool(d and d.get("internal"))


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
    """Field labels normalize like `amd_norm`: lowercase, hyphens/spaces -> `_`.
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
                     ("signal", amd_signal_name), ("duration", amd_duration_seconds),
                     ("lines", _as_lines)):
        _PARSERS.setdefault(name, fn)


def _as_lines(raw):
    """A stage-direction block -> a list of lines. A single-line value is still a list of
    one, so a caller never has to test which shape it got."""
    if isinstance(raw, (list, tuple)):
        return [str(v).strip() for v in raw if str(v).strip()]
    return [l.strip() for l in str(raw).splitlines() if l.strip()]


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
        # undeclared: keep today's behavior exactly (amd_num), and let the linter
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
