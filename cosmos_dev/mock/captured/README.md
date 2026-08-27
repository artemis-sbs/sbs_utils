# Captured engine data

Raw readings taken from a live Artemis Cosmos engine through the dev queue
(`cosmos_dev/engine_driver`), kept so the mock's values can be traced to a source rather
than to somebody's memory.

**Why these are here at all.** The mock stands in for engine behavior the script-facing API
never exposes as data. Where that behavior is *derivable* — from shipData, from a documented
formula — the mock derives it. Where it is not, the only honest options are to capture it or
to leave the gap open, because a plausible-but-wrong value is worse than an absent one: it
makes a headless run look like it exercised something it did not.

| file | engine | what |
|---|---|---|
| `eng_controls_1.3.7.json` | 1.3.7 | `eng_control_label` / `eng_control_type_index` and the `system_*` arrays for a `tsn_light_cruiser` player ship at spawn |

`eng_control_label` appears in no shipData key — the engine builds the table itself — so it
had to be read from a running engine. Before this the mock had no controls at all, and every
`range(30)` walk over the array (LegendaryMissions autoplay's power loop and its can-turn
check, plus `set_engineering_value`) iterated zero times headless and silently did nothing.

`tests/test_mock_eng_controls.py` asserts the mock still matches these values, so a drift in
either direction has to be deliberate.

## Re-capturing

The engine must not already be running — the driver kills every Artemis process on launch.
The capture script is `capture_eng.py` in the session scratchpad; the essentials are:
build the devqueue mastlib, declare it in a THROWAWAY copy of a mission (never the shipped
one), launch server-only with a map that spawns a player, then read the arrays over the
queue. A second local instance makes the engine assert, so server-only is not optional.
