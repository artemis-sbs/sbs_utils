# Tooling

Develop, test, and serve missions **outside Cosmos** with the `sbs` command line
tool and the `cosmos_dev` dev package (a browser mock GUI, headless testing, and a
web-page server). None of this ships inside a mission &mdash; it's for building and
debugging.

!!! warning "The mock is for testing only — not an engine replacement"
    The mock GUI and headless runner **approximate** the engine so you can test
    missions offline. They are **not** a reimplementation of Cosmos, and **100%
    parity is not a goal** &mdash; some behaviors are approximated or absent by
    design. Please **don't open issues or feature requests for more engine
    parity**; if something must behave exactly like the engine, verify it in
    Cosmos.

- [The `sbs` CLI](cli.md) &mdash; debug, soak-test, serve web pages, build libraries
- [Testing missions](testing.md) &mdash; headless conformance runs + the browser mock GUI
- [Serving web pages](web-proxy.md) &mdash; `sbs web` / `sbs web-static`
