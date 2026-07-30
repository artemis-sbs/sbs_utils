# GUI

Build screens and console layouts with the `gui_*` functions. A GUI task lays out
widgets, then suspends on `await gui()` until the player interacts; `on` handlers
react to changes and clicks.

<video controls loop width="640" height="480" src="../../media/gui_layout.mp4"></video>

!!! tip "Every control on this page is also running, in the Control Gallery"
    The [Control Gallery](control-gallery.md) is a mission that shows each widget live
    with **the source that built it** sliced out of its own file underneath — plus a
    Layout category for sizing, and a Traps category for the mistakes that produce a
    plausible-looking screen. Run it with `sbs debug control_gallery --map 0`.

## The shape of a GUI task

A console or screen is a label that builds a layout and then awaits input:

=== ":mast-icon: {{ab.m}}"
    ```
    @console/helm !0 ^5 "Helm"
        gui_console("helm")
        await gui()
    ```

`await gui()` presents the layout and suspends until the player interacts. Each
client should have exactly one main GUI task.

## Layout

Widgets are placed top to bottom into sections and rows.

=== ":mast-icon: {{ab.m}}"
    ```
    gui_section(style="area: 10, 10, 90, 90;")   # a positioned region (percent)
    gui_row("row-height: 2em;")                  # a new row
    """Some text"""                              # triple-quoted string = a text label
    """{count} ships"""                          # f-string style interpolation
    gui_blank()                                  # a spacer
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    gui_section(style="area: 10, 10, 90, 90;")
    gui_row("row-height: 2em;")
    gui_text("Some text")
    gui_blank()
    ```

## Buttons

Inside `await gui()`, `*` is a one-shot button (consumed after a click) and `+` is
sticky (stays visible). Or create a button widget with `gui_button` and react with
an `on` handler.

=== ":mast-icon: {{ab.m}}"
    ```
    await gui():
        * "Launch":                 # one-shot
            launch_fighter()
        + "Status" //comms/status   # sticky, navigates a route

    # or, as a widget with a handler:
    on gui_message(gui_button("Refresh")):
        refresh_panel()
    ```

## Widgets

Most widgets take a style string and bind to a variable with `var=`. Handle
changes with `on gui_message(widget):` (fires when the value changes) or
`on gui_click(widget):` (fires on click, for icons and `click_tag` elements).

=== ":mast-icon: {{ab.m}}"
    ```
    cb  = gui_checkbox("text: {label}; state: {enabled}")
    dd  = gui_drop_down("text: {menu}; list: arc, line, box", var="menu")
    sl  = gui_int_slider("low: 0; high: 10;", var="level")
    lb  = gui_list_box(items, "row-height: 1em;", item_template=my_template, select=True)
    ib  = gui_icon("icon_index: 137; color: white;", style="click_tag: menu;")
    fa  = gui_face(face_string)

    on gui_message(dd):
        menu = dd.get_value()
    on gui_click(ib):
        jump menu_label
    ```

Read a widget's value with `widget.get_value()` / `widget.value`; a list box also
has `get_selected()`, `get_selected_index()`, and `set_selected_index(i)`.

## Rich text areas

`gui_text` is a single styled line. For a **multi-line, formatted block** — help,
briefings, a log, a comms transcript — use **`gui_text_area`**, which parses a
small markdown-like language and **auto-scrolls** when its content overflows.

=== ":mast-icon: {{ab.m}}"
    ```
    brief = "$t Mission Briefing^^Reach the beacon and hold the line.^^- Jump to the Kessel system.^- Defend the relay for five minutes.^- Do not let the convoy through."
    gui_text_area(brief)
    ```

- `$t` a title; `#`/`##`/`###` headings (auto-numbered, so use `$t` for a plain
  title); `-` bullets; `1.` ordered lists; a blank line resets; `^` is a newline;
  `{var}` interpolates.
- Inline objects by namespace: `![](image://key?scale=0.5)`, `[](ship://hull?...)`,
  `[](face://...)`, `[](style://font:gui-4;color:#8cf)`.
- **Pipe tables** — `| Ship | Hull |` rows with a `|:--|--:|` alignment row — render
  as a grid, columns sized to fit. (For an *interactive* table with controls, use
  [`gui_table`](gui_table.md) instead.)
- **Hyperlinks** — a `[Torgoth](ref://torgoth)` line is a clickable link; give the
  area a `link_resolver` (`fn(key) -> new text`) and it **navigates within the same
  document** — a Kralien entry can link straight to the Torgoth one (a codex). `<hr>`
  draws a horizontal rule.
- A single unformatted line just renders as plain text; a parse slip shows
  `Document syntax issue line number N` — so a blank/garbled area is usually a
  syntax slip on that line. Engine text is ASCII-only.

## Reacting while the GUI is up

`on` handlers run while a GUI is on screen:

=== ":mast-icon: {{ab.m}}"
    ```
    on change red_alert:                       # a variable changed
        repaint_alert()

    on change get_data_set_value(ship_id, "red_alert", 0):   # any expression
        update_banner()

    on gui_message(gui_button("Dock")):        # a button was pressed
        request_dock()

    on signal "wave_cleared":                  # a signal fired
        show_bonus()
    ```

## Updating without a rebuild

Set a widget's value and the dirty system re-renders it automatically &mdash; no
need to rebuild the whole page:

=== ":mast-icon: {{ab.m}}"
    ```
    the_face.value = new_face_string
    on_screen.update(f"image:{get_mission_dir_filename('RedAlert')}")
    ```

!!! note "`gui_represent()` is deprecated"
    Widgets mark themselves dirty when their value changes and re-render on their
    own. Calling `gui_represent()` is harmless but redundant.

## Consoles

Route a client to a standard console, or build one widget by widget:

=== ":mast-icon: {{ab.m}}"
    ```
    gui_console("helm")                  # a standard console
    gui_activate_console("cockpit")      # switch this client to a console
    gui_layout_widget("2dview")          # size a gameplay view (2dview / 3dview)
    ```

## Full rebuild / reroute

To rebuild a page, jump back to its label; to move clients between pages:

=== ":mast-icon: {{ab.m}}"
    ```
    gui_reroute_server(server_status)          # redirect the server task
    gui_reroute_clients(mission_end_screen)    # redirect every client task
    ```

See the [gui API](../api/procedural/gui.md) for the full list of widgets and
options, and the [GUI tutorial](../tutorial/gui/simple_gui.md) for a worked
example.
