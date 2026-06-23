# Running and Writing Unit Tests

`sbs_utils` uses the standard **`unittest`** framework.  No extra packages
are required — everything runs with the Python bundled in your dev environment.

---

## Running the Tests

From the repo root (`missions/sbs_utils/`):

```sh
python -m unittest discover -s tests
```

All test files in `tests/` are discovered automatically.  A passing run
currently shows ~200+ test cases.

---

## The `test_set_exe_dir()` Requirement

Cosmos embeds Python in a non-standard way; `__file__` on `script.py` is
unreliable at runtime.  The `fs` module resolves paths from `sys.path[0]`,
which `python -m unittest discover` sets to `tests/` — not the project root.
This breaks all path resolution unless corrected.

**Every test file that touches file paths or MAST compilation must call
`test_set_exe_dir()` at module level**, before any class definitions:

```python
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest
# ... test classes follow
```

`test_set_exe_dir()` uses `__file__` from `fs.py` itself (a library module
whose path is always reliable) to locate the project root.  Calling it
re-initialises `fs.exe_dir` and `fs.script_dir` correctly.

---

## Mock Setup

`cosmos_dev/mock/sbs.py` provides a partial stub of the Pybind11 `sbs` API so
tests can run without a Cosmos process.

Typical test setUp:

```python
import unittest
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.agent import Agent
from sbs_utils.spaceobject import SpaceObject

class MyTest(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        SpaceObject.clear()   # reset all agent state between tests
```

`SpaceObject.clear()` resets `Agent.all` and all role/link tables.  Always
call it in `setUp` so tests are isolated.

---

## Importing MAST Node Types

If your test compiles or runs MAST scripts, you must import the node
registries **before** compiling.  Import order matters — core nodes before
Cosmos extensions:

```python
from sbs_utils.mast import core_nodes               # registers built-in node types
from sbs_utils.mast_sbs import story_nodes          # registers Cosmos node types
from sbs_utils.mast_sbs import mast_sbs_procedural  # wires procedural API
```

!!! warning
    `story_nodes` must be imported explicitly in each test file that uses it.
    Do not rely on test-discovery order to import it as a side effect of
    another test file running first.

---

## Test File Checklist

When writing a new test file:

- [ ] Call `test_set_exe_dir()` at module level if any path resolution or MAST
      compilation is involved.
- [ ] Import `core_nodes` and `story_nodes` before any `Mast.load()` call.
- [ ] Call `SpaceObject.clear()` in `setUp` to reset agent state.
- [ ] Create a fresh sim with `sbs.create_new_sim()` and set
      `FrameContext.context` before calling any procedural API.
- [ ] Inherit from `unittest.TestCase`; use `self.assertEqual`, `self.assertTrue`,
      etc. — not pytest assertions.

---

## Running a Single Test File

```sh
python -m unittest tests.test_my_module
```

Or a single test method:

```sh
python -m unittest tests.test_my_module.MyTestClass.test_something
```

---

## What to Test

- **Procedural API functions** — call with a mock sim, assert return values and
  side effects on `Agent` / `SpaceObject` state.
- **MAST compilation** — compile a snippet with `Mast.load()`, assert that
  expected labels/nodes are present.
- **MAST execution** — run a snippet through `cosmos_event_handler` and assert
  that signals fired, inventory changed, etc.
- **`fs` path helpers** — call `get_script_dir()`, `get_mission_dir_filename()`,
  etc. and assert the returned path is correct.

Avoid testing the GUI layer (`send_gui_*` calls) — the mock stubs these as
no-ops and browser rendering cannot be asserted in unit tests.
