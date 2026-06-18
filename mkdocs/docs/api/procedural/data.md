# The data module

Utilities for randomising spawn templates and other structured data dicts.

## Overview

`data_choose_value_from_template` takes a template dict where each value is either a list (one element chosen at random) or a dict of parallel lists (a single random index is picked and applied consistently across all inner lists). This keeps related attributes — for example a name and a ship type — coherent when randomly selecting.

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    template = {
        "name": ["Raider", "Marauder", "Corsair"],
        "ship": ["cruiser", "frigate", "fighter"],
    }
    chosen = data_choose_value_from_template(template)
    log(f"Spawning {chosen['name']} in a {chosen['ship']}")
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.data import data_choose_value_from_template

    template = {
        "name": ["Raider", "Marauder", "Corsair"],
        "ship": ["cruiser", "frigate", "fighter"],
    }
    chosen = data_choose_value_from_template(template)
    # chosen == {"name": "Marauder", "ship": "frigate"}  (consistently paired)
    ```

## Parallel arrays (consistent index)

When a key maps to a dict of parallel lists, the same random index is used for all inner lists:

```python
template = {
    "unit": {
        "name": ["Alpha", "Beta", "Gamma"],
        "ship": ["cruiser", "frigate", "scout"],
        "side": ["tsn", "tur", "skaraan"],
    }
}
chosen = data_choose_value_from_template(template)
# e.g. chosen["unit"] == {"name": "Beta", "ship": "frigate", "side": "tur"}
#      All three values came from index 1.
```

## API

::: sbs_utils.procedural.data
