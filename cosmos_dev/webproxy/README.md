# webproxy — MAST web pages from the real engine (no engine changes)

Serve MAST `//web/<path>` pages to browsers from a **running Cosmos engine**,
bridged over the dev queue. No engine/C++ changes: the engine already runs
`sbs_utils` Python (dev queue), and every GUI widget renders through
`FrameContext.context.sbs`, so a web client's output is captured in pure Python.

```
browser <-- WS/HTTP --> proxy.py <-- dev queue --> real engine (engine_side.py)
```

## Pieces
- `render_sink.py` — `WebRenderSink`: in-engine shim installed as
  `Gui.web_render_sink`; serialises a web client's `send_gui_*` into the wire
  commands `cosmos_dev.mockgui`'s `client.html` already renders.
- `engine_side.py` — in-engine API driven over the dev queue:
  `web_open / web_event / web_close / web_drain`.
- `proxy.py` — host process: runs the mockgui WS/HTTP server and shuttles
  browser ⇄ engine over the dev-queue files.

## Run
1. Launch the engine on a mission whose `story.json` loads the `cosmos_dev`
   sbslib + `cosmos_devqueue` mastlib, with at least one `//web/<path>` route.
   Enable the dev queue by dropping a `dev_queue.enable` marker file in the
   mission dir (or set `COSMOS_DEV_QUEUE=1`) - the marker lets you launch the
   engine normally, no env vars.
2. Start the proxy:
   ```
   python -m cosmos_dev.webproxy.proxy <mission_dir> --host 127.0.0.1 --port 8770
   ```
3. Open `http://127.0.0.1:8770/web/<path>` (e.g. `/web/scores?title=Hi`).

The proxy is **always-on**: start it before or after the engine; it (re)arms when
the engine appears and survives engine restarts (re-opening live sessions).

### Multiple engines behind one proxy
One web server can front several engines - route by URL `/web/<engine>/<page>`:
```
python -m cosmos_dev.webproxy.proxy \
    --engine alpha=/path/to/missionA \
    --engine beta=/path/to/missionB  --port 8770
# /web/alpha/scores -> engine alpha,  /web/beta/scores -> engine beta
```
A positional `mission_dir` (or a single `--engine`) is the default, served at
`/web/<page>` with no prefix. It works because every browser gets a unique
proxy-assigned client id, so each engine's frames route back to the right browser
with no collisions. Each engine has its own dev-queue + frames file (same machine;
cross-machine needs a shared filesystem or a network transport).

## Static pages (read-only, no live session)
For a read-only page (dashboard/report) you can render it **once** to a
self-contained HTML file instead of holding a live session:

```
python -m cosmos_dev.webproxy.snapshot <mission_dir> scores -o scores.html \
        --query title=Standings
```

It renders `//web/scores` once via `engine_side.web_snapshot` (open -> present a
few ticks -> capture -> close, no lingering session) and embeds the frames into
`client.html` as `window.__STATIC_FRAMES__` (`static_render.frames_to_html`), so
the renderer draws them once and skips the WebSocket. Open the file directly or
serve it from any web server - it scales to any number of viewers with zero
engine load after generation. Purely additive: the live `//web` path is
unchanged, and a simple page works either way.

## Verification status
Everything except the live-engine process and the browser render is unit-tested
against the mock (`tests/test_web_render_sink.py`, `test_web_engine_side.py`,
`test_web_proxy_contract.py`): open → drain browser frames (query params
included) → widget event mutates the world → close. The end-to-end run against a
real engine + browser is the remaining hands-on check.
