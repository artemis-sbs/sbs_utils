"""Stage directions - the ``Action:`` block that fires when a beat STARTS.

AMD's three lifecycle slots are all conditions, and ``Then:`` fires when a record
*completes*. There was nowhere to write what happens the moment a beat begins, so an
author who wanted "when the trap springs, the raider turns and the freighter runs"
dropped into MAST. This is that slot::

    ### [The trap closes](ambush)
    ---
    Beat
    Starts when: signal alarm
    Action:
      - Kidnapper becomes a pirate
      - Kidnapper is no longer a suspect
      - Xorn joins tsn
      - Kessel Station arrives
    ---

A line is ``<actor> <verb> <operand>``. The verb sits BETWEEN the two names, which is
what keeps two same-typed references unambiguous - the reason a terser ``Verb: a b``
form was rejected. Lines are **simultaneous**: list order is not execution order. There
is no branching, looping or sequencing, deliberately - a direction is a statement, and
the moment one needs an ``if`` the answer is a second beat with its own ``Starts when:``.

**The vocabulary is deliberately small.** A survey of seven missions found 25 real
stage-direction runs, and ``becomes`` (role/side, 30 uses) plus ``arrives`` (spawn, 20)
account for 81% of them. Everything else registers: ``amd_action_register(phrase, fn)``,
the same seam ``dialogue_register_outcome`` already uses, so a mission adds vocabulary
without touching this module.

**Nothing fails silently.** An unknown verb, an unresolvable actor and a missing
landmark each log a warning naming the line - the rule ``amd_cutscene`` already follows
for a dropped shot, and the failure mode the AMD tooling exists to end.
"""
import re

# phrase (normalized, spaces kept) -> {"fn", "operand"}
_VERBS = {}

_ARTICLE = re.compile(r"^(a|an|the)\s+", re.IGNORECASE)


def _action_log(message):
    try:
        from .execution import log
        log(message, "action", "warning")
    except Exception:
        pass


def _action_norm(text):
    return " ".join(str(text).strip().lower().split())


# --- the registry ------------------------------------------------------------
def amd_action_register(phrase, fn, operand="required", domain=None):
    """Declare a stage-direction verb.

    ``fn(actor, operand, line)`` applies it and returns False if it could not. ``actor``
    is the raw name as written (resolution is the verb's business - ``becomes`` wants a
    live object, ``arrives`` wants a landmark record). ``operand`` is
    ``required`` / ``optional`` / ``none``.

    Collisions are loud: re-registering a phrase with a different function raises, the
    same contract as ``amd_register_fields``. Re-registering the identical function is a
    no-op so reloading is safe.
    """
    key = _action_norm(phrase)
    if not key:
        raise ValueError("an action verb needs a phrase")
    prior = _VERBS.get(key)
    if prior is not None and prior["fn"] is not fn:
        who = f" (from {domain})" if domain else ""
        raise ValueError(f"action verb {phrase!r}{who} is already registered by something else")
    _VERBS[key] = {"fn": fn, "operand": operand}
    return key


def amd_action_verbs():
    """Every registered phrase, longest first - the order the parser matches in, and
    what an error message offers."""
    return sorted(_VERBS, key=lambda p: (-len(p.split()), p))


def amd_action_clear_verbs():
    """Test-only: drop every registered verb (then re-install the built-ins)."""
    _VERBS.clear()


# --- parsing (pure) ----------------------------------------------------------
def amd_action_parse(value):
    """``Action:`` -> ``[{actor, verb, operand, raw, error}]``, in written order.

    Pure and engine-free, so it unit-tests offline and the linter can call it. A line
    that matches no verb still comes back, carrying ``error`` - the caller decides
    whether that is a warning (runtime) or a diagnostic (lint), and neither has to
    re-parse.
    """
    out = []
    for raw in _action_lines(value):
        line = raw.strip()
        if not line or line.startswith("//") or line.startswith("#"):
            continue
        if line.startswith("-"):
            line = line[1:].strip()
        if not line:
            continue
        out.append(_parse_line(line))
    return out


def _action_lines(value):
    """A fence value that may be a list (the nested form) or one string."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value]
    return str(value).splitlines()


def _parse_line(line):
    text = line.rstrip(".")
    padded = " " + _action_norm(text) + " "
    # Longest phrase wins, so `is no longer` is never read as a bare `is`.
    for phrase in amd_action_verbs():
        at = padded.find(" " + phrase + " ")
        if at < 0:
            continue
        # Map the normalized offset back onto the written text by word count.
        words = text.split()
        before = len(padded[:at + 1].split())
        actor = " ".join(words[:before]).strip()
        operand = " ".join(words[before + len(phrase.split()):]).strip()
        operand = _ARTICLE.sub("", operand).strip()
        spec = _VERBS[phrase]
        error = None
        if not actor:
            error = f"no one to act on: {line!r} - a direction reads '<who> {phrase} <what>'"
        elif spec["operand"] == "required" and not operand:
            error = f"{phrase!r} needs something after it: {line!r}"
        elif spec["operand"] == "none" and operand:
            error = f"{phrase!r} takes nothing after it, got {operand!r}"
        return {"actor": actor, "verb": phrase, "operand": operand,
                "raw": line, "error": error}
    return {"actor": None, "verb": None, "operand": None, "raw": line,
            "error": f"no action verb in {line!r} - known verbs: "
                     + ", ".join(amd_action_verbs())}


# --- running -----------------------------------------------------------------
def amd_action_run(value, where=""):
    """Apply every direction in an ``Action:`` block. Returns how many applied.

    One bad line never stops the others: a beat that half-fires is bad, but a beat that
    stops at the first dead actor is worse, and the log names which line went wrong.
    """
    done = 0
    for act in amd_action_parse(value):
        if act["error"]:
            _action_log(f"{where}{act['error']}")
            continue
        fn = _VERBS[act["verb"]]["fn"]
        try:
            if fn(act["actor"], act["operand"], act["raw"]) is not False:
                done += 1
            else:
                _action_log(f"{where}could not apply: {act['raw']!r}")
        except Exception as e:
            _action_log(f"{where}{act['raw']!r} failed: {e}")
    return done


def amd_action_run_record(record):
    """Run the ``Action:`` block of a parsed AMD record (nothing to do without one)."""
    data = (record or {}).get("data") or {}
    value = data.get("action")
    if not value:
        return 0
    key = (record or {}).get("key") or "?"
    return amd_action_run(value, where=f"action in {key!r}: ")


# --- actor resolution --------------------------------------------------------
def amd_action_actors(name):
    """The live agent ids a direction's actor names, as a set (possibly empty).

    Resolution order: a declared AMD **landmark** key first (the specific thing an
    author named in this mission), then a **role** (which covers a group - "Raiders
    become hostile" acts on all of them). Both are role lookups underneath, so this
    stays O(1) and self-cleans when an object dies.
    """
    from .roles import role
    from .query import to_id_list
    from .amd_landmarks import landmark_key_role
    if not name:
        return set()
    key = str(name).strip()
    ids = set(to_id_list(role(landmark_key_role(_action_slug(key)))))
    if ids:
        return ids
    return set(to_id_list(role(_action_slug(key)))) or set(to_id_list(role(key)))


def _action_slug(text):
    return str(text).strip().lower().replace("-", "_").replace(" ", "_")


# --- the built-in verbs ------------------------------------------------------
# `becomes` and `arrives` are 81% of measured demand, and neither needs the objective
# layer. Orders (`heads to`, `targets`) are deliberately NOT here - the corpus has zero
# of them, so they wait until migrating a real mission asks for them.

def _becomes(actor, operand, line):
    """`Kidnapper becomes a pirate` - add a role."""
    from .roles import add_role
    ids = amd_action_actors(actor)
    if not ids:
        _action_log(f"nobody called {actor!r} to act on: {line!r}")
        return False
    for r in _role_list(operand):
        add_role(ids, r)
    return True


def _no_longer(actor, operand, line):
    """`Kidnapper is no longer a suspect` - remove a role."""
    from .roles import remove_role
    ids = amd_action_actors(actor)
    if not ids:
        _action_log(f"nobody called {actor!r} to act on: {line!r}")
        return False
    for r in _role_list(operand):
        remove_role(ids, r)
    return True


def _joins(actor, operand, line):
    """`Xorn joins tsn` - change side. Distinct from `becomes` because a side is not a
    role: it drives diplomacy, and conflating the two hid that."""
    from .query import to_object
    ids = amd_action_actors(actor)
    if not ids:
        _action_log(f"nobody called {actor!r} to act on: {line!r}")
        return False
    side = _action_slug(operand)
    for so_id in ids:
        obj = to_object(so_id)
        if obj is not None:
            obj.side = side
    return True


def _arrives(actor, operand, line):
    """`Kessel Station arrives` - place a declared landmark.

    Idempotent by construction: ``landmark_spawn`` returns the existing object when the
    key is already placed, so a beat entered twice does not duplicate it, and a landmark
    that was destroyed IS re-placed. That is why an event verb needs no `once` flag - the
    identity is the landmark key, checked against the live world.
    """
    from .amd_landmarks import landmark_record, landmark_spawn
    record = landmark_record(_action_slug(actor))
    if record is None:
        _action_log(f"{actor!r} is not a declared landmark, so it cannot arrive: {line!r}")
        return False
    return landmark_spawn(record) is not None


def _departs(actor, operand, line):
    """`The freighter departs` - remove it from the world."""
    from .space_objects import delete_object
    ids = amd_action_actors(actor)
    if not ids:
        _action_log(f"nobody called {actor!r} to act on: {line!r}")
        return False
    delete_object(ids)
    return True


def _role_list(operand):
    """`a pirate` / `pirate, discovered` -> role tokens."""
    return [_action_slug(p) for p in str(operand).replace(",", " ").split() if p.strip()]


def _install_builtins():
    amd_action_register("becomes", _becomes, domain="core")
    amd_action_register("is no longer", _no_longer, domain="core")
    amd_action_register("joins", _joins, domain="core")
    amd_action_register("arrives", _arrives, operand="none", domain="core")
    amd_action_register("departs", _departs, operand="none", domain="core")


_install_builtins()
