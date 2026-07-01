# Comms

Comms is how players talk to the things they select. When a player selects an
entity, the engine routes a comms event; the comms system checks eligibility with
`//enable/comms`, then shows the matching `//comms` menu. Scripts don't open comms
manually.

## Enabling comms

An `//enable/comms` route decides whether an entity offers comms, and can set up
any state it needs:

=== ":mast-icon: {{ab.m}}"
    ```
    //enable/comms if has_roles(COMMS_SELECTED_ID, "station")
        set_inventory_value(COMMS_SELECTED_ID, "apples", 3)
    ```

Useful context variables inside comms routes: `COMMS_ORIGIN_ID` (who initiated,
usually the player) and `COMMS_SELECTED_ID` (what they selected).

## The comms menu

`//comms` is the root menu. Buttons add choices; `+` is a sticky button and `*` is
consumed after one click. A button can run an inline block, or navigate to a
submenu route.

=== ":mast-icon: {{ab.m}}"
    ```
    //comms if has_roles(COMMS_ORIGIN_ID, "__player__")
        + "Hail":
            << [green] "Hail"
                % Greetings, commander.
                % How can I help you?
        + "Trade" //comms/trade
        + "Attack!" if side_are_enemies(COMMS_ORIGIN_ID, COMMS_SELECTED_ID):
            >> "Prepare to be boarded."
    ```

A submenu is its own route; `+ "Back" //comms` returns to the root:

=== ":mast-icon: {{ab.m}}"
    ```
    //comms/trade
        + "Back" //comms
        + "Buy apple" if get_inventory_value(COMMS_SELECTED_ID, "apples", 0) > 0:
            set_inventory_value(COMMS_SELECTED_ID, "apples",
                                get_inventory_value(COMMS_SELECTED_ID, "apples", 0) - 1)
            << [green] "Trade" % One apple, coming up.
    ```

Button forms:

```
+ "Label"                                # run the inline block
+ "Label" //comms/path                   # navigate to a submenu
+ "Label" handler_label                  # jump to a label
+ "Label" handler_label {"key": "value"} # jump with data
+ "Label" if condition:                  # conditional
+ !0 "Back" //comms                       # !0 = sort priority
+ "{dynamic_text}" handler_label          # interpolated label
```

## Dialogue

`<<` is an incoming line (the NPC speaks); `>>` is outgoing (the player speaks).
`%` lines are alternatives &mdash; one is picked at random each time, so messages
feel fresh:

=== ":mast-icon: {{ab.m}}"
    ```
    << [green] "Hostile Hail"
        % Go climb a tree!
        % You can't win!

    >> "Understood, moving out."
    ```

Other message kinds: `<all>` (broadcast), `<scan>` (science scan result), and `()`
(a speech bubble).

## Colors

`=$` declares a named color/style for dialogue titles:

=== ":mast-icon: {{ab.m}}"
    ```
    =$ raider red, white
    =$ friendly green

    << [$raider] "Hail"
        % This sector is ours.
    ```

## Navigating and sending from code

```
comms_navigate("//comms/trade")   # jump to a submenu
comms_navigate("")                 # go back / up
comms_message(text, players, from_id)   # push a message to players' comms
```

See the [comms routes](../mast/routes/comms.md) reference and the
[comms tutorial](../tutorial/comms/simple_comms.md) for a worked example. Legendary
Missions' `comms`, `gamemaster_comms`, and `internal_comms` add-ons provide
ready-made comms trees.
