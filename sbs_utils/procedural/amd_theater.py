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
import re

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


def _weights(value):
    """A weight row: ``{race: share}`` when keyed, ``[share, ...]`` when positional.

    KEYED IS THE REAL FORM. ``kralien:70, torgoth:10`` names who gets what, so the row has
    no length and no order to get wrong. The positional form is what the maps used to pass -
    a bare ``70, 10, 10, 10`` zipped against a race list somewhere else - and is still read
    so existing theaters and callers keep working.

    Told apart by a colon, because a race name cannot contain one.
    """
    text = value if isinstance(value, str) else ", ".join(str(v) for v in (value or []))
    if ":" not in str(text):
        return _numbers(value)
    out = {}
    for item in _csv(text):
        k, sep, v = item.partition(":")
        if not sep or not k.strip():
            continue
        try:
            out[k.strip()] = float(v.strip())
        except ValueError:
            continue
    return out


# `Weights 5:` / `Weights Tier 5:` - the label reaches a handler lowercased with its spaces
# intact, so the tier is read off the text rather than off an underscored key.
_TIER_RE = re.compile(r"^weights?(?:\s+tier)?\s+(\d+)$")


# Every fence label a theater understands, in the normalized form the handler sees
# (lowercased, spaces -> underscores). Kept beside the handler because it has to move with
# it: a label accepted there and missing here would be reported as a typo.
_KNOWN_FIELDS = frozenset((
    "races", "factions", "enemies", "roster",
    "weights", "weights_add", "weight_tiers", "art", "hulls", "faces", "face",
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
        # The label arrives lowercased with its SPACES INTACT (`amd_parse_facts` says so),
        # so every multi-word branch below was unreachable and those fields only ever landed
        # via the parser's own fallback. Normalizing here makes the branches real - and is
        # what lets `Weights Add:` be typed rather than left as a raw string.
        label = str(label).strip().lower()
        tier = _TIER_RE.match(label)
        if tier is not None:
            data.setdefault("weight_tiers", {})[int(tier.group(1))] = _weights(value)
            return True
        label = label.replace(" ", "_")
        if label in ("races", "factions", "enemies", "roster"):
            data["factions"] = _csv(value)
        elif label == "weights":
            data["weights"] = _weights(value)
        elif label in ("weights_add", "add_weights"):
            data["weights"] = _weights(value)
            data["weights_add"] = True
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
                "weight_tiers": data.get("weight_tiers") or {},
                "weights_add": bool(data.get("weights_add")),
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
        # A theater has a roster if it NAMES races anywhere: in `Races:`, or as the keys of
        # any keyed weight row. Requiring `Races:` specifically would refuse a theater whose
        # ladder already names every race it fields - which is the whole point of keyed
        # weights, and would have made the stock ladder unselectable.
        has_roster = bool(r.get("factions"))
        if not has_roster:
            rows = list((r.get("weight_tiers") or {}).values())
            own = r.get("weights")
            if isinstance(own, dict):
                rows.append(own)
            has_roster = any(isinstance(row, dict) and row for row in rows)
        if not has_roster:
            # A roster with no races cannot be selected, and registering it silently would
            # make `THEATER=x` look accepted while changing nothing.
            print("theater '" + key + "' declares no races - ignored. Name them in "
                  "`Races:` or as the keys of a `Weights:` row")
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


def theater_get_list():
    """Every declared theater record, in key order.

    The list an operator control is built from - the same shape `music_get_list` and
    `crew_get_list` hand the server panel, so a mod that ships theaters shows up in the
    picker without the panel knowing anything about it.
    """
    return [_theaters[k] for k in sorted(_theaters)]


def theater_display_name(key=None):
    """A theater's display name, falling back to its key. Empty string when unset."""
    rec = theater_get(key)
    if rec is None:
        return ""
    return str(rec.get("name") or rec.get("key") or "")


def theater_find(spec):
    """Resolve a KEY or a DISPLAY NAME to a theater key. None when nothing matches.

    An operator control shows display names ("Dominion War") while the `THEATER` setting is
    a key (`dominion_war`), so something has to translate. Accepts either, case- and
    space-insensitively, so a profile that already writes the key keeps working and a
    dropdown selection resolves too.
    """
    if not spec:
        return None
    want = str(spec).strip().lower()
    if not want or want in ("none", "random", ""):
        return None
    if want in _theaters:
        return want
    for key, rec in _theaters.items():
        if str(rec.get("name") or "").strip().lower() == want:
            return key
    # Last chance: a key written with spaces instead of underscores.
    squashed = want.replace(" ", "_")
    return squashed if squashed in _theaters else None


def theater_get(key=None):
    """One theater record by key, or the ACTIVE one when key is None. None when unset."""
    if key is None:
        # SHARED VARIABLE FIRST, then the setting. Both live-selection paths write a shared
        # var and neither would work otherwise: the server panel's Theater dropdown sets
        # `shared THEATER`, and `map_apply_defaults` publishes a map's `Defaults: THEATER:`
        # the same way. `settings_get_defaults()` is a CACHED merge of yaml + profile and
        # never sees either of them, so reading only that made a theater selectable in
        # exactly one place - a profile file - and silently ignored everywhere else.
        key = None
        try:
            from .execution import get_shared_variable
            key = get_shared_variable("THEATER", None)
        except Exception:
            key = None
        if key is None:
            from .settings import settings_get_defaults
            key = settings_get_defaults().get("THEATER") or ""
    if not str(key).strip():
        return None
    # "None" is what the operator's dropdown says when no theater is wanted, and what
    # `theater_selected_name()` seeds the shared var with. Treat it as the choice it is:
    # warning about it named the default setting as a mistake, once per read, all game.
    if str(key).strip().lower() in ("none", "random", ""):
        return None
    # Resolve through theater_find, so the variable may hold EITHER a key or a display
    # name. A Properties dropdown binds `var="THEATER"` to whatever the operator picked,
    # and that is the display name; a profile writes the key. Both have to land here.
    resolved = theater_find(key)
    if resolved is not None:
        return _theaters[resolved]
    key = str(key).strip().lower()
    rec = _theaters.get(key)
    if rec is None:
        print("THEATER '" + key + "' is not declared - known: "
              + (", ".join(theater_names()) or "none"))
    return rec


def theater_factions(count=None, key=None, eligible=None):
    """The active theater's factions, dominant first, or None when no theater is set.

    Returning None rather than [] is the whole backward-compatibility story: a caller reads
    "no theater" and keeps its own literal list, so stock missions are untouched.

    A theater with only a ``Weights:`` row and no ``Races:`` line still has a roster - the
    keys of that row - so a keyed theater does not have to say its races twice.

    ``eligible`` drops races the caller cannot use (see `theater_pick_race`).

    ``count`` TRUNCATES. It used to cycle the roster to fill the caller's slots, which quietly
    gave the first race the surplus weight - a 3-race roster under ``[70,10,10,10]`` made it
    80%, not 70. Nothing in the library asks for a count any more; the argument stays for
    callers that pass one.
    """
    rec = theater_get(key)
    if rec is None:
        return None
    factions = list(rec.get("factions") or [])
    if not factions:
        # A keyed theater need not repeat itself: the weight rows already name every race.
        seen = []
        rows = list((rec.get("weight_tiers") or {}).values())
        own = rec.get("weights")
        if isinstance(own, dict):
            rows.append(own)
        for row in rows:
            for r in (row or {}):
                if r not in seen:
                    seen.append(r)
        factions = seen
    if eligible is not None:
        factions = [f for f in factions if eligible(f)]
    if not factions:
        return None
    if count is None:
        return factions
    return factions[:count]


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


def theater_weights(difficulty=None, key=None):
    """The active theater's weight row as ``{race: share}``, or None.

    Reads, strongest first: the tier matching ``difficulty`` (``Weights 5:``), then the
    single ``Weights:`` row, then nothing. A positional row is NOT returned here - it has no
    race names in it, so it cannot answer "what does each race get" on its own; that form is
    handled in :func:`theater_pick_race` against the roster.

    ``difficulty`` is the 1-based tier a map reads (LM's DIFFICULTY), clamped into whatever
    tiers the theater actually declared, so a theater that ships fewer than eleven cannot be
    fallen off either end of.
    """
    rec = theater_get(key)
    if rec is None:
        return None
    tiers = rec.get("weight_tiers") or {}
    if tiers and difficulty is not None:
        try:
            want = int(difficulty)
        except (TypeError, ValueError):
            want = None
        if want is not None:
            keys = sorted(tiers)
            want = max(keys[0], min(keys[-1], want))
            # Clamped, not interpolated: a theater declaring tiers 1 and 11 and asked for 5
            # gets tier 1, which is the row its author actually wrote.
            row = tiers.get(want)
            if row is None:
                row = tiers[min(keys, key=lambda k: abs(k - want))]
            if isinstance(row, dict) and row:
                return dict(row)
    own = rec.get("weights")
    if isinstance(own, dict) and own:
        return dict(own)
    return None


def _positional_row(factions, curve):
    """Zip a POSITIONAL curve onto a roster, fixing the three ways it used to go wrong.

    Measured against the shipped data before this existed:

      * ROSTER LONGER THAN THE CURVE silently dropped the tail. borderwar and deepstrike pass
        a 3-long curve, every TNG theater rosters 4, and the fourth race - ximni in all five
        of them - never spawned at all. The last curve weight is now SHARED among the races
        past its end, so nobody gets zero and the head keeps its share.
      * ROSTER SHORTER THAN THE CURVE cycled the roster to fill the slots, which handed the
        first race the surplus: a 3-race roster under ``[70,10,10,10]`` made it 80%, not 70.
        The curve is truncated instead, and the row normalizes by its own sum.
      * NO CURVE AT ALL is uniform, which is correct and unchanged - singlefront passes none.

    Returns ``{race: share}``.
    """
    if not factions:
        return {}
    if not curve:
        return {f: 1.0 for f in factions}
    curve = [float(w) for w in curve]
    if len(factions) > len(curve):
        head = curve[:-1]
        spread = len(factions) - len(head)
        tail = [curve[-1] / spread] * spread
        curve = head + tail
    else:
        curve = curve[:len(factions)]
    return {f: w for f, w in zip(factions, curve)}


def theater_pick_race(weights=None, names=None, key=None, difficulty=None, eligible=None):
    """Pick one race from the active theater. None when no theater is set.

    Returns None rather than a default so the caller keeps its own behavior, which is what
    leaves a mission with no theater untouched.

    ``difficulty`` selects a ``Weights <n>:`` tier - the ladder that used to be a table of
    positional rows in the map. ``eligible`` is a predicate the map supplies for what the
    race must be able to DO: borderwar and deepstrike pass `race_has_station`, because they
    build enemy starbases and not every race has one. That constraint was previously written
    out by hand as a shortened race list in each of those maps.

    ``weights`` is the caller's own row, used only when the theater declares none. A theater
    row REPLACES it unless the theater said ``Weights Add:``, in which case the two merge -
    and merging rescales everyone, because these are relative shares and not percentages.

    ``names`` is the caller's spelling of the races it knows. It is NOT a gate: a race the
    theater rosters is returned even when the caller has never heard of it, because the whole
    point is that a roster is no longer limited to what one map hardcoded. It still supplies
    the SPELLING when it has one, so a caller that does compare against its own literals gets
    a match.
    """
    import random
    rec = theater_get(key)
    if rec is None:
        return None

    row = theater_weights(difficulty, key=key)
    if row is not None and rec.get("weights_add") and weights:
        merged = _positional_row(theater_factions(key=key) or [], list(weights))
        merged.update(row)
        row = merged

    if row is None:
        own = rec.get("weights")
        curve = list(own) if isinstance(own, list) and own else list(weights or [])
        factions = theater_factions(key=key)
        if not factions:
            return None
        row = _positional_row(factions, curve)

    # Eligibility last, so it filters whatever the row turned out to be. A race the map
    # cannot use is dropped rather than picked and then failed on.
    if eligible is not None:
        row = {r: w for r, w in row.items() if eligible(r)}
    row = {r: w for r, w in row.items() if w > 0}
    if not row:
        return None

    picks = list(row)
    pick = random.choices(picks, weights=[row[p] for p in picks])[0]
    _depth_check(rec, row)

    if names:
        for n in names:
            if str(n).strip().lower() == str(pick).strip().lower():
                return n
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


def theater_name_list():
    """Dropdown options string: ``'None, <Display>, ...'``.

    Matches the idiom a map's ``Properties:`` block already uses for its own pickers (see
    siege's ``BOSS_LIST``), so a map opts in with two lines and no new concepts::

        default shared THEATER      = theater_selected_name()
        default shared THEATER_LIST = theater_name_list()
        ...
        Theater: 'gui_drop_down("$text: {THEATER};list: {THEATER_LIST}", var="THEATER")'

    Built from what is DECLARED, so a mod that ships theaters shows up without the map
    knowing about it - and with none declared the list is just "None", which is the honest
    control for "there is nothing to choose".
    """
    return ", ".join(["None"] + [str(r.get("name") or r.get("key")) for r in theater_get_list()])


def theater_selected_name():
    """The active theater's DISPLAY name, or ``"None"``.

    What a map seeds its shared var from. Called before any shared value exists, it falls
    through to the setting - so a profile's ``THEATER: dominion_war`` becomes the dropdown's
    starting selection instead of being overwritten with "None" by the `default`.
    """
    return theater_display_name() or "None"


def theater_hull_counts(key=None):
    """{faction: how many non-station hulls it has}, for the active theater."""
    from .ship_data import _side_split
    from .races import race_hull_count
    art = theater_art(key)
    out = {}
    for race in (theater_factions(key=key) or []):
        # Count the hulls of what the race LOOKS like, not of the race name: a roster entry
        # may be re-skinned by `Art:`, and it is the mapped faction whose hull count decides
        # whether a heavy slot will be repetitive.
        #
        # NOT filtered on the `ship` role, which is what this used to do - the exact mistake
        # `_side_split` was written to avoid. Plenty of hulls carry no `ship` role
        # (`arvonian_fighter` is `cockpit,fighter`), so the filter undercounted a faction and
        # the guard then false-reported a perfectly deep roster as too thin.
        # By SIDE first, defaulting to the race's own name, because that is how the stock
        # races and every `Art:` target are addressed. A mod race that is only ever an
        # ORIGIN - the point of the races registry - has no side of that name, and answers
        # here instead of counting zero.
        side = art.get(race, race)
        count = len(_side_split(side)[0])
        out[race] = count if count else race_hull_count(race)
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
    # `weights` may be the keyed row the pick actually used, or a positional curve from an
    # older caller. Both end up as {race: share} so the report reads one shape.
    if isinstance(weights, dict) and weights:
        row = dict(weights)
    else:
        own = rec.get("weights")
        curve = list(own) if isinstance(own, list) and own else list(weights or [])
        row = theater_weights(key=key)
        if row is None:
            row = _positional_row(theater_factions(key=key) or [], curve)
    if not row:
        return []
    total = float(sum(row.values())) or 1.0
    counts = theater_hull_counts(key=key)
    out = []
    for f, w in row.items():
        share = w / total
        n = counts.get(f, race_hull_count_safe(f))
        if share >= HEAVY_SLOT_SHARE and n < MIN_HULLS_FOR_HEAVY_SLOT:
            out.append((f, n, share))
    return out


def race_hull_count_safe(race):
    """A race's mobile hull count, or 0 when the ship table cannot answer."""
    try:
        from .races import race_hull_count
        return race_hull_count(race)
    except Exception:
        return 0


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
