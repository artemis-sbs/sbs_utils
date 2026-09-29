"""Skill checks for a boarding party: can THIS person do THIS, right now?

A scene's role guard (`if engineering`) says who may TRY. A check says whether it works:
the character's skill, a roll, and the people standing next to them helping. It is what
turns "the engineer fixes the hauler" into "the engineer might fix the hauler, and the
science officer standing beside her makes it likelier".

SKILLS come from three places, strongest first:

1. ``boarding_skills_set(lifeform, {"engineering": 3})`` - set on the body.
2. A table read from a crew roster's ``Skills:`` field (``boarding_skills_from_amd``),
   matched to a body by NAME - a crew body is spawned from a post and carries its name.
3. A JOB is worth ``JOB_SKILL`` (2): a crew member cast as `engineering` is competent at
   it even when nobody wrote a number down.

Anything else is 0.

THE ROLL is ``d10 + skill + help + bonus >= dc``. ``boarding_checks_mode("flat")`` drops
the die (``5 + skill ...``) for tests and for a table that wants no luck; the module owns
its own `random.Random`, so ``boarding_checks_seed`` makes a run repeatable without
touching anyone else's randomness.

In dialogue, the outcome verb::

    - [Force the coupling](coupled) if engineering ; check engineering 8 else sheared

applies the check to whoever picked the choice, goes to ``coupled`` on a success and to
``sheared`` on a failure, and puts the roll in the transcript.
"""
import random

from .inventory import get_inventory_value, set_inventory_value
from .query import to_id

JOB_SKILL = 2
SKILLS_KEY = "BOARDING_SKILLS"
_DIE = 10

_RNG = random.Random()
_MODE = {"mode": "dice"}
_TABLE = {}              # normalized name -> {skill: n}
_LAST = {}               # lifeform id -> last CheckResult (for a transcript line)


def _norm(s):
    return str(s or "").strip().lower()


def boarding_checks_mode(mode="dice"):
    """``"dice"`` (the default) or ``"flat"`` - no randomness."""
    _MODE["mode"] = "flat" if _norm(mode) == "flat" else "dice"


def boarding_checks_seed(seed):
    _RNG.seed(seed)


def boarding_skills_set(lifeform, skills):
    """Give a body its skills: ``{"engineering": 3, "athletics": 1}``."""
    set_inventory_value(to_id(lifeform), SKILLS_KEY,
                        {_norm(k): int(v) for k, v in (skills or {}).items()})


def boarding_skills_parse(text):
    """``"engineering 3, science 1"`` (or a dict) -> ``{"engineering": 3, "science": 1}``."""
    if isinstance(text, dict):
        return {_norm(k): int(v) for k, v in text.items()}
    if isinstance(text, (list, tuple)):
        text = ", ".join(str(t) for t in text)
    out = {}
    for part in str(text or "").split(","):
        bits = part.split()
        if len(bits) >= 2:
            try:
                out[_norm(" ".join(bits[:-1]))] = int(float(bits[-1]))
            except ValueError:
                continue
    return out


def boarding_skills_declare(name, skills):
    """Skills for whoever is NAMED this - a crew member, before any body exists."""
    _TABLE[_norm(name)] = boarding_skills_parse(skills)


def boarding_skills_from_amd(section):
    """Read ``Skills:`` off every record in an AMD section (a crew roster), by name.

    Nested sections are walked, so the roster file's own ``## [Watch]`` heading with its
    ``### [Person]`` children works as it is.
    """
    count = 0
    stack = [section] if section is not None else []
    while stack:
        node = stack.pop()
        for child in node.get("children", []) or []:
            stack.append(child)
            data = child.get("data") or {}
            if data.get("skills"):
                boarding_skills_declare(child.get("display_text") or child.get("key"),
                                        data["skills"])
                count += 1
    return count


def _table_for(lifeform):
    from .query import to_object
    so = to_object(lifeform)
    name = _norm(getattr(so, "name", ""))
    if not name:
        return None
    if name in _TABLE:
        return _TABLE[name]
    # A crew body is named "Rank Name" - match a declared name at the end of it.
    for declared, table in _TABLE.items():
        if name.endswith(" " + declared) or declared.endswith(" " + name):
            return table
    return None


def boarding_skill(lifeform, name):
    """How good this character is at ``name``."""
    lf = to_id(lifeform)
    name = _norm(name)
    own = get_inventory_value(lf, SKILLS_KEY, None)
    if own and name in own:
        return int(own[name])
    table = _table_for(lf)
    if table and name in table:
        return int(table[name])
    from .boarding import boarding_jobs
    return JOB_SKILL if name in boarding_jobs(lf) else 0


def _helpers(lifeform, skill):
    """Teammates standing next to this one who have the skill."""
    from .boarding import boarding_team
    from .tilemap import tilemap_actors_near
    team = set(boarding_team())
    return [a for a in tilemap_actors_near(lifeform, 1)
            if a in team and boarding_skill(a, skill) > 0]


def boarding_check(lifeform, skill, dc, bonus=0, help=True):
    """Try something. Returns a dict: ``ok``, ``roll``, ``skill``, ``help``, ``total``,
    ``dc``, ``who``, and ``text`` - one line for a transcript.

    Emits ``boarding_checked`` with the same values as ``BOARDING_*`` keys.
    """
    lf = to_id(lifeform)
    level = boarding_skill(lf, skill)
    helpers = _helpers(lf, skill) if help else []
    roll = 5 if _MODE["mode"] == "flat" else _RNG.randint(1, _DIE)
    total = roll + level + len(helpers) + int(bonus)
    ok = total >= int(dc)
    from .query import to_object
    who = getattr(to_object(lf), "name", "Someone")
    helped = f" +{len(helpers)} help" if helpers else ""
    text = (f"{who} - {skill} {level}{helped}, rolled {roll}: {total} vs {dc}, "
            f"{'success' if ok else 'failure'}.")
    result = {"ok": ok, "roll": roll, "skill": level, "help": len(helpers),
              "total": total, "dc": int(dc), "who": lf, "name": skill, "text": text}
    _LAST[lf] = result
    from .signal import signal_emit
    signal_emit("boarding_checked", {"BOARDING_WHO": lf, "BOARDING_SKILL": _norm(skill),
                                     "BOARDING_OK": ok, "BOARDING_TOTAL": total,
                                     "BOARDING_DC": int(dc), "BOARDING_TEXT": text})
    return result


def boarding_last_check(lifeform):
    """The last check this character made, or None."""
    return _LAST.get(to_id(lifeform))


def _check_outcome(agent_id, speaker, tokens):
    """The ``check <skill> <dc> [else <target>]`` outcome verb."""
    if len(tokens) < 2:
        return None
    skill = tokens[0]
    try:
        dc = int(tokens[1])
    except ValueError:
        return None
    result = boarding_check(agent_id, skill, dc)
    if not result["ok"]:
        rest = [t for t in tokens[2:]]
        if len(rest) >= 2 and rest[0].lower() == "else":
            from .boarding import boarding_redirect
            boarding_redirect(rest[1])
    return None


def _checks_metric(name):
    """``skill engineering`` for a guard: ``if skill engineering >= 3``."""
    name = _norm(name)
    if name.startswith("skill "):
        return name[6:].strip()
    return None


from .amd_dialogue import dialogue_register_outcome  # noqa: E402
dialogue_register_outcome("check", _check_outcome)


def boarding_checks_clear():
    _TABLE.clear()
    _LAST.clear()
    _MODE["mode"] = "dice"
    _RNG.seed()


def boarding_checks_count():
    """Reset-ledger probe."""
    return len(_TABLE) + len(_LAST)
