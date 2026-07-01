# Mission settings (`settings.yaml`)

`settings.yaml` (optional) provides default values the mission reads via
`settings_get_defaults()`. Its keys become variables available to your MAST &mdash;
and the setup screen's Properties can override them per game.

## Common keys

```yaml
AUTO_START: false            # start the mission the moment it's selected
DIFFICULTY: 5
GAME_TIME_LIMIT: 20          # minutes - your mission decides what this means

# Player ships
PLAYER_CREATE_DEFAULT: true  # let the fleets add-on pre-create ships from PLAYER_LIST
PLAYER_COUNT: 1              # how many are active
PLAYER_SHIP_RESPAWN: false
PLAYER_LIST:
    -   name: "Artemis"
        side: "tsn"
        ship: "tsn_light_cruiser"
        face: "terran"
    -   name: "Intrepid"
        side: "tsn"
        ship: "tsn_battle_cruiser"
        face: "terran"

# Standard docking behavior (LegendaryMissions docking add-on)
DOCKING:
    refuel_amount: 20
    refuel_delay: 2
    shield_delay: 2
    shield_coeff: 2
    torps_delay: 6
    interior_delay: 2
    interior_count: 2

GAMEMASTER:
    enable: true
```

## How they're used

- **Reading:** `settings_get_defaults()` returns them; the standard consoles/fleets
  add-ons read `PLAYER_LIST`, `PLAYER_COUNT`, `DIFFICULTY`, `DOCKING`, etc. for you.
- **Overriding per game:** a `@map/` `metadata` `Properties` block puts widgets on
  the setup screen bound to these variables &mdash; e.g. a Difficulty slider
  `var="DIFFICULTY"`. See [Anatomy of a mission](../build/anatomy.md).
- **Testing:** the `sbs` tool can override settings without editing this file
  (`--auto-start`, `--players N`, `--set KEY=VALUE`). See [the CLI](../tooling/cli.md).

Everything here is optional &mdash; the keys are just defaults your mission (and the
add-ons) may read. See the [settings API](../api/procedural/settings.md).
