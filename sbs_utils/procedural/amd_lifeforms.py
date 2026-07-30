"""Declarative lifeform cast from AMD - author a mission's named characters (crew, contacts,
comms NPCs) as data instead of imperative ``lifeform_spawn`` calls, the way Open Universe authors
its captains/officers. A section authors one heading per character:

    # [Deck Chief Renner](deck_chief)
    ---
    Face: terran_male
    Roles: informant
    ---
    Keeps the arrival logs; remembers every hull that ever cleared his dock.

``Face`` is a face keyword (``terran`` / ``male`` / ``female`` / ``fluid`` / ``terran_male`` ...)
resolved via the shared ``face_resolve`` (a raw face string passes through; nothing -> a random
terran). ``Roles`` is a comma list. Optional: ``Color`` (or ``Title color``) for the comms-card
colour, ``Path`` (a ``//comms`` route = the character's voice), ``Scene`` (a dialogue scene key,
stored on the lifeform for a dialogue bridge), and ``Host`` (carried on the record for a caller
that wants to host it on a ship - the base spawn leaves it unhosted).

All fields are plain strings, so a lifeforms section parses under the default AMD coercion (or a
mission's ``amd_mission_data``) - no dedicated fact handler needed. ``lifeforms_spawn`` returns a
``{key: lifeform}`` map so a caller resolves a character by key (an interview contact, or a
``Speaker: <key>`` dialogue voice). Generalised from OU's ``universe_spawn_lifeform``.
"""
from sbs_utils.procedural.amd import amd_parse_facts
from sbs_utils.faces import face_resolve
from sbs_utils.procedural.lifeform import lifeform_spawn
from sbs_utils.procedural.inventory import set_inventory_value, get_inventory_value
from sbs_utils.procedural.query import to_object, to_id
from sbs_utils.mast.mast_node import MastDataObject


def amd_lifeform_data(text):
    """Parse one lifeform fence into a data dict (default coercion - all fields are strings).
    Use as the ``data_parser`` for a cast-only .amd; a consolidated mission file uses
    ``amd_mission_data`` and its lifeform fences fall through to the same default coercion."""
    return amd_parse_facts(text)


def lifeforms_from_section(section):
    """Cast records (MastDataObject) from a section node's children (empty if None)."""
    out = []
    if section is not None:
        for n in section.get("children", []):
            data = {str(k).lower(): v for k, v in (n.get("data") or {}).items()}
            out.append(MastDataObject({
                "key": n.get("key"),
                "name": n.get("display_text"),
                "desc": (n.get("description") or "").strip(),
                "face": data.get("face"),
                "roles": data.get("roles") or "",
                "host": data.get("host"),
                "color": data.get("color") or data.get("title_color") or "green",
                "path": data.get("path"),
                "scene": data.get("scene"),
                "data": data,   # carry the raw fence for mission-specific extras
            }))
    return out


def lifeform_key_role(key, host_id=None):
    """The role marking the lifeform spawned for AMD ``key`` on ``host_id``.

    Keyed on key AND host: `lifeforms_spawn(section, host_id)` legitimately casts the same
    section onto several hosts (one crew roster, many stations), and keying on the record
    alone would make the second host silently resolve to the first host's character.
    """
    suffix = "" if host_id is None else f"@{to_id(host_id)}"
    return f"amd_lifeform:{str(key).strip()}{suffix}"


def lifeform_of_key(key, host_id=None):
    """The live lifeform already spawned for ``key`` on ``host_id``, or None."""
    from sbs_utils.procedural.roles import role
    from sbs_utils.procedural.query import to_id_list
    if not key:
        return None
    for agent_id in to_id_list(role(lifeform_key_role(key, host_id))):
        agent = to_object(agent_id)
        if agent is not None:
            return agent
    return None


def lifeform_from_record(record, host_id=None):
    """Spawn one authored lifeform: name + ``face_resolve(Face)`` + Roles, optionally hosted on
    ``host_id``, with the record's ``Path`` as its comms voice and ``Color`` as its card colour.
    A ``Scene`` (if any) and the record ``key`` are stored on the lifeform for a dialogue bridge.
    Returns the spawned lifeform Agent.

    Idempotent on (record ``key``, ``host_id``): a character already cast on that host is
    returned as-is, so re-running a section - a map body that runs twice, a re-emitted
    setup signal - does not create a second copy of the same person. The same section cast
    onto a DIFFERENT host still produces its own character.
    """
    key = record.get("key")
    existing = lifeform_of_key(key, host_id)
    if existing is not None:
        return existing
    agent = lifeform_spawn(record.get("name"), face_resolve(record.get("face")),
                           record.get("roles") or "", host_id,
                           path=record.get("path"), title_color=record.get("color") or "green")
    if record.get("scene") is not None:
        set_inventory_value(agent, "scene", record.get("scene"))
    set_inventory_value(agent, "lf_key", record.get("key"))
    # Store the card colour + key on the lifeform so a comms-cast route can resolve its speaker
    # from the hailed lifeform itself (lifeform_speaker_of), with no separate records source.
    set_inventory_value(agent, "lf_color", record.get("color") or "green")
    if key:
        from sbs_utils.procedural.roles import add_role
        add_role(agent, lifeform_key_role(key, host_id))
    return agent


def lifeform_speaker_of(agent_id, default_color="#0cf"):
    """A dialogue speaker card (key/name/color/leans) built from a spawned lifeform Agent ITSELF -
    for the comms-cast route, where the hailed lifeform IS the speaker (its badge was selected).
    ``None`` if the id is not a live agent; cast NPCs carry no reputation, so leans is empty."""
    a = to_object(agent_id)
    if a is None:
        return None
    return MastDataObject({
        "key": get_inventory_value(agent_id, "lf_key", None),
        "name": a.name,
        "color": get_inventory_value(agent_id, "lf_color", None) or default_color,
        "leans": {},
    })


def lifeforms_spawn(section, host_id=None):
    """Spawn every character in a section (optionally all hosted on ``host_id``); returns a
    ``{key: lifeform}`` map. Convenience over ``lifeforms_from_section`` + ``lifeform_from_record``."""
    out = {}
    for rec in lifeforms_from_section(section):
        out[rec.get("key")] = lifeform_from_record(rec, host_id)
    return out


def lifeform_speaker(records, key, default_color="#0cf"):
    """A dialogue voice record (key/name/color/leans) for a cast character, so a scene's
    ``Speaker: <key>`` resolves to that character's card. ``None`` if the key is not in the cast;
    cast NPCs carry no reputation, so leans is empty. ``records`` is ``lifeforms_from_section``'s
    list (or the ``.values()`` of a spawned map's records)."""
    for r in records:
        if r.get("key") == key:
            return MastDataObject({"key": r.get("key"), "name": r.get("name"),
                                   "color": r.get("color") or default_color, "leans": {}})
    return None
