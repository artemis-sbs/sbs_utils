"""Rewrite pre-redraw face strings in source files, in place.

The six stock atlases were REPLACED in 2026-09 under the same aliases, so every face
string authored before then names cells that now hold something else. There is no way to
detect that at runtime - "ter #fff 3 0" was a feminine face and is now hair #3, the same
six tokens - so the repair has to happen where the strings are written down, by somebody
who knows the file predates the change.

    python _tools/face_migrate_sources.py <path> [<path>...]          # report only
    python _tools/face_migrate_sources.py <path> --write              # rewrite

Reports every change as old -> new so the diff can be read before it is taken.

RUNNING IT TWICE IS THE FOOT-GUN. Migration is not idempotent - a migrated string is a
perfectly valid face string, so a second pass reads it as if it were old and restyles
everybody again, silently. Nothing in the file can distinguish the two, so the tool keeps
a ledger of what it has already rewritten and refuses to touch those files again without
--force.

Dev-only, and deliberately not wired into any build.
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))

from sbs_utils.fs import test_set_exe_dir  # noqa: E402

test_set_exe_dir()
from sbs_utils import faces  # noqa: E402

#: A run of one or more layers. Deliberately anchored on the alias so it cannot match a
#: mod atlas (tng1 and friends are untouched - their art did not change).
LAYER = r"(?:ter|tor|ska|kra|zim|arv)\s+#[0-9a-fA-F]{3,6}(?:\s+-?\d+){2,4}\s*;?"
RUN = re.compile(r"(?:%s)+" % LAYER)

SKIP_DIRS = {".git", "__pycache__", "node_modules", "__build__", "site", "__lib__"}
TEXT_EXT = {".py", ".mast", ".amd", ".md", ".json", ".yaml", ".yml", ".txt"}


def migrate_text(text):
    """(new_text, [(old, new)]) for every face run in a blob of source."""
    changes = []

    def sub(m):
        old = m.group(0)
        # A run has to END in ';' to be a whole face - a trailing partial match would be
        # re-emitted normalised and quietly change a string that was never a face.
        core = old.rstrip()
        if not core.endswith(";"):
            return old
        new = faces.face_migrate(core)
        if not new or new == core:
            return old
        changes.append((core, new))
        return old.replace(core, new)

    return RUN.sub(sub, text), changes


LEDGER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out",
                      "face_migrate.done")


def load_ledger():
    try:
        with open(LEDGER, encoding="utf-8") as f:
            return {line.strip() for line in f if line.strip()}
    except OSError:
        return set()


def record(path):
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(os.path.abspath(path) + "\n")


def walk(paths):
    for root in paths:
        if os.path.isfile(root):
            yield root
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for name in filenames:
                if os.path.splitext(name)[1].lower() in TEXT_EXT:
                    yield os.path.join(dirpath, name)


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", nargs="+")
    ap.add_argument("--write", action="store_true", help="apply the rewrites")
    ap.add_argument("--quiet", action="store_true", help="counts only")
    ap.add_argument("--force", action="store_true",
                    help="rewrite even a file the ledger says was already migrated")
    args = ap.parse_args(argv)

    done = set() if args.force else load_ledger()
    files = hits = skipped = 0
    for path in walk(args.path):
        if os.path.abspath(path) in done:
            skipped += 1
            continue
        try:
            # newline="" both ways: read the exact bytes and write them back, so a
            # CRLF file does not silently become LF and turn a 2-line change into a
            # whole-file diff in a repo without autocrlf.
            with open(path, encoding="utf-8", newline="") as f:
                text = f.read()
        except (OSError, UnicodeDecodeError):
            continue
        new_text, changes = migrate_text(text)
        if not changes:
            continue
        files += 1
        hits += len(changes)
        print(f"{path}  ({len(changes)})")
        if not args.quiet:
            for old, new in changes:
                print(f"    - {old}")
                print(f"    + {new}")
        if args.write:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(new_text)
            record(path)
    verb = "rewrote" if args.write else "would rewrite"
    print(f"\n{verb} {hits} face string(s) in {files} file(s)")
    if skipped:
        print(f"skipped {skipped} file(s) already in the ledger (--force overrides)")
    if not args.write and hits:
        print("(report only - pass --write to apply)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
