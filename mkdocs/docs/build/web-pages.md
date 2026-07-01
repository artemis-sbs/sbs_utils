# Web pages

Author **browser pages in MAST**, using the same `gui_*` layout you already know.
A `//web/<path>` route becomes a page you open in a browser while a mission runs
&mdash; with **no engine changes**. Great for venue scoreboards, operator
dashboards, and debug panels.

## A live page

Add a `//web/<path>` route and build it like any GUI:

```
//web/scores
    gui_section("area: 5,5,95,95;")
    """Cosmos Standings"""
    """Stations: {len(to_object_list(role('station')))}"""
    gui_button("Refresh")
    await gui()
```

Run the [web server](../tooling/web-proxy.md) and open
`http://localhost:8770/web/scores`. Widget events (buttons, dropdowns) route back
to the page exactly like a console.

Web clients are **not** consoles: they never enter console-select or get a player
ship, and they carry the `__web__` role so mission code can target viewers.

## Parameters from the URL

A query string seeds page variables:

```
//web/scores
    default title = "Standings"
    gui_section("area: 5,5,95,95;")
    """{title}"""
    await gui()
```

`/web/scores?title=Final%20Results` renders with that title.

## Living pages (update during the game, keep after)

A leaderboard should update while playing **and** still be viewable after the
game. Declare it living, and refresh it when the data changes:

=== ":mast-icon: {{ab.m}}"
    ```
    //web/scores
        web_living(persist=True, refresh=5)   # persist on game end; snapshot every 5s
        gui_section("area: 5,5,95,95;")
        """{get_scoreboard_text()}"""
        await gui()
    ```

- `web_refresh("scores")` &mdash; call from mission code when stats change; every
  open browser re-renders.
- `web_living(persist=True, refresh=N)` &mdash; declare the page persistent. The
  web server snapshots it when the game ends (and every `N` seconds) and serves
  the saved copy at the **same URL** once the engine is gone.

## Static pages (read-only, no live session)

For a read-only report you can bake a page to a standalone HTML file &mdash; no
live session, scales to any number of viewers:

```
sbs web-static . scores -o scores.html --query title=Standings
```

See [Tooling: the web server](../tooling/web-proxy.md) for `sbs web`,
`sbs web-static`, multi-engine serving, and how it works in the mock vs. the real
engine.

## Navigation

Move an open session to another `//web` page from mission code:

```
web_page_navigate(client_id, "admin/panel")
```

A browser can also just open a different `/web/<path>` URL.

!!! note "Same page, live or static"
    A simple page works **both** ways unchanged &mdash; `sbs web` serves it live,
    `sbs web-static` bakes a snapshot. Pages that rely on live updates or in-place
    buttons only make sense served live.
