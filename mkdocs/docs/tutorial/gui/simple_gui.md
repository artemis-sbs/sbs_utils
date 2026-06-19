# Tutorial: Simple GUI

Add a custom GUI panel to an Artemis Cosmos mission.

## Create mission

Start from a starter template.

=== ":mast-icon: {{ab.m}}"
    ```bash
    .\fetch artemis-sbs mast_starter simple_gui
    ```

=== ":simple-python: {{ab.pm}}"
    ```bash
    .\fetch artemis-sbs pymast_starter simple_gui
    ```

## Add a console label

A `@console/` decorator label defines a named tab available to clients. It builds a GUI layout and then calls `await gui()` to wait for player interaction.

=== ":mast-icon: {{ab.m}}"
    ```
    @console/status !0 ^10 "Status"
    " Show mission status
        gui_section(style="area: 0, 0, 100, 100;")
        gui_row()
        gui_text("$text: Mission Active;")
        await gui()
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    @label()
    def status_panel():
        gui_section(style="area: 0, 0, 100, 100;")
        gui_row()
        gui_text("$text: Mission Active;")
        yield AWAIT(gui({}))
    ```

## Add a button

Use `gui_button` inside `await gui()` to add a clickable button. The `*` prefix makes it single-use — it is consumed after the first click.

=== ":mast-icon: {{ab.m}}"
    ```
    @console/status !0 ^10 "Status"
    " Show mission status
        gui_section(style="area: 0, 0, 100, 100;")
        gui_row()
        gui_text("$text: Mission Active;")
        await gui():
            * "Send Alert":
                signal_emit("alert_sent")
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    @label()
    def status_panel():
        gui_section(style="area: 0, 0, 100, 100;")
        gui_row()
        gui_text("$text: Mission Active;")
        yield AWAIT(gui({"send_alert": handle_alert}))

    @label()
    def handle_alert():
        signal_emit("alert_sent")
        yield jump(status_panel)
    ```

## Update a widget without rebuilding

Use `on change` to watch a value and update a single widget in place. `gui_represent` re-renders just that widget.

=== ":mast-icon: {{ab.m}}"
    ```
    @console/status !0 ^10 "Status"
        ship_id = sbs.get_ship_of_client(client_id)
        gui_section(style="area: 0, 0, 100, 100;")
        alert = get_data_set_value(ship_id, "red_alert", 0)
        status_text = gui_text(f"$text: {'RED ALERT' if alert else 'Ready'};")

        on change get_data_set_value(ship_id, "red_alert", 0):
            alert = get_data_set_value(ship_id, "red_alert", 0)
            status_text.update(f"$text: {'RED ALERT' if alert else 'Ready'};")
            gui_represent(status_text)

        await gui()
    ```
