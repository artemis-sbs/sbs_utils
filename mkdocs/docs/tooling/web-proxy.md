# Serving web pages

MAST [web pages](../build/web-pages.md) are served to browsers by a small
host-side proxy &mdash; the engine itself hosts no web server. It works two ways:

- **From a running engine** over the dev queue (`sbs web`), or
- **In-process** from a non-engine MAST host (the mock runner serves `//web`
  pages directly).

Either way there are **no engine changes**.

## `sbs web` &mdash; live server

```
sbs web .                 # serve this mission at /web/<page>
sbs web . --port 8770
```

- **Always-on**: start it before or after the engine; it re-arms when the engine
  appears and survives restarts.
- **Multi-engine**: front several engines from one server, routed by URL.
  ```
  sbs web --engine alpha=missionA --engine beta=missionB
  # /web/alpha/scores , /web/beta/scores
  ```
- **Live updates** via `web_refresh`, and **living pages** (`web_living`) are
  snapshotted at game end and served after the engine is gone.

The engine must be running the mission with the dev queue enabled &mdash; drop a
`dev_queue.enable` file in the mission dir (no env vars needed).

## `sbs web-static` &mdash; standalone HTML

```
sbs web-static . scores -o scores.html --query title=Standings
```

Renders `//web/scores` once to a self-contained HTML file &mdash; no live session,
scales to any number of viewers. Great for read-only dashboards/reports.

## How it works

Every GUI widget renders through a swappable `sbs` reference, and the dev queue
already runs `sbs_utils` Python inside the engine &mdash; so a web client's output
is captured in pure Python and bridged to the browser. Live frames stream over an
NDJSON push channel; static pages reuse the same renderer with the socket off.
