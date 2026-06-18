# The popup system

Context menus shown when a player clicks or hold-clicks an object in the 2D/3D views.

## Overview

Popups work like a mini comms tree. When a player clicks or hold-clicks in the science, comms, comms2d, or weapons view, the engine fires an event that creates a `PopupPromise`. The promise walks a route tree rooted at `//popup/<console>` (e.g. `//popup/science`) and displays the available buttons as a hold-menu on the client.

Each button in the route leads to a sub-path, just like comms. Use `popup_navigate` from within a popup handler to programmatically change which buttons are shown.

The variables `SCIENCE_ORIGIN_ID`, `SCIENCE_SELECTED_ID`, and `SCIENCE_POPUP_ID` (or the equivalent `COMMS_*`/`WEAPONS_*` variants) are set when the popup fires so the handler knows which ship, which object was clicked, and what was under the cursor.

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    //popup/science
    * "Scan"
        signal_emit("scan_object", {"TARGET_ID": SCIENCE_SELECTED_ID})
    * "Attack"
        target(ship_id, SCIENCE_SELECTED_ID)
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.popup import popup_navigate

    # Redirect to a different set of buttons inside a popup handler
    popup_navigate("popup/science/follow_up")
    ```

## Console popup routes

| Route | Triggers on |
|---|---|
| `//popup/science` | Science hold-click |
| `//popup/comms` | Comms hold-click |
| `//popup/comms2d` | 2D comms hold-click |
| `//popup/weapons` | Weapons hold-click |

## API

::: sbs_utils.procedural.popup
