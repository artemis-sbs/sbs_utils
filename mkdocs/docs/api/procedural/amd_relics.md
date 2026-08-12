# Relics (AMD)

Reads a relic interior out of an `.amd` file and builds it — the declarative front end to
[Volume](volume.md).

## Overview

A relic is authored as **flat sibling records** in a `Relics` section: one record for the
relic itself, one per chamber, box or subtracted solid, joined by a `Relic:` field. See
[Relic interiors](../../build/relics.md) for the authoring guide; this page is the
function list.

Two things the reader remembers that are easy to overlook, because both exist to make
**live preview** work without any code in the mission:

- **Where the relic came from.** `relics_load` and `relics_build` stamp the file path and
  section onto every record, so `relic_reload` can re-read it later. A relic assembled in
  code has no source and is not reloadable — deliberately, and the tools say so rather
  than pretending.
- **Which volume it built.** A mission may build a relic under a name of its own. Anything
  that guesses the record's *key* instead then addresses a volume that does not exist and
  silently does nothing — which is exactly how one demo's authored `Scrape band:` never
  reached its watcher. `relic_volume_name` is the one right answer, and `relic_contain`
  and `relic_reload` both use it.

## Quick example

```
# build it, and start containment from the authored fields
rec = relics_build("maps/ossuary.amd")
relic_contain(rec)

# later - the editor's Preview button does this for you
relic_reload("ossuary")
```

A rebuild replaces the volume **in place** under the same name, so a live
`volume_watch` follows it automatically, keeping its margin and hold. It then emits
`relic_rebuilt` (`key`, `volume`, `file`) so a mission can re-scatter its own props;
nothing listening to that is a perfectly good outcome.

## API

::: sbs_utils.procedural.amd_relics
