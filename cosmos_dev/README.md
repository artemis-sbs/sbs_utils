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

Full docs: the **Tooling** section of the sbs_utils documentation
(<https://artemis-sbs.github.io/sbs_utils/tooling/>).
