# Science

Science scans work like comms: an object must be **enabled** for science, then a
`//science` route provides the scan tabs and their results.

Context variables inside science routes:

- `SCIENCE_ORIGIN_ID` / `SCIENCE_ORIGIN` &mdash; the player ship doing the scan
- `SCIENCE_SELECTED_ID` / `SCIENCE_SELECTED` &mdash; the object being scanned

## Enabling science

NPCs aren't scannable until science is enabled for them. Use conditions specific
enough that each agent is enabled **once** (enabling more than once can drop scan
tabs):

=== ":mast-icon: {{ab.m}}"
    ```
    //enable/science if has_roles(SCIENCE_SELECTED_ID, "wreck")
        bio_scan_count = 0        # optional per-scan state
    ```

## Scan tabs and results

Each `+ "tab":` is a scan tab; its block runs when the scan completes, and
`<scan>` provides the result. `%` lines are alternatives &mdash; one is chosen at
random each time:

=== ":mast-icon: {{ab.m}}"
    ```
    //science if has_role(SCIENCE_SELECTED_ID, "wreck")
        + "scan":
            <scan>
                % Gutted, battle-scarred wreckage that used to be a starship.
                % Hulk of a destroyed ship.
        + "bio":
            <scan>
                % Indeterminate life signs detected - proceed with caution.
                % No life detected.
    ```

## Making more things scannable

Link extra objects to a player ship so science can scan them (used to surface lore
and side content):

=== ":mast-icon: {{ab.m}}"
    ```
    link(artemis_id, "extra_scan_source", whale_watcher_id)
    ```

See the [science routes](../mast/routes/science.md) reference, the
[science API](../api/procedural/science.md), and
[extra scan sources](../api/procedural/extra_scan_sources.md). Legendary Missions'
`science_scans` add-on provides ready-made scan responses.
