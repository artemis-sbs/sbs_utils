"""Declarative urges from AMD - author what an actor keeps asking for as data.

An ``Urge`` heading's BODY is its line pool, exactly the way ``amd_chatter`` already
treats a pool: no fence needed for the words, so ``{placeholder}`` and colon-heavy prose
never trip the YAML-flow path. A leading ``%`` (the dialogue random-variant marker) is
stripped, and ``//`` comment lines are ignored::

    ## [DS1 calls for resupply](ds1_calling)
    ---
    Urge
    Actor: DS1
    Whenever: quest ds1_resupply active
    Every: 5m
    Weight: 20
    ---
    % DS1 requests a resupply run when someone has the tonnage.
    % DS1 is below reserve. We need that shipment.

``Actor:`` is resolved by ``amd_action_actors`` - a declared landmark key, then a role -
so "DS1" means the same thing here as in the stage direction ``DS1 departs``. The runtime
(selection, cooldowns, speaking) lives in ``urge.py``; this module is only the reader.
"""
from sbs_utils.procedural.amd import amd_parse_facts, amd_duration_seconds
from sbs_utils.procedural.urge import urge_record, urge_add


def amd_urge_data(text):
    """Parse one urge fence into a data dict (default coercion - all fields are
    strings). Most urges need no fence values beyond these few; the words are the BODY."""
    return amd_parse_facts(text)


def _urge_pool(desc):
    """Body prose -> ``(pool, stages)``.

    Same rules as ``amd_chatter``: one line per entry, ``//`` comments ignored. The
    number of leading ``%`` is the escalation STAGE - ``%`` first asking, ``%%`` more
    insistent, ``%%%`` the last time. A line with no marker sits at stage 1.

        % Ambassador Vell is on the docking ring, when convenient.
        %% Vell again. My transport window is closing, captain.
        %%% This is the last time I ask.

    ``pool`` is every line flat (what a non-escalating urge uses, unchanged from before);
    ``stages`` is ``{1: [...], 2: [...]}``, present only when the author actually wrote
    more than one stage. So the marker count IS the escalation curve - no second field to
    keep in sync with the words, and the author keeps the dial.
    """
    pool, stages = [], {}
    for raw in (desc or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        stage = 0
        while line.startswith("%"):
            stage += 1
            line = line[1:].strip()
        if not line:
            continue
        pool.append(line)
        stages.setdefault(max(1, stage), []).append(line)
    return pool, (stages if len(stages) > 1 else None)


def urges_from_section(section):
    """Urge records from a section node's children (empty list if None).

    A heading with no body is skipped and logged - an urge with nothing to say would
    burn its turn every pass and never be noticed.
    """
    out = []
    if section is None:
        return out
    for n in section.get("children", []):
        data = {str(k).lower().replace(" ", "_"): v
                for k, v in (n.get("data") or {}).items()}
        pool, stages = _urge_pool(n.get("description") or "")
        key = n.get("key")
        if not pool and not data.get("action"):
            from sbs_utils.procedural.urge import _urge_log
            _urge_log(f"urge {key!r} has no lines and no Action: - it would do nothing")
            continue
        every = amd_duration_seconds(data.get("every")) if data.get("every") else None
        escalates = _escalates(data.get("escalates"), stages, key)
        out.append(urge_record(
            key=key,
            actor=data.get("actor"),
            whenever=data.get("whenever") or data.get("when") or "always",
            every=60 if every is None else every,
            until=data.get("until"),
            weight=_int(data.get("weight"), 0),
            pool=pool,
            stages=stages,
            escalates=escalates,
            action=data.get("action"),
        ))
    return out


def _escalates(value, stages, key):
    """``Escalates:`` -> ``"deadline"`` | ``"firing"`` | None.

    ``with deadline`` (the interesting one) takes the stage from how much of the bound
    quest's clock is left, so the drama curve IS the countdown that already exists - no
    second clock to keep in sync. ``yes`` advances a stage per firing, for an urge with
    no deadline behind it.

    Staged lines with no ``Escalates:`` are a warning, not a guess: the author clearly
    meant something by writing ``%%``, and silently flattening it would look like the
    feature was broken. Defaulting it on would be worse - it would change how existing
    flat pools with a stray ``%%`` behave.
    """
    word = str(value or "").strip().lower()
    if not word:
        if stages:
            from sbs_utils.procedural.urge import _urge_log
            _urge_log(f"urge {key!r} has staged lines (%% / %%%) but no 'Escalates:' - "
                      f"they will read as one flat pool")
        return None
    if "deadline" in word:
        return "deadline"
    if word in ("yes", "true", "firing", "per firing", "on"):
        return "firing"
    from sbs_utils.procedural.urge import _urge_log
    _urge_log(f"urge {key!r}: 'Escalates: {value}' is not 'with deadline' or 'yes'")
    return None


def _int(value, default):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def urges_install(section):
    """Give every authored urge to the agents its ``Actor:`` names. Returns how many
    (record, agent) pairs were installed.

    An urge whose actor nobody answers to is LOGGED and skipped, never silently dropped -
    most often it means the AMD was installed before the actor spawned, which the message
    says. Idempotent per (agent, urge key), so re-running a section is safe.
    """
    from sbs_utils.procedural.amd_action import amd_action_actors
    from sbs_utils.procedural.urge import _urge_log
    installed = 0
    for rec in urges_from_section(section):
        actor = rec.get("actor")
        if not actor:
            _urge_log(f"urge {rec.get('key')!r} has no Actor: - nobody to want it")
            continue
        ids = amd_action_actors(actor)
        if not ids:
            _urge_log(f"urge {rec.get('key')!r} is held by {actor!r}, but nothing "
                      f"answers to that name - is it installed before the actor spawns?")
            continue
        urge_add(ids, rec)
        installed += len(ids)
    return installed
