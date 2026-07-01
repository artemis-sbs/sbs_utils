# Creating a mission

A mission is a folder in your Cosmos `missions/` directory. Cosmos runs its
`script.py` at startup; almost everything else is written in
[{{ab.m}}](../mast/tutorial.md).

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
