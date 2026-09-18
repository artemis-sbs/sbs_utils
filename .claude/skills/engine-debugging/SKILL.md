---
name: engine-debugging
description: Running and debugging against the REAL Artemis Cosmos engine rather than the cosmos_dev mock - launching Artemis3-x64-release.exe from the command line (autostartserver, defaultmission=, map=, key=value passthrough), getting values out of it (DEBUG/debug.log, file loggers, the send_gui wire tap, the devqueue, verdict files), the known engine-vs-mock divergences, the crash ledger (ObjectDataBlob, TreeRemove, CreateIndexList, HCDraw3DShip, grid list, enet, set_music_folder, standby) and the dump/cdb/ProcDump method, object lifetime (deferred deletes, tombstoned Agents, recycled ids, standby), and engine API traps. Use when running the engine yourself, investigating an engine crash / CTD / dump / assert / hang, when something "works in the mock but not the engine", when you need real engine-side values, when an object deletion / id / standby / stale-handle problem appears, or when a new exe changes the sbs API.
---

The engine is the only authoritative environment. The mock (`cosmos_dev`) is an
oracle for **our own output** (what the library sends), not for what the engine does
with it. A green headless run means "not obviously broken"; only the engine (or the
user's report of it) means "works". This file is how to get engine evidence quickly.

- Crash method and signatures: sections 5-6.
- Deletes, ids, standby: section 7.
- Mission authoring: the `writing-a-mission` skill. Packaging detail: the
  `packaging-and-release` skill.

---

## 1. Run the engine yourself

The engine accepts launch arguments (1.3.5+), so a run needs no mouse. Do not hand an
engine run back to the user - launch it, read the result, stop it. What stays genuinely
the user's is whether something LOOKS right.

```powershell
cd E:\a\Cosmos-dev
$p = Start-Process .\Artemis3-x64-release.exe -PassThru -ArgumentList `
     "autostartserver","defaultmission=<MissionFolder>","map=<map>"
# wait ~25-45s (a small mission ~25s, LegendaryMissions ~45s), read the report file...
$p.HasExited; $p.ExitCode        # 3221225477 / -1073741819 = 0xC0000005 = crashed
Stop-Process -Id $p.Id           # ALWAYS stop it - the server port is fixed
```

- Launching from a sandboxed tool call needs the sandbox disabled (it starts a GUI app).
- **Rebuild the libs first** (section 2) - the engine never reads the working tree.
- **The server renders** (a DX11 app with a render loop). **Server-only is the
  default.** Add a client only when the question is genuinely client-side (a per-console
  view, the client's own shipData / hull resolution):
  `Start-Process .\Artemis3-x64-release.exe -ArgumentList "autostartclient","clientautoconnectip=127.0.0.1"`.
  A second local instance has been seen to assert alongside the devqueue - if it does,
  stop; do not keep raising timeouts.
- **Launch args reach only the SERVER.** A client does not run `script.py`, so
  `autostartclient console=helm` is inert. `sbs run` seeds each client's console through
  `client_string_set.txt` instead (`sbs_cli/src/run_cmd.py`), and two clients on two
  consoles is `sbs run comms,weapons ...`, not raw args.
- `sbs run [consoles] [key=value ...] --mission X [--dry-run]` (sbs_cli) wraps all of
  this: server + standard consoles, extra args appended verbatim to every window.

### Launch arguments

| Kind | Arguments | Notes |
|---|---|---|
| Engine exe | `autostartserver`, `autostartclient`, `clientautoconnectip=`, `defaultmission=` | bare flags are argv-only |
| Library/mission (passthrough) | `map=`, `console=`, `profile=`, `var.NAME=`, `seed=`, `run=`, `record=`, `test=<s>` | any unrecognized `key=value` reaches `command_line_dict()` |

- **Any unrecognized `key=value` survives to the mission**, so a GUI-only step is not a
  reason to ask the user - add a launch argument. Read them with
  `procedural/command_line.py`: `command_line_get(key, default)`, `command_line_has(flag)`
  (bare flags, list-only), `command_line_list()` (index 0 is the exe path),
  `maps_find(spec)` for `map=`.
- `profile`, `map`, `console` and `var.*` are **mission-scoped**: after
  `run_next_mission` switches to a different mission than `defaultmission=`,
  `command_line_dict()` drops them (with one warning each) - argv belongs to the process.
- `test=<seconds>` writes `<mission>/records/verdict.json` (`procedural/conformance.py`):
  runtime errors, whether the duration was reached, engine version. It does **not**
  measure label coverage - the headless `--test` is the stronger check; this is the one
  that runs where the mock cannot.
- **Raw `sbs.command_line_dict()` is a pybind mapping, not a dict** - `"case" in args`
  has answered True for a key it did not contain. Library callers are safe
  (`_raw_dict()` wraps it in `dict()`); in a raw probe mission:

  ```python
  args = dict(sbs.command_line_dict())      # a real dict from here on
  which = str(args.get("case", "")).strip() # test the VALUE, not membership
  ```

---

## 2. Before an engine run: rebuild

**The engine loads `data/missions/__lib__/` zips, never the working tree.** Unit tests,
`--use-working-tree`, and a mission's own addon source all pass over a stale build.
Rebuild in the same breath as the change:

```
cd E:/a/Cosmos-dev/data/missions         # the missions ROOT; folder NAME as argument
python sbs.pyz lib sbs_utils             # the .sbslib
python sbs.pyz lib LegendaryMissions     # that mission's .mastlibs + media pack
```

Run them as separate statements; exit 0 is not evidence - open the zip and read the file
you changed. Use the deployed `data/missions/sbs.pyz` (it resolves paths relative to
itself). Details, release holds, and what each green check is blind to: the
`packaging-and-release` skill.

---

## 3. Getting values out of the engine

**Absent output looks exactly like absent execution.** Pick a channel that lands in a
file, then read it from the session START (where a `start_server` error lands), not the
tail.

| Where | Reaches you | Does NOT |
|---|---|---|
| Headless `mission_runner --test` | `print(f"TAG ...")` -> runner stdout, greppable | `log(msg, "category")` - a named logger with no handler goes nowhere, and the run still says PASS |
| Real engine | a FILE: `DEBUG(msg)`, or `logger(file=...)` + `log()` | `print()` - screen only; the exe hands back no stdout |

- **`DEBUG(msg)`** (`sbs_utils/mast/mast.py`) lazily opens
  `logging.FileHandler('debug.log', mode='w')` - relative to the process CWD
  (`E:\a\Cosmos-dev\debug.log`), not the mission folder. Works from anywhere, including
  `script.py`. Note the mission loader also writes `debug.log` at LOAD, so its last line
  is not a crash site.
- **`logger(name=, file=)`** (`procedural/execution.py`) attaches the FileHandler **only
  when `FrameContext.task` is set** - call it from MAST (e.g. the `@map` body), not
  `script.py` startup, or it is silently never added. `file` goes through
  `task.format_string` + `fs.get_mission_dir_filename` (a bare name lands in the mission
  folder); `file_mode='w'`. **Every call ADDS a handler** - clear
  `logging.getLogger(name).handlers` first or you double-log.
- **Always read `<mission>/mast.runtime.log` after an engine run** - a background task
  can die while everything else looks fine. 0 bytes at crash time rules the script layer
  out. Each `mission_runner` reload archives it to `mast.runtime.run<N>.log`.
- Never hand-roll a writer from `__file__` in library code (CLAUDE.md fs.py rule). A
  throwaway probe's `script.py` may.
- Before blaming your diff for an engine-only symptom, `git log --since` in EVERY repo
  involved - shared modules change under you.

### The wire tap: library or engine?

"Is this widget bug ours or the engine's" is decided by the exact message the library
hands the engine. Capture it inside the real engine by wrapping the sender at the top of
the mission's `script.py`, **before** `from sbs_utils.handlerhooks import *`:

```python
import sbs as _sbs, os as _os
_LOG = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "probe.log")
_orig = _sbs.send_gui_typein
def _tap(client_id, parent, tag, props, l, t, r, b, *a, **k):
    with open(_LOG, "a") as f:
        print("tag=", tag, "rect=", (l, t, r, b), "props=", repr(props), file=f)
    return _orig(client_id, parent, tag, props, l, t, r, b, *a, **k)
_sbs.send_gui_typein = _tap
```

`sbs` is a module, so the assignment sticks and `ctx.sbs.send_gui_*` picks it up. Order:

1. **Headless capture** - tap `cosmos_dev.mock.sbs` senders (or `cosmos_dev/layout_audit.py`)
   and diff the stream across variants / N rebuilds.
2. **In-engine tap** (above) - confirms the capture is faithful.
3. **Library-free probe** - a mission whose `script.py` defines `cosmos_event_handler`
   with no `sbs_utils`, replaying the captured raw `sbs.send_gui_*` calls. If the bug
   survives, it is the engine's.

If props are byte-identical and the relevant rect dimension is unchanged across variants,
the library is not the variable - say so and stop.

### The devqueue: query a live engine

`cosmos_dev/devqueue/` (engine side, packaged as the opt-in `cosmos_devqueue.mastlib`) +
`cosmos_dev/engine_driver/driver.py` (host side). The consumer polls a JSON command file on
app-time (`delay_app`, so it answers at a paused lobby), gated on the `COSMOS_DEV_QUEUE`
env var.

```python
from cosmos_dev.engine_driver import EngineDriver
drv = EngineDriver(cosmos_dir=r"E:/a/Cosmos-dev", mission="quick_example")
drv.build_mastlib(); drv.enable_in_story()
drv.launch(map="<map>")      # passes autostartserver defaultmission=<mission> map=<map>
print(drv.eval("1+1"))       # round-trip proof; send()/ping()/read_log()/screenshot()
drv.close()
```

- `launch()` **taskkills any running Artemis first** (fixed server port).
- The queue sequence must be monotonic across host runs (time-based ms) or the
  long-lived consumer dedups and you read a stale reply.
- `enable_in_story()` edits the mission's `story.json` - revert it (and the
  `dev_queue.*.json` artifacts) when borrowing someone's mission.
- Starting a map from the queue: `task_schedule_server(map_label, defer=True)` +
  `GAME_STARTED` + `signal_emit("game_started")` + `resume_sim()`.

---

## 4. Engine vs mock divergences

A mock kinder than the engine makes a fix and its absence indistinguishable. **When you
find a divergence, fix the mock in the same change** (and write the test so it fails
without the fix). The inverse - inventing behavior the engine lacks - needs asking first.

| Engine | Mock (historically) | Guard now |
|---|---|---|
| The event is **read-only** (Pybind11) | `FakeEvent` was writable, so re-stamping it "worked" | `FakeEvent.freeze()` (`helpers.py`) called at the choke point in `cosmos_event_handler`; carry per-frame values on something you own |
| Unset `data_set` field answers **`None`** | Typed default from `_DATA_SET_DEFAULTS` (`cosmos_dev/mock/sbs.py`) | `mission_runner --strict-blob`; `sbs lint` `blob-unguarded-none` (`procedural/blob_lint.py`); use `get_data_set_value(id, key, index, default=)` - the 3rd positional is an INDEX |
| `push_to_standby_list_id` on a dead id = **server CTD** | Silently no-oped | Mock now raises `ValueError` |
| Deletes free C++ memory synchronously; use-after-free is real | Frees differently | UAF prevention is confirmable only in the engine |
| **A tick always follows an event** (`tick_the_rest`) | Tests could dispatch N clicks with no tick between | A test `click()` = `Gui.on_message(...)` + present (`tests/test_gui_message_dead_builder.py`) |
| `--map` / `--exercise` paths | Start maps during server init, fake `client_connect` | Trace the production entry path before claiming a fix is reachable |

`if energy < 30` on a raw blob read runs headless for years and ends a task silently on
a bridge (`'NoneType' < int`) - and since a failing expression stops the command, the
feature just stops.

Wording: say **"should fix X - unverified in the engine"** unless the symptom was seen
to go away there.

---

## 5. Crashes: triage table

Read the stack before assuming which one you have - a dump folder holds a mix. Offsets
compare only within one build.

| # | Signature | Cause | Status | Workaround |
|---|---|---|---|---|
| 1 | **ObjectDataBlob**, server main thread: `map::operator[]` <- inlined `ObjectDataBlob::Get` (`ObjectDataBlob.cpp:358`) <- `Simulation::Tick` (`Simulation.cpp:170`). Corrupt `_Myhead` (often `0xBAADF00D...`). The dominant CTD, seconds-minutes in | Every ~15 ticks the engine walks `objects->allList` calling `blob.Get("exciting")`; one `SpaceObject*` is dangling. Leading cause: **spawn + delete of one SpaceObject in the same frame** (adds are deferred via `objectToAddList`) | Script side fixed (nebula markers merged before spawning, `tests/test_nebula_marker_merge.py`); not engine-confirmed | Never create+delete in one frame; start the map and let art load **before** clients connect |
| 1b | `RTDataTracker::AddData` (`RTDataTracker.cpp:33`), network sub-thread; or a "string too long" dialog | Corrupt `std::string` into `AddData` | OPEN, unrelated to #1 - do not pool counts | none |
| 2 | **SuperContainer::TreeRemove** (`SuperContainer.cpp:335`) <- `TreeUpdate` (:378) <- `Simulation::Tick` (:156); later also `0xC0000374` heap corruption | `while (index != root)` never tests the `-1` parent sentinel (`TreeInsert:277` uses `>= 0`), so it reads and writes node[-1]. Trigger: duplicate `AddToUpdate` entries, `Remove()` scrubs only the first | Root-caused from engine source; C++ repro harness + patches handed to the engine team | none script-side |
| 3 | **CreateIndexList assert** "elementCount is zero" (client), or its AV twin at `ProcessAssetDataMessage -> PointSandwich::CreateDrawAssets` | Client draws placeholder `ships/unknown` (a hull failed to resolve client-side); a hull with no internal-map fields in shipData gets no pointcube grid | Data-fixed for `unknown`; real fix = engine bounds check | Connect clients only after the server has started the map |
| 4 | **HCDraw3DShip -> HCDrawMeshToScreenRect** (`RenderManager.cpp:1411`) under `RetainedGUIManager::DrawSection` (client) | Mod hull mesh partially built; suspected client/server cache aliasing on reskinned keys. Unproven | OPEN | Avoid `gui_ship` in the ship picker (the only party-path producer of `send_gui_3dship`) |
| 5 | **ViewGridObjectListDraw** (client render thread, engineering `grid_object_list`), "read of 0xFFFF..." | A non-canonical address (recycled memory), not a -1 sentinel; suspect grid object deleted under the list | Mitigated: `grid_delete_object` clears `grid_selected_UID`; dropped engine widgets pushed offscreen | - |
| 6 | **Client enet double free on disconnect** `0xC0000374`, `enet_peer_reset_queues <- enet_peer_disconnect <- PaxEnetNetworkClient::DisconnectFromServer` | Engine locking: `PaxEnetNetworkClient::Send -> enet_peer_send` takes no lock while the net thread services the host | OPEN, reported | - |
| 7 | **set_music_folder** `PaxXA2StreamingSong::Start`, read of 0x0 | Any PATH argument: lookup fails, result used unchecked. Absolute path HANGS (no dump) | Reported - do not re-investigate | Bare folder names only; `MUSIC_ENGINE_ACCEPTS_PATHS` (`mast_sbs/story_nodes/media.py`) gates the path branch until fixed |
| 8 | Early segfault `0xC0000005` at t+9-12s in ~50% of `peacetime_remastered` launches, **no dump** | Unknown; may be #1 or #2 | OPEN | Repro: `python -m cosmos_dev.tools.mission_soak ../LegendaryMissions peacetime --engine --runs 6 --seconds 45 --timeout 300`; needs ProcDump |
| 9 | `SuperContainer::PushToStandbyList` (:562) <- `GSPushToStandbyListID` (`MissionScript.cpp:378`), read of 0x38 | `push_to_standby_list_id` on an id the engine no longer has | FIXED script-side (`procedural/standby.py::_standby_push`) | Guard with `object_exists` (section 7) |

Also latent in `SuperContainer` (not yet seen in the field): `SyncHeirarchy:424` (`!= 0`
not `>= 0`) and `BroadTest:394/413` (a `-1` child -> unbounded recursion -> `0xC00000FD`).

**Known-benign crash-histogram offsets** (deliberate path probes, seconds of uptime): a
failed asset load null-derefs rather than failing - `Yaml::load`, the PointSandwich ctor,
`Draw3DMesh`, `GetVertexPosition`.

**Confounders that have cost the most:** client-connect timing moved together with other
variables (hull choice, roster size) and got the wrong one blamed - ask what else changed
with the variable you A/B'd. A hypothesis that fits every timestamp can still die in the
A/B. Uptime is PROCESS age, not play time (an engine left on the picker overnight accrues
hours).

---

## 6. Crash investigation method

### Exit code first - a missing dump means nothing

- **The verdict is the process exit code**: `3221225477` / `-1073741819` = `0xC0000005`
  (`$p.ExitCode`, `Popen.returncode`). The exe installs `SetUnhandledExceptionFilter`,
  so WER often records no dump and no event.
- An MSVC assert that is ABORTED leaves nothing. On a CRT assert dialog press **Retry**
  (raises `80000003`, WER captures the stack). Faulting module for an assert: `ucrtbase.dll`.
- Dumps: `%LOCALAPPDATA%\CrashDumps\Artemis3-x64-{release,debug}.exe.<pid>.dmp`.
  **The folder caps at 10 and evicts the oldest.** A full folder writes nothing new, and
  anything that crashes on purpose (a fuzzer, a repro harness) flushes the real dumps.
  **Copy dumps out before running anything that faults deliberately**, and never delete
  them - they are evidence.

### Event log - fault offset, build id, uptime without a dump

`Get-WinEvent -FilterHashtable @{LogName='Application'; ProviderName='Application Error'}`,
filter `*Artemis3*`:

| Property | Meaning |
|---|---|
| `[2]` / `[5]` | app / faulting-module PE timestamp = **the build id** (group by it first) |
| `[6]` | exception code: `c0000005` AV, `c00000fd` stack overflow, `c0000374` heap corruption, `c0000409` fastfail |
| `[7]` | fault offset (RVA) |
| `[8]` | pid |
| `[9]` | process start FILETIME -> `[datetime]::FromFileTime()` -> uptime |

Read of `0x0` = missing resource / unchecked lookup (load-time). A plausible heap-shaped
address = use-after-free or stale index (volume/lifetime). A reported
`0xFFFFFFFFFFFFFFFF` may be a non-canonical address - read the real register.

### ProcDump for a real capture

```
E:\a\Cosmos-dev\tools\procdump64.exe -accepteula -ma -e -x <absdumpdir> Artemis3-x64-release.exe autostartserver defaultmission=X map=Y
```

`-e` catches the first-chance exception; `-ma` is a full dump (4-6 GB - keep one per
distinct site). WER minidumps have **no heap**, so only a full dump shows what surrounds a
corrupt pointer. `<absdumpdir>` must be absolute and exist (a relative one resolves
against the engine CWD and the launch "dies in 0s").
`python -m cosmos_dev.engine_soak --mission X --map Y --profile autoplay7 --hours N` (run
from `data/missions`) automates launch-under-procdump, exit codes, dump analysis and
per-arm A/B (`--arms A,B`). `cosmos_dev/tools/engine_soak.py` is a separate
client-connect-timing soak that freezes and hashes `__lib__` for the whole run.

### Symbolize with cdb - never hand-roll a stack

`winget install Microsoft.WinDbg`. `cdb.exe` lives inside the MSIX under
`C:\Program Files\WindowsApps\Microsoft.WinDbg_*_x64__8wekyb3d8bbwe\amd64\` - a glob there
returns empty (ACL) and reads as "not installed"; resolve the version with
`Get-AppxPackage` (`engine_soak.py::_find_cdb` does this).

```
cdb -z <dump> -y E:\a\Cosmos-dev -i E:\a\Cosmos-dev -c ".lines -e; .symfix; .reload; !analyze -v; .ecxr; kn; q"
```

- PDBs ship beside the exes (`Artemis3-x64-release.pdb` / `-debug.pdb`); `.lines -e`
  gives file:line. `cosmos_dev/crash_format.py` renders the output.
- Ignore `!analyze`'s `WRONG_SYMBOLS ... ntdll` bucket; use `.ecxr; kn`. Add the
  Microsoft symbol server to `-y` for ntdll frames.
- A raw stack scan finds stale slots and **cannot see inlined frames** - it once named
  `ObjectDataBlob::Set` when the real caller was an inlined `Get`. Source comments that
  say `Set` about those crashes are unverified.
- `dt` the real types from the PDB before naming a mechanism; `uf /c <fn>` lists every
  call (fast check for `_Mtx_lock`); `dps` on a vtable maps `call [rax+N]` to names.

### Techniques that pay

- **Register arithmetic proves a chain with no heap**: `base + index*scale + disp ==
  fault address` separates a run-off index from a dangling pointer.
- **Scan the crash thread for ASCII** (hull keys, blob keys). But strings below `rsp` are
  often exception-dispatcher CONTEXT copies - if the slot 8 bytes on is the faulting RIP
  (x64 CONTEXT: Rip at `+0xF8`), it is a copy, not evidence.
- The engine command line is recoverable from dump memory (search `autostart`).
- Correlate: `profile=autoplay*` soaks append every run to
  `data/missions/game_results.yaml`; check nothing under `data/missions` was rebuilt
  mid-soak.
- For a client-only path (#3, #4), add the client process to the repro - server-only
  will not hit it.

---

## 7. Object lifetime and ids

### Deletes are deferred - always use the procedural wrapper

`sbs.delete_object(id)` / `sbs.delete_grid_object(host, id)` **free the C++ object
synchronously**. With many MAST tasks interleaved on one thread, another task holding
that object / `engine_object` / `data_set` then derefs freed memory - or a recycled slot
now owned by a new spawn.

So `sbs_utils/delete_queue.py` (`DeleteQueue.queue/queue_grid/drain/has_pending/is_pending`)
defers them: the procedural `delete_object(id_or_objs)` (`procedural/space_objects.py`),
`SpaceObject.delete_object()`, `GridObject.delete_object()` and `grid_delete_object`
tombstone the Agent NOW and enqueue; `cosmos_event_handler` drains after
`Dirty.represent_dirty()` (the "no task mid-statement" boundary).

- **Never call raw `sbs.delete_object`** - it bypasses the queue and the tombstone.
- **`sim.delete_object()` does not exist.** An `except: pass` around it deleted nothing
  for years in two places. An `except` around an unverified call turns a misspelling
  into a silent behavior change.
- **Never spawn and delete a SpaceObject in the same frame** (crash #1).
- `GarbageCollector.collect()` is not a free point.

### The tombstone

`Agent._alive` (`agent.py`) goes False on remove: `data_set` / `engine_object` return
None, and `to_object()` returns None for a dead Agent, CloseData or SpawnData. Before
this, `->END if to_object(x) is None` was inert whenever `x` was an OBJECT rather than an
id. Anything that hands out the engine object needs the same check - guard `to_blob()`
results (`if blob is None: return`).

### "Does it exist?" - pick the right question

| Check | Answers |
|---|---|
| `to_object(id) is not None` | the live test; False immediately after a deferred delete |
| `object_exists(id)` (`procedural/query.py`) | False if `id in DeleteQueue._pending`; False for a non-space id (asking the engine about one would assert); else engine `space_object_exists`. **True for a standby-parked object** |
| engine name/tag/id lookups (`get_grid_object_by_name`, `_by_tag`, `_by_id`) | **still resolve until the queue drains** - a "restore" can find the objects a rebuild just deleted |
| `grid_object_valid()` | the blob; still valid until the free - not a substitute |
| `sbs.in_standby_list_id(id)` | parked/docked vs destroyed - never use `not object_exists` for that |

A GridObject Agent's `.data_set` is not the engine blob (`curx` reads 0) - use
`grid_pos_data(id)`.

### Recycled ids and dangling links

- **The engine recycles ids.** `Agent._remove(id)` purges `Agent.roles`,
  `Agent._has_inventory` and `Agent.has_links` via `remove_every_collection(id)`; a
  missed mirror once let a new object with a recycled id inherit a dead one's brain entry.
  Anything keyed by a raw id that outlives the object is suspect.
- **Incoming links dangle by design** - links are uni-directional raw ids with no reverse
  index. After recycling, a stale member id can resolve to a DIFFERENT object. Resolve at
  read time and prune; a library function that takes a link set must do its own cull:

  ```python
  for member_id in list(linked_to(fleet_id, "ship_list")):   # list(): unlink mutates it
      if object_exists(member_id):
          live.append(member_id)
      else:
          unlink(fleet_id, "ship_list", member_id)
  ```

### Standby (parking)

- `push_to_standby_list_id(id)` suspends physics + replication; it is not a delete, and
  the object stays `object_exists` True (engine-confirmed; mock matches).
- **Pushing an id the engine no longer has is a server CTD** - null deref, no raise, no
  log (crash #9). Double push is safe; retrieve is safe by luck but inserts a null key.
  Guard both with `object_exists(id)`, which also catches tombstoned ids -
  `procedural/standby.py::_standby_push/_standby_retrieve` are the model
  (`tests/test_standby.py::TestStandbyNeverPushesADeadId`).

### Script conventions

- Hold **ids, not objects**; guard `->END if not object_exists(id)`, then re-resolve
  `to_object(id)`.
- `engine_object` / `data_set` are borrow-only - never stash across `await` / `yield`.
- One owner deletes; others observe `//damage/destroy` / `//damage/killed`.
- Test against the SIM, not the bookkeeping: a dict that empties while the objects live
  passes; only the total object count moves for an orphan.

---

## 8. Engine API facts and traps

- **A raising `TickDispatcher.do_interval` callback freezes the mission.**
  `TickTask._update` calls `self.cb(self)` bare (`tickdispatcher.py`), `dispatch_tick`
  iterates bare (other tasks silently skip that tick), `tick_the_rest` is bare, and
  `_cosmos_event_handler`'s `except BaseException` **pauses the sim** and pushes
  `ErrorPage`; from then on the handler short-circuits every event except the error
  page's clicks. `TickTask.start` is only refreshed after the callback returns, so
  **Resume fires the same task immediately and it raises again** - unrecoverable without
  a restart. Guard every interval body per item and drop the offender;
  `DripQueue._run` ("One bad item must not take down the tick loop") is the precedent.
- **A tick always follows an event.** Every `_cosmos_event_handler` case ends in
  `tick_the_rest(event)` (-> `TickDispatcher.dispatch_tick()` + `Gui.present`). Two
  clicks cannot land between ticks; reasoning that needs N queued events is wrong for the
  engine.
- **The engine offers no quit.** A mission cannot end the process - it leaves evidence
  (a verdict / report file) and the launcher supplies the exit code.
- **`reposition_space_object` exists twice** - `sbs.reposition_space_object(space_object,
  x, y, z)` and `sim.reposition_space_object(space_object, x, y, z)`, both taking the
  engine handle, not an id. **Version-dependent, measured with
  `data/missions/repos_probe`:** on engine **1.3.11** the module-level `sbs.` form raised
  `ValueError: invalid input position, after calling reposition_space_object` for every
  input and moved nothing (the message blames the coordinates; the failing check is
  `VALID_SPACE_OBJ`), while `sim.` worked. On engine **1.3.13** (2026-09-18) `sbs.` works -
  positional, keyword and on a player ship. The library's call sites (`spaceobject.py`
  `pos` setter and `MSpawn.spawn_common`, `procedural/space_objects.py`,
  `procedural/internal_damage.py`, `procedural/a2x/spawn.py`) call **`sbs.`** (commit
  `3a7b2467`), so **1.3.13+ is required**: on a 1.3.11 install every spawn and `.pos`
  write through the library raises. Re-run the probe (`autostartserver
  defaultmission=repos_probe`, read `repos_probe.txt`) whenever the exe changes. The mock
  answers both forms.
- `sbs.set_music_folder` takes a bare name under `data/audio/music/` - a path segfaults or
  hangs (crash #7).

---

## 9. New engine API: read the stub diff

When a new exe lands, **`git diff typings/sbs/__init__.pyi`** is the API change list -
the stub is regenerated from the running exe ("stub gen" commits) and is usually sitting
uncommitted in the working tree. Read the `def` line, not the prose.

- **The pybind docstring lags** - it is hand-written in C++ and not regenerated with the
  signature (a 10th `name: str = 'unset'` parameter has appeared with a 9-arg docstring).
- **`E:\a\Cosmos-dev\data\script_documentation.txt`** is only as fresh as its last dump -
  compare its mtime to the exe's before trusting it.
- The exe's string pool is a third confirmation: pybind arg names appear in order,
  followed by default literals - useful across archived `Artemis3-x64-release-*.exe`
  copies.
- **A defaulted new parameter breaks nothing until the library passes it - then the MOCK
  breaks.** `cosmos_dev/mock/sbs.py` and `cosmos_dev/mockgui/sbs.py` are hand-written
  twins that know nothing of the stub; update both in the same change.
