"""Declarative enemy THEATERS from AMD - who a mission fights, as data.

A theater is an ORDERED roster of enemy factions. It says WHO turns up and in what
proportion; the map still says how hard::

    # [Dominion War](dominion_war)
    ---
    Races: kralien, torgoth, arvonian, ximni
    Art:   kralien=Cardassian, torgoth=Dominion, arvonian=Breen, ximni=Klingon
    Faces: kralien=cardassian, torgoth=jemhadar, arvonian=vorta, ximni=klingon
    Music: TNG_Music
    ---
    The Alpha Quadrant at war. Cardassian space is the front line.

THE ROSTER IS IN THE MISSION'S OWN VOCABULARY, and that is not a stylistic choice - it is
forced. LM's maps BRANCH ON THE RACE NAME: `borderwar` and `deepstrike` both run
`if enemy1 == "Kralien":` to choose the enemy station type and the roles string. A theater
that returned `cardassian` would make every one of those branches fall through, and the
mission would spawn no enemy stations at all - silently, because nothing tests a chain of
ifs that all miss. So `Races:` lists what the mission already understands, and `Art:` says
what those races LOOK like.

That leaves two independent levers, and either reaches the goal: reorder `Races:` to move a
different race into the heavy slot, or repoint `Art:` so the heavy race is drawn as the
faction you want.

WHY THIS EXISTS. A mission picks its enemy race from a literal - LegendaryMissions has
eleven of them across five maps, e.g. ``["Kralien", "Torgoth", "Arvonian", "Ximni"]`` with
``weights=(50, 25, 25)``. Nothing reads a setting, so no profile and no mod can change who
shows up. Under a total conversion that is how you get a mix nobody chose: LM's difficulty-5
curve is ``[70, 10, 10, 10]``, so if the conversion happens to pair the 70% race with a
minor faction, the whole game is that faction.

THE THEATER SUPPLIES THE ORDER; THE MAP KEEPS ITS WEIGHT CURVE. That split is deliberate.
LM's curve runs ``[85,5,5,5]`` at difficulty 1 and ``[10,30,30,30]`` at 11 - the enemy mix
DIVERSIFIES as the game gets harder, which is a real design feature. Flat weights in the
theater would throw it away. So :func:`theater_pick_race` applies the caller's curve to the
theater's factions in order, and a map wanting three of them passes three weights. A theater
MAY declare its own ``Weights:`` when an author wants a fixed mix; that then wins.

FACTION DEPTH IS A REAL CONSTRAINT, and it is the failure that hides. A faction with one
hull in a heavy slot does not error - the same ship simply turns up forever, which reads as
"the mod is broken" rather than "the roster is wrong". :func:`theater_depth_report` names
it, and picking reports it once per mission instead of staying silent.
"""
from ..mast.mast_node import MastDataObject
from .amd import amd_parse_facts, amd_read_text


# Per-mission, cross-document registries. `cosmos_dev` REUSES one interpreter across
# missions, so anything module-level here outlives the mission that declared it unless it is
# cleared and put on the reset ledger - a second mission would inherit the first one's
# theaters. Cleared from reset_mission_state(); probe registered in handlerhooks.py.
_theaters = {}
_depth_warned = set()
_side_key_warned = set()


def amd_theater_clear():
    """Drop every declared theater. Called from reset_mission_state()."""
    _theaters.clear()
    _side_key_warned.clear()
    _depth_warned.clear()


def amd_theater_count():
    """How many theaters are declared - the reset-ledger probe."""
    return len(_theaters)


# ---------------------------------------------------------------------------
# parsing
# ---------------------------------------------------------------------------

def _csv(value):
    """A comma list -> [str], lowercased and stripped, empties dropped."""
    if value is None:
        return []
    items = list(value) if isinstance(value, (list, tuple)) else str(value).split(",")
    return [str(i).strip().lower() for i in items if str(i).strip()]


def _pairs(value):
    """An ``a=b, c=d`` list -> {a: b}, lowercased. Entries without ``=`` are ignored."""
    out = {}
    for item in _csv(value):
        k, sep, v = item.partition("=")
        if sep and k.strip() and v.strip():
            out[k.strip()] = v.strip()
    return out


def _numbers(value):
    """A comma list of numbers -> [float]. Non-numeric entries are dropped."""
    out = []
    for item in _csv(value):
        try:
            out.append(float(item))
        except ValueError:
            continue
    return out


# Every fence label a theater understands, in the normalized form the handler sees
# (lowercased, spaces -> underscores). Kept beside the handler because it has to move with
# it: a label accepted there and missing here would be reported as a typo.
_KNOWN_FIELDS = frozenset((
    "races", "factions", "enemies", "roster",
    "weights", "art", "hulls", "faces", "face",
    "music", "music_select", "name", "desc",
    "player_faction", "players_faction", "crew_faction",
    "players", "player_ships", "player_hulls",
    "player_side_name", "player_name",
    "player_side_color", "player_color",
    "player_side_icon", "player_icon",
    "player_side_key",
))


def amd_theater_facts():
    """amd_parse_facts handler for a theater fence.

    ``Factions`` is the roster, dominant first. ``Weights`` is optional and overrides the
    caller's curve. ``Faces`` maps a faction to the FACE RACE its crews are drawn from -
    those are different namespaces (a Federation ship is crewed by `human`, not by
    `federation`), which is exactly why it cannot be inferred.
    """
    def handler(data, label, value):
        if label in ("races", "factions", "enemies", "roster"):
            data["factions"] = _csv(value)
        elif label == "weights":
            data["weights"] = _numbers(value)
        elif label in ("art", "hulls"):
            data["art"] = _pairs(value)
        elif label in ("faces", "face"):
            data["faces"] = _pairs(value)
        elif label in ("music", "music_select"):
            data["music"] = str(value).strip()
        elif label in ("player_faction", "players_faction", "crew_faction"):
            data["player_faction"] = str(value).strip()
        elif label in ("players", "player_ships", "player_hulls"):
            data["players"] = _csv(value)
        elif label in ("player_side_name", "player_name"):
            data["player_side_name"] = str(value).strip()
        elif label in ("player_side_color", "player_color"):
            data["player_side_color"] = str(value).strip()
        elif label in ("player_side_icon", "player_icon"):
            data["player_side_icon"] = str(value).strip()
        elif label == "player_side_key":
            # Parsed so it is not an "unknown field", and REFUSED at read time - see
            # theater_player_side_key. Storing it keeps the refusal honest: the author
            # asked for something specific and gets told why it did not happen.
            data["player_side_key"] = str(value).strip()
        elif label in ("name", "desc"):
            data[label] = str(value).strip()
        else:
            return None
        return True
    return handler


def amd_theater_data(text):
    """Parse one theater fence into a data dict."""
    return amd_parse_facts(text, amd_theater_facts())


def theaters_from_section(node):
    """Theater records from a node whose children are the theater headings."""
    out = []
    if node is not None:
        for n in node.get("children", []):
            # Lower-case the fence keys, as sides_from_section does: a mission authors
            # natural case (`Factions:`) and the default reader preserves it.
            data = {str(k).lower(): v for k, v in (n.get("data") or {}).items()}
            # A field this file does not understand is DROPPED, and silently dropping it is
            # how `Player Facton:` reads as working and changes nothing. The fence parser
            # keeps unrecognized labels in the data dict, so they can be named here.
            #
            # Reported at declare time rather than left to `sbs lint`: these headings carry
            # no section name, so the linter cannot resolve them to an archetype and calls
            # the whole file clean no matter what is in it (verified - a deliberately bogus
            # field lints clean). This is the only place that can see the mistake.
            unknown = sorted(k for k in data if k not in _KNOWN_FIELDS)
            if unknown:
                print("theater '" + str(n.get("key")) + "': unknown field(s) "
                      + ", ".join(unknown) + " - ignored. Known fields: "
                      + ", ".join(sorted(_KNOWN_FIELDS)))
            out.append(MastDataObject({
                "key": n.get("key"),
                "name": data.get("name") or n.get("display_text"),
                "desc": data.get("desc") or ((n.get("description") or "").strip() or None),
                "factions": data.get("factions") or [],
                "weights": data.get("weights") or [],
                "art": data.get("art") or {},
                "faces": data.get("faces") or {},
                "music": data.get("music"),
                "player_faction": data.get("player_faction"),
                "players": data.get("players") or [],
                "player_side_name": data.get("player_side_name"),
                "player_side_color": data.get("player_side_color"),
                "player_side_icon": data.get("player_side_icon"),
                "player_side_key": data.get("player_side_key"),
            }))
    return out


# ---------------------------------------------------------------------------
# declaring
# ---------------------------------------------------------------------------

def theater_declare(records):
    """Register every theater record. Returns {key: record}.

    A later declaration of the same key REPLACES the earlier one, matching `side_create`'s
    idempotence, so a mission can override a theater an addon shipped.
    """
    for r in records or []:
        key = str(r.get("key") or "").strip().lower()
        if not key:
            continue
        if not r.get("factions"):
            # A roster with no factions cannot be selected, and registering it silently
            # would make `THEATER=x` look accepted while changing nothing.
            print("theater '" + key + "' declares no Factions - ignored")
            continue
        _theaters[key] = r
    return dict(_theaters)


def theater_declare_amd(doc):
    """Declare every theater in a parsed AMD document."""
    return theater_declare(theaters_from_section(doc))


def theater_declare_text(content):
    """Declare theaters from AMD text already in hand.

    This is the call an ADDON wants: it reads its own file with `media_read_relative_file`,
    which works inside a packaged `.mastlib` where `get_mission_dir_filename` cannot reach.
    """
    from .amd_doc import amd_document
    return theater_declare_amd(amd_document(content, data_parser=amd_theater_data))


def theater_load_amd(file_path):
    """Load a theater file relative to the mission folder and declare it.

    Bakes in ``data_parser=amd_theater_data`` so a caller cannot omit it - the default AMD
    reader is YAML and would read the comma lists differently.
    """
    from ..fs import get_mission_dir_filename
    return theater_declare_text(amd_read_text(get_mission_dir_filename(file_path)))


# ---------------------------------------------------------------------------
# selection
# ---------------------------------------------------------------------------

def theater_names():
    """Every declared theater key."""
    return sorted(_theaters)


def theater_get(key=None):
    """One theater record by key, or the ACTIVE one when key is None. None when unset."""
    if key is None:
        from .settings import settings_get_defaults
        key = settings_get_defaults().get("THEATER") or ""
    key = str(key).strip().lower()
    if not key:
        return None
    rec = _theaters.get(key)
    if rec is None:
        print("THEATER '" + key + "' is not declared - known: "
              + (", ".join(theater_names()) or "none"))
    return rec


def theater_factions(count=None, key=None):
    """The active theater's factions, dominant first, or None when no theater is set.

    Returning None rather than [] is the whole backward-compatibility story: a caller reads
    "no theater" and keeps its own literal list, so stock missions are untouched.
    """
    rec = theater_get(key)
    if rec is None:
        return None
    factions = list(rec.get("factions") or [])
    if not factions:
        return None
    if count is None:
        return factions
    # Fewer factions than slots: cycle the roster rather than shorten the CURVE, so a
    # 3-faction theater in a 4-slot map still fills every slot.
    out = [factions[i % len(factions)] for i in range(count)]
    return out


def theater_art(key=None):
    """The active theater's race -> ART FACTION map ({} when unset).

    Feeds `RACE_ART`. Separate from the roster because the roster is in the MISSION's
    vocabulary and this is what those races LOOK like.
    """
    rec = theater_get(key)
    return dict(rec.get("art") or {}) if rec is not None else {}


def theater_faces(key=None):
    """The active theater's faction -> face-race map ({} when unset)."""
    rec = theater_get(key)
    return dict(rec.get("faces") or {}) if rec is not None else {}


def theater_music(key=None):
    """The active theater's MUSIC_SELECT, or None."""
    rec = theater_get(key)
    return (rec.get("music") or None) if rec is not None else None


def theater_pick_race(weights=None, names=None, key=None):
    """Pick one race from the active theater, honoring ``weights`` as the slot curve.

    Returns None when no theater is set - the caller then keeps its own literal list, which
    is what leaves stock missions byte-identical.

    ``weights`` is the MAP's curve (siege's ``diff_weight[DIFFICULTY]``, say). A theater that
    declared its own ``Weights:`` overrides it. Uses `random` directly so the mission seed
    applies, exactly as `fleet_table_pick_race` does.

    ``names`` is the CALLER'S own race list, and passing it matters for two reasons:

      * THE RESULT COMES BACK IN THE CALLER'S SPELLING. LM branches on the literal
        (`if enemy1 == "Kralien":`) to choose an enemy station type, so returning the
        lower-cased roster entry would make every branch fall through and the map would
        spawn no enemy stations - silently, because a chain of ifs that all miss raises
        nothing.
      * A RACE THE CALLER DOES NOT KNOW FALLS BACK. If the theater rosters something this
        map has no branches for, returning None hands control back to the map's own list
        rather than half-applying a roster it cannot honor.
    """
    import random
    rec = theater_get(key)
    if rec is None:
        return None
    own = rec.get("weights") or []
    curve = list(own) if own else list(weights or [])
    factions = theater_factions(len(curve) if curve else None, key=key)
    if not factions:
        return None
    if not curve:
        pick = random.choice(factions)
    else:
        curve = curve[:len(factions)]
        while len(curve) < len(factions):
            curve.append(curve[-1] if curve else 1)
        pick = random.choices(factions, weights=curve)[0]
    _depth_check(rec, curve)
    if names:
        for n in names:
            if str(n).strip().lower() == pick:
                return n
        return None
    return pick


# ---------------------------------------------------------------------------
# the depth guard
# ---------------------------------------------------------------------------

MIN_HULLS_FOR_HEAVY_SLOT = 3
HEAVY_SLOT_SHARE = 0.25


def theater_player_faction(key=None):
    """The shipData faction the CREW's hulls should be drawn from, or None.

    Separate from the ``Art:`` map on purpose. That map says how the mission's own races
    are drawn, and `tsn` in it re-skins the friendly NPCs; this says what the PLAYERS fly,
    which is not always the same thing. A theater where the crew are pirates re-skins them
    to Orion while its allied `tsn` NPCs stay Federation.

    ART ONLY - it never moves anybody's side. See :func:`theater_player_side_key`.

    **The value is a shipData SIDE, and stock data splits the Federation across two of
    them**: `tsn` is the navy, `USFP` is the freighters and starbases. `Player Faction:
    USFP` therefore seats the crew in a science ship and a luxury liner - correct pairing,
    wrong side. Name the side whose WARSHIPS you want; for a mod that keeps its hulls under
    one side (the TNG pack's `Federation`) there is no such split to fall into.
    """
    rec = theater_get(key)
    if rec is None:
        return None
    value = rec.get("player_faction")
    return value or None


def theater_players(key=None):
    """Explicit per-slot hull keys the theater wants the crew in, or []."""
    rec = theater_get(key)
    if rec is None:
        return []
    return list(rec.get("players") or [])


def theater_player_side(key=None):
    """The COSTUME for the players' existing side: ``{name, color, icon}``, empties dropped.

    A re-dress, not a re-faction. The side KEY is untouched, so diplomacy, `side_are_enemies`,
    every `//comms` gate and every station-friendliness lookup keep working exactly as the
    mission wrote them - only what the crew is called and coloured changes. That is what
    makes "the players are pirates tonight" cost nothing.
    """
    rec = theater_get(key)
    if rec is None:
        return {}
    out = {}
    for field, name in (("player_side_name", "name"),
                        ("player_side_color", "color"),
                        ("player_side_icon", "icon")):
        value = rec.get(field)
        if not value:
            continue
        if name == "icon":
            # An icon index is an int wherever it lands (side_set_side_icon_index takes
            # one), but the two parse paths disagree on type: a fence handler hands over a
            # string, the section reader an already-typed value.
            try:
                value = int(str(value).strip())
            except ValueError:
                continue
        out[name] = value
    return out


def theater_player_side_key(key=None):
    """Always None, and says so out loud when a theater asked for one.

    ``Player Side Key:`` would move the crew onto a different DIPLOMATIC side, and the
    missions are not ready for it: LegendaryMissions carries around 45 literal `tsn` sites
    across maps, fleets, consoles and prefabs, and `spawn_players` places crews via
    ``side_members_set(side) & role("station")`` - so a raider crew with no raider station
    is simply never placed, with nothing logged.

    Refused rather than half-applied. A theater that moved the key would look like it
    worked right up to the point where the crew spawned nowhere. Use the costume fields
    (:func:`theater_player_side`) for the look; the key waits on the de-hardcoding pass.
    """
    rec = theater_get(key)
    if rec is None:
        return None
    asked = rec.get("player_side_key")
    if asked:
        name = rec.get("key")
        if name not in _side_key_warned:
            _side_key_warned.add(name)
            print("theater '" + str(name) + "': 'Player Side Key: " + str(asked)
                  + "' is NOT SUPPORTED yet and is being ignored - it would move the crew's"
                  + " diplomatic side, which the missions still hardcode. Use Player Side"
                  + " Name/Color/Icon to re-dress the existing side instead.")
    return None


def theater_hull_counts(key=None):
    """{faction: how many non-station hulls it has}, for the active theater."""
    from .ship_data import filter_ship_data_by_side
    art = theater_art(key)
    out = {}
    for race in (theater_factions(key=key) or []):
        # Count the hulls of what the race LOOKS like, not of the race name: the roster is
        # in the mission's vocabulary (`kralien`), and it is the mapped faction whose hull
        # count decides whether a heavy slot will be repetitive.
        side = art.get(race, race)
        out[race] = len(filter_ship_data_by_side(None, side, "ship", ret_key_only=True) or [])
    return out


def theater_depth_report(weights=None, key=None):
    """Factions given a heavy slot they do not have the hulls to fill.

    Returns ``[(faction, hulls, share)]``. Empty is good.

    THIS IS THE FAILURE THAT HIDES. Nothing errors when a one-hull faction takes the 70%
    slot; the same ship simply turns up for the rest of the night, and that reads as broken
    art rather than as a wrong roster.
    """
    rec = theater_get(key)
    if rec is None:
        return []
    # No ship table loaded yet means every faction counts 0, which would report EVERY
    # roster as too thin. "Cannot judge" is not "is broken" - stay quiet.
    from .ship_data import ship_data_is_loaded
    if not ship_data_is_loaded():
        return []
    own = rec.get("weights") or []
    curve = list(own) if own else list(weights or [])
    factions = theater_factions(len(curve) if curve else None, key=key)
    if not factions:
        return []
    if not curve:
        curve = [1] * len(factions)
    while len(curve) < len(factions):
        curve.append(curve[-1] if curve else 1)
    total = float(sum(curve)) or 1.0
    counts = theater_hull_counts(key=key)
    out = []
    for f, w in zip(factions, curve):
        share = w / total
        n = counts.get(f, 0)
        if share >= HEAVY_SLOT_SHARE and n < MIN_HULLS_FOR_HEAVY_SLOT:
            out.append((f, n, share))
    return out


def _depth_check(rec, curve):
    """Report a thin faction in a heavy slot ONCE per mission, per theater."""
    key = str(rec.get("key") or "")
    if key in _depth_warned:
        return
    _depth_warned.add(key)
    for f, n, share in theater_depth_report(weights=curve, key=key or None) or []:
        print("theater '" + key + "': faction '" + f + "' holds "
              + format(share, ".0%") + " of the roster but has only " + str(n)
              + " hull(s) - every one of its ships will be the same model")
