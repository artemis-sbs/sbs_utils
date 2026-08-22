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
              hint=kw.get("hint"),
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
    A reputation clause is only meaningful on a player-held quest (DESIGN_RECORD.md s4)."""
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
def field(descriptor, key=None, aka=None, internal=True if False else None, doc=None):
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
    d = dict(descriptor)
    if key:
        d["key"] = key
    if aka:
        d["aka"] = [str(a).strip().lower() for a in aka]
    if doc:
        d["doc"] = " ".join(str(doc).split())
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
                      key="state", aka=("state",),
                      doc="What condition this record is in when the mission BEGINS. "
                          "`posting` is listed like an available job but shows no Accept "
                          "button - something else has to offer it."),
    "objective": field(text(hint="the sentence the player reads"),
                       doc="The sentence the player reads in the quest log."),
    # `Goal:` used to set BOTH the completion trigger and the objective TEXT, so a
    # job's quest log read "Signal 5 drone_down". Split: Objective is the prose,
    # Done when is the trigger.
    # THE LIFE CYCLE - three questions, one trigger grammar:
    #   `signal X` | `destroy 6 raiders` | `reach 6, 4` | `dock station` |
    #   `5 minutes` | `all dead convoy` | `accepted` | `revealed`
    # This replaces seven differently-shaped fields (At start / Complete after /
    # Fail after / Fail on signal / Fail on all dead, and the two spellings of the
    # first two). An author learns one grammar and can answer all three.
    "done when": field(trigger(), key="goal", aka=("goal",),
                       doc="The COMPLETION trigger - what has to happen for this quest "
                           "to be done."),
    "starts when": field(trigger(hint="signal X | accepted | revealed | destroy 6 raiders"),
                         key="when", aka=("when",),
                         doc="When it ARMS - `at once`, `accepted` (the player takes it "
                             "off the board), `revealed` (another quest reveals it). Not "
                             "what completes it; that is `Done when:`."),
    "fails when": field(trigger(hint="signal X | all dead convoy | 5 minutes"),
                        key="fails_when",
                        doc="What FAILS it - the same trigger grammar, plus "
                            "`all dead <role>` and a bare time."),
    "then": field(compound({"reveal": ref("node"), "signal": signal()},
                           hint="reveal KEY  |  signal NAME"),
                  doc="Follow-up on COMPLETION - `reveal <quest>` to unlock another, or "
                      "`signal <name>`. Those two verbs only; anything else is read as a "
                      "reveal target."),
    # What happens the MOMENT this record starts. `Then:` is the other end - it fires on
    # completion - and the two were being conflated because there was no entry slot.
    # Lines are simultaneous; see procedural/amd_action.py.
    "action": field(lines(),
                    doc="What the world does the moment this beat STARTS - one stage "
                        "direction per line, all simultaneous. `Then:` is the other end."),
    "part of": field(ref("node"), key="parent", aka=("parent",),
                     doc="The quest this one belongs under, by key."),
    "scope": field(enum("shared", "ship"),
                   doc="Who holds it - `shared` is one quest for the whole game, `ship` "
                       "gives every player ship its own copy."),
    # WHO owns the quest, named outright - `Scope:` generalized from "the crew or this
    # ship" to any actor, so a station's resupply job is held by the station and its
    # deadline and penalty land on the world rather than on a passing crew. Resolved the
    # same way an `Action:` actor is (landmark key, then role); `shared` names the story
    # agent. DESIGN_RECORD.md s4.
    "held by": field(text(hint="ds1"), key="held_by",
                     doc="WHO owns the quest - a landmark key or a role, so a station's "
                         "resupply job is held by the station and its deadline lands on "
                         "the world rather than on a passing crew."),
    # `Reward:` over `Pays:`. Its partner is free - the failure side already exists in
    # code (quest_grant_penalty) with no authored word yet, and `Reward:`/`Penalty:`
    # mirrors the two functions, while `Pays:`/`Costs:` collides with what you spend to
    # BUILD something in research and recipes. `Pays:` also presumes an employer, which
    # is wrong for a rescue or a story beat that simply hands you salvage. `Pays:` still
    # parses. (A record speaks in the JOB's voice - a job pays, a crew earns - so
    # `Earns:` is the wrong voice whichever word wins.)
    "reward": field(reward(), key="reward", aka=("pays",),
                    doc="What COMPLETING it gives - credits, an item key, or a "
                        "reputation clause."),
    # The failure side has had code since the beginning (quest_grant_penalty) and no
    # word. `Reward:` / `Penalty:` is the pair.
    "penalty": field(reward(hint="100 credits, earns tsn diplomatic -15"), key="penalty",
                     doc="What FAILING it costs - the same grammar as `Reward:`. "
                         "Abandoning an accepted job fails it, so this is what walking "
                         "away costs."),
    "tier": field(integer(), doc="Optional ordering for the quest log."),
    # WHO speaks for this quest. Same word DIALOGUE and LIFEFORM already use, extended
    # to a quest rather than a new one invented for it - the vocabulary is meant to be
    # one language. Today it names the voice for deadline reminders (the shuttle crew
    # calling in on their own rescue, the client chasing a delivery); anything else the
    # quest needs to SAY should use it too rather than growing a second field.
    #
    # Optional by design. Unset falls back to `Held by:` when that resolves to a real
    # agent - a station's job speaks with the station's face for nothing - and then to
    # whatever voice the mission registered for dispatch.
    "speaker": field(ref("node", hint="who says it - falls back to Held by:, then dispatch"),
                     doc="WHO this quest talks as - a character or ship key. The voice of "
                         "its deadline reminders, and of anything else it needs to say."),
    # What the SIGNAL reads out, the way `Scan says:` is what a scan reads out. The line
    # sent as a deadline closes in, so an automated distress beacon sounds like one
    # instead of like a person reporting the time. `{time}` interpolates the remaining
    # clock; without it the line is sent as written.
    #
    # NOT to be confused with `Done when: signal <name>` - that "signal" is an event
    # name, this one is the thing transmitting. Same word, and the only reason it is safe
    # is that one is a field LABEL and the other a field VALUE.
    "signal says": field(multiline(hint="LIFE SUPPORT CRITICAL. {time} TO FAILURE."),
                         key="reminder",
                         doc="The words a deadline reminder transmits. `{time}` "
                             "interpolates the remaining clock."),
    "fail on signal": field(signal(), internal=True),
    "fail on all dead": field(ref("role"), internal=True),
    "fail after": field(duration(), internal=True),
    "complete after": field(duration(), internal=True),
    "on accept": field(text(hint="toast <message>"),
                       doc="What to say the moment the player accepts it."),
    "on complete": field(text(hint="toast <message>"),
                         doc="What to say the moment it completes."),
    "required": field(boolean(),
                      doc="Whether the mission needs this one completed to succeed."),
    # Failing this ENDS the mission - "critical" said how much it mattered, not what
    # happens.
    "fatal": field(boolean(), key="critical", aka=("critical",),
                   doc="Failing this ENDS the mission."),
    "win": field(boolean(), doc="Completing this WINS the mission."),
    "lose": field(boolean(), doc="Completing this LOSES the mission."),
    # `Win:` / `Lose:` carry their own prose; these are what that prose is STORED as.
    "win text": field(text(hint="the end-screen line"), internal=True),
    "lose text": field(text(hint="the end-screen line"), internal=True),
    "citation": field(multiline(hint="the commendation read out at the end"),
                      doc="The commendation read out on the end screen."),
    # `Then: reveal <quest>` UNLOCKS; this is what a scan READS OUT. Same word, two
    # concepts - the author-facing one says which.
    "scan says": field(multiline(hint="what a scan of the target returns"),
                       key="reveals", aka=("reveals", "scan text"),
                       doc="What a SCAN of the target reads out. Not `Then: reveal`, "
                           "which unlocks another quest - same word, two concepts."),
    # WHEN this quest is listed in the log. `when done` runs it unseen and shows it
    # once it resolves (complete OR failed) - a story beat is history, not a to-do.
    # `with children` is for a pure GROUPING heading: it earns a row only while
    # something under it is listed, so it never names a thread that has not started.
    # A job that HAS steps but is a quest in its own right (accept it, it pays) stays
    # `always` - which is why this is declared, not guessed from the shape of the tree.
    # NOT the same as State: secret, which also stops the triggers.
    "show": field(enum("always", "when done", "with children", "never",
                       aka={"when children": "with children"}),
                  doc="WHEN this quest is listed. `when done` runs it unseen and shows it "
                      "once it resolves, reading as history; `with children` earns a row "
                      "only while something under it is listed; `never` drives its events "
                      "invisibly. Not the same as `Starts when: revealed`, which also "
                      "stops the triggers."),
    "accept on": field(csv(hint="comms, admiral"),
                       doc="Restrict which CONSOLES may Accept or Abandon this job, "
                           "overriding the mission default."),
    "engage on": field(csv(hint="helm"),
                       doc="Restrict which consoles may ENGAGE (travel to) this job."),
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
    "cockpit": field(text(hint="the craft a sortie is flown in"),
                     doc="The craft a sortie is flown in."),
}

DIALOGUE = {
    "speaker": field(ref("node", hint="who says it"), doc="WHO says it."),
    # `comms` = a contact the player selects and hails; `hail` = the ship IS
    # hailed, script- or AMD-initiated (procedural/hail.py). OPEN on purpose:
    # enum_values() returns None for an open enum, so the field-value lint pass
    # skips it exactly as it skipped text() - every value already in the corpus
    # keeps parsing and no shipped file gains a finding.
    "when": field(enum("comms", "hail", open=True,
                       hint="comms = a selectable contact; hail = the ship is hailed"),
                  doc="Which SURFACE this dialogue appears on - `comms` is a contact the "
                      "player selects and hails, `hail` is the ship being hailed. Nothing "
                      "to do with a quest's `When:`, which is a start trigger."),
    # (`File:` was declared here and never read by anything in the dialogue/hail path,
    # with zero uses in any shipped .amd. Removed rather than left to be offered by
    # completion - what missions actually use is amd_doc's multi-file loading and
    # `![[key]]` transclusion.)
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

    # --- incoming hails (When: hail) --------------------------------------
    # How the conversation is PRESENTED when a console puts it on screen. Closed:
    # a brand-new field with no legacy values, so it can afford a real dropdown
    # and real lint from day one. The crew picks WHERE it shows; this is the
    # writer picking what it looks like.
    "presentation": field(enum("portrait", "still", "orbit"), aka=("shot", "form")),
    # NOT `Image:` - `image` is already a section word (_SECTION_ALIASES), and one
    # label must never mean two things.
    "backdrop": field(text(hint="an image key for a full still"), aka=("still",)),
    # Resolved LATE, exactly like CUTSCENE's `Subject:` and for the same reason:
    # the ship an orbit shot films is usually spawned at runtime and does not
    # exist when the .amd loads. text(), not ref("node") - a ref would make lint
    # dangle on every legitimate role-based subject.
    "subject": text(hint="what an orbit shot films - cast name or a role"),
    "audio": text(hint="a mission audio file, played when the scene starts"),
    "priority": integer(hint="higher jumps the hail queue"),
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

# A CREW ROSTER, and the people in it. NOT a lifeform, because a crew member never spawns:
# they are a label on a seat a human player is sitting in, where a lifeform is an agent that
# exists in the world. Sharing the archetype would mean sharing the lint, the Inspector
# widgets and eventually a `lifeforms_spawn(section)` that populates the bridge with NPCs
# standing in space.
#
# The SECTION fence carries what every member shares - the hull it crews, the race their
# faces come from, the sheet their photographs are cut from - and each entry says only what
# makes them them. That is what lets a member be a `Console:` line and a `Face:` line.
CREW = {
    # A CAST assigns by console (sit at helm, you are Data); a GROUP is a list of people who
    # pick THEMSELVES and keep their face at whatever station they take. Open, so a mission
    # that invents a third way is warned about nothing.
    "by": field(enum("console", "person", open=True), aka=("assign",)),
    # THE SAME descriptor ITEM["consoles"] uses - one enum, so `Console: helm` completes and
    # lints identically in both places and both learn a mod's console at once. Open because
    # console types are registered at RUNTIME from @console labels; there is no fixed list.
    "console": enum("helm", "weapons", "science", "engineering", "comms", open=True),
    "rank": text(hint="Captain, Lt. Commander - display only"),
    # NOT `Image:`. `image` is already a section word (_SECTION_ALIASES) and one label must
    # never mean two things - CUTSCENE reached for `backdrop` for exactly this reason.
    "portrait": text(hint="a photograph: an atlas key, or a path under `Portraits:`"),
    # --- section-level, inherited by every member below ---
    "portraits": text(hint="the folder every Portrait: below is relative to"),
    "hull": csv(hint="shipData KEYS this roster crews by default - tng_fed_galaxy"),
    "ship": csv(hint="ship NAMES bound to this roster - Enterprise"),
    "race": text(hint="face race for members with no Face of their own"),
    "sheet": text(hint="one portrait sheet, cut exactly like an image atlas"),
    "cell": coord2(hint="portrait cell size in pixels"),
    "grid": coord2(hint="cells across, down"),
    # `face`, `display`, `weight`, `aka`, `color` and `at` all come from GLOBAL. `At:` is the
    # cell on `Sheet:` - the same field amd_images uses, with the same meaning.
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
    # PREFER Framing over lens/move: it sizes the shot to the subject own hull, so one
    # shot frames a runabout and a starbase alike. lens/move are world POSITIONS and so
    # also depend on where the subject happens to be parked.
    "framing": text(hint="close | medium | wide - or two, e.g. wide, close, for a move"),
    "yaw": integer(hint="optional - degrees around the subject"),
    "pitch": integer(hint="optional - degrees above it"),
    "lens": text(hint="x, y, z - where the lens sits (absolute world position)"),
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
# consequence belongs to the quest it watches (DESIGN_RECORD.md s4).
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

# WHAT A KILL LEAVES BEHIND, keyed by role - loot follows from what a ship IS.
#
# The hand-written defaults stay the default: a mission that authors no table behaves
# exactly as before. This exists so an author can SEE the answer and change it, instead of
# a practice target dropping contraband because it happens to be spawned hostile (PRM-14).
DROP = {
    "drops": text(hint="salvage x2-4, contraband 20%   (or `none`)"),
}

# A LOOK: a named particle effect, referenced by many records.
#
# An archetype rather than a trait, because a look is a whole thing with a name that
# several records point AT - two sides can share one, a derelict can wear the one a
# quest marker uses. A trait adds fields to a record that already exists, which would
# mean authoring the look inside each side and copying it to share it.
#
# `Look:` names a Python preset (procedural/particles.py) as the BASE; every other
# field overrides it. So the built-in table stays the library and this is how an
# author varies it, rather than the two duplicating each other.
#
# A ramp is written `A -> B`, the same arrow a cutscene `Move:` already uses.
EFFECT = {
    "look": text(hint="a preset name: sparks, smoke, charge, ember"),
    "size": text(hint="9, or 0.6 -> 2.0 to ramp"),
    "count": text(hint="60, or 10 -> 80 to ramp"),
    "speed": text(hint="0, or 0.5 -> 3.0 to ramp"),
    "lifespan": integer(hint="how long ONE particle lives, in frames (30/sec)"),
    "cell": field(text(hint="sprite cell 0-15: 4, or 0,3 for a random range"),
                  key="image_cell", aka=("image cell",)),
    # `hull` emits over the whole plating; the rest are the engine's own shape words.
    "on": enum("hull", "point", "ring_x", "ring_y", "ring_z",
               "cone_x", "cone_y", "cone_z", "line_x", "line_y", "line_z", open=True),
    "offset": text(hint="0, 0, 200 - where a point emitter sits, or A -> B to close in"),
    "smoke": boolean(),
    "grows over": field(duration(hint="3.5 seconds"), key="ramp_seconds"),
    "steps": integer(hint="how many stages a ramp is drawn in (default 6)"),
    # `color` comes from GLOBAL - do NOT redeclare it here, and note a comma PAIR is
    # the grammar's "random between", while `A -> B` on the other fields is a ramp.
}


# A RELIC: a structure a ship flies INSIDE - a hollow ruin, a canyon, a docking throat.
#
# ONE archetype for the relic AND its parts, exactly as SHOT = CUTSCENE. A section
# resolves to a single archetype, so splitting the container from its chambers would
# leave half of every relic file untyped and lint calling its fields unknown.
#
# A record carrying `Relic:` is a PART; one carrying neither is the relic itself. Which
# kind of part follows from the field it carries - `Chamber:`, `Box:` or `Solid:`.
#
# Coordinates are RELATIVE to the relic's `Loc:`, which is what lets one authored layout
# be dropped at two places in a system.
#
# NOTE there is deliberately no `Kind:` here: the bare label `kind` infers LANDMARK (see
# ("kind","landmark") below), the trap that already cost the cutscene design a redesign.
RELIC = {
    # -- the relic itself
    "loc": coord2(),
    "system": text(),
    "atmosphere": text(hint="a nebula colour: purple, blue, ... or `none` for no murk"),
    "containment": enum("tractor", "clamp", "none",
                        hint="tractor holds with engine physics; clamp teleports"),
    "scrape band": integer(hint="units past the wall before a scrape becomes a breach"),
    "margin": integer(hint="how far inside the wall a held ship is put"),
    "speed limit": text(hint="0.5 for half impulse; usually unset - the nebula does this"),
    "forbid jump": boolean(),
    "art": csv(hint="prop art keys to dress the walls with"),
    # Named looks, so an author picks "plated" without having to know that the mesh is
    # called generic-rectangle. Works on the RELIC and on any PART - a hall can be
    # plated while the cave it collapsed into stays rock. `Art:` still wins where it is
    # given, because naming a mesh is a deliberate act.
    "walls": enum("rock", "plates", "blocks", "ribs", "none", open=True,
                  hint="rock (default), plates, blocks, ribs, none"),
    "debris": integer(hint="loose rocks drifting inside the rooms (default 60)"),
    "plate": integer(hint="how big one piece of wall is, in units (0 = fit the room)"),
    # text() rather than integer(), the same way `speed limit` is: it is a fraction, and
    # the schema has no float type.
    "gaps": text(hint="0 to 1 - the fraction of wall plates missing. It is a ruin."),
    "seed": integer(),
    # -- a part
    "relic": ref("node"),
    "chamber": text(hint="x, y, z, radius"),
    "box": text(hint="x, y, z, hx, hy, hz   (HALF-extents)"),
    "solid": text(hint="sphere, x, y, z, r  |  box, x, y, z, hx, hy, hz  |  capsule, ..."),
    "passage to": text(hint="hub 300, gallery 240"),
    "point": text(hint="x, y, z   - a named place: an item, a spawn, the way in"),
    "roles": csv(hint="entrance, item, spawn   - what this point is FOR"),
    # -- what is AT a part, and when it appears
    #
    # `item` is a reference rather than free text on purpose: a typo in `Roles:` is
    # silent, while an unresolvable ref is a lint error with a line number. It names a
    # record in the mission's `Items` section, which amd_items already reads.
    "item": field(ref("node", hint="red_beacon   - a record in the Items section"),
                  doc="An authored item is found here."),
    "qty": integer(hint="how many of it"),
    "spawn": csv(hint="raider x2, skaraan 4   - what wakes up here"),
    # THE SAME trigger grammar quests use, not a second one. Absent means it is simply
    # there from the start, which is the common case and needs no word.
    "starts when": field(trigger(hint="reach vault_door 900 | signal X | 5 minutes"),
                         key="when", aka=("when",),
                         doc="When the contents appear. Without it they are there from "
                             "the moment the relic is armed."),
}


ARCHETYPES = {
    "quest": QUEST, "lifeform": LIFEFORM, "item": ITEM, "side": SIDE,
    "scan": SCAN, "landmark": LANDMARK, "region": REGION, "map": MAP,
    "dialogue": DIALOGUE, "image": IMAGE,
    "cutscene": CUTSCENE, "urge": URGE, "drop": DROP,
    "effect": EFFECT, "relic": RELIC, "crew": CREW,
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
    _schema_changed()


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
    _schema_changed()


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
    "characters": "lifeform", "character": "lifeform",
    # CREW is not CAST. `cast` and `character` stay on lifeform - those are the NPC words -
    # while a crew roster is people at consoles, which never spawn. `crew` pointed at
    # lifeform until the archetype existed; nothing in the corpus had used it.
    #
    # These four and no more. `officers` was claimed here first and had to be given back:
    # OpenUniverse's `## [Officers](officers)` is a real lifeform cast - named fleet captains
    # that spawn and carry hail scenes - and retyping it would have broken them. The corpus
    # snapshot caught it. `bridge` is unused today but is a PLACE as often as it is a set of
    # people, so it is left alone on the same principle.
    "crew": "crew", "crews": "crew", "roster": "crew", "rosters": "crew",
    "items": "item", "item": "item",
    "sides": "side", "side": "side", "factions": "side",
    "scans": "scan", "scan": "scan", "science": "scan",
    "landmarks": "landmark", "landmark": "landmark",
    "regions": "region", "region": "region",
    "maps": "map", "map": "map",
    "dialogue": "dialogue", "lines": "dialogue",
    "urges": "urge", "urge": "urge",
    # A LOOK. The kind line is the bare noun `Effect`, resolving here - NOT
    # `Kind: effect`, which would infer landmark (see ("kind","landmark") below).
    "effects": "effect", "effect": "effect", "looks": "effect", "fx": "effect",
    "drops": "drop", "drop": "drop", "loot": "drop", "drop tables": "drop",
    # A RELIC and its chambers share one section and one archetype (see RELIC above).
    # The kind line is the bare noun `Relic`, resolving here - NOT `Kind: relic`.
    "relics": "relic", "relic": "relic", "ruins": "relic", "interiors": "relic",
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
    ("look", "effect"),
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
    # BEFORE the lifeform rules: `face` is legal on both, so a flat record carrying a face
    # and a console must classify as crew. `hull`/`ship` are deliberately NOT here - too
    # generic, a landmark or a map could carry either.
    ("console", "crew"), ("portrait", "crew"), ("rank", "crew"),
    ("face", "lifeform"), ("scene", "lifeform"),
    ("drops", "drop"),
    ("speaker", "dialogue"),
    # Relic parts before the landmark rules: a chamber record carries no `Kind:`, but
    # being explicit here keeps a flat file (no section heading) classifiable.
    ("chamber", "relic"), ("passage to", "relic"), ("passage_to", "relic"),
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
    ("Content", ("character", "item", "side", "scan", "landmark", "region", "relic",
                 "map", "dialogue")),
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


# --- lookup memos -----------------------------------------------------------
# _declared is called THREE times per authored field line (amd_is_declared, then
# amd_canonical_label -> _declared_under, then _declared again inside
# amd_read_field) and each call is a triple-nested scan that re-normalizes every
# declared label it walks. On a profile of a 6.5k-line document _norm_label was
# the single largest cost in the parser at ~40k calls. The tables it walks only
# ever change at REGISTRATION time, so all of it memoizes.
_MISS = object()
_NORM_CACHE = {}      # raw label -> normalized. PURE, so it is never invalidated.
_DECLARED_MEMO = {}   # (key, archetype, traits) -> descriptor | _MISS
_UNDER_MEMO = {}      # (norm_key, archetype) -> bool


def _schema_changed():
    """Every table mutation lands HERE, and every memo over those tables is
    cleared HERE. One function on purpose: the previous shape had each registrar
    clearing _ALIAS_CACHE by hand, and two of the three forgot - which is why a
    trait registered after a lookup stayed invisible."""
    _DECLARED_MEMO.clear()
    _UNDER_MEMO.clear()
    _ALIAS_CACHE.clear()


def _traits_key(traits):
    """Traits arrive as a tuple from one caller and a list from another. Normalize
    to a hashable tuple here rather than reaching for lru_cache, which would raise
    TypeError on the list form - at parse time, on an author's file."""
    if not traits:
        return ()
    return tuple(str(t).strip().lower() for t in traits)


def _declared(label, archetype=None, traits=()):
    """The declared descriptor for `label`, or None when nothing declares it.

    Order is archetype -> its TRAITS (as written) -> GLOBAL, so what a record IS always
    wins a name collision and a trait only fills in what the archetype left unsaid.

    Lookup is normalized on BOTH sides, so a table may spell a key `fail on signal`
    while the author writes `Fail on signal` / `fail_on_signal` and all three land
    together. Aliases are tried after canonical names."""
    key = _norm_label(label)
    memo_key = (key, archetype, _traits_key(traits))
    hit = _DECLARED_MEMO.get(memo_key, _MISS)
    if hit is not _MISS:
        return hit
    # NEGATIVE results are cached too, and they are the ones worth caching: an
    # undeclared label is the case that walks every table to the end.
    tables = [ARCHETYPES.get(archetype) if archetype else None]
    # what it always is, then what this record says it ALSO does
    implicit = ARCHETYPE_TRAITS.get(str(archetype).strip().lower(), ()) if archetype else ()
    tables += [TRAITS.get(str(t).strip().lower()) for t in implicit]
    tables += [TRAITS.get(str(t).strip().lower()) for t in (traits or ())]
    tables.append(GLOBAL)
    tables = [t for t in tables if t]
    canonical = _alias_index(archetype, traits).get(key, key)
    for want in (key, canonical):
        for table in tables:
            for declared_label, descriptor in table.items():
                if _norm_label(declared_label) == want:
                    # The table's OWN descriptor object, exactly as before - the
                    # memo stores that same reference, so it adds no aliasing.
                    _DECLARED_MEMO[memo_key] = descriptor
                    return descriptor
    _DECLARED_MEMO[memo_key] = None
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
    "crew": ("display", "console", "face"),
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


def _trait_tables(archetype, traits):
    """The trait field tables in play: what the archetype ALWAYS has, then what this
    record says it ALSO does. Same order _declared uses."""
    out = []
    implicit = ARCHETYPE_TRAITS.get(str(archetype).strip().lower(), ()) if archetype else ()
    for t in tuple(implicit) + tuple(traits or ()):
        table = TRAITS.get(str(t).strip().lower())
        if table:
            out.append(table)
    return out


def _alias_index(archetype, traits=()):
    """`{alias -> canonical label}` for one archetype (plus its traits, plus GLOBAL).

    TRAITS GO IN FIRST, which means LOWEST priority - later tables overwrite earlier
    ones. That is the opposite of _declared's order (archetype, traits, GLOBAL) and it
    is deliberate: an alias that resolves today must keep resolving to the same field,
    so a trait can only fill in a name nothing else claims. Traits were absent from
    this index entirely, which is why a trait's `aka` never resolved at all.
    """
    ckey = (archetype, _traits_key(traits))
    cached = _ALIAS_CACHE.get(ckey)
    if cached is not None:
        return cached
    index = {}
    for table in tuple(_trait_tables(archetype, traits)) + (GLOBAL, ARCHETYPES.get(archetype) or {}):
        for canonical, d in table.items():
            for a in d.get("aka", ()):
                index[_norm_label(a)] = _norm_label(canonical)
    _ALIAS_CACHE[ckey] = index
    return index


def amd_canonical_label(label, archetype=None, traits=()):
    """The canonical spelling of `label` - itself when it is already canonical (or
    unknown), else the field it is an alias of. Underscore/space/hyphen tolerant, so
    `fail_on_signal`, `Fail on signal` and `fail-on-signal` all land together."""
    key = _norm_label(label)
    if _declared_under(key, archetype, traits):
        return key
    return _alias_index(archetype, traits).get(key, key)


def _declared_under(norm_key, archetype, traits=()):
    """True when `norm_key` is itself a declared (canonical) label, alias aside.

    Trait tables are consulted too, and LAST - a trait's own field must count as
    canonical or its aliases could never resolve to it."""
    memo_key = (norm_key, archetype, _traits_key(traits))
    hit = _UNDER_MEMO.get(memo_key)
    if hit is not None:
        return hit
    found = False
    tables = [ARCHETYPES.get(archetype) if archetype else None, GLOBAL]
    tables += _trait_tables(archetype, traits)
    for table in (t for t in tables if t):
        if any(_norm_label(l) == norm_key for l in table):
            found = True
            break
    _UNDER_MEMO[memo_key] = found
    return found


def amd_field_key(label, archetype=None, traits=()):
    """The name the RUNTIME should store this field under: the descriptor's `key`
    when it declares one, else the canonical label. This is the one place the
    authored word and the stored word are allowed to differ."""
    canonical = amd_canonical_label(label, archetype, traits)
    return field_schema(canonical, archetype, traits).get("key", canonical)


def amd_authored_label(runtime_key, archetype=None, traits=()):
    """The canonical AUTHORED label for a key found in a parsed record's `data` -
    the inverse of `amd_field_key`, and `None` when nothing declares it.

    WHY THIS IS NEEDED. A record parsed from `Done when:` / `Part of:` stores `goal` /
    `parent`, because renaming the authored word must never move the stored key. So
    anything that PUBLISHES a parsed record - a fact table, a web page - and titles the
    stored keys prints `Goal` and `Parent`: the exact retired spellings the rename
    existed to remove, taught back to authors by the tooling. Go through here instead."""
    key = _norm_label(runtime_key)
    for label in _labels_of(archetype, traits):
        if _norm_label(amd_field_key(label, archetype, traits)) == key:
            return label
    return None


def amd_field_doc(label, archetype=None, traits=()):
    """The one-sentence meaning of a field, or `None` when it has none yet.

    Callers should degrade to the `hint` rather than inventing prose: a generated field
    table with a blank cell says "nobody has explained this yet", which is true and
    fixable in one line. Prose invented at the point of display is how the last set of
    hand-written tables drifted."""
    return field_schema(label, archetype, traits).get("doc")


def amd_field_aliases(archetype=None, traits=()):
    """`{canonical label -> [other spellings]}` for one archetype.

    The alias index runs alias -> canonical because that is the direction a PARSER
    needs. Anything explaining a field to a human needs the other direction: which
    older words still work. Both are the same table, read two ways."""
    out = {}
    for alias, canonical in _alias_index(archetype, traits).items():
        out.setdefault(canonical, []).append(alias)
    for canonical in out:
        out[canonical].sort()
    return out


def _labels_of(archetype, traits=()):
    """Every declared label in play for an archetype, most specific table first - the
    same precedence `_declared` resolves with.

    Labels come back exactly as the tables spell them (`at start`, not `at_start`), so
    this composes with `template_fields`. Matching is still done on the normalized form
    everywhere else; only what is HANDED BACK keeps the authored shape."""
    seen, out = set(), []
    tables = [ARCHETYPES.get(archetype) if archetype else None]
    tables += list(_trait_tables(archetype, traits))
    tables.append(GLOBAL)
    for table in (t for t in tables if t):
        for label in table:
            norm = _norm_label(label)
            if norm not in seen:
                seen.add(norm)
                out.append(label)
    return out


def _norm_label(label):
    """Field labels normalize like `amd_norm`: lowercase, hyphens/spaces -> `_`.
    Inlined (not imported) to keep this module's import graph empty."""
    # Cached because the normalization is PURE and the same few hundred labels
    # recur across every record of a document. Capped so a hostile file full of
    # unique labels cannot grow it without bound.
    if type(label) is str:
        got = _NORM_CACHE.get(label)
        if got is None:
            got = str(label).strip().lower().replace("-", "_").replace(" ", "_")
            if len(_NORM_CACHE) < 8192:
                _NORM_CACHE[label] = got
        return got
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


def amd_read_field(label, value, archetype=None, traits=()):
    """One authored `Label: value` -> `(runtime_key, parsed_value)`.

    The whole point of the registry in one call: alias resolved, type coerced, stored
    under the runtime key - so the reader, the linter and the editor cannot disagree
    about what a line means."""
    canonical = amd_canonical_label(label, archetype, traits)
    d = _declared(canonical, archetype, traits)
    if d is None:
        # undeclared: keep today's behavior exactly (amd_num), and let the linter
        # be the one that says "I don't know this field".
        return canonical, amd_coerce({}, value)
    return d.get("key", canonical), amd_coerce(d, value)


# --- extension: a mission/addon adds vocabulary ------------------------------
def amd_vocabulary_snapshot():
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
    process, which is how OpenUniverse briefly inherited LegendaryMissions' fields.
    """
    return {
        "archetypes": {k: dict(v) for k, v in ARCHETYPES.items()},
        "traits": {k: dict(v) for k, v in TRAITS.items()},
        "archetype_traits": dict(ARCHETYPE_TRAITS),
        "sections": dict(_SECTION_ALIASES),
        "parsers": dict(_PARSERS),
    }


def amd_vocabulary_restore(snap):
    """Put back an `amd_vocabulary_snapshot`, and drop every memo over it."""
    if not snap:
        return
    for live, saved in ((ARCHETYPES, snap["archetypes"]), (TRAITS, snap["traits"])):
        live.clear()
        live.update({k: dict(v) for k, v in saved.items()})
    for live, saved in ((ARCHETYPE_TRAITS, snap["archetype_traits"]),
                        (_SECTION_ALIASES, snap["sections"]),
                        (_PARSERS, snap["parsers"])):
        live.clear()
        live.update(saved)
    _schema_changed()


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
    _schema_changed()
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
    # Section names feed kind resolution rather than _declared, so no memo here
    # depends on them today. Routed through the one invalidator anyway, so the
    # next registrar added to this module cannot be the one that forgets.
    _schema_changed()
