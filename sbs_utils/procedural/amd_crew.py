"""Declarative CREW ROSTERS from AMD - author who sits where as data.

    ## [Enterprise-D](tng_d)
    ---
    crew
    By: console
    Hull: tng_fed_galaxy
    Ship: Enterprise, Enterprise-D
    Race: terran
    Portraits: media/crew/tng
    ---
    The Galaxy-class flagship's senior staff.

    ### [Jean-Luc Picard](picard)
    ---
    Rank: Captain
    Console: mainscreen
    Face: tng1 #fff 0 0;
    ---

    ### [Data](data)
    ---
    Rank: Lt. Commander
    Console: science
    Portrait: data
    ---

The SECTION fence carries what every member shares - the hull it crews, the race their
faces come from, the folder their photographs live in - and each entry says only what makes
them them. `Data` is three lines, and that is the point.

TWO KINDS, ONE FORMAT, chosen by ``By:``:

``By: console`` (the default)
    A CAST. Each member names a seat, so opening helm makes you whoever crews helm. This is
    what fills a Director bridge multiview with nobody typing anything.

``By: person``
    A GROUP. The console is irrelevant and members are never auto-assigned - you pick
    YOURSELF out of the list and keep your name and face at whatever station you take::

        ## [Thursday Night Crew](thursday)
        ---
        crew
        By: person
        Sheet: media/crew/thursday/faces
        Cell: 256
        Grid: 4, 2
        ---

        ### [Doug](doug)
        ---
        Rank: Captain
        At: 0, 0
        ---

A roster's ``Sheet:``/``At:`` are the SAME cell arithmetic
:mod:`sbs_utils.procedural.amd_images` uses, and go through the same ``media_shared``, so a
group's photographs are cut exactly like an icon sheet and resolve the same in a clone and
in a fetched copy. There is no second image mechanism to learn.

.. note::
   The kind noun is a BARE WORD on the fence's first line - ``crew``, not ``Kind: crew``.
   The label ``kind`` infers *landmark*, which would type the whole roster wrong and take
   every member with it.

TWO READERS, ONE RECORD BUILDER. :func:`crew_from_section` is the game and
:func:`crew_from_core` is the linter; they share :func:`crew_member_record` so a fact
cannot mean one thing to the linter and another to the game.
"""
from sbs_utils.mast.mast_node import MastDataObject
from sbs_utils.procedural.amd import amd_read_text, amd_parse_facts


CREW_KINDS = ("crew", "crews", "roster", "rosters", "officers", "bridge")

# Facts that name several things at once. Everything else on a crew fence is plain text, so
# it does NOT go through the numeric default coercion `amd_parse_facts` would otherwise
# apply - a rank of "1st Officer" must not become the number 1.
_CSV_FIELDS = ("hull", "ship", "roles")
_TEXT_FIELDS = ("name", "desc", "by", "assign", "console", "rank", "portrait", "portraits",
                "race", "face", "sheet", "display", "color")


def _lower(data):
    return {str(k).lower(): v for k, v in (data or {}).items()}


def _csv(value):
    """A comma-separated fact as a list. Already-a-list passes through."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    return [p.strip() for p in str(value).split(",") if p.strip()]


def amd_crew_facts():
    """``amd_parse_facts`` handler for a crew fence.

    Unknown labels return None so they fall through to the field registry and then to the
    numeric default, exactly as every other domain reader does - a mission may declare extra
    fields on crew and read them off ``record.data``.
    """
    def handler(data, label, value):
        if label in _CSV_FIELDS:
            data[label] = _csv(value)
        elif label in _TEXT_FIELDS:
            data[label] = str(value).strip()
        else:
            return None
        return True
    return handler


def amd_crew_data(text):
    """Parse one crew fence into a data dict."""
    return amd_parse_facts(text, amd_crew_facts())


def crew_member_record(section, data, key, name=None, roster_key=None):
    """One crew member from the section's facts and their own.

    Section-level ``Race``/``Portraits``/``Cell``/``Grid`` are the member's defaults, which
    is what lets a member be a ``Console:`` line and a ``Face:`` line.
    """
    from sbs_utils.procedural.amd_images import _pair
    section = _lower(section)
    data = _lower(data)
    return MastDataObject({
        "key": key,
        "name": data.get("name") or name or key,
        "rank": data.get("rank") or "",
        "console": str(data.get("console") or "").strip().lower(),
        "face": data.get("face") or "",
        "portrait": data.get("portrait") or "",
        "at": _pair(data.get("at")),
        "roster": roster_key,
        "data": data,
    })


def crew_roster_record(key, section, name=None, desc=None, members=None):
    """One roster from its section fence.

    ``By:`` defaults to ``console`` because a cast is the common case and the one that needs
    no player input; a group has to say so.
    """
    from sbs_utils.procedural.amd_images import _pair
    section = _lower(section)
    by = str(section.get("by") or section.get("assign") or "console").strip().lower()
    members = list(members or ())
    return MastDataObject({
        "key": key,
        # `path` and `display_name` are what `maps.label_find_by_spec` matches on, so a
        # roster resolves from a dropdown, a setting and a command line the one way.
        "path": key,
        "name": section.get("name") or name or key,
        "display_name": section.get("name") or name or key,
        "desc": desc,
        "by": "person" if by.startswith("person") else "console",
        "hull": _csv(section.get("hull")),
        "ship": _csv(section.get("ship")),
        "race": section.get("race") or "",
        "portraits": section.get("portraits") or "",
        "sheet": section.get("sheet") or "",
        "cell": _pair(section.get("cell")),
        "grid": _pair(section.get("grid")),
        "members": members,
        "usable": bool(members),
        "data": section,
    })


def _declared_kind(section):
    """The kind noun the fence actually declared, or ""."""
    return str(section.get("__kind__") or section.get("kind") or "").strip().lower()


def _is_crew_section(node, section, allow_key=True):
    """Is this node a roster?

    Two ways to say so, and they are NOT equal. A bare ``crew`` noun on the fence is the AMD
    idiom and is definitive. A section merely KEYED ``crew``/``rosters`` is a guess, kept
    because ``## [Crew](crew)`` reads naturally and an author should not have to say it
    twice - but it is only consulted when nothing in the file declared the noun outright.

    That ordering is load-bearing. A file whose root heading is ``# [Rosters](rosters)``
    holding two real ``crew`` sections would otherwise match on the ROOT, and every actual
    roster in it would be read as one of its members.
    """
    kind = _declared_kind(section)
    if not kind and allow_key and hasattr(node, "get"):
        kind = str(node.get("key") or "").strip().lower()
    return kind in CREW_KINDS


def crew_from_section(node):
    """Roster records from one ``## [Name](key)`` crew section of an ``amd_document``."""
    if node is None:
        return []
    section = _lower(node.get("data"))
    key = node.get("key")
    members = [crew_member_record(section, n.get("data"), n.get("key"),
                                  n.get("display_text"), key)
               for n in node.get("children", [])]
    return [crew_roster_record(key, section, node.get("display_text"),
                               node.get("description"), members)]


def crew_sections(doc):
    """Every crew section in a document, AT ANY DEPTH.

    `amd_document` wraps a file's sections under a single root heading, and a mission is
    free to nest its rosters under one of its own - so this walks rather than looking one
    level down. A node that IS a roster is not descended into: its children are its members,
    not more rosters.
    """
    if doc is None:
        return []

    def collect(allow_key):
        found = []

        def walk(node):
            if _is_crew_section(node, _lower(node.get("data")), allow_key):
                found.append(node)
                return          # its children are its MEMBERS, not more rosters
            for child in node.get("children", []) or ():
                walk(child)

        walk(doc)
        return found

    return collect(False) or collect(True)


def crew_from_document(doc):
    """Every roster in a document. A file with no crew section yields nothing rather than
    complaining, so a mission may keep its rosters in a file beside anything else."""
    out = []
    for node in crew_sections(doc):
        out.extend(crew_from_section(node))
    return out


def crew_from_core(section):
    """The same, from an ``amd_core`` node - the model the LINTER parses into.

    Two readers exist because the linter needs spans and the runtime does not; they share
    the record builders above so the two can never disagree about what a fact means.
    """
    data = _lower(getattr(section, "data", None))
    key = getattr(section, "key", None)
    return [(child, crew_member_record(data, getattr(child, "data", None), child.key,
                                       getattr(child, "display", None), key))
            for child in getattr(section, "children", [])]


def crew_read_amd(file_path):
    """Read a MISSION-relative ``.amd`` file and return its roster records.

    Mission-relative, so an ADDON CANNOT USE THIS. An addon reads its own file out of its
    mastlib and calls :func:`sbs_utils.procedural.crew.crew_declare_amd`.
    """
    from sbs_utils.procedural.amd_doc import amd_document
    from sbs_utils.fs import get_mission_dir_filename
    content = amd_read_text(get_mission_dir_filename(file_path))
    return crew_from_document(amd_document(content, data_parser=amd_crew_data))


def crew_validate(records, check_files=True):
    """Problems a mission would otherwise meet as a blank name plate.

    Returns a list of ``(key, severity, code, message)``.

    A ``Console:`` no ``@console`` label registers is a WARNING, never an error: console
    types are registered at runtime from decorator labels, so a mod's own console genuinely
    may not exist at lint time and refusing it would make the linter wrong about correct
    files.
    """
    out = []
    for roster in records or ():
        rkey = roster.get("key")
        if not roster.get("members"):
            out.append((rkey, "warning", "crew-empty-roster",
                        "crew roster '%s' has no members" % rkey))
        if roster.get("by") == "console":
            seen = {}
            for m in roster.get("members") or ():
                con = m.get("console")
                if con:
                    seen.setdefault(con, []).append(m.get("key"))
            for con, keys in seen.items():
                if len(keys) > 1:
                    out.append((rkey, "info", "crew-console-shared",
                                "console '%s' is named by %s - they will fill it in order"
                                % (con, ", ".join(keys))))
        for m in roster.get("members") or ():
            if m.get("at") is not None and not roster.get("sheet"):
                out.append((m.get("key"), "error", "crew-at-without-sheet",
                            "'%s' has At: but its roster declares no Sheet:" % m.get("key")))
            if not m.get("name"):
                out.append((m.get("key"), "error", "crew-no-name",
                            "a crew member needs a name"))
        for hull in roster.get("hull") or ():
            if check_files and not _hull_known(hull):
                out.append((rkey, "warning", "crew-unknown-hull",
                            "Hull: '%s' is not in shipData - this roster will never bind"
                            % hull))
    return out


def _hull_known(hull):
    try:
        from sbs_utils.procedural.ship_data import get_ship_index
        return str(hull).strip() in (get_ship_index() or {})
    except Exception:
        # No ship data loaded (a bare lint run) - cannot tell, so do not accuse.
        return True
