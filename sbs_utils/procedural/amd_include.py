"""Generated blocks inside hand-written documentation - the cure for copy-paste drift.

A documentation page that explains AMD needs to SHOW some AMD: a record, the fields of
a kind, a table of what a folder holds. Every one of those was hand-copied, and hand
copies rot. Measured across the shipped docs when this module was written:

  * `OpenUniverse/mkdocs/docs/writing/silver-reach.md` was a 331-line copy of the
    364-line `silver_reach.amd` - `Reward:` had become `Pays:`, `Done when:` had become
    `When:`, and a whole `## [Effects](effects)` chapter was missing;
  * `LegendaryMissions/mkdocs/docs/script/bosses.md` hand-maintained a table of the
    folder-scanned `maps/bosses/`, so a new boss was invisible until someone remembered;
  * and one copy taught `When:` as the COMPLETION trigger. It is an alias of
    `Starts when:`, the START one - so a quest written from the documentation arms on
    its trigger and then waits forever on a `Done when:` it does not have.

That last one is why this is not a tidiness exercise. A drifted example does not look
wrong; it looks like documentation.

HOW IT WORKS. The PAGE declares what it wants, between two HTML comments, and this
module refills the span. Prose around the block is untouched - the point is not to
generate pages, it is to stop the *quoted* part of a hand-written page from being a
copy:

    <!-- amd:begin excerpt maps/bosses/warlord.amd#warlord -->
    ```amd
    # [Warlord](warlord)
    ...
    ```
    <!-- amd:end -->

The generator has no per-page knowledge, which is what lets one implementation serve
every repo. `gen_icon_gallery.py` is the precedent and it keeps the knowledge in the
script; that works for exactly one page and no more.

The directive vocabulary is CLOSED (see `_RENDERERS`). A directive nobody can read is
worse than a hand-written table, so an unknown one is an error that names itself rather
than a silently empty block.

Stdlib-only, like `amd_schema` - it ships in `sbs.pyz` and unit-tests offline.
"""
import glob as _glob
import os
import re

from . import amd_schema
from .amd import amd_read_text
from .amd_core import parse as amd_parse

BEGIN = "<!-- amd:begin "
END = "<!-- amd:end -->"

RE_BLOCK = re.compile(
    r"^[ \t]*<!--[ \t]*amd:begin[ \t]+(?P<directive>.*?)[ \t]*-->[ \t]*$"
    r"(?P<body>.*?)"
    r"^[ \t]*<!--[ \t]*amd:end[ \t]*-->[ \t]*$",
    re.DOTALL | re.MULTILINE)


class IncludeError(Exception):
    """A directive that cannot be honored. Raised rather than rendered as a comment:
    a page that silently keeps its stale copy is the failure this module exists to
    prevent, so the build has to stop instead."""


# --- the public surface -----------------------------------------------------

def amd_include_expand(text, base_dir):
    """Refill every `amd:begin ... amd:end` span in `text`. Returns
    `(new_text, [(directive, changed)])`.

    CRLF IS PRESERVED. Every one of these pages lives in a Windows repo with
    `autocrlf`, and a generator that normalizes line endings rewrites the whole file
    on its first run - which buries the one real change in a diff nobody can read."""
    crlf = "\r\n" in text
    body = text.replace("\r\n", "\n")
    report = []
    fenced = _fenced_spans(body)

    def sub(m):
        if _inside(m.start(), fenced):
            return m.group(0)
        directive = m.group("directive").strip()
        fresh = "\n" + amd_include_render(directive, base_dir).rstrip("\n") + "\n"
        report.append((directive, fresh != m.group("body")))
        return (m.group(0)[:m.start("body") - m.start(0)] + fresh
                + m.group(0)[m.end("body") - m.start(0):])

    body = RE_BLOCK.sub(sub, body)
    return (body.replace("\n", "\r\n") if crlf else body), report


RE_FENCE = re.compile(r"^[ \t]*(?P<ticks>`{3,}|~{3,})", re.MULTILINE)


def _fenced_spans(body):
    """`[(start, end)]` for every fenced code block.

    A MARKER INSIDE A FENCE IS AN EXAMPLE, NOT AN INSTRUCTION. The page that documents
    this syntax has to show it, and without this the generator reads its own
    documentation as work to do - then fails, because the example names a file that
    exists in some other repo. Anything explaining the marker hits this."""
    spans, open_at, fence = [], None, None
    for m in RE_FENCE.finditer(body):
        ticks = m.group("ticks")
        if open_at is None:
            open_at, fence = m.start(), ticks[0] * 3
        elif ticks.startswith(fence):
            spans.append((open_at, m.end()))
            open_at, fence = None, None
    if open_at is not None:
        spans.append((open_at, len(body)))
    return spans


def _inside(pos, spans):
    return any(start <= pos < end for start, end in spans)


def amd_include_render(directive, base_dir):
    """Render one directive to markdown. `base_dir` is the MISSION root - directive
    paths are relative to it, never to the page, so the same directive means the same
    thing from any page in the tree."""
    argv = directive.split()
    if not argv:
        raise IncludeError("empty amd:begin directive")
    verb, rest = argv[0], argv[1:]
    fn = _RENDERERS.get(verb)
    if fn is None:
        raise IncludeError(
            f"unknown directive {verb!r} - expected one of "
            f"{', '.join(sorted(_RENDERERS))}")
    return fn(rest, base_dir)


def amd_include_directives(text):
    """Every live directive in a page, in order - examples inside a code fence
    excluded, same as `amd_include_expand`. For `--check` and for reporting."""
    body = text.replace("\r\n", "\n")
    fenced = _fenced_spans(body)
    return [m.group("directive").strip() for m in RE_BLOCK.finditer(body)
            if not _inside(m.start(), fenced)]


# --- excerpt: quote the source, exactly ------------------------------------

def _render_excerpt(argv, base_dir):
    """`excerpt <file>[#<key>] [--with-children]`

    Quotes the SOURCE BYTES, not a re-rendering of the parsed record. The reader of an
    excerpt is being shown what to type, so a round-trip through the parser would be
    the wrong answer even when it agreed - it would drop comments, reorder nothing
    visibly, and quietly canonicalize the very spellings the page may be explaining."""
    with_children = "--with-children" in argv
    target = next((a for a in argv if not a.startswith("--")), None)
    if not target:
        raise IncludeError("excerpt needs a file")
    rel, _, key = target.partition("#")
    path = os.path.join(base_dir, rel.replace("/", os.sep))
    if not os.path.isfile(path):
        raise IncludeError(f"excerpt: no such file {rel}")
    text = amd_read_text(path).replace("\r\n", "\n")
    lines = text.split("\n")

    if key:
        doc = amd_parse(None, file_path=path)
        node = next((n for n in doc.nodes if n.key == key), None)
        if node is None:
            raise IncludeError(f"excerpt: {rel} has no record {key!r}")
        start = node.span.line - 1
        after = _next_sibling_line(doc, node, with_children)
        lines = lines[start:(after - 1) if after else len(lines)]

    while lines and not lines[-1].strip():
        lines.pop()
    return "```amd\n" + "\n".join(lines) + "\n```"


def _next_sibling_line(doc, node, with_children):
    """The 1-based line where this record's excerpt STOPS, or None for end-of-file.

    Without `--with-children` that is simply the next heading; with it, the next
    heading at the same level or shallower - which is what "and everything under it"
    means in a document whose nesting IS its structure."""
    seen = False
    for n in doc.nodes:
        if n is node:
            seen = True
            continue
        if not seen:
            continue
        if not with_children or n.level <= node.level:
            return n.span.line
    return None


# --- fields: the schema explains itself ------------------------------------

def _render_fields(argv, base_dir):
    """`fields <archetype> [--only a,b,c] [--traits x,y]`

    The table that could not drift, because the prose comes from the same table the
    parser reads. `doc=` carries the meaning, `aka` carries the older spellings, and
    the archetype key is what lets `When:` be a start trigger on a quest and a
    comms surface on dialogue - a distinction a flat hand-written table cannot make,
    and did not."""
    if not argv:
        raise IncludeError("fields needs an archetype")
    archetype = argv[0]
    only = _opt_list(argv, "--only")
    traits = tuple(_opt_list(argv, "--traits") or ())
    labels = amd_schema.template_fields(archetype)
    if not labels:
        raise IncludeError(f"fields: unknown archetype {archetype!r}")
    if only:
        missing = [o for o in only if amd_schema._norm_label(o) not in
                   {amd_schema._norm_label(l) for l in labels}]
        if missing:
            raise IncludeError(
                f"fields {archetype}: --only names undeclared field(s) "
                f"{', '.join(missing)}")
        want = {amd_schema._norm_label(o) for o in only}
        labels = [l for l in labels if amd_schema._norm_label(l) in want]

    aliases = amd_schema.amd_field_aliases(archetype, traits)
    rows = [("Field", "Meaning", "Also")]
    for label in labels:
        doc = amd_schema.amd_field_doc(label, archetype, traits) or ""
        if not doc:
            # An empty cell is honest and fixable in one line. Inventing prose at the
            # point of display is how the tables this replaces drifted in the first
            # place, so the fallback is the schema's own example text, marked as such.
            hint = amd_schema.field_schema(label, archetype, traits).get("hint")
            doc = f"_e.g._ `{hint}`" if hint else ""
        also = aliases.get(amd_schema._norm_label(label)) or ()
        rows.append((f"`{_title(label)}:`", doc,
                     ", ".join(f"`{_title(a)}:`" for a in also)))
    if not any(r[2] for r in rows[1:]):
        rows = [r[:2] for r in rows]
    return amd_table(rows)


def _title(label):
    """`done when` -> `Done when`. Sentence case, not Title Case: these are labels an
    author types, and the tables spell them with one capital."""
    s = str(label).replace("_", " ").strip()
    return s[:1].upper() + s[1:] if s else s


# --- index: a folder lists itself -------------------------------------------

def _render_index(argv, base_dir):
    """`index <glob> [--fields a,b] [--level N] [--link <prefix>]`

    What a folder currently HOLDS. The hand-written version of this table is the one
    that silently omits whatever was added last."""
    if not argv:
        raise IncludeError("index needs a glob")
    pattern = argv[0]
    fields = _opt_list(argv, "--fields") or []
    level = int((_opt_list(argv, "--level") or ["1"])[0])
    link = (_opt_list(argv, "--link") or [None])[0]

    paths = sorted(_glob.glob(os.path.join(base_dir, pattern.replace("/", os.sep))))
    if not paths:
        raise IncludeError(f"index: {pattern} matched no files")

    header = ["Name"] + [_title(f) for f in fields] + ["Summary"]
    rows = [tuple(header)]
    for path in paths:
        doc = amd_parse(None, file_path=path)
        for node in doc.nodes:
            if node.level != level:
                continue
            name = node.display or node.key
            if link:
                rel = os.path.relpath(path, base_dir).replace(os.sep, "/")
                rel = rel[:-4] if rel.endswith(".amd") else rel
                name = f"[{name}]({link.rstrip('/')}/{rel}.md)"
            cells = [_field_cell(node, f) for f in fields]
            rows.append(tuple([name] + cells + [node.summary or ""]))
    return amd_table(rows)


def _field_cell(node, label):
    """One `--fields` cell. Reads by the label an AUTHOR writes, through the schema, so
    an index never has to know that `Done when:` is stored as `goal`."""
    data = node.data or {}
    arch = data.get("__kind__")
    key = amd_schema.amd_field_key(label, arch)
    value = data.get(key, data.get(amd_schema._norm_label(label), ""))
    if isinstance(value, (list, tuple)):
        value = ", ".join(str(v) for v in value)
    return f"`{value}`" if value not in ("", None) else ""


# --- shared helpers ---------------------------------------------------------

def amd_table(rows):
    """A GFM pipe table from an iterable of row tuples, first row the header.

    Cells are escaped for `|` only: everything else in them is deliberate markdown
    (inline code in a field name, a link in an index)."""
    rows = [tuple("" if c is None else str(c).replace("|", "\\|").replace("\n", " ")
                  for c in r) for r in rows]
    width = max(len(r) for r in rows)
    rows = [r + ("",) * (width - len(r)) for r in rows]
    out = ["| " + " | ".join(rows[0]) + " |",
           "|" + "|".join(["---"] * width) + "|"]
    out += ["| " + " | ".join(r) + " |" for r in rows[1:]]
    return "\n".join(out)


def _opt_list(argv, name):
    """`--only a,b,c` or `--only a b c` -> `['a','b','c']`; None when absent.

    Both spellings because a field label contains spaces (`done when`), so the comma
    form is the only one that can name it - and someone will still write the other."""
    if name not in argv:
        return None
    values = []
    for token in argv[argv.index(name) + 1:]:
        if token.startswith("--"):
            break
        values.append(token)
    joined = " ".join(values)
    return [p.strip() for p in joined.split(",") if p.strip()]


_RENDERERS = {
    "excerpt": _render_excerpt,
    "fields": _render_fields,
    "index": _render_index,
}
