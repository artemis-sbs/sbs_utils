# sbs_utils

**Mission scripting library for Artemis: Cosmos.**

Artemis: Cosmos embeds Python 3.11 and drives a whole mission through a single event
handler. `sbs_utils` is the layer above that: a scripting language for mission logic, a
large procedural API, the console and GUI system, and a mock engine you can develop
against without launching the game.

**Documentation: <https://artemis-sbs.github.io/sbs_utils/>**

## What's in the box

- **MAST** &mdash; a small, python-like scripting language for mission logic. Compiler,
  task scheduler, labels, routes, comms and science trees.
  ([`sbs_utils/mast/`](sbs_utils/mast) is the generic language core;
  [`sbs_utils/mast_sbs/`](sbs_utils/mast_sbs) adds the Cosmos-specific nodes.)
- **The procedural API** &mdash; over 100 modules callable from both MAST and Python:
  spawning, roles, links, inventory, comms, science, quests, terrain, fleets, items,
  timers, GUI. ([`sbs_utils/procedural/`](sbs_utils/procedural))
- **The console and GUI system** &mdash; what missions build their bridge screens with.
  ([`sbs_utils/pages/`](sbs_utils/pages), [`sbs_utils/gui.py`](sbs_utils/gui.py))
- **`cosmos_dev`** &mdash; a mock of the engine's `sbs` module, a mission runner, a
  browser-based renderer and a MAST source debugger, so a mission can be run, tested and
  stepped through **without starting Cosmos**. ([`cosmos_dev/`](cosmos_dev))

`cosmos_dev` is a development tool. It is never needed to *play* a mission.

## A taste

```
@map/border_watch "Border Watch"
" A station on the frontier, and something inbound.

    npc_spawn(0, 0, 0, "DS 5", "tsn, station", "starbase", "behav_station")
    await delay_sim(20)
    signal_emit("raiders_inbound")

//shared/signal/raiders_inbound
    for i in range(3):
        npc_spawn(9000, 0, i * 800, name_random_hostile("ximni"), "ximni, raider", "xim_light_cruiser", "behav_npcship")
```

A `@map` label is a scenario the crew can pick; a `//` route is an entry point the
engine or a signal fires. Everything in between is ordinary code calling the procedural
API.

You do not have to use the language. The same mission can be written in plain Python
generators against the same API &mdash; see
[PyMAST](https://artemis-sbs.github.io/sbs_utils/mast/python/).

## Using it in a mission

Missions do not vendor the library. They load it at runtime from a shared `__lib__/`
folder next to your `missions/` directory, and pin the version in `story.json`:

```json
{
    "sbslib": ["artemis-sbs.sbs_utils.v1.4.0.sbslib"],
    "mastlib": ["artemis-sbs.LegendaryMissions.consoles.v1.4.0.mastlib"]
}
```

The easiest way to get all of that in place is the `sbs` command-line tool, which lives
in your `missions/` folder:

```
sbs templates              # see what you can start from
sbs create MyMission       # scaffold it, and fetch the libraries it pins
sbs debug MyMission --map 0
```

You can also download the `.sbslib` asset straight from
[Releases](https://github.com/artemis-sbs/sbs_utils/releases) into `__lib__/`.

Full detail: [Creating a mission](https://artemis-sbs.github.io/sbs_utils/home/start/)
and [Getting the library](https://artemis-sbs.github.io/sbs_utils/home/get_library/).

## Documentation

Everything below the surface lives on the docs site. This README deliberately stops
short of repeating it.

| Section | What's there |
|---|---|
| [Get started](https://artemis-sbs.github.io/sbs_utils/home/start/) | Creating a mission, getting the library, mission settings |
| [Learn MAST](https://artemis-sbs.github.io/sbs_utils/mast/) | Tutorial, syntax, routes, tasks, the agent model, common gotchas |
| [Build a mission](https://artemis-sbs.github.io/sbs_utils/build/) | Worlds, consoles, GUI, comms, science, AI, quests, add-ons, mods |
| [Tooling](https://artemis-sbs.github.io/sbs_utils/tooling/) | The `sbs` CLI, running and debugging a mission, AMD authoring |
| [Reference](https://artemis-sbs.github.io/sbs_utils/api/) | Every procedural module, the engine `sbs` API, event fields |

New to all of this? Start with the
[MAST tutorial](https://artemis-sbs.github.io/sbs_utils/mast/tutorial/). Recent changes
are in [What's New](https://artemis-sbs.github.io/sbs_utils/whats-new/) and
[CHANGELOG.md](CHANGELOG.md).

## Reporting a bug

Issues for the whole Cosmos scripting stack &mdash; this library, the add-ons and the
missions &mdash; are tracked in **one** place:

**<https://github.com/artemis-sbs/LegendaryMissions/issues>**

Please file there rather than on this repository. That single tracker is why fixes in
this repo's commits and changelog refer to issues as "LM #614".

---

# Working on the library

The rest of this file is for people changing `sbs_utils` itself. The docs site has a
fuller [Contributing](https://artemis-sbs.github.io/sbs_utils/home/contributing/)
section.

Clone this repo into your Cosmos `missions/` directory. It sits alongside the missions
it serves, which is what lets the tools below find the shared `__lib__/` folder.

## Repo layout

| Path | What lives there |
|---|---|
| [`sbs_utils/`](sbs_utils) | The library. Shipped as `artemis-sbs.sbs_utils.<version>.sbslib`. |
| [`sbs_utils/mast/`](sbs_utils/mast) | The generic MAST language core: compiler, scheduler, core node types. |
| [`sbs_utils/mast_sbs/`](sbs_utils/mast_sbs) | Cosmos-specific MAST: mission scheduler, story page, GUI/comms/science nodes. |
| [`sbs_utils/procedural/`](sbs_utils/procedural) | The procedural API, callable from MAST and Python alike. |
| [`sbs_utils/pages/`](sbs_utils/pages) | Console pages and the layout engine behind the GUI. |
| [`cosmos_dev/`](cosmos_dev) | Dev-only: mock engine, mission runner, browser GUI, debugger. Ships as its own `.sbslib`. |
| [`tests/`](tests) | The `unittest` suite. |
| [`mkdocs/`](mkdocs) | The documentation site. |
| [`typings/`](typings) | Type stubs for the engine's `sbs` Pybind11 module. |
| [`bench/`](bench) | Micro-benchmarks for the runtime and layout. |

Root `script.py` is a legacy in-game demo and test harness from early development. It is
not how you run the tests today; see below.

## Running the tests

From the repo root:

```
python -m unittest discover -s tests
```

One rule that is not obvious: **every test file that touches file paths or MAST
compilation must call `test_set_exe_dir()` at module level**, before any class
definitions.

```python
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()
```

Cosmos embeds Python in a way that makes `__file__` unreliable, so
[`fs.py`](sbs_utils/fs.py) resolves paths from `sys.path[0]` &mdash; which
`unittest discover` sets to `tests/`. Without the call, every path lookup in that file
resolves against the wrong root.

[`.github/workflows/test.yml`](.github/workflows/test.yml) runs the stdlib-only suites
(AMD, the golden parse file, the lint rules) on every push and pull request. It is a
subset on purpose: much of the suite needs shipData and other data files that live in a
Cosmos install rather than in this repo.

More detail, including mock setup for new tests:
[Testing](https://artemis-sbs.github.io/sbs_utils/home/contributing/testing/).

## Running a mission outside Cosmos

`cosmos_dev` runs a real mission in an ordinary Python process, with a browser standing
in for the bridge consoles.

```
python -m cosmos_dev.mission_runner <mission> --gui              # browser GUI on :8765
python -m cosmos_dev.mission_runner <mission> --test 30 --map 0  # headless, pass/fail
python -m cosmos_dev.mission_runner <mission> --help             # every flag
```

The `sbs` CLI wraps the same thing as `sbs debug <mission> --map 0`.

When you are changing the library, add **`--use-working-tree`** so the run uses this
checkout instead of the packaged `.sbslib` sitting in `__lib__/`.

More detail, including VS Code debugpy setup:
[Debugging](https://artemis-sbs.github.io/sbs_utils/home/contributing/debugging/).

## Building the docs

The site is [mkdocs](https://www.mkdocs.org/) with the Material theme.

```
pip install -r requirements-mkdocs.txt
cd mkdocs
mkdocs serve                 # live preview on :8000
mkdocs gh-deploy --force     # publish to gh-pages
```

Publishing is **manual** &mdash; there is no docs CI. The only workflows in this repo
are releases and the offline test suites.

The build uses the multirepo plugin to pull the LegendaryMissions and OpenUniverse docs
into one site from their own repositories, so those projects' pages publish from here
too.

## Branches and releases

`master` carries the v1.3.0 line; `v1.4.0_dev` carries v1.4.0. A mission and every
library it loads must come from the same line.

The version comes from [`__lib__.json`](__lib__.json). Pushing a tag fires
[`.github/workflows/main.yml`](.github/workflows/main.yml), which zips `sbs_utils` and
`cosmos_dev` into `.sbslib` assets plus a typings archive and attaches them to the
GitHub Release.

```
sbs release . "What changed"     # tags from __lib__.json and pushes
sbs release . -u                 # un-release: delete the tag locally and on origin
```

By hand, that is:

```
git tag -a vXX.XX.XX -m "Some comment"
git push --tags

git tag -d vXX.XX.XX             # to redo a release, delete then re-tag
git push --delete origin vXX.XX.XX
```

The release tag is rolling within a line, so re-tagging updates the existing Release
rather than creating a new one.

## Typings

[`typings/`](typings) holds stubs for the engine's `sbs` Pybind11 module, so editors can
complete against an API that only exists inside the game. To regenerate: empty the
folder, run the script inside Artemis and choose **stubgen**.
