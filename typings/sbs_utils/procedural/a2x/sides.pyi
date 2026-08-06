def declare_sides (side_values, names=None, colors=None, hostile_color=None, neutral_color=None):
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
    
            a2x_declare_sides([1, 2])"""
def set_diplomacy_colors (hostile_color='#F00', neutral_color='#077'):
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
    
    Returns True if the colours were applied, False if there was no sim to apply them to."""
def side_color (side_value):
    """An icon color for a 2.8 sideValue, matching the LegendaryMissions palette."""
def side_key (side_value):
    """2.8 ``sideValue`` -> the Cosmos side key for that faction.
    
    0/1/2 keep the readable legacy names (``neutral``/``enemy``/``friendly``); 3 and up
    get a synthesized ``side_N`` so an N-faction mission stays N factions. Values are
    NOT collapsed onto the three LegendaryMissions keys -- see the module docstring."""
def side_name (side_value):
    """A display name for a 2.8 sideValue (shown on the 2D map / sensor contacts)."""
