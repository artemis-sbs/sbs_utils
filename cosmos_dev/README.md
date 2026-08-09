# cosmos_dev — dev-only tooling

`cosmos_dev` is tooling for **building, testing, and serving** Artemis: Cosmos
missions outside the game. It is not part of a normal mission.

> ## ⚠️ For testing only — not an engine replacement
> The mock (`cosmos_dev.mock`) and mock GUI (`cosmos_dev.mockgui`) **approximate**
> the Cosmos engine so you can test missions offline. They are **NOT** a
> reimplementation of the engine, and **100% parity is not a goal** — many engine
> behaviors are approximated or absent by design.
>
> **Please do not open issues or feature requests asking for more engine parity.**
> If something must behave exactly like the engine, verify it in Cosmos.

## What's here

- **`mock/`** — an in-process mock of the `sbs` Pybind API, used by unit tests.
- **`mockgui/`** — the mock plus a browser GUI over WebSocket (`sbs debug --gui`).
- **`mission_runner.py`** — runs a mission headlessly or with the mock GUI
  (`--test` for CI conformance runs).
- **`overnight_runner.py`** — long soak runs under autoplay.
- **`devqueue/` + `engine_driver/`** — drive/query the **real** engine (run
  sbs_utils Python in-engine over a file queue).
- **`webproxy/`** — serve MAST `//web` pages to browsers (see
  [webproxy/README.md](webproxy/README.md)).

## How the threads fit together

The real engine is single-threaded (Python embedded via Pybind11). **The mock is not**, and
that is deliberate — physics runs off the main loop so a large mission's collision pass
cannot block GUI events or the MAST tick.

```
Main thread (60 Hz loop)
  |- GUI event drain       <- always immediate
  |- MAST tick (5 Hz)
  |- Client connect/disconnect
  '- Physics-event drain   <- queue.Queue, thread-safe

Physics thread (30 Hz, daemon)
  |- acquire sim._lock
  |- behavior dispatch      <- active objects only
  |- rotation + translation <- active objects only
  |- spatial-hash collision <- active-active + active-terrain only
  |- passive systems        <- active objects only
  |- release sim._lock
  '- _push_radar()          <- no lock needed (eventual consistency OK)

WebSocket server process
  |- drain gui_queue        <- batch all pending commands into ONE frame
  '- broadcast to clients
```

Physics runs at **30 Hz (`dt = 1/30`)**, matching the engine's `TICKS_PER_SECOND`. Terrain is
passive and never integrates — only `_active_ids` objects move, which is why asteroids do not
tumble in the mock. The radar stream is culled per ship (`CULL_RADIUS`) and tagged with a
`ship_id` so all consoles on one ship share a single message.

Full docs: the **Tooling** section of the sbs_utils documentation
(<https://artemis-sbs.github.io/sbs_utils/tooling/>).
