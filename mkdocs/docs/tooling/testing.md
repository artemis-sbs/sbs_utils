# Testing missions

The `cosmos_dev` package runs missions **outside Cosmos**, so you can test in the
browser or headlessly in CI.

!!! warning "Testing aid, not the engine"
    The mock **approximates** Cosmos to make offline testing useful &mdash; it is
    **not** a reimplementation and **does not aim for 100% parity**. Some behaviors
    are approximated or absent by design. Please **don't file issues or feature
    requests for more engine parity**; confirm anything engine-exact in Cosmos.

## Mock GUI (in the browser)

```
sbs debug . --gui           # or just: sbs debug .
```

Opens a browser renderer at `http://localhost:8765/` with a 3D cinematic view and
a 2D radar, backed by an in-process mock of the `sbs` engine API. The mock is
calibrated to the real engine: ship speeds, 3D steering, per-facing shields, heat,
energy, and the weapons model (beams, torpedoes, drones, mines, EMP).

## Headless conformance run

```
sbs debug . --no-gui --map 0 --test 30
```

Plays ~30 sim-seconds, prints MAST coverage, and exits `0`/`1` with a pass/fail
verdict &mdash; ideal for CI. Add `--exercise` to actively drive
selections/comms/console-cycling for more route coverage, `--junit <path>` for a
JUnit report, and `--seed N` for reproducibility.

## Unit tests

The library uses `unittest`:

```
python -m unittest discover -s tests
```

See [Contributing &rsaquo; Testing](../home/contributing/testing.md) for writing tests
against the `cosmos_dev.mock` API.
