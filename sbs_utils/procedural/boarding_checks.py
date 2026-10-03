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


#: How close another SUIT has to be to lend a hand, in world units - a person's working
#: distance inside a relic, the same order as a suit's reach.
EVA_HELP_RADIUS = 500.0


def _helpers(lifeform, skill):
    """Teammates standing next to this one who have the skill.

    On the ground that is the tile map's neighbours. In a relic nobody is on a tile, and
    `tilemap_actors_near` answers [] for a body with no cell - so a suit's check was
    always rolled alone however many of the crew were floating beside it. There the
    neighbours are the other SUITS within `EVA_HELP_RADIUS`.
    """
    from .boarding import boarding_team
    from .tilemap import tilemap_actors_near
    team = set(boarding_team())
    near = [a for a in tilemap_actors_near(lifeform, 1)
            if a in team and boarding_skill(a, skill) > 0]
    if near:
        return near
    return [a for a in _suit_neighbours(lifeform)
            if a in team and boarding_skill(a, skill) > 0]


def _suit_neighbours(lifeform):
    """The people in the other suits near this one's suit. [] when it is not in one."""
    try:
        from .eva import eva_suit_of, eva_lifeform_of, eva_suits, KEY_RELIC
    except Exception:                                    # noqa: BLE001
        return []
    from .query import to_object
    suit = eva_suit_of(lifeform)
    obj = to_object(suit) if suit else None
    if obj is None:
        return []
    here = obj.pos
    r2 = EVA_HELP_RADIUS * EVA_HELP_RADIUS
    out = []
    for other in eva_suits(get_inventory_value(suit, KEY_RELIC, None)):
        if other == suit:
            continue
        so = to_object(other)
        if so is None:
            continue
        p = so.pos
        if (p.x - here.x) ** 2 + (p.y - here.y) ** 2 + (p.z - here.z) ** 2 > r2:
            continue
        who = eva_lifeform_of(other)
        if who is not None:
            out.append(who)
    return out


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
        _check_unreadable(tokens)
        return None
    skill = tokens[0]
    try:
        dc = int(tokens[1])
    except ValueError:
        _check_unreadable(tokens)
        return None
    result = boarding_check(agent_id, skill, dc)
    _roll_note(agent_id, result["text"])
    if not result["ok"]:
        rest = [t for t in tokens[2:]]
        if len(rest) >= 2 and rest[0].lower() == "else":
            from .boarding import boarding_redirect
            boarding_redirect(rest[1])
        # A FAILED CHECK ENDS THE CHOICE. Everything written after it on the line is
        # what success does - `; check engineering 12 else held ; open seal` - and it
        # used to run anyway, so a failed roll still opened the seal.
        from .amd_dialogue import OUTCOME_STOP
        return OUTCOME_STOP
    return None


def _check_unreadable(tokens):
    """Say that a `check` could not be read - where the author will see it.

    Nothing was rolled, and the choice carried on as if the roll had worked: a locked
    door that is open, with no roll line in the transcript to say why. `sbs lint` reports
    the same line as `check-shape`; this is for the mission nobody linted.
    """
    try:
        import logging
        logging.getLogger("mast.runtime").warning(
            "boarding: `check %s` is not `check <skill> <number> [else <room>]` - no roll "
            "was made and the choice went ahead. A skill is one word and the number is "
            "written in digits." % " ".join(str(t) for t in tokens))
    except Exception:                                    # noqa: BLE001
        pass


def _roll_note(lifeform, text):
    """Put the roll in the transcript of everyone in the actor's conversation - what the
    module docstring always said happened, and never did: `boarding_check` only emitted
    a signal, so a player saw the scene jump to the failure beat with no roll to explain
    why."""
    try:
        from .boarding import (boarding_client_of, boarding_channel_of,
                               boarding_channel_members, boarding_reader_note)
    except Exception:                                    # noqa: BLE001
        return
    cid = boarding_client_of(lifeform)
    if cid is None:
        return
    members = boarding_channel_members(boarding_channel_of(cid)) or {cid}
    for member in sorted(members):
        boarding_reader_note(member, text)


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
