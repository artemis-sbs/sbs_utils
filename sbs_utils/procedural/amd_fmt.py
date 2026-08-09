"""A canonical formatter for AMD files - safe, idempotent, prose-preserving.

AMD is prose-first, so the formatter is deliberately conservative: it normalizes
*structure and whitespace* and never reflows or rewrites prose. Guarantees:

  * it does not change the parsed model - `amd_core.parse(fmt(x))` has the same
    nodes and references as `amd_core.parse(x)` (see test_amd_fmt);
  * it is idempotent - `fmt(fmt(x)) == fmt(x)`.

What it normalizes:
  * trailing whitespace stripped from every line;
  * link-form headings -> `#{level} [Display](urn)` (one space, no stray spaces);
  * other `#`-headings -> one space after the hashes;
  * `---` data fences -> exactly three dashes (content inside preserved verbatim);
  * runs of blank lines collapsed to one; leading/trailing blanks removed;
  * exactly one trailing newline.

Dependency-free (stdlib `re`), so it's unit-testable and embeddable anywhere.
"""
import re
from sbs_utils.procedural.amd import amd_read_text, RE_HEADING

# THE PARSER'S rule (see amd_lint for the same note). A formatter that claims a
# line the reader does not is a formatter that can rewrite prose into a heading.
_RE_SECTION = RE_HEADING
_RE_HEADING = re.compile(r"^(?P<hashes>#+)[ \t]+(?P<rest>.*?)[ \t]*$")
_RE_FENCE = re.compile(r"^\s*-{3,}\s*$")


def format_text(content):
    """Return the canonically formatted form of AMD `content`."""
    out = []
    in_data = False
    pending_blank = False

    for raw in (content or "").splitlines():
        line = raw.rstrip()

        if _RE_FENCE.match(line):
            if pending_blank and out:
                out.append("")
            pending_blank = False
            out.append("---")
            in_data = not in_data
            continue

        if in_data:
            out.append(line)          # fence content preserved (trailing ws only)
            continue

        if line.strip() == "":
            pending_blank = True
            continue

        if pending_blank and out:
            out.append("")
        pending_blank = False

        m = _RE_SECTION.match(line)
        if m:
            out.append(f"{m.group('hashes')} [{m.group('display')}]({m.group('urn')})")
            continue
        mh = _RE_HEADING.match(line)
        if mh:
            out.append(f"{mh.group('hashes')} {mh.group('rest')}")
            continue
        out.append(line)

    text = "\n".join(out)
    return text + "\n" if text else ""


def format_file(path, write=False):
    """Format the file at `path`. Returns (changed, formatted_text). Writes back
    only when `write` is True and the content actually changed."""
    original = amd_read_text(path)
    formatted = format_text(original)
    changed = formatted != original
    if changed and write:
        with open(path, "w", newline="\n") as f:
            f.write(formatted)
    return changed, formatted


def _main(argv):
    """`python -m sbs_utils.procedural.amd_fmt [--check|--write] <file.amd> ...`
    Default prints the formatted text; --write formats in place; --check exits 1
    if any file is not already formatted (and writes nothing)."""
    mode = "print"
    if argv and argv[0] in ("--check", "--write"):
        mode = argv[0][2:]
        argv = argv[1:]
    if not argv:
        print("usage: python -m sbs_utils.procedural.amd_fmt [--check|--write] <file.amd> ...")
        return 2

    any_changed = False
    for path in argv:
        changed, formatted = format_file(path, write=(mode == "write"))
        any_changed = any_changed or changed
        if mode == "print":
            print(formatted, end="")
        elif mode == "check" and changed:
            print(f"would reformat: {path}")
        elif mode == "write" and changed:
            print(f"formatted: {path}")
    return 1 if (mode == "check" and any_changed) else 0


if __name__ == "__main__":
    import sys
    raise SystemExit(_main(sys.argv[1:]))
