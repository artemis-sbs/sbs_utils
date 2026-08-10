"""Branching dialogue scenes - the movie-script flavor of AMD, a runtime driver (like the
quest driver), promoted out of Open Universe.

A dialogue section authors conversations as scenes. Each scene is a heading whose fence sets
``Speaker:`` (who talks - a faction/character key, for face/name/color + the reputation
context) and ``When:`` (``comms`` marks a hail entry point); the prose body is the NPC's
lines (``%`` = a random variant, optional ``{gate}`` to condition a line), followed by a
markdown list of choices linking to the next scene:

    # [Ashfang Hail](ashfang_hail)
    ---
    Speaker: ashfang
    When: comms
    ---
    % You're a long way from friends, captain.
    % Brave or stupid, flying in here.

    - [Apologize](ashfang_backoff)
    - [Threaten them](ashfang_standoff) if fearsome > 20
    - [Offer a cut](ashfang_deal) if credits >= 200 ; costs 200 credits, earns ashfang selfish +5

Parsing is pure (unit-testable). Guards and outcomes are DECLARATIVE and evaluated through
two injected seams so the engine stays domain-free:
  * ``dialogue_set_metric_resolver(fn)`` - fn(name, agent_id, speaker) -> number, for guard
    left-sides (a mission maps ``credits`` / ``standing`` / a reputation pole to a value).
  * ``dialogue_register_outcome(verb, fn)`` - fn(agent_id, speaker, tokens) applies an outcome
    (``signal`` is built in; a mission registers ``costs`` / ``earns`` / ...). fn returning
    False refuses the whole pick (e.g. can't afford a cost).
The ``speaker`` is opaque here - the mission resolves the Speaker key to a face/color/name
card itself and passes that record in.
"""
import random
import re
from sbs_utils.procedural.amd import RE_CUE, RE_DIRECTION
from sbs_utils.procedural.signal import signal_emit
from sbs_utils.mast.mast_node import MastDataObject

# An EMPTY target is legal and means "this answer ends the hail" - `hail_answer`
# already closes on a falsy target, so `+` here only made an authored terminal
# choice VANISH: the line looked like a choice, matched nothing, and was dropped
# without a word. A conversation whose last beat is an acknowledgement is the
# common case, so it must be writable.
_CHOICE = re.compile(r"^-\s*\[(?P<label>.*?)\]\((?P<target>[\w.\-]*)\)\s*(?P<rest>.*?)\s*$")
_GATE = re.compile(r"^%?\{(?P<gate>[^}]*)\}\s*(?P<text>.*)$")
_GUARD = re.compile(r"^(?P<lhs>[\w ]+?)\s*(?P<op>>=|<=|==|!=|>|<)\s*(?P<num>-?\d+)$")


def _dlg_norm(s):
    return str(s).strip().lower().replace("-", "_").replace(" ", "_")


# --- Surfaces and directions -------------------------------------------------
# A cue extension is either a SURFACE (`@Vell (comms)` - where the line is
# delivered) or a DIRECTION (`@Vell (shaken)` - how it is delivered). They share
# the parenthesis because a screenwriter writes both that way; they are told apart
# by whether the word is a registered surface, which is why surfaces are a small
# closed set and directions are open.
#
# Directions are deliberately PERMISSIVE. A writer must be able to type
# `(with the weariness of a man who has explained this twice)` without the format
# arguing - an unregistered direction is preserved verbatim as flavor and the
# renderer simply has nothing extra to apply. Registering one only adds meaning
# (a face mood, a color style); it never adds a rule.
_SURFACES = {"comms": "comms", "over": "over", "card": "card"}
_DIRECTIONS = {}


def amd_register_surfaces(domain, names):
    """Register delivery surfaces a cue may name (`@Vell (comms)`). `domain` is the
    registering mission/addon, kept for error messages on a clash."""
    for name in names or ():
        key = _dlg_norm(name)
        owner = _SURFACES.get(key)
        if owner is not None and owner != key:
            raise ValueError(f"{domain}: surface `{name}` is already registered")
        _SURFACES[key] = key


def amd_register_directions(domain, table):
    """Register delivery directions: `{name: payload}`, where payload is whatever the
    mission's renderer understands (a face mood, a style string, a delay). Mirrors
    `amd_register_fields`: a clash with an existing name is a startup failure, not
    silent drift."""
    for name, payload in (table or {}).items():
        key = _dlg_norm(name)
        if key in _DIRECTIONS and _DIRECTIONS[key] != payload:
            raise ValueError(f"{domain}: direction `{name}` is already registered")
        _DIRECTIONS[key] = payload


def dialogue_direction(name):
    """The registered payload for a direction, or None when it is free-form flavor."""
    return _DIRECTIONS.get(_dlg_norm(name)) if name else None


def amd_surface_names():
    """Every registered delivery surface, for completion and lint."""
    return sorted(_SURFACES)


def amd_direction_names():
    """Every registered direction. NOT the set an author is limited to - a direction
    may be any words at all; these are the ones that carry extra meaning."""
    return sorted(_DIRECTIONS)


def _dlg_split_extension(ext):
    """A cue's `(...)` -> `(surface, direction)`. A registered word is the surface;
    anything else is a direction."""
    if not ext:
        return None, None
    key = _dlg_norm(ext)
    if key in _SURFACES:
        return _SURFACES[key], None
    return None, ext.strip()


# --- Pure parsing ------------------------------------------------------------
def dialogue_parse(node):
    """Parse one scene node into a plain dict. Pure - no engine calls.

    Returns `speaker`, `when`, `lines` [(text, gate)], `choices`, and `beats` - one
    speech block per `@cue`, each `{speaker, surface, direction, lines}` where a
    line is `(text, gate, direction)`.

    `lines` is the FLAT list of every spoken variant in the scene, unchanged from
    before cues existed. That is what keeps the shipped single-speaker corpus
    working: `raider_hails.amd` is 8 scenes of bare `%` lines with the speaker in
    the fence, and `dialogue_pick_line` still sees exactly what it always saw. A
    scene with no `@` at all parses to one beat whose speaker is the fence's."""
    data = node.get("data") or {}
    default_speaker = data.get("speaker")
    lines = []
    choices = []
    beats = []
    current = None
    pending = None          # a `(direction)` waiting for the line beneath it

    def open_beat(speaker, surface=None, direction=None):
        beat = {"speaker": speaker, "surface": surface,
                "direction": direction, "lines": []}
        beats.append(beat)
        return beat

    for raw in (node.get("description") or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        if line.startswith("-") and "](" in line:
            ch = _dlg_parse_choice(line)
            if ch is not None:
                choices.append(ch)
            continue
        cue = RE_CUE.match(line)
        if cue is not None:
            surface, direction = _dlg_split_extension(cue.group("ext"))
            current = open_beat(_dlg_norm(cue.group("key")), surface, direction)
            pending = None
            continue
        drc = RE_DIRECTION.match(line)
        if drc is not None:
            pending = drc.group("text").strip() or None
            continue
        # An NPC speech variant. `%` is optional; `%{gate}` / `{gate}` gates the line.
        if line.startswith("%"):
            line = line[1:].strip()
        m = _GATE.match(line) if line.startswith("{") else None
        if m is not None:
            text, gate = m.group("text").strip(), m.group("gate").strip()
        else:
            text, gate = line, None
        if current is None:
            current = open_beat(default_speaker)
        current["lines"].append((text, gate, pending))
        lines.append((text, gate))
        pending = None
    return {"speaker": default_speaker, "when": data.get("when"),
            "lines": lines, "choices": choices, "beats": beats}


def _dlg_parse_choice(line):
    m = _CHOICE.match(line)
    if m is None:
        return None
    rest = m.group("rest").strip()
    guard = None
    outcomes = []
    # `; outcomes` first (so a guard can't swallow them), then a leading `if guard`.
    if ";" in rest:
        rest, outpart = rest.split(";", 1)
        outcomes = _dlg_parse_outcomes(outpart)
        rest = rest.strip()
    if rest.lower().startswith("if "):
        guard = rest[3:].strip()
    return {"label": m.group("label").strip(), "target": m.group("target").strip(),
            "guard": guard, "outcomes": outcomes}


def _dlg_parse_outcomes(s):
    """'costs 200 credits, earns ashfang selfish +5, signal paid' -> [(verb, *tokens), ...].
    Tokens are interpreted by the registered outcome handler (only `signal` is built in), so
    the grammar of costs/earns/etc. lives with the mission, not here."""
    out = []
    for item in [x.strip() for x in str(s).split(",") if x.strip()]:
        toks = item.split()
        if toks:
            out.append(tuple([toks[0].lower()] + toks[1:]))
    return out


# --- Scene lookup ------------------------------------------------------------
def dialogue_scenes(section):
    """key -> scene node for every scene in a dialogue SECTION node (empty if None). The
    caller resolves the section (e.g. amd_section(doc, "dialogue"))."""
    out = {}
    if section is not None:
        for n in section.get("children", []):
            out[n.get("key")] = n
    return out


def dialogue_get(scenes, key):
    return scenes.get(key)


def dialogue_entry_for(scenes, speaker_key, when="comms"):
    """The entry scene key whose Speaker == speaker_key and When == `when` (default comms),
    or None. Used to open a character/faction's hail."""
    for key, n in scenes.items():
        data = n.get("data") or {}
        if data.get("speaker") == speaker_key and str(data.get("when", "")).lower() == when:
            return key
    return None


# --- Injected seams ----------------------------------------------------------
_METRIC_RESOLVER = None
_OUTCOME_HANDLERS = {}


def dialogue_set_metric_resolver(fn):
    """Set the guard metric resolver: fn(name, agent_id, speaker) -> number."""
    global _METRIC_RESOLVER
    _METRIC_RESOLVER = fn


def dialogue_register_outcome(verb, fn):
    """Register an outcome handler: fn(agent_id, speaker, tokens) - tokens are the words
    after the verb. Returning False refuses the pick. (`signal` is built in.)"""
    _OUTCOME_HANDLERS[verb] = fn


# --- Runtime: guards, line pick, outcomes ------------------------------------
def dialogue_guard_ok(guard, agent_id, speaker):
    """Evaluate a simple `lhs op number` guard (no guard -> True). Safe: only a resolved
    metric, a comparison operator, and an integer - never arbitrary code."""
    if not guard:
        return True
    m = _GUARD.match(guard.strip())
    if m is None:
        return False
    lhs = _METRIC_RESOLVER(m.group("lhs"), agent_id, speaker) if _METRIC_RESOLVER else 0
    op = m.group("op")
    rhs = int(m.group("num"))
    if op == ">":
        return lhs > rhs
    if op == ">=":
        return lhs >= rhs
    if op == "<":
        return lhs < rhs
    if op == "<=":
        return lhs <= rhs
    if op == "==":
        return lhs == rhs
    if op == "!=":
        return lhs != rhs
    return False


def dialogue_pick_line(scene, agent_id, speaker):
    """A random NPC line whose gate passes (gates reuse the metric resolver). '' if the
    scene has no eligible line."""
    eligible = [t for (t, gate) in scene["lines"] if dialogue_guard_ok(gate, agent_id, speaker)]
    return random.choice(eligible) if eligible else ""


def dialogue_beats(scene, agent_id, speaker=None):
    """One playable beat per `@cue`, in script order.

    Each is a MastDataObject `{speaker, surface, direction, text}` where `text` is a
    random eligible variant for that beat (gates use the same metric resolver as
    everything else) and `direction` is the beat's own, or the one written directly
    above the chosen line. A beat with no eligible line is dropped, so a fully gated
    beat disappears rather than playing silence.

    `speaker` here is the resolved CARD for guard evaluation (the mission's own
    record), not the beat's cue key - a beat names its speaker in `.speaker`, which
    the caller resolves per beat via `lifeform_speaker`."""
    out = []
    for beat in scene.get("beats") or ():
        eligible = [(t, d) for (t, gate, d) in beat["lines"]
                    if dialogue_guard_ok(gate, agent_id, speaker)]
        if not eligible:
            continue
        text, line_direction = random.choice(eligible)
        out.append(MastDataObject({
            "speaker": beat.get("speaker"),
            "surface": beat.get("surface"),
            "direction": line_direction or beat.get("direction"),
            "text": text,
        }))
    return out


def dialogue_speakers(scene):
    """Every distinct speaker key a scene cues, in first-appearance order."""
    out = []
    for beat in scene.get("beats") or ():
        key = beat.get("speaker")
        if key and key not in out:
            out.append(key)
    return out


def dialogue_choices(scene, agent_id, speaker):
    """Choices whose guard passes, as MastDataObject (label/target/outcomes) so a mast comms
    route can render one button each."""
    out = []
    for ch in scene["choices"]:
        if dialogue_guard_ok(ch.get("guard"), agent_id, speaker):
            out.append(MastDataObject({"label": ch["label"], "target": ch["target"],
                                       "outcomes": ch.get("outcomes") or []}))
    return out


def dialogue_apply(agent_id, speaker, outcomes):
    """Apply a chosen line's outcomes: built-in `signal`, plus any registered verbs. Returns
    False if a handler refuses (e.g. a cost can't be afforded) - the pick is rejected."""
    for oc in (outcomes or []):
        verb = oc[0]
        if verb == "signal":
            if len(oc) >= 2:
                signal_emit(oc[1])
            continue
        fn = _OUTCOME_HANDLERS.get(verb)
        if fn is not None and fn(agent_id, speaker, tuple(oc[1:])) is False:
            return False
    return True
