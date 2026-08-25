# The `sbs` CLI

`sbs` (the `sbs.pyz` tool) builds, runs, and serves missions from the command
line. Run `sbs <command> --help` for full options.

| Command | What it does |
|---|---|
| `sbs create <name>` | **Start a new mission** from a boilerplate template |
| `sbs templates` | List the templates available, per release line |
| `sbs debug <mission>` | Run a mission in a browser **mock GUI** (3D cinematic + 2D radar) |
| `sbs debug <mission> --map 0` | Auto-start a map instead of the picker; `--no-gui` for headless |
| `sbs overnight <mission>` | Long **soak test** under autoplay |
| `sbs web <mission>` | Serve the mission's [web pages](../build/web-pages.md) to browsers |
| `sbs web-static <mission> <page>` | Render one web page to a standalone HTML file |
| `sbs lib <folder>` | Build a `.sbslib` / `.mastlib` library |
| `sbs compile <mission>` | Compile-check the MAST |
| `sbs lint <mission>` | **Validate** the mission's `.amd` files (headings, references, signals) |
| `sbs fmt <mission>` | **Format** the mission's `.amd` files (canonical, prose-safe) |
| `sbs docs <mission>` | **Print** the mission's `.amd` as a paper-ready HTML document ([four lenses](amd-docs.md)) |
| `sbs docs <mission> --pdf` | ...and a **PDF**, via a headless browser or the weasyprint CLI |
| `sbs doctor` | **Check the setup** - tools, libraries, mission health ([details](doctor.md)) |
| `sbs deps install <pkg>` | Optional Python libraries, on an interpreter that cannot `pip` ([why](doctor.md)) |
| `sbs swap <name>` | Switch which `missions_*` set Cosmos loads |
| `sbs fetch` / `sbs update` | Fetch missions / update the tool |

## Starting a mission

```
sbs templates                        # what's on offer, per release line
sbs create MyMission                 # pick from a list
sbs create MyMission -t sandbox      # pick up front
sbs create MyMission --title "My Mission"
```

`create` lays the template down, rewrites the mission's name into
`description.yaml`, and fetches everything its `story.json` pins. It refuses to write
into a folder that already has anything in it.

Templates come from the
[mast_starter](https://github.com/artemis-sbs/mast_starter) repo, which keeps a
`templates.json` catalog **on each branch** — so a new template is a commit there,
not a release of this tool.

### Release lines

A branch per line (`v1.3.0`, `v1.4.0`), and every dependency of a mission comes from
one line. That is not just a version string: a template can only use what its line
has — `provides`/`requires` are v1.4.0+, and `pickup_spawn` / `scatter_box` don't
exist in the v1.3.0 library at all — so **the branch decides which templates exist**.

Resolution order is: what you asked for, then a line this install already has an
sbslib for, capped by your Cosmos version. Deliberately *not* in that list: the
newest branch on GitHub. That's the upper bound, not a default.

```
sbs create MyMission -l v1.4.0       # pin the line
sbs create MyMission -b v1.4.0_dev   # a specific branch (pre-releases are opt-in)
sbs create MyMission --retarget      # re-pin a template's deps to the resolved line
```

## Running a mission

```
sbs debug .                 # browser GUI, map picker
sbs debug . --map 0         # auto-start map 0
sbs debug . --no-gui --map 0 --test 30    # headless, play ~30s, pass/fail verdict
```

Handy flags: `--use-working-tree` (test local library edits against the packaged
mission), `--seed N` (reproducible runs), and settings overrides that don't touch
`settings.yaml` (`--auto-start`, `--players N`, `--set KEY=VALUE`).

## Launching the real game

`sbs debug` runs a mission in the browser; `sbs run` opens the actual game — a server and
as many console clients as you ask for, arranged on screen.

```
sbs run                                    server + a full test bridge
sbs run comms,weapons                      just those two consoles
sbs run -m LM_TestRange                    a different mission (default: LegendaryMissions)
sbs run comms --ip 192.168.1.50            clients pointed at another machine
sbs run --dry-run                          show the command lines, launch nothing
```

Nothing needs clicking: the server starts itself, clients connect, and each lands on its
console. `--no-auto` restores the old launcher-menu behavior.

The mission is passed as `defaultmission=`, so `preferences.json` is never edited.

**Anything you add on the end reaches the mission**, which is how you start a particular
map or set of settings:

```
sbs run -m LM_TestRange map=sandbox profile=soak var.DIFFICULTY=3
sbs run -m LegendaryMissions test=60       a pass/fail verdict from the real engine
sbs run -m LegendaryMissions record=session  transcribe what you click
```

See [Command-line arguments](command-line.md) for the full list and how settings merge.

## Switching mission sets

Cosmos loads exactly one `data/missions` folder. Keep several sets beside it as
`data/missions_<name>` and let `data/missions` be a link to whichever you want:

```
sbs swap            # current target + available sets
sbs swap amd        # point data/missions at data/missions_amd
sbs swap cos        # back to the stock missions
```

The prefix is optional (`amd` and `missions_amd` are the same). Any
`missions_<name>` folder is a target, so adding a set is just creating the folder.
A real (non-link) `data/missions` is renamed to `missions_cos` on the first swap
rather than deleted — nothing but the link is ever removed. Run it from anywhere
under the install; it finds the data folder by walking up, or pass `--data`.

!!! warning "Back up `data/missions` before your first swap"
    The command rearranges the folder that holds all your missions. It will not
    delete a mission folder, but take a backup anyway if you have edits that
    aren't in source control. And close Cosmos first — a running client holds
    files open under the link, and the swap will refuse rather than half-finish.

## Validating AMD

`compile` checks the MAST and **exits non-zero** when it fails, so it can gate a build.

!!! warning "What `compile` cannot see"
    A `{ }` literal split across lines. MAST parses line by line, so the first line is
    an unclosed `{`; the parser desyncs for the rest of the file, the story's main task
    can end up **empty**, and the compiler still reports zero errors. The mission then
    runs and does nothing. Keep dict literals on one line or inside `~~ … ~~`, and if a
    mission mysteriously does nothing, suspect this first. A headless
    `--test` run catches it (`labels 0/N`); a compile never will.

`lint` checks the `.amd` content (quests, dialogue, cast, maps). AMD fails *silently* — a typo'd `# [Display](key)` heading becomes body
text and its node vanishes — so lint re-scans a mission's `.amd` and surfaces it.

```
sbs lint .                 # errors + warnings, exit 0/1
sbs lint . --strict        # warnings fail too (CI)
sbs lint . --no-cross      # skip cross-file (signal->route, reach->landmark) checks
```

**Errors** (fail the run): broken/vanishing headings, unclosed `---` fences,
heading-level jumps. **Warnings**: dangling choice / `Scene:` / `Then: reveal` /
`Parent:` targets, an emitted `signal X` with no `//signal/X` route, a quest
`Starts when: signal X` that nothing emits, a `reach i,j` with no landmark `At:`, and
non-ASCII author text (the engine renders ASCII only). Backed by `sbs_utils.procedural.amd_lint` — also callable
directly on a single file: `python -m sbs_utils.procedural.amd_lint <file.amd>`.

`lint` also reads the mission's `.mast` for two signal problems that are easy to write and
hard to see. First, work that runs **once per console** when it should run once on the
server (`signal-side-effect-*` — a `//signal` route that spawns, rewards, saves, counts or
rolls random). Second, setup that can run **more than once** because its signal gets
emitted more than once:

| Code | Fires on |
|---|---|
| `signal-init-unkeyed-spawn` | a `//shared/signal/create_*` route that spawns without a key and isn't marked `once` |
| `signal-emit-in-loop` | a setup `signal_emit` inside a `for` / `while` |
| `signal-multi-emit` | such a signal emitted from more than one place in the mission |

All are warnings — the fix is usually a keyed create (`player_ensure`) or a `once` route.
See [Signal routes](../mast/routes/signals.md#running-setup-only-once). Skip them with
`--no-signals`.

References resolve across **all of the mission's `.amd` files** and against MAST
`== labels ==`, so a `Scene:` / choice / `reveal` that targets a node in a sibling
file (or a MAST handler label) isn't wrongly flagged. To vouch for a signal the
linter can't see statically — a dynamic or computed `signal_emit` — add an optional
`emits: [name, …]` (or `handles: [name]`) line to a `metadata:` block; it needs no
new syntax (MAST just treats the key as an unused variable).

`--format compact` emits `file:line:col:` lines for editor problem-matchers;
`--format json` emits structured findings (with exact ranges) for tools/CI.

## Formatting

```
sbs fmt .                  # canonically format this mission's .amd (writes in place)
sbs fmt . --check          # report + exit 1 if any file isn't formatted (CI)
```

Normalizes trailing whitespace, heading spacing, `---` fences, and blank-line runs.
It is **prose-safe and idempotent** — it never reflows prose and is guaranteed not to
change the parsed model. Backed by `sbs_utils.procedural.amd_fmt` (single file:
`python -m sbs_utils.procedural.amd_fmt --write <file.amd>`), and exposed as the LSP
formatting provider below (format-on-save).

### In your editor (language server)

```
sbs lint --lsp             # AMD language server over stdio
```

Point any LSP client at that command for **live diagnostics as you type** — VSCode,
Neovim, Emacs, Sublime, JetBrains. A ready-to-build **VSCode extension** (syntax
highlighting + a thin client for this server) lives in the `sbs_cli` repo under
`editors/vscode/`. It's the same checks over the same `amd_core`
model (`sbs_utils.procedural.amd_lsp`), dependency-free. Beyond diagnostics it also
provides **go-to-definition** (a `reveal` / choice / `Scene:` target → its node),
**find-references** and **rename** (a node key + every reference to it), a
**document outline**, **hover**, **completion**, **quick-fixes** (did-you-mean /
create-node), a reference **CodeLens**, **color swatches** for `#rrggbb`, **inlay
hints** (a reference's display name inline), and **formatting** — all from the one
model, and all resolved across the whole mission.

## Serving web pages

```
sbs web .                                  # serve this mission's //web pages
sbs web --engine a=missionA --engine b=missionB   # one server, many engines
sbs web-static . scores -o scores.html --query title=Standings
```

See [Serving web pages](web-proxy.md) and the [Web pages](../build/web-pages.md)
cookbook.

## Repairing engine-baked art

A hull's `.paxmesh` and its `<root>1024.png` / `<root>256.png` are not authored -
the engine generates them the first time it draws that hull, beside the source
`.obj`, and they are never packaged (a baked mesh hardcodes its texture paths under
`data/graphics/`, so shipping one points another install at somebody else's disk).

```
sbs art check              # what is half-baked?
sbs art check --strict     # exit 1 if anything is
sbs art clear              # delete the partial files so the engine starts over
sbs art bake               # ...and drive the engine to rebuild them
```

**A half-baked hull is a crash-to-desktop, not a cosmetic gap.** The engine retries
the bake on every draw, dies in the same place, and leaves the same partial output,
so one bad hull kills that client every time it sees it. `clear` touches only what
the engine made - your `.obj` and textures are never removed - and `bake` runs the
engine once per hull so a crash costs one hull rather than the batch, finishing with
the list of hulls that still will not build.

Mod-carried art cannot be baked where it lives, for the texture-path reason above;
`sbs art` reports those rather than trying. `sbs doctor` runs the same check as part
of its report - see [Checking your setup](doctor.md#half-baked-art).
