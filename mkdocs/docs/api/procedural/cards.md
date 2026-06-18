# The card system

Tilemap / ASCII-art map parsing for procedural world generation and room layouts.

## Overview

Cards are tile-based layouts defined in ASCII art or structured data. The card system parses these maps and provides helpers for reading tile data, placing objects based on tile positions, and querying tile contents. It is most commonly used for procedural dungeon-style or room-layout generation.

A card definition assigns each character in the ASCII map to a tile type with associated spawn rules. `card_get` retrieves a parsed card by name; `card_spawn` instantiates the card's objects into the simulation.

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    == setup ==
    layout = card_get("station_interior")
    card_spawn(layout, offset_x=1000, offset_z=2000)
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.cards.card import card_get, card_spawn

    layout = card_get("station_interior")
    card_spawn(layout, offset_x=1000, offset_z=2000)
    ```

## API

::: sbs_utils.cards.card
