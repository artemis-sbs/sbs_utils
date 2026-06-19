# The science module

Control and respond to science console scanning and intel display.

## Overview

The science module provides helpers for the science console: setting what information is shown when an object is scanned, controlling scan-data visibility, and emitting the scan event programmatically.

`science_add_scan_data` attaches key→value intel entries to an object that appear on the science console when the player scans it. `science_clear_scan_data` removes them.

The `//focus/science` route fires when the science console focuses on an object. The selected object's ID is in `EVENT.selected_id`.

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    == setup ==
        science_add_scan_data(enemy_id, "Ship Class", "Battlecruiser")
        science_add_scan_data(enemy_id, "Threat Level", "High")
        science_add_scan_data(enemy_id, "Shields", "Online")
        ->END

    //focus/science
        if EVENT.selected_id == enemy_id: jump enemy_scanned

    == enemy_scanned ==
        comms_broadcast(ship_id, "Science: Enemy battlecruiser detected!", "red")
        ->END
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.science import science_add_scan_data, science_clear_scan_data

    science_add_scan_data(enemy_id, "Ship Class", "Battlecruiser")
    science_add_scan_data(enemy_id, "Threat Level", "High")
    science_clear_scan_data(enemy_id)
    ```

## API

::: sbs_utils.procedural.science
