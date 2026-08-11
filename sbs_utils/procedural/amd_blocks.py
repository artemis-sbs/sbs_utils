"""One AMD record body -> a list of typed blocks.

`amd_core.parse` gives a renderer everything about a document's STRUCTURE - the
record tree, the fence facts, the reference spans - and nothing about its BODY,
which arrives as `node.body_lines`: raw text, exactly as typed. Every consumer so
far has re-derived meaning from those lines itself, which is why the same `%` and
the same `- [label](target)` were being read four slightly different ways.

This module reads them ONCE, into blocks:

    [{"type": "cue", "line": 12, "speaker": "vex", "surface": "comms"},
     {"type": "speech", "line": 13, "variants": [{"text": "...", "gate": None}]},
     {"type": "choice", "line": 15, "label": "Pay", "target": "paid", ...}]

Every block is a plain JSON-able dict with a 1-based `line`, following the house
style `amd_schema` set for descriptors - so blocks cross a process boundary (the
LSP, a `--format json` dump, a golden test) untouched, and a test can pin the
MEANING of a document rather than one renderer's HTML.

**This module owns no grammar.** Every mark is recognized by the function in
`amd` that already owned it. What lives here is only the ORDER those recognizers
are tried in and where one block ends and the next begins - which is exactly the
part that has to be identical between the game and a printed page.

Deliberately NOT here: measuring, wrapping, styling, or anything that needs the
engine. A block says "these lines were a table"; how wide its columns are is the
renderer's business, and the in-game one answers differently from a sheet of
paper on purpose.
"""
from sbs_utils.procedural.amd import (
    RE_COMMENT, RE_CUE, RE_DIRECTION, RE_CALLOUT, RE_LINK_DEF, RE_LINK_REF,
    RE_REF_LINK, RE_STYLE_DEF, amd_body_synopsis, amd_body_transclude,
    amd_body_transition, amd_body_variant, amd_choice, amd_parse_url,
    amd_table_rows, amd_table_scan, amd_wikilinks,
)
from sbs_utils.procedural.amd_callout import amd_callout_blocks

# How deep `![[key]]` may nest before we stop. A transclusion cycle is a mistake,
# not an attack, so this only has to be small enough to stay fast and large enough
# that no honest document hits it.
MAX_TRANSCLUDE_DEPTH = 4

# `- ` and `1. ` open list items. Checked AFTER the choice rule, because a choice
# is also a `-` line; a choice that fell through to here would render as a bullet
# and quietly lose its target.
_ORDERED = tuple(str(d) for d in range(10))


def _split_cue_extension(ext):
    """A cue's `(...)` -> `(surface, direction)`.

    `amd_dialogue` owns the surface registry, but importing it drags `signal` and
    `mast_node` in behind it - too much for a module a static exporter loads. So
    this asks the registry when it is already available and otherwise falls back
    to the three built-in surfaces, which is what an unconfigured document has
    anyway. The failure mode is a surface a mission REGISTERED reading as a
    direction, which prints as flavor text rather than crashing."""
    text = (ext or "").strip()
    if not text:
        return None, None
    try:
        from sbs_utils.procedural.amd_dialogue import _dlg_split_extension
        return _dlg_split_extension(ext)
    except Exception:
        return (text.lower(), None) if text.lower() in ("comms", "over", "card") \
            else (None, text)


class _Run:
    """Accumulates consecutive lines that belong to one block (a paragraph, a
    variant set, a list) and flushes them when the run ends."""

    def __init__(self, out):
        self.out = out
        self.kind = None
        self.line = 0
        self.items = []

    def add(self, kind, line, item):
        if self.kind != kind:
            self.flush()
            self.kind, self.line = kind, line
        self.items.append(item)

    def flush(self):
        if not self.kind:
            return
        kind, line, items = self.kind, self.line, self.items
        self.kind, self.items = None, []
        if kind == "paragraph":
            text = " ".join(items)
            self.out.append({"type": "paragraph", "line": line, "text": text,
                             "links": [{"target": t, "alias": a}
                                       for t, a, _s, _e in amd_wikilinks(text)]})
        elif kind == "speech":
            self.out.append({"type": "speech", "line": line, "variants": items})
        elif kind in ("ul", "ol"):
            self.out.append({"type": "list", "line": line, "ordered": kind == "ol",
                             "items": items})


def amd_blocks(node, doc=None, profile="author", resolve=None, depth=0, _seen=None):
    """The blocks of one `amd_core.AmdNode`'s body.

    `doc` lets `![[key]]` transclusions and `[[key]]` links resolve; `resolve` is
    an optional `key -> AmdNode` callable for a MISSION-wide lookup, which a
    single document cannot do on its own. `profile` is `"author"` or `"player"` -
    see `amd_blocks_filter`."""
    lines = _body_lines(node)
    seen = set(_seen or ())
    if node is not None:
        seen.add(id(node))      # a record cannot transclude itself
    blocks = _classify(lines, doc=doc, profile=profile, resolve=resolve,
                       depth=depth, seen=seen, owner=node)
    # `amd_core` lifts the `= ` synopsis OUT of body_lines (so no renderer can
    # leak it by forgetting to check), which means the classifier never sees one
    # and a caller reading blocks alone would silently lose the author's note.
    # Put it back at the front, for the author profile only.
    note = getattr(node, "synopsis", "") if node is not None else ""
    if note and profile != "player":
        span = getattr(node, "synopsis_span", None)
        blocks.insert(0, {"type": "synopsis",
                          "line": getattr(span, "line", 0) or 0, "text": note})
    return amd_blocks_filter(blocks, profile)


def amd_blocks_text(text, profile="author"):
    """The blocks of a raw body string, for callers that have text and no node.

    A record read this way has no document around it, so `[[links]]` are recorded
    but transclusions cannot resolve."""
    lines = [(i + 1, raw) for i, raw in enumerate((text or "").splitlines())]
    blocks = _classify(lines, doc=None, profile=profile, resolve=None,
                       depth=0, seen=set(), owner=None)
    return amd_blocks_filter(blocks, profile)


def _body_lines(node):
    """A node's body as `(1-based lineno, raw)`, with the pre-fence lines dropped.

    `amd_core.parse` appends every non-heading, non-fence line to `body_lines`,
    INCLUDING any stray line between the heading and the `---` fence, and then
    resets `body_start` to the fence's closing line. Filtering on `body_start` is
    what keeps that stray out of the rendered body - the same filter the LSP's
    detail view applies."""
    if node is None:
        return []
    start = getattr(node, "body_start", 0) or 0
    return [(ln, raw) for (ln, raw) in (node.body_lines or []) if (ln - 1) >= start]


def _classify(lines, doc, profile, resolve, depth, seen, owner):
    out = []
    run = _Run(out)
    callouts = _callout_ranges(lines)
    raws = [r for _ln, r in lines]
    i = 0
    while i < len(lines):
        if i in callouts:
            run.flush()
            block, i = callouts[i]
            out.append(block)
            continue
        lineno, raw = lines[i]
        text = (raw or "").strip()

        if not text:
            run.flush()
            i += 1
            continue
        if RE_COMMENT.match(raw or ""):
            i += 1
            continue

        block = _line_block(lineno, raw, text, raws, i, doc, profile, resolve,
                            depth, seen, owner)
        if block is not None:
            run.flush()
            blk, consumed = block
            if blk is not None:
                out.append(blk)
            i += consumed
            continue

        variant = _speech(text)
        if variant is not None:
            run.add("speech", lineno, variant)
            i += 1
            continue

        item = _list_item(text)
        if item is not None:
            kind, value = item
            run.add(kind, lineno, value)
            i += 1
            continue

        run.add("paragraph", lineno, text)
        i += 1
    run.flush()
    return out


def _line_block(lineno, raw, text, raws, i, doc, profile, resolve, depth, seen,
                owner):
    """The block one line opens, as `(block, lines_consumed)`, or None when the
    line belongs to a multi-line run (paragraph / speech / list).

    ORDER IS THE CONTRACT here, and three pairs of it are load-bearing, each for
    a reason `amd` already records beside the rule:

      * transclude before wikilink - `RE_WIKILINK`'s negative lookbehind assumes
        `![[...]]` was claimed first;
      * synopsis before style - `= ` requires the space precisely so `=$name`
        stays a style declaration;
      * choice before list - both open with `-`.
    """
    note = amd_body_synopsis(raw)
    if note is not None:
        # Author-only, always. `amd_core` already keeps this out of `body_lines`,
        # so this arm only fires for `amd_blocks_text` - but it fires the same way,
        # because a note leaking to a player must be impossible by construction
        # rather than by which entry point the caller happened to use.
        if profile == "player":
            return None, 1
        return {"type": "synopsis", "line": lineno, "text": note}, 1

    target = amd_body_transclude(raw)
    if target is not None:
        return _transclude(lineno, target, doc, profile, resolve, depth, seen,
                           owner), 1

    trans = amd_body_transition(raw)
    if trans is not None:
        return {"type": "transition", "line": lineno, "text": trans}, 1

    m = RE_CUE.match(raw or "")
    if m is not None:
        surface, direction = _split_cue_extension(m.group("ext"))
        return {"type": "cue", "line": lineno, "speaker": m.group("key"),
                "surface": surface, "direction": direction}, 1

    m = RE_DIRECTION.match(raw or "")
    if m is not None:
        return {"type": "direction", "line": lineno,
                "text": m.group("text").strip()}, 1

    scan = amd_table_scan(raws, i)
    if scan is not None:
        rows, nxt = scan
        cells, aligns = amd_table_rows(rows)
        return ({"type": "table", "line": lineno, "rows": cells,
                 "aligns": aligns} if cells else None), nxt - i

    if text in ("<hr>", "<hr/>"):
        return {"type": "rule", "line": lineno}, 1
    if text in ("<br>", "<br/>"):
        return {"type": "break", "line": lineno}, 1

    m = RE_REF_LINK.match(text)
    if m is not None:
        return {"type": "link", "line": lineno, "display": m.group("disp").strip(),
                "target": m.group("key").strip()}, 1

    m = RE_STYLE_DEF.match(text)
    if m is not None:
        return {"type": "style", "line": lineno, "name": m.group("style_name"),
                "spec": (m.group("remainder") or "").strip()}, 1

    m = RE_LINK_DEF.match(text)
    if m is not None:
        return {"type": "media_def", "line": lineno,
                "name": m.group("link_name") or "", "ns": m.group("ns"),
                **_media_url(m.group("urn"))}, 1

    media = _media(text)
    if media is not None:
        media["line"] = lineno
        return media, 1

    choice = amd_choice(raw)
    if choice is not None:
        return {"type": "choice", "line": lineno, "label": choice["label"],
                "target": choice["target"], "guard": choice["guard"],
                "outcomes": [list(o) for o in choice["outcomes"]]}, 1
    return None


def _media(text):
    """A whole line that is only a media reference -> a `media` block, else None.

    `RE_LINK_REF` is deliberately permissive - it has to claim `![x](image://y)`
    in the middle of a sentence - so requiring the `ns` group is what keeps an
    ordinary line that merely starts with `[` from becoming an image."""
    m = RE_LINK_REF.match(text)
    if m is None or not m.group("ns"):
        return None
    ns = (m.group("ns") or "").lower()
    if ns in ("style", "ref", "link"):
        # Same shape, not the same thing. `[](style:font:gui-2;color:blue)` is a
        # STYLE applied to the line, and `ref`/`link` is navigation - neither is
        # art, and treating them as art printed three "an image goes here"
        # placeholders into the corpus for marks that were never pictures.
        return {"type": "style_ref", "spec": m.group("urn") or "", "ns": ns}
    return {"type": "media", "alt": m.group("link_name") or "", "ns": m.group("ns"),
            "trailing": (m.group("remainder") or "").strip(),
            **_media_url(m.group("urn"))}


def _media_url(urn):
    opts = amd_parse_url((urn or "").rstrip(")"))
    return {"url": opts.pop("url", ""), "options": opts}


def _speech(text):
    """A `%` variant line -> `{"text", "gate"}`, else None.

    The sigil is REQUIRED here even though a dialogue body makes it optional,
    because this classifier has no idea whether it is inside dialogue. An
    unmarked line stays a paragraph, and the screenplay lens - which does know the
    record is dialogue - promotes it. Guessing here would turn every prose
    sentence in the corpus into a spoken line."""
    if not text.startswith("%"):
        return None
    body, gate = amd_body_variant(text)
    return {"text": body, "gate": gate}


def _list_item(text):
    if text.startswith("- "):
        return "ul", text[2:].strip()
    head = text.split(".", 1)
    if len(head) == 2 and head[0] and all(c in _ORDERED for c in head[0]):
        return "ol", head[1].strip()
    return None


def _callout_ranges(lines):
    """`{start_index: (block, next_index)}` for every callout in `lines`.

    `amd_callout_blocks` owns what a callout IS and works on text, so the body is
    handed to it whole and the resulting 0-based ranges are mapped back onto the
    line list. Re-walking `>` lines here would be a second copy of the rule the
    in-game renderer already shares from that module."""
    if not any(RE_CALLOUT.match(raw or "") for _ln, raw in lines):
        return {}
    text = "\n".join(raw or "" for _ln, raw in lines)
    out = {}
    for b in amd_callout_blocks(text):
        out[b["start"]] = ({"type": "callout", "line": lines[b["start"]][0],
                            "kind": b["kind"], "title": b["title"],
                            "known": b["known"],
                            "lines": [t.strip() for t in b["lines"] if t.strip()]},
                           b["end"])
    return out


def _transclude(lineno, target, doc, profile, resolve, depth, seen, owner):
    """`![[key]]` -> the referenced record's blocks, inlined.

    Unresolved or too deep, the block still exists and says so: a printed page
    should show that something was meant to be here, the way the linter reports
    the same target as dangling, rather than silently closing the gap."""
    block = {"type": "transclude", "line": lineno, "target": target,
             "resolved": False, "blocks": []}
    if depth >= MAX_TRANSCLUDE_DEPTH:
        block["reason"] = "too deep"
        return block
    found = None
    if doc is not None:
        found = doc.resolve_target(target, owner)
    if found is None and resolve is not None:
        found = resolve(target)
    if found is None:
        block["reason"] = "unresolved"
        return block
    ident = id(found)
    if ident in seen:
        block["reason"] = "cycle"
        return block
    block["resolved"] = True
    block["display"] = getattr(found, "display", "") or target
    block["blocks"] = amd_blocks(found, doc=doc, profile=profile, resolve=resolve,
                                 depth=depth + 1, _seen=seen | {ident})
    return block


def amd_blocks_filter(blocks, profile="author"):
    """Strip everything `profile` must not see, recursively.

    `player` is a HARD filter, not a stylesheet class: an author-only note or a
    choice's outcome must be ABSENT from the output, because "print to PDF" and
    "view source" have to agree about what a player was told. Anything merely
    hidden by styling is one right-click from being read.

    `amd_blocks` and `amd_blocks_text` both run this before returning, so a
    caller never has to remember to. It stays public for a caller that built the
    author cut once and now wants the player one without re-parsing."""
    if profile != "player":
        return blocks
    out = []
    for b in blocks:
        kind = b.get("type")
        if kind == "synopsis":
            continue
        b = dict(b)
        if kind == "choice":
            # The target key is a walkthrough, the guard and outcomes are the
            # machinery behind the curtain. The LABEL is what a player read.
            b["guard"], b["outcomes"], b["target"] = None, [], ""
        elif kind == "speech":
            b["variants"] = [{"text": v.get("text", ""), "gate": None}
                             for v in b.get("variants", ())]
        elif kind == "transclude":
            b["blocks"] = amd_blocks_filter(b.get("blocks", ()), profile)
        out.append(b)
    return out
