# The quest system

Track mission objectives and quest states attached to any agent or shared globally.

## Overview

Quests are data records stored on an agent's inventory under the key `__quests__`. Each quest has a unique string ID (supports `/`-separated nesting like `"main/patrol"`), a display name, a description, and a `QuestState`. When a quest changes state a signal is emitted (`quest_activated` or `quest_completed`) so other parts of the mission can react.

Quests can be attached to a specific player ship, a specific client console, or the shared game agent (`Agent.SHARED_ID`) for mission-wide tracking. `quest_flatten_list()` collects from all three sources and returns a flat list ready for display in a `gui_property_list_box`.

## Quest states

| State | Value | Meaning |
|---|---|---|
| `QuestState.IDLE` | 0 | Not yet started |
| `QuestState.ACTIVE` | 1 | In progress |
| `QuestState.SECRET` | 2 | Hidden from player |
| `QuestState.POSTING` | 3 | Job board posting |
| `QuestState.FAILED` | 98 | Failed |
| `QuestState.COMPLETE` | 99 | Completed |

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    == setup ==
        quest_add(ship_id, "patrol", "Patrol Sector 7", "Keep the peace in sector 7.")
        quest_set_key(ship_id, "patrol", "state", QuestState.ACTIVE)

    == on_patrol_done ==
        quest_complete(ship_id, "patrol")
        quest_set_key(ship_id, "patrol", "state", QuestState.COMPLETE)
        ->END
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.quest import quest_add, quest_set_key, quest_complete, QuestState

    quest_add(ship_id, "patrol", "Patrol Sector 7", "Keep the peace in sector 7.")
    quest_set_key(ship_id, "patrol", "state", QuestState.ACTIVE)
    # ... later ...
    quest_complete(ship_id, "patrol")
    quest_set_key(ship_id, "patrol", "state", QuestState.COMPLETE)
    ```

## Displaying quests

```
items = quest_flatten_list()
gui_property_list_box(items, style="area:0,0,100,100;")
```

## Loading quests from YAML

```
yaml_text = """
patrol:
  display_text: Patrol Sector 7
  description: Keep the peace.
  state: ACTIVE
rescue:
  display_text: Rescue the crew
  description: Find the survivors.
"""
quest_add_yaml(ship_id, yaml_text)
```

## API

::: sbs_utils.procedural.quest
