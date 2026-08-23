# The popup system

Context menus shown when a player clicks or hold-clicks an object in the 2D/3D views.

## Overview

Popups work like a mini comms tree. When a player clicks or hold-clicks in the science, comms, comms2d, or weapons view, the engine fires an event that creates a `PopupPromise`. The promise walks a route tree rooted at `//popup/<console>` (e.g. `//popup/science`) and displays the available buttons as a hold-menu on the client.

Each button in the route leads to a sub-path, just like comms. Use `popup_navigate` from within a popup handler to programmatically change which buttons are shown.

### Three ids, and which one you want

Three variables are set when the popup fires - `SCIENCE_ORIGIN_ID`, `SCIENCE_SELECTED_ID` and `SCIENCE_POPUP_ID`, or the equivalent `COMMS_*`/`WEAPONS_*` variants. They are **not interchangeable**, and reaching for the wrong one is the single most common popup bug:

| Variable | What it is |
|---|---|
| `<CONSOLE>_ORIGIN_ID` | The ship the client is flying. |
| `<CONSOLE>_SELECTED_ID` | The console's **standing selection** - whatever it had targeted before the hold. **0** when it has none. |
| `<CONSOLE>_POPUP_ID` | The object **under the cursor** when the player held. **0** for a hold on empty space (`<CONSOLE>_POPUP_POINT` then carries the point). |

**A menu that acts on the object the player clicked wants `POPUP_ID`.** Gated on `SELECTED_ID` instead, it silently acts on the console's target rather than on what was clicked, and offers nothing at all when nothing is selected - which reads as a menu that only works sometimes. `SELECTED_ID` is right only when the selection is genuinely part of the interaction, as in "give THIS ship (selected) an order about THAT object (popup)".

There is one `PopupPromise` per (origin, selection) pair, and `POPUP_ID` changes with each hold - so one promise serves however many objects the player holds on while the selection stays put.


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
