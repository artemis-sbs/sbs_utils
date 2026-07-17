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
from sbs_utils.procedural.signal import signal_emit
from sbs_utils.mast.mast_node import MastDataObject

_CHOICE = re.compile(r"^-\s*\[(?P<label>.*?)\]\((?P<target>[\w.\-]+)\)\s*(?P<rest>.*?)\s*$")
_GATE = re.compile(r"^%?\{(?P<gate>[^}]*)\}\s*(?P<text>.*)$")
_GUARD = re.compile(r"^(?P<lhs>[\w ]+?)\s*(?P<op>>=|<=|==|!=|>|<)\s*(?P<num>-?\d+)$")


def _dlg_norm(s):
    return str(s).strip().lower().replace("-", "_").replace(" ", "_")


# --- Pure parsing ------------------------------------------------------------
def dialogue_parse(node):
    """Parse one scene node into a plain dict: speaker, when, lines [(text, gate)], and
    choices [{label, target, guard, outcomes}]. Pure - no engine calls."""
    data = node.get("data") or {}
    lines = []
    choices = []
    for raw in (node.get("description") or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        if line.startswith("-") and "](" in line:
            ch = _dlg_parse_choice(line)
            if ch is not None:
                choices.append(ch)
            continue
        # An NPC speech variant. `%` is optional; `%{gate}` / `{gate}` gates the line.
        if line.startswith("%"):
            line = line[1:].strip()
        m = _GATE.match(line) if line.startswith("{") else None
        if m is not None:
            lines.append((m.group("text").strip(), m.group("gate").strip()))
        else:
            lines.append((line, None))
    return {"speaker": data.get("speaker"), "when": data.get("when"),
            "lines": lines, "choices": choices}


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
