# Getting the library

Missions don't bundle the library &mdash; they load it at runtime from a shared
`__lib__/` folder next to your `missions/` directory. Each library is a versioned
zip:

- `artemis-sbs.sbs_utils.v1.4.0.sbslib` &mdash; the `sbs_utils` library
- `artemis-sbs.LegendaryMissions.<addon>.v1.4.0.mastlib` &mdash; optional
- `artemis-sbs.LegendaryMissions.races.v1.4.0.mastlib` &mdash; **needed if you use the
  `ai` or `fleets` add-on.** Carries ship interiors and fleet compositions; without it a
  player ship has an empty Engineering console and nothing raids you. See
  [The races add-on](../build/race-addons.md).
  [LegendaryMissions](../legendarymissions/addons/index.md) addons

Your mission's [`story.json`](start.md) lists the ones it needs:

```json
{
    "sbslib": ["artemis-sbs.sbs_utils.v1.4.0.sbslib"],
    "mastlib": ["artemis-sbs.LegendaryMissions.consoles.v1.4.0.mastlib"]
}
```

## Getting the files

- **Starting a new mission?** [`sbs create`](start.md#start-from-a-template) fetches
  everything the template pins, so there's nothing to do by hand.
- **With the `sbs` tool:** `sbs fetch` pulls missions and their libraries. See
  [the CLI](../tooling/cli.md).
- **From GitHub releases:** download the `.sbslib` / `.mastlib` assets from the
  [sbs_utils](https://github.com/artemis-sbs/sbs_utils/releases) and
  [LegendaryMissions](https://github.com/artemis-sbs/LegendaryMissions/releases)
  releases into `__lib__/`.

## Building from source

If you're developing the library itself, build a lib from a source folder with
`sbs lib <folder>` (see [the CLI](../tooling/cli.md)); the working tree can also be
run directly with `sbs debug --use-working-tree`.
