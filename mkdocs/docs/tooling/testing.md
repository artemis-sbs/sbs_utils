# Testing missions

The `cosmos_dev` package runs missions **outside Cosmos**, so you can test in the
browser or headlessly in CI.

!!! warning "Testing aid, not the engine"
    The mock **approximates** Cosmos to make offline testing useful &mdash; it is
    **not** a reimplementation and **does not aim for 100% parity**. Some behaviors
    are approximated or absent by design. Please **don't file issues or feature
    requests for more engine parity**; confirm anything engine-exact in Cosmos.

## Mock GUI (in the browser)

```
sbs debug . --gui           # or just: sbs debug .
```

Opens a browser renderer at `http://localhost:8765/` with a 3D cinematic view and
a 2D radar, backed by an in-process mock of the `sbs` engine API. The mock is
calibrated to the real engine: ship speeds, 3D steering, per-facing shields, heat,
energy, and the weapons model (beams, torpedoes, drones, mines, EMP).

## Headless conformance run

```
python -m cosmos_dev.mission_runner . --test 30 --map 0
```

Plays ~30 sim-seconds, prints MAST coverage, and exits `0`/`1` with a pass/fail
verdict &mdash; ideal for CI. (The runner is invoked directly here: `sbs debug` wraps it
for interactive browser debugging and does not expose the conformance flags.) Add `--exercise` to actively drive
selections/comms/console-cycling for more route coverage, `--junit <path>` for a
JUnit report, and `--seed N` for reproducibility.

A PASS here means *nothing raised*, which is not the same as the mission working.
For a mission whose content is quests, see [Soaking a quest-driven
mission](#soaking-a-quest-driven-mission) below.

## Soaking a quest-driven mission

`--test --exercise` drives the world generically: select everything, hail everything,
shoot something. That is the right policy for a combat mission and close to useless for a
quest-driven one, where the content sits behind a job somebody has to **accept** and then
a specific act somebody has to **perform**.

```
sbs soak run LegendaryMissions peacetime
```

A scenario lives at `<mission>/soaks/<name>.yaml` and supplies the whole run &mdash; map,
seed, duration, drive settings and, crucially, what to **expect** of it.

```yaml
map: peacetime_remastered
seed: 7
seconds: 600
settings:
  JOBS_SELECT: lots
  AUTO_PLAY: {enable: false}
drive:
  accept_quests: all      # every offered quest
  goals: true             # drive each one's declared goal
  consoles: [helm, weapons, engineering, comms, science]
  dwell: 20               # NOT the default 3 - see the warning below
expect:
  quests_complete: []
  routes_covered: [damage/object]
  game_end: none
strict_blob: true
```

A scenario may also name a `profile:`, and `--profile NAME` overrides it. It is honored by **both** legs &mdash; the mock runner gets `--profile`, the engine gets `profile=` on its command line &mdash; so the two stay comparable.

### What the pilot does

It reads the **live quest tree** rather than a per-mission script, so the same code drives
a peacekeeping job board, a stealth-archaeology campaign and a siege. Every quest declares
its own completion trigger &mdash; `on_kill`, `on_scan`, `on_dock`, `on_tow`, `on_collect`,
`on_reach`, `on_signal` &mdash; usually with a `role` naming what to do it to.

Everything it does is the call the real interaction makes: accepting is `quest_mark_active`
(the entire body of the Accept button), scanning is `science_ensure_scan`, towing is
`grav_tether_attach`, flying is the helm's own direction steering. Nothing teleports,
refills or grants.

Two things it deliberately does **not** do:

* **Synthesize `on_signal`.** That trigger exists so a mission can define a beat of its
  own; firing it directly would test the harness instead of the mission. Those quests are
  listed as `NOT DRIVABLE` in the report and never fail a run.
* **Stage combat in a mission that never asked for one.** Staging drops the player's
  shields and overheats it. On a peacetime map that simply kills the player: measured, it
  ended and restarted the mission nine times inside a 60-second run, holding coverage at
  26.5% with **0 of 123** comms routes reached. Combat is staged only while some active
  quest carries an `on_kill` goal.

### Starting one for a new mission

```
sbs soak init LegendaryMissions
```

Compiles the mission and writes a starter scenario per `@map` into `soaks/`. It fills in
three things you would otherwise have to dig for:

* **The map's real option keys**, read from its `Properties:` metadata &mdash; the only
  `settings:` a map honors; anything else is silently inert.
* **A quest census**, parsed straight from the mission's `.amd` files, with every goal
  marked `[drive]` or `[----]` so you can see how much of the board a soak can reach
  before running anything.
* **Keys written the way a run reports them** &mdash; relative to the section the mission
  grants, so they paste straight into `expect:`.

It never overwrites an existing scenario. Two honest limits, also stated in the generated
file: quests declared inside a loaded `.mastlib` are not seen (the census walks the
mission's own `.amd`), and whether a mission ever *grants* a quest is a runtime decision,
so the census is an upper bound. The realized board is what a run reports.

### Running it unattended

```
sbs soak run LegendaryMissions peacetime --hours 8
sbs soak run LegendaryMissions peacetime --runs 5
```

Repeats the scenario, keeps every run's evidence under `soaks/runs/<stamp>/` (coverage
JSON, JUnit, the run log, the mission's own `mast.runtime.log`), and **exits non-zero if
any iteration regressed** &mdash; unlike `overnight_runner`, which returns 0 whatever it saw.

It runs against an **auto-managed copy** of the mission, for two reasons that happen to
share one fix: `mast.runtime.log` is opened `"w"` in the mission directory, so a soak
would destroy the log of an engine session somebody is playing; and an engine leg needs
the cosmos_dev sbslib declared in `story.json`, which nobody wants shipped to players.

It also borrows two guards from the engine soak: the build is **SHA1-frozen** at the start
and re-checked at the end (a rebuild mid-soak voids the report, exit `2`), and a run that
times out is **VOID rather than passing** &mdash; a hung run measured nothing and must not
read as evidence that things are fine.

The whole loop is: **init &rarr; run &rarr; bless a few &rarr; commit.**

### In the real engine

One flag - the same scenario, the same pilot, the same assertions, inside Cosmos:

```
sbs soak run LegendaryMissions peacetime --engine --runs 6
```

It maintains the soak copy, declares the harness in it, launches the engine, waits
for the verdict and turns it into an exit code. Under the hood that is:

```
Artemis3-x64-release.exe autostartserver defaultmission=<mission>_soak \n    map=<map> soak=<scenario> profile=<profile> seed=7 test=600
```

`soak=` loads the scenario, drives the pilot from the same per-tick hook `test=` uses, and
folds the expectation result into `<mission>/records/verdict.json`. The engine exposes no
quit in its pybind surface, so the mission can only leave evidence &mdash; the launcher
supplies the exit code, which is what `mission_soak --engine` does.

An engine run is **not** bit-repeatable: physics runs on its own threads and `seed=` only
pins the RNG. That is why the pass rule is a ratchet rather than a fixed list.

!!! note "The harness must be declared to be loaded"
    `soak=` needs `artemis-sbs.cosmos_dev.*.sbslib` in the mission's `story.json`, and a
    **profile cannot add one** &mdash; that list is read at `import script`, before any
    profile is consulted. The soak copy handles this for you. Without it the run logs a
    warning naming the cause and behaves exactly like a plain `test=`.

### What the mock can and cannot show you

The mock approximates the engine, and where it is silent a green run means nothing rather
than something. One example is worth carrying, because it was invisible for a long time:
the mock used to populate **no `eng_control_label` at all**, so every `range(30)` walk over
that array &mdash; LegendaryMissions autoplay's power loop, its can-turn check,
`set_engineering_value` &mdash; iterated zero times headless and did nothing. Engineering
could only be checked by watching the sliders move in a real engine.

It now seeds the table the engine actually reports, **captured from a live engine rather
than written from memory** (`cosmos_dev/mock/captured/`). Eight controls onto four systems,
which is the part that catches bugs: `FRONT SHIELD` and `REAR SHIELD` both feed system 3, so
anything stopping at the first label match leaves half a system unset.

The rule it illustrates is the general one: **where the mock cannot derive engine behaviour,
capture it or leave the gap open.** A plausible-but-wrong value is worse than an absent one
&mdash; it makes a run look like it exercised something it did not.

### The ratchet

`expect:` is the positive half of the verdict. Today a run passes when nothing raised, and
a run that completed no quest, entered no route and ended nothing at all satisfies that
perfectly.

Rather than a fixed list (red every morning, then ignored), the demand is a **baseline**
of what runs have actually achieved, at `<mission>/soaks/<name>.baseline.json`. A run fails
only when it achieves *less*. Fold in a good run with:

```
sbs soak bless LegendaryMissions peacetime --runs 8
```

The baseline demands what **every** blessed run reached, not what any of them ever
reached, so **blessing more runs makes it more trustworthy, not stricter**: an item that
showed up once out of three stops being demanded, while a dependable one stays. Bless a
few runs before relying on it &mdash; a one-run baseline over-fits that run's luck, and
measured, it reported 17 routes as regressed on the next run purely from variance.

It cannot drift down on its own either: counts change only when somebody blesses, never as
a side effect of a failing run.

**Routes come in two kinds, and the difference is what keeps this usable.** A route named
in `expect.routes_covered` is a **contract**: one absence fails the run, no tolerance. That
is the right home for a path you know matters. A route the baseline merely learned is a
**drift signal**, and `expect.route_tolerance` (default 3) says how many may go missing
before it counts &mdash; because some are genuinely probabilistic.
`pr_poacher_surrender` needs a poacher's shields below half inside the window; measured,
even with eight blessed runs one fresh run in three still lost a route. Failing on that is
how a check becomes noise and then gets ignored.

The route half is the one that earns its keep. `LM_TETHER_BREAK_DAMAGE` was a Python module
constant the MAST namespace never exported, so the grav-tether `//damage/object` route
raised a `NameError` on every hit for a whole mission. Nothing headless had ever shot a
ship that was towing, so the route was never entered and every run reported PASS. Coverage
knew; nothing asked it.

!!! warning "`--exercise-dwell` defaults to 3"
    That is well under a sim-second per console, so an `on change` watcher keyed to a
    one-second tick fires **exactly zero times** &mdash; which is how a `NameError` in a
    region watcher reached a real engine session under a green headless run. Scenarios
    should set a real dwell, and budget at least `dwell x (5 + extras) / 3` seconds of run
    time, because `--exercise-console` extras come last in the cycle.

!!! warning "The runtime log is truncated in the mission folder"
    `mast.runtime.log` is opened with mode `"w"` in the mission directory, so a headless
    run against a folder somebody is playing in the engine destroys the log that session
    just produced. Soak against a copy (it must live under a `__lib__`-bearing missions
    root).

## Validating AMD files

```
sbs lint .                  # check .amd for silent structural/reference errors
```

AMD's failure modes are **silent** — a typo'd `# [Display](key)` heading drops a whole
quest with no error. `sbs lint` re-scans a mission's `.amd` and reports broken/vanishing
headings, unclosed `---` fences, and heading-level jumps (**errors**, exit `1`), plus
dangling `Then: reveal` / choice / `Scene:` targets, a `signal X` with no `//signal/X`
route, and a `reach i,j` with no landmark `At:` (**warnings**). Add `--strict` to fail on
warnings for CI. See [the CLI page](cli.md#validating-amd).

## Unit tests

The library uses `unittest`:

```
python -m unittest discover -s tests
```

See [Contributing &rsaquo; Testing](../home/contributing/testing.md) for writing tests
against the `cosmos_dev.mock` API.
