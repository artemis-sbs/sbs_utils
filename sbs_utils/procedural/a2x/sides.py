"""Legacy-style factions: 2.8 ``sideValue`` -> Cosmos sides + diplomacy.

2.8 has no diplomacy table. A ship's ``sideValue`` **is** its faction, and the engine
applies one implicit rule: two objects with different non-zero sideValues are hostile,
the same value is friendly, and ``0`` means "no side" (neutral to everything). Nothing
in a 2.8 mission ever declares that -- it is baked into the engine.

Cosmos resolves allegiance the other way round, through registered SIDE agents linked
by ``side_ally`` / ``side_hostile``. A converted mission must therefore **declare** what
2.8 left implicit, or every ``side_are_enemies`` test is False -- which is quiet but
fatal, because the LegendaryMissions NPC brains gate the trigger on it::

    shoot = side_are_enemies(BRAIN_AGENT_ID, _target) or force_shoot

so undeclared sides give you ships that chase and never fire, a Science console with no
allied/hostile split, and grey sensor contacts.

:func:`declare_sides` is that declaration. Hand it the sideValues a mission actually
uses; it creates one Cosmos side per value and applies the 2.8 rule pairwise. Call it
**once, before any spawn**, so the ``a2x_create_*`` side lookups resolve (same ordering
requirement LegendaryMissions has for its own ``//shared/signal/create_sides`` route).

Side KEY vs combat ROLE -- these are different jobs and both are needed:

* the **key** (``side_key``) carries identity and diplomacy. It stays 2.8-faithful, one
  key per sideValue, so an N-way mission (MISS_The_Arena puts eight player ships on
  sideValues 4..11, each with its own station) keeps all N factions mutually hostile
  instead of collapsing onto three LegendaryMissions keys.
* the **role** ``raider`` is only a combat SCOPE tag, added by the caller at spawn time
  (``a2x_create_enemy(..., side="enemy, raider")`` -- ``spawn_common`` splits the string
  and the first entry is the key, the rest are roles). LegendaryMissions intersects it
  with diplomacy rather than trusting it alone, e.g. the docking addon's enemies-near
  gate: ``side_hostile_members(DOCKING_PLAYER_ID, "raider")``. Tagging without declaring
  sides achieves nothing -- diplomacy is what makes a ship an enemy.
"""

# 2.8 sideValue -> Cosmos side key. The single source of truth for the mapping: the
# arme2cosmos emitter mirrors it when writing literals, and props.set_side_value (the
# runtime `set_side_value` reassignment) imports side_key from here so a mid-mission
# defection can only ever land on a side this module declared.
_SIDE_KEY = {0: "neutral", 1: "enemy", 2: "friendly"}

# Cosmetic defaults, matching the LegendaryMissions sides.amd palette (tsn #07F /
# raider #F00 / civ white) so converted missions read the same on the 2D map.
_SIDE_NAME = {0: "Neutral", 1: "Enemy", 2: "Friendly"}
_SIDE_COLOR = {0: "#FFF", 1: "#F00", 2: "#07F"}

# Colors for synthesized sides (2.8 sideValue 3+, e.g. a multi-team PvP mission), cycled.
_EXTRA_COLORS = ["#FA0", "#0F0", "#F0F", "#0FF", "#FF0", "#F80", "#8F0", "#08F"]


def side_key(side_value):
    """2.8 ``sideValue`` -> the Cosmos side key for that faction.

    0/1/2 keep the readable legacy names (``neutral``/``enemy``/``friendly``); 3 and up
    get a synthesized ``side_N`` so an N-faction mission stays N factions. Values are
    NOT collapsed onto the three LegendaryMissions keys -- see the module docstring.
    """
    v = int(side_value)
    return _SIDE_KEY.get(v, f"side_{v}")


def side_name(side_value):
    """A display name for a 2.8 sideValue (shown on the 2D map / sensor contacts)."""
    v = int(side_value)
    return _SIDE_NAME.get(v, f"Side {v}")


def side_color(side_value):
    """An icon color for a 2.8 sideValue, matching the LegendaryMissions palette."""
    v = int(side_value)
    c = _SIDE_COLOR.get(v)
    if c is not None:
        return c
    return _EXTRA_COLORS[(v - 3) % len(_EXTRA_COLORS)]


def declare_sides(side_values, names=None, colors=None,
                  hostile_color=None, neutral_color=None):
    """Declare one Cosmos side per 2.8 ``sideValue`` and apply 2.8's implicit diplomacy.

    Creates a side for every value in ``side_values`` (via ``side_create``, so each is
    allied to itself), then relates every pair by the 2.8 rule:

    * different non-zero values -> ``HOSTILE``
    * either value is 0 ("no side") -> ``NEUTRAL``

    Idempotent -- ``side_create`` reconfigures an existing side in place, so calling it
    twice (or alongside a mission that already declared a side) is safe. Re-declaring also
    RE-ISSUES every engine-side write (icon colours, self-ally, pairwise relations,
    diplomacy colours), so a second call fully repairs an engine table that lost the
    first one; that is what a converted mission's re-assert loop relies on.

    Args:
        side_values (iterable[int]): The 2.8 sideValues the mission actually uses.
            Order is irrelevant; duplicates are ignored.
        names (dict[int, str], optional): Per-value display name overrides.
        colors (dict[int, str], optional): Per-value icon color overrides.
        hostile_color (str, optional): Map colour for HOSTILE contacts. Defaults to
            LegendaryMissions' ``"#F00"``.
        neutral_color (str, optional): Map colour for NEUTRAL contacts. Defaults to
            LegendaryMissions' ``"#077"``.

    Returns:
        dict[int, int]: 2.8 sideValue -> the created side agent's ID.

    Example:
        A mission whose objects carry sideValue 1 (enemies) and 2 (player + station)::

            a2x_declare_sides([1, 2])
    """
    from sbs_utils.procedural.sides import side_create, side_set_relations
    from sbs_utils.helpers import FrameContext

    names = names or {}
    colors = colors or {}

    # dict-not-set: dedupe but keep a stable order, so the relation pass below (and any
    # log of it) is deterministic rather than hash-ordered.
    values = list(dict.fromkeys(int(v) for v in side_values))

    ids = {}
    for v in values:
        ids[v] = side_create(side_key(v),
                             names.get(v, side_name(v)),
                             color=colors.get(v, side_color(v)))

    sbs = FrameContext.context.sbs
    if sbs is None:
        # No engine context (e.g. a compile-time/mock pass): the sides exist, but
        # DIPLOMACY constants aren't reachable, so skip the relation pass.
        return ids

    # Re-assert the SELF-ally pair on every call, not just at creation. side_ensure seeds
    # it, but only for a side it actually creates -- so on a re-declare (the whole point of
    # the re-assert loop a converted mission runs) the same-side ALLIED relation is never
    # re-issued to the engine. If the first declaration's writes were lost (they are, when
    # anything issues them in the same frame as sim_create), the engine's table keeps
    # same-side pairs at UNKNOWN for the rest of the mission and no amount of re-declaring
    # repairs it. Cheap and idempotent, so just always send it.
    for v in values:
        side_set_relations(side_key(v), side_key(v), sbs.DIPLOMACY.ALLIED)

    for i, a in enumerate(values):
        for b in values[i + 1:]:
            # 2.8: sideValue 0 is "no side" -- present, but nobody's enemy.
            relation = (sbs.DIPLOMACY.NEUTRAL if a == 0 or b == 0
                        else sbs.DIPLOMACY.HOSTILE)
            side_set_relations(side_key(a), side_key(b), relation)

    # Contacts are drawn by RELATION, and those colours stay unset until a mission
    # configures them -- so correctly-hostile ships still rendered in the neutral
    # colour and "enemies looked neutral" on the map. LegendaryMissions sets these in
    # maps/watch_for_end.mast, which is its own mission content and NOT one of the
    # shipped mastlibs, so a converted mission never inherited them. Declaring the
    # relations and not colouring them is exactly the half-done state that reads as a
    # diplomacy bug, so it belongs here with the rest of the declaration.
    set_diplomacy_colors(hostile_color or _DIPLOMACY_HOSTILE_COLOR,
                         neutral_color or _DIPLOMACY_NEUTRAL_COLOR)
    return ids


# Contact colours by DIPLOMACY relation, matching LegendaryMissions' own values.
_DIPLOMACY_HOSTILE_COLOR = "#F00"
_DIPLOMACY_NEUTRAL_COLOR = "#077"


def set_diplomacy_colors(hostile_color=_DIPLOMACY_HOSTILE_COLOR,
                         neutral_color=_DIPLOMACY_NEUTRAL_COLOR):
    """Set the map colours the engine draws contacts with, by RELATION.

    Split out of :func:`declare_sides` and callable on its own, because these writes are
    frame-sensitive. ``sim`` here is ``FrameContext.context.sim`` -- the handle the engine
    passed into ``cosmos_event_handler`` at the top of the CURRENT event. ``sim_create()``
    replaces the simulation but cannot refresh that handle (the engine's ``sbs`` module
    exposes no module-level ``sim``), so anything calling this in the same frame as
    ``sim_create()`` writes to the pre-``sim_create`` simulation and the colours are lost
    silently -- contacts draw as UNKNOWN, i.e. grey.

    That was the real cause of the long-standing "converted missions have no diplomacy
    colours" bug: LegendaryMissions' server console ran ``sim_create()`` and
    ``signal_emit("create_sides")`` in one frame, so the whole engine-facing half of
    ``declare_sides`` went to a dead simulation. server_console now yields a frame between
    the two. The earlier "the engine does not retain early writes, re-apply at ~3s"
    reading was a misdiagnosis: the ~1s re-apply looked like it failed only because it
    re-issued the COLOURS alone, leaving the relations still missing.

    Safe to call repeatedly; converted missions still re-assert on a short loop so they
    keep working against an older LegendaryMissions library that lacks the frame yield.

    Returns True if the colours were applied, False if there was no sim to apply them to.
    """
    from sbs_utils.helpers import FrameContext

    sbs = FrameContext.context.sbs
    sim = FrameContext.context.sim
    if sbs is None or sim is None:
        return False
    sim.set_diplomacy_color(sbs.DIPLOMACY.HOSTILE, hostile_color)
    sim.set_diplomacy_color(sbs.DIPLOMACY.NEUTRAL, neutral_color)
    return True
