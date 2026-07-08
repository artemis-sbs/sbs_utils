# The `sbs` CLI

`sbs` (the `sbs.pyz` tool) builds, runs, and serves missions from the command
line. Run `sbs <command> --help` for full options.

| Command | What it does |
|---|---|
| `sbs debug <mission>` | Run a mission in a browser **mock GUI** (3D cinematic + 2D radar) |
| `sbs debug <mission> --map 0` | Auto-start a map instead of the picker; `--no-gui` for headless |
| `sbs overnight <mission>` | Long **soak test** under autoplay |
| `sbs web <mission>` | Serve the mission's [web pages](../build/web-pages.md) to browsers |
| `sbs web-static <mission> <page>` | Render one web page to a standalone HTML file |
| `sbs lib <folder>` | Build a `.sbslib` / `.mastlib` library |
| `sbs compile <mission>` | Compile-check the MAST |
| `sbs lint <mission>` | **Validate** the mission's `.amd` files (headings, references, signals) |
| `sbs fetch` / `sbs update` | Fetch missions / update the tool |

## Running a mission

```
sbs debug .                 # browser GUI, map picker
sbs debug . --map 0         # auto-start map 0
sbs debug . --no-gui --map 0 --test 30    # headless, play ~30s, pass/fail verdict
```

Handy flags: `--use-working-tree` (test local library edits against the packaged
mission), `--seed N` (reproducible runs), and settings overrides that don't touch
`settings.yaml` (`--auto-start`, `--players N`, `--set KEY=VALUE`).

## Validating AMD

`compile` checks the MAST; `lint` checks the `.amd` content (quests, dialogue,
cast, maps). AMD fails *silently* — a typo'd `# [Display](key)` heading becomes body
text and its node vanishes — so lint re-scans a mission's `.amd` and surfaces it.

```
sbs lint .                 # errors + warnings, exit 0/1
sbs lint . --strict        # warnings fail too (CI)
sbs lint . --no-cross      # skip cross-file (signal->route, reach->landmark) checks
```

**Errors** (fail the run): broken/vanishing headings, unclosed `---` fences,
heading-level jumps. **Warnings**: dangling choice / `Scene:` / `Then: reveal` /
`Parent:` targets, an emitted `signal X` with no `//signal/X` route, a `reach i,j`
with no landmark `At:`. Backed by `sbs_utils.procedural.amd_lint` — also callable
directly on a single file: `python -m sbs_utils.procedural.amd_lint <file.amd>`.

## Serving web pages

```
sbs web .                                  # serve this mission's //web pages
sbs web --engine a=missionA --engine b=missionB   # one server, many engines
sbs web-static . scores -o scores.html --query title=Standings
```

See [Serving web pages](web-proxy.md) and the [Web pages](../build/web-pages.md)
cookbook.
