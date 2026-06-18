# Sides system

Query and manage the faction/allegiance side of space objects.

## Overview

Every space object has a `side` string that the simulation uses for targeting and IFF (Identify Friend or Foe). Common side values are `"tsn"`, `"tur"`, `"tsc"`, `"skaraan"`, `"biomech"`, and `"unsc"`. The side is set at spawn time and can be changed in flight.

The side is automatically added as a role, so `role("tsn")` matches all TSN objects and can be combined with other role queries:

```python
tsn_stations = broad_test_around(pos, 5000) & role("tsn") & role("station")
```

`get_side_for_display` returns a human-readable faction name (e.g. `"TSN"` instead of `"tsn"`). `side_set` changes an object's side and the `side_changed` signal is emitted.

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    == check_side ==
        if get_side(target_id) == "tsc": jump enemy_detected
        if get_side(target_id) == "tsn": jump friendly_detected

    == defect ==
        side_set(npc_id, "tsn")
        log("Enemy ship has defected to TSN!")
        ->END
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.sides import side_set, get_side, get_side_for_display

    # Check faction
    if get_side(target_id) == "tsc":
        target(ship_id, target_id)

    # Change side mid-mission
    side_set(npc_id, "tsn")

    # Human-readable name
    name = get_side_for_display(target_id)  # e.g. "TSN"
    ```

## Common side values

| Side | Faction |
|---|---|
| `"tsn"` | Terran Stellar Navy |
| `"tur"` | Tur (hostile) |
| `"tsc"` | Terran Stellar Command (hostile in some missions) |
| `"skaraan"` | Skaraan |
| `"biomech"` | Biomech (Hegemony) |
| `"unsc"` | UNSC |

## API

::: sbs_utils.procedural.sides
