"""Let an addon declare ships the ENGINE will know, with no build step.

SUPERSEDED. Use :func:`sbs_utils.procedural.ship_data.add_extra` instead - an addon
SHIPS a ship-data file in its media pack and names it, and nothing is written at
any point::

    add_extra("turrets/extraShipData_turrets", mod="MyMod")

This route is kept working for anything that still calls it, and should not be
used by anything new.

WHY IT WAS SUPERSEDED - and note this contradicts a guarantee made further down
this docstring, which was true of the writer and false of the loader. There are
TWO readers of `extraShipData.json` and only one of them drops mod entries:

* the FLUSH's reader (`_read_mission_entries`) drops `#mod` entries before
  merging, so flushing twice really is not additive - that much held;
* `ship_data.get_ship_data()` prepends the file's whole `#ship-list`
  **unconditionally**, `#mod` and all.

So run 1 writes N generated entries to disk, and run 2 loads those N back AND the
addon declares the same N again. Measured on the TNG mod: 51 hulls became 102 from
the second run onward. The file the feature generates is the input that breaks it,
and no amount of care in the writer can fix a loader that does not know to ignore
its output.

The replacement avoids the class entirely by never writing: a media pack is
unpacked to disk once, so the engine can be handed a real folder, and the same
file is merged into the library. A mastlib cannot serve this because it is a zip
and the engine cannot read inside one - which is what the writing was working
around in the first place.

THE RULE THIS IS BUILT ON, measured rather than assumed: the engine reads a mission's
`extraShipData.json` **inside `create_new_sim()`**. Not at executable start, not at mission
load - at sim creation. Confirmed on engine 1.3.4 with a file that did not exist when
Cosmos launched: a script wrote it, called `sim_create()`, and the engine knew the ship.
(`SHIP_MOD_PLAN.md` s6a. The tell was `speed_coeff` coming back as 0.550000011920929 -
0.55 through float32 - where the library would have returned exactly 0.55.)

So the condition is "the file exists before `sim_create()`", and a script can satisfy it.
There is no CLI and no merge command.

HOW IT FITS TOGETHER. An addon declares its ships at story top level, exactly as it
declares interiors::

    ship_data_merge_mod(media_read_relative_file("myships.json"), "MyMod")

That runs at story compile, long before any sim exists. Entries accumulate here.
`sim_create()` then flushes them to `extraShipData.json` immediately before calling
`create_new_sim()` - see :func:`sbs_utils.procedural.cosmos.sim_create`.

WHY NOT A SIGNAL. A signal emitted just before `sim_create()` was the obvious design and is
wrong. A signal route is synchronous only while nothing in it awaits, and an addon's route
is someone else's code: one `await` in one mod's handler puts the write after the sim was
created, silently, on that mod's machine only. Putting the flush inside `sim_create()`
makes the ordering a fact of the call instead of a convention every addon has to honor.

WHAT IT WILL NOT DO:

* **Overwrite a hand-authored file.** A mission's own entries are read, kept, and win any
  key collision - the mod's version is dropped and reported by name.
* **Accumulate across runs** *when only the flush is looked at*. Generated entries carry
  ``#mod`` and the FLUSH's reader drops them, so writing twice is not additive. This does
  NOT hold end to end: ``get_ship_data()`` is a different reader and prepends the file
  whole, so the entries come back on the next run anyway. See SUPERSEDED, above.
* **Write when nothing asked for it.** No mod entries, no file touched.
* **Touch `data/shipData.yaml`.** Ever. That is the game's own table.
"""

import json
import os
import re

from ..fs import get_mission_dir, load_yaml_string
from .ship_data import SHIP_DATA_MOD_KEY, merge_mod_ship_yaml

#: A whole line whose first non-space characters are `//`.
_LINE_COMMENT = re.compile(r"^[ \t]*//.*$", re.M)


def _strip_line_comments(text):
    """Drop HJSON `//` comment lines so a YAML or JSON parser will accept the text.

    The shipped `extraShipData.json` example opens with them and every hand-written one
    copies that, so an add-on's file almost certainly has them - but neither `json` nor
    YAML accepts `//`, and YAML fails especially confusingly (a comment containing a colon
    reads as a mapping). Without this, a perfectly ordinary mod file is silently rejected.

    Only whole lines are stripped. A `//` inside a JSON string is safe because JSON strings
    cannot contain a literal newline, so no string value can start a line.
    """
    return _LINE_COMMENT.sub("", text)

#: The file the engine reads. camelCase, `.json` - its grid sibling is `extra_grid_data.json`
#: with underscores, and the two really are spelled differently. See the shipped example at
#: `missions_sh/production/missions/legendarymissions/example-extraShipData.json`.
EXTRA_SHIP_DATA = "extraShipData.json"

_pending = {}          # ship key -> entry, contributed by mods this mission
_pending_mods = {}     # ship key -> which mod supplied it
_last_written = None   # the exact text last written, so a re-flush is a no-op


def ship_data_merge_mod(content, mod=None):
    """Declare ship entries for the engine, from JSON/YAML text.

    .. deprecated::
        Use :func:`sbs_utils.procedural.ship_data.add_extra`, which points both the
        engine and the library at a file the addon SHIPS rather than generating one.
        This route reaches the engine by writing ``extraShipData.json``, which
        ``get_ship_data()`` then loads back on the next run while the addon declares
        the same entries again - measured at 51 hulls becoming 102 from run 2. Kept
        working for existing callers.

    Pair with ``media_read_relative_file`` so it works from a packaged ``.mastlib``::

        ship_data_merge_mod(media_read_relative_file("myships.json"), "MyMod")

    The entries also go into sbs_utils' own ``#ship-list`` (via ``merge_mod_ship_yaml``),
    so queries, ``filter_ship_data_by_side`` and the ``*_keys`` helpers see them without
    waiting for a sim to be created.

    Args:
        content (str): JSON or YAML text with a ``#ship-list``.
        mod (str, optional): Who supplied it. Stamped as ``#mod`` and used to name
            collisions.

    Returns:
        int: How many entries are pending, or ``None`` if nothing parsed.
    """
    if not content:
        return None
    content = _strip_line_comments(content)
    data = load_yaml_string(content)      # YAML is a JSON superset, so both parse
    if not isinstance(data, dict):
        return None
    entries = data.get("#ship-list")
    if not isinstance(entries, list):
        return None

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        key = entry.get("key")
        if not key:
            continue
        previous = _pending_mods.get(key)
        if previous is not None and mod is not None and previous != mod:
            from .execution import log
            log(f"ship data collision: '{key}' is supplied by both '{previous}' and "
                f"'{mod}' - '{mod}' wins. One of them should be renamed.",
                "ship_data", "warning")
        entry = dict(entry)
        if mod is not None:
            entry[SHIP_DATA_MOD_KEY] = mod
            _pending_mods[key] = mod
        _pending[key] = entry

    # Also give them to the library side, so the mission can query them immediately.
    merge_mod_ship_yaml(content, mod)
    return len(_pending)


def ship_data_pending_count():
    """How many mod-contributed entries are waiting to be written. Reset-ledger probe."""
    return len(_pending)


def _read_mission_entries(path):
    """The mission's OWN entries from an existing file, with generated ones dropped.

    Dropping anything carrying ``#mod`` is what makes flushing idempotent: without it, the
    entries this function wrote last time would be read back as mission-authored and
    re-merged, and a mod could never be removed.
    """
    if not os.path.exists(path):
        return [], None
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
    except OSError:
        return [], None
    try:
        data = json.loads(raw)
    except ValueError:
        # HJSON allows // comments; strict json does not. Strip them and retry rather
        # than treating a hand-authored commented file as unreadable.
        try:
            data = json.loads(_strip_line_comments(raw))
        except ValueError:
            from .execution import log
            log(f"{EXTRA_SHIP_DATA} could not be parsed; leaving it alone rather than "
                f"replacing it", "ship_data", "warning")
            return None, raw          # None means "do not touch this file"
    entries = data.get("#ship-list") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        return [], raw
    return [e for e in entries
            if isinstance(e, dict) and SHIP_DATA_MOD_KEY not in e], raw


def ship_data_flush_mod_file(mission_dir=None):
    """Write the mission's ``extraShipData.json`` so the engine can read it.

    Called by :func:`sbs_utils.procedural.cosmos.sim_create` immediately before
    ``create_new_sim()``, which is the moment the engine reads it. Safe to call when
    nothing is pending - it returns without touching anything.

    Returns:
        str | None: The path written, or ``None`` if nothing needed writing.
    """
    global _last_written
    if not _pending:
        return None

    base = mission_dir or get_mission_dir()
    path = os.path.join(base, EXTRA_SHIP_DATA)
    own, raw = _read_mission_entries(path)
    if own is None:
        return None                    # unparseable and hand-authored: do not clobber it

    # The mission's own entries win: someone wrote them by hand, on purpose.
    own_keys = {e.get("key") for e in own}
    merged = list(own)
    for key, entry in sorted(_pending.items()):
        if key in own_keys:
            from .execution import log
            log(f"ship data: '{key}' is already in {EXTRA_SHIP_DATA} by hand; the mod "
                f"entry from '{_pending_mods.get(key)}' is ignored", "ship_data", "warning")
            continue
        merged.append(entry)

    mods = sorted({m for m in _pending_mods.values() if m})
    text = json.dumps({
        "#credits-text": "GENERATED by sbs_utils before sim_create(). Entries marked "
                         "#mod come from add-ons and are rewritten every run; entries "
                         "without it are yours and are preserved. Contributing add-ons: "
                         + (", ".join(mods) or "none"),
        "#ship-list": merged,
    }, indent=4) + "\n"

    if text == _last_written and raw == text:
        return None                    # nothing changed; do not churn the file

    # Validate before anything replaces anything. A malformed extraShipData is a broken
    # game, not a broken feature.
    try:
        json.loads(text)
    except ValueError as e:
        from .execution import log
        log(f"refusing to write {EXTRA_SHIP_DATA}: generated content is not valid JSON "
            f"({e})", "ship_data", "warning")
        return None

    tmp = path + ".tmp"
    try:
        # Keep the previous file recoverable, once, before the first generated write.
        if raw is not None and not os.path.exists(path + ".bak"):
            with open(path + ".bak", "w", encoding="utf-8") as f:
                f.write(raw)
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)          # atomic on Windows and POSIX
    except OSError as e:
        from .execution import log
        log(f"could not write {EXTRA_SHIP_DATA}: {e}", "ship_data", "warning")
        try:
            os.remove(tmp)
        except OSError:
            pass
        return None

    _last_written = text
    return path


def ship_data_mod_reset():
    """Drop pending entries at a mission boundary.

    Per-mission state: the next mission enables its own add-ons, and inheriting these would
    write ships it never asked for into its folder.
    """
    global _last_written
    _pending.clear()
    _pending_mods.clear()
    _last_written = None
