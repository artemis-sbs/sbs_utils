# Creating a mission

A mission is a folder in your Cosmos `missions/` directory. Cosmos runs its
`script.py` at startup; almost everything else is written in
[{{ab.m}}](../mast/tutorial.md).

## Start from a template

From your `missions/` folder:

```
sbs templates              # see what you can start from
sbs create MyMission       # make one, and fetch the libraries it needs
```

`sbs create` writes the folder described below and downloads its dependencies, so
you can go straight to `sbs debug MyMission --map 0`. Pick a template up front with
`-t`:

| Template | What you get |
|---|---|
| `minimal` | One `@map` and a line of narration &mdash; the smallest thing that runs. |
| `sandbox` | Two sides, a station in an asteroid field, player ships, and raider waves. Start here if you want a mission. |
| `addon` | A shareable [add-on](../build/addons.md) plus a harness map to run it. |
| `amd` | Quests and science scans authored as data in an [`.amd` fact sheet](../build/amd-format.md). |
| `ou` | A whole procedurally generated universe, built on the OpenUniverse engine. |

Missions are pinned to a **release line** (v1.3.0, v1.4.0), and everything a mission
loads comes from the same line. `sbs create` picks the newest line your install
already has libraries for and never one newer than your copy of Cosmos &mdash; a
mission your game can't launch is not a useful starting point. It says which line it
chose and why; override with `-l` or `-b`.

Not every template exists on every line: a template can only use language and library
features its line actually has.

The templates live in the
[mast_starter](https://github.com/artemis-sbs/mast_starter) repository, so new ones
appear without updating the tool. See [the CLI](../tooling/cli.md#starting-a-mission).

## Folder layout

```
MyMission/
├── script.py         # required - Cosmos entry point (boilerplate)
├── story.mast        # required - your mission logic
├── story.json        # required - which libraries to load
├── description.yaml  # required - name/category shown in the mission list
├── settings.yaml     # optional - difficulty, player count, etc.
└── media/            # optional - images, skyboxes, music
```

Every template lays this down for you; the rest of this page is what those files are
for, so you can change them.

## The required files

**`script.py`** &mdash; boilerplate that wires the library to Cosmos:

```python
import sbslibs
from sbs_utils.handlerhooks import *
from sbs_utils.gui import Gui
from sbs_utils.mast.maststorypage import StoryPage

class MyStoryPage(StoryPage):
    story_file = "story.mast"

Gui.server_start_page_class(MyStoryPage)
Gui.client_start_page_class(MyStoryPage)
```

**`story.json`** &mdash; the libraries to load (see [Getting the library](get_library.md)):

```json
{
    "sbslib": ["artemis-sbs.sbs_utils.v1.4.0.sbslib"]
}
```

**`description.yaml`** &mdash; how the mission appears in the browser:

```yaml
format version: 1
Category: Standard
Visible Mission Name: My Mission
Description: A short description.
```

**`story.mast`** &mdash; the mission itself. Every mission starts at the implicit
`main`; a playable scenario is a `@map/` label:

```
@map/my_mission "My Mission"
" Fight off raiders.
    npc_spawn(0, 0, 0, "Home Base", "tsn, station", "starbase_civil", "behav_station")
    await task_schedule(spawn_players)
    ->END
```

## Next steps

- Learn the language: [{{ab.m}} tutorial](../mast/tutorial.md)
- Build features (GUI, comms, science, AI): [Build a mission](../build/index.md)
- Run and debug it in a browser: [Run & debug](../tooling/testing.md)
