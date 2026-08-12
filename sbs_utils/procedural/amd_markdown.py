"""AMD records as Markdown - the one emitter behind both documentation sites.

There are two outputs and they must never disagree: pages committed into a mission's
`mkdocs/docs/` tree, and a standalone static HTML site. Markdown is the single
intermediate, so the HTML site does not get its own renderer - it calls
`amd_markdown_page` and hands the result to a markdown parser. A bug in a table, an
admonition or a choice therefore shows up in both, and one golden test pins both.

Everything is shared except two injected callables:

    ctx["link"]  = (node, ctx) -> href | None     # None => plain text, no link
    ctx["media"] = (block, ctx) -> markdown | None

`link` differs only in file extension between the two sites; `media` differs in where
a copied asset lands. Heading levels, anchors, fact tables, choices, transclusion and
the player filter are one code path.

WHAT THIS MODULE OWNS AND WHAT IT DOES NOT. It owns only ORDER and MARKDOWN SPELLING.
The grammar lives in `amd.py`, the block model in `amd_blocks.py`, and what a field
means in `amd_schema.py` - so a mark that needs interpreting is interpreted there and
arrives here already decided. Stdlib-only, no filesystem: that is what lets it ship
in the .sbslib and unit-test from Python strings.

TWO PHASES, because link rewriting needs to know every node's page before any page
renders: `amd_markdown_site(docs)` returns the page plan, then each page renders
against it. The index lives in `ctx["page_of"]`, never a module global.
"""
import posixpath
import re

from . import amd_schema
from .amd import amd_wikilinks
from .amd_blocks import amd_blocks
from .amd_core import path_of

# Blocks that deliberately render to nothing. `style`, `style_ref` and `media_def` are
# engine GUI declarations - `font:gui-6` is a font name, not art - and treating them as
# pictures printed three "an image goes here" placeholders into the shipped corpus.
# `break` is `<br>` used as a paragraph separator (43 of the 43 uses); a blank line
# already does that, and emitting the tag litters stray markup between paragraphs.
SILENT = ("style", "style_ref", "media_def", "break")

# Every callout kind `amd_callout` knows is also a Material admonition type, so the
# mapping is identity for all five. Anything else keeps its word visible rather than
# being silently retyped.
CALLOUT_FALLBACK = "quote"

# Always structural, anywhere in a line.
_MD_INLINE = re.compile(r"([\\`*\[\]<>|])")
# An underscore that could open or close emphasis - one at a word boundary. An
# intra-word one (`enemies_low`) is literal in both CommonMark and Python-Markdown.
_MD_PAIRED_US = re.compile(r"(?<![A-Za-z0-9])_|_(?![A-Za-z0-9])")
# Structural only at the START of a line, and only in the exact shape that makes them
# structural: a list marker needs the space after it, so `+1` and `-3` are just numbers.
_MD_LEADER = re.compile(
    r"^(>|#(?=[ \t#])|[-+*](?=[ \t])|\d+\.(?=[ \t])|[-=](?=[-=]{2,}[ \t]*$))",
    re.MULTILINE)
_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


# --- page planning ----------------------------------------------------------

def amd_markdown_site(docs, layout=None):
    """`[{path, title, uri, nodes, nav}]` - one page per document, in the order given.

    ONE FILE IS ONE PAGE and every record is an anchor on it. That is the decision the
    in-game reader already made: `amd_doc.lore_document` makes each registered source a
    top-level section, so the chapter unit is the file. Page-per-record would turn the
    shipped corpus into 89 pages, most of them one hail or one bar patron, and a nav of
    89 entries is worse than none.

    `layout` may name a document to SPLIT at level 2 (`{"split": ["big.amd"]}`) for the
    one genuine outlier. Declared, never inferred from a record count: a threshold
    silently changes a page's URL the day a file grows past it."""
    split = {str(s) for s in (layout or {}).get("split", ())}
    titles = (layout or {}).get("titles", {})
    pages = []
    for doc in docs:
        rel = _doc_rel(doc)
        base = rel[:-4] if rel.endswith(".amd") else rel
        title = titles.get(rel) or _doc_title(doc)
        if rel in split or base in split:
            top = [n for n in doc.nodes if n.level <= 1]
            pages.append({"path": f"{base}/index.md", "title": title, "doc": doc,
                          "uri": rel, "nodes": top, "nav": [title]})
            for chapter in [n for n in doc.nodes if n.level == 2]:
                kids = _subtree(doc, chapter)
                pages.append({"path": f"{base}/{_slug(chapter.key)}.md",
                              "title": chapter.display or chapter.key, "doc": doc,
                              "uri": rel, "nodes": [chapter] + kids,
                              "nav": [title, chapter.display or chapter.key]})
        else:
            pages.append({"path": f"{base}.md", "title": title, "doc": doc,
                          "uri": rel, "nodes": list(doc.nodes), "nav": [title]})
    return pages


def _subtree(doc, chapter):
    out, seen = [], False
    for n in doc.nodes:
        if n is chapter:
            seen = True
            continue
        if not seen:
            continue
        if n.level <= chapter.level:
            break
        out.append(n)
    return out


def _doc_rel(doc):
    rel = (getattr(doc, "rel_path", None) or getattr(doc, "file_path", None)
           or getattr(doc, "path", None) or "")
    return str(rel).replace("\\", "/").lstrip("./")


def _doc_title(doc):
    """The page's H1.

    A document whose root has exactly ONE level-1 child with a display is that
    record's page - `silver_reach.amd` is "The Silver Reach", not "Silver Reach". A
    document with several (7 hails, 4 bar patrons) has no such record, so the filename
    titles it and every level-1 node becomes an H2."""
    tops = [n for n in getattr(doc, "nodes", ()) if n.level == 1]
    if len(tops) == 1 and tops[0].display:
        return tops[0].display
    stem = posixpath.basename(_doc_rel(doc))
    stem = stem[:-4] if stem.endswith(".amd") else stem
    return stem.replace("_", " ").replace("-", " ").strip().title() or "Records"


def amd_markdown_context(pages, page, profile="author", link=None, media=None,
                         resolve=None):
    """The render context for ONE page. `pages` is the whole plan, so links can point
    at records on other pages."""
    page_of = {}
    for p in pages:
        for node in p["nodes"]:
            page_of.setdefault(id(node), p)
    return {"pages": pages, "page": page, "page_of": page_of, "doc": page.get("doc"),
            "profile": profile, "link": link, "media": media, "resolve": resolve,
            "dangling": []}


# --- rendering --------------------------------------------------------------

def amd_markdown_page(page, ctx):
    """One page's whole markdown."""
    doc = page.get("doc")
    tops = [n for n in getattr(doc, "nodes", ()) if n.level == 1]
    owns_h1 = len(tops) == 1 and bool(tops[0].display) and tops[0] in page["nodes"]
    out = []
    if not owns_h1:
        out.append(f"# {_esc(page['title'])}")
        out.append("")
    for node in page["nodes"]:
        out.extend(amd_markdown_record(node, ctx, shift=0 if owns_h1 else 1))
    return "\n".join(out).rstrip() + "\n"


def amd_markdown_record(node, ctx, shift=0):
    """One record: its heading, its facts, its own body. Children are NOT inlined -
    they are records in their own right and appear in source order, exactly as the
    in-game reader shows them."""
    out = []
    level = min(6, max(1, node.level + shift))
    display = node.display or node.key or ""
    anchor = amd_markdown_anchor(node)
    # `{: #id}`, not `{#id}`. Both are attr_list and both produce the same anchor, but
    # mkdocs runs pages through the macros plugin FIRST, and Jinja reads `{#` as the
    # start of a comment - so every generated heading opened a comment that never
    # closed, and every OU records page logged a macro error on every site build.
    out.append(f"{'#' * level} {_esc(display)} {{: #{anchor}}}")
    out.append("")
    facts = amd_markdown_facts(node, ctx)
    if facts:
        out.append(facts)
        out.append("")
    body = amd_markdown_blocks(amd_blocks(node, doc=ctx.get("doc"),
                                          profile=ctx.get("profile", "author"),
                                          resolve=ctx.get("resolve")), ctx)
    if body:
        out.append(body)
        out.append("")
    return out


def amd_markdown_anchor(node):
    """Page-scoped, from `path_of` - the unambiguous name for a record. Bare keys are
    not unique (40 of the corpus's 374 repeat); measured across LegendaryMissions and
    Open Universe, no document has two nodes with the same `path_of`, so the page is
    all the disambiguation an anchor needs. The print path prefixes a per-file token
    because it puts every document on ONE page; a site must not carry that over."""
    return _slug(path_of(node) or getattr(node, "key", "") or "record")


def amd_markdown_facts(node, ctx):
    """The fence, as a two-column table.

    VALUES COME FROM THE SOURCE LINES, not from `node.data`. The parsed value is
    coerced - `Difficulty: +1` stores as the integer 1 - and a page that publishes `1`
    where the file says `+1` has published something false, losing exactly the
    distinction (relative vs absolute) that the field exists to make.

    LABELS are canonicalized through the schema, so a record written `Goal:` is listed
    under `Done when:`. The value is what this file says; the label is what an author
    should type today. Those are different jobs and the table can do both."""
    fields = _fence_fields(node)
    if not fields:
        return ""
    arch = _archetype(node, fields)
    traits = tuple(amd_schema.amd_traits_of(node.data or {}) or ())

    canonical = [(amd_schema.amd_canonical_label(label, arch, traits) or label, value)
                 for label, value in fields]
    order = {amd_schema._norm_label(l): i
             for i, l in enumerate(amd_schema.template_fields(arch) if arch else ())}
    ranked = sorted(enumerate(canonical),
                    key=lambda pair: (order.get(amd_schema._norm_label(pair[1][0]),
                                                len(order) + pair[0]), pair[0]))
    rows = [("Fact", "Value")]
    for _i, (label, value) in ranked:
        rows.append((_title(label), _fact_value(label, value, arch, traits, ctx)))
    return _table(rows)


def _archetype(node, fields):
    """What KIND of record this is - declared if it says so, inferred if not.

    Most records never write a bare kind line: a beat under `## Narrative` is a quest
    because of the words in its fence, and `infer_archetype` is the function that knows
    that. Reading `__kind__` alone leaves the archetype None for those, and then nothing
    resolves - `State:` stays `State:` instead of `At start:`, and `Then: reveal x`
    renders as flat text instead of a link to x. The whole typed layer silently switches
    off for exactly the records that make up most of a story."""
    declared = (node.data or {}).get("__kind__")
    if declared:
        return declared
    parent = getattr(node, "parent", None)
    section = getattr(parent, "key", None) if parent is not None else None
    return amd_schema.infer_archetype([label for label, _v in fields],
                                      section_key=section)


def _fence_fields(node):
    """`[(label, value)]` from a record's fence, as the author wrote them.

    A bare line with no colon is the KIND (`Boss`, `Quest`) - it is the record's type,
    already carried by the heading's context, and is not a fact about it. An indented
    line continues the field above, which is how the nested `Properties:` / `Defaults:`
    blocks are authored."""
    out = []
    for _lineno, raw in getattr(node, "fence_lines", ()) or ():
        line = (raw or "").rstrip()
        if not line.strip():
            continue
        if line[:1] in " \t":
            if out:
                out[-1] = (out[-1][0], (out[-1][1] + " " + line.strip()).strip())
            continue
        label, sep, value = line.partition(":")
        if not sep:
            continue
        out.append((label.strip(), value.strip()))
    return out


def _fact_value(label, value, arch, traits, ctx):
    """One fact cell, typed through the schema - so a color is a swatch and a node
    reference is a link rather than every value being an undifferentiated string."""
    d = amd_schema.field_schema(label, arch, traits)
    kind = d.get("type")
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (list, tuple)):
        parts = [str(v) for v in value]
    elif kind in ("ref", "csv") and d.get("csv", kind == "csv"):
        parts = [p.strip() for p in str(value).split(",") if p.strip()]
    else:
        parts = [str(value)]

    if kind == "color":
        return " ".join(f"`{p}`" for p in parts)
    if kind == "ref" and d.get("ref") == "node":
        return ", ".join(_ref_link(p, ctx) for p in parts)
    if kind == "compound":
        return " ".join(_compound(str(value), d, ctx))
    if kind in ("signal",):
        return " ".join(f"`{p}`" for p in parts)
    if kind == "multiline":
        return _inline(" ".join(str(value).splitlines()), ctx)
    return ", ".join(_inline(p, ctx) for p in parts)


def _compound(value, d, ctx):
    """`Then: reveal <key>` - a verb-led field whose operand type depends on the verb.
    Split so the reveal target is a real link; an unknown verb stays literal rather
    than being guessed at."""
    toks = value.split(None, 1)
    if len(toks) < 2:
        return [f"`{value}`"]
    verb, rest = toks[0].lower(), toks[1].strip()
    operand = (d.get("verbs") or {}).get(verb)
    if operand and operand.get("type") == "ref":
        return [f"`{verb}`", _ref_link(rest, ctx)]
    return [f"`{verb}`", f"`{rest}`"]


def amd_markdown_blocks(blocks, ctx, depth=0):
    """Typed blocks -> markdown, in order.

    A RUN OF CHOICES IS ONE LIST. Each choice is its own block, so separating them by a
    blank line the way every other pair of blocks is separated turns a menu of three
    options into three one-item lists - which is both wrong about the fiction and looks
    wrong. Joining the run is an ORDER decision, which is what this module owns."""
    out, run = [], []
    for block in blocks or ():
        piece = _block(block, ctx, depth)
        if not piece:
            continue
        if block.get("type") == "choice":
            run.append(piece)
            continue
        if run:
            out.append("\n".join(run))
            run = []
        out.append(piece)
    if run:
        out.append("\n".join(run))
    return "\n\n".join(out)


def _block(block, ctx, depth):
    kind = block.get("type")
    if kind in SILENT:
        return ""
    fn = _BLOCKS.get(kind)
    if fn is None:
        # A block type nobody taught this module about. Its text is better than
        # silence: dropping it loses authored content with nothing to say it went.
        return _inline(str(block.get("text") or ""), ctx)
    return fn(block, ctx, depth)


def _b_paragraph(block, ctx, _depth):
    return _inline(block.get("text") or "", ctx)


def _b_rule(_block, _ctx, _depth):
    return "---"


def _b_synopsis(block, ctx, _depth):
    # Author-only; `amd_blocks_filter` has already removed it for the player profile,
    # so reaching here at all means it is meant to be shown.
    return _admonition("abstract", "Author note", [block.get("text") or ""], ctx)


def _b_callout(block, ctx, _depth):
    kind = block.get("kind") or CALLOUT_FALLBACK
    if not block.get("known", True):
        kind = CALLOUT_FALLBACK
    return _admonition(kind, block.get("title") or "", block.get("lines") or (), ctx)


def _b_list(block, ctx, _depth):
    marker = (lambda i: f"{i + 1}.") if block.get("ordered") else (lambda _i: "-")
    return "\n".join(f"{marker(i)} {_inline(item, ctx)}"
                     for i, item in enumerate(block.get("items") or ()))


def _b_table(block, ctx, _depth):
    rows = block.get("rows") or ()
    if not rows:
        return ""
    return _table([tuple(_inline(c, ctx) for c in row) for row in rows],
                  block.get("aligns"))


def _b_cue(block, ctx, _depth):
    who = _esc(block.get("speaker") or "")
    bits = [f"**{who.upper()}**"] if who else []
    for extra in (block.get("surface"), block.get("direction")):
        if extra:
            bits.append(f"*({_esc(extra)})*")
    return " ".join(bits)


def _b_direction(block, ctx, _depth):
    return f"*({_inline(block.get('text') or '', ctx)})*"


def _b_transition(block, ctx, _depth):
    return f"*{_inline(block.get('text') or '', ctx)}*"


def _b_speech(block, ctx, _depth):
    """One variant is a quote. Several are ALTERNATIVES THE ENGINE ROLLS BETWEEN, which
    is why they are not tabs: a tab set says the reader chooses, and that is a different
    claim about the fiction."""
    variants = block.get("variants") or ()
    lines = []
    for v in variants:
        text = v.get("text") if isinstance(v, dict) else str(v)
        gate = v.get("gate") if isinstance(v, dict) else None
        rendered = _inline(text or "", ctx)
        if gate:
            rendered = f"*(if {_esc(gate)})* {rendered}"
        lines.append(rendered)
    if not lines:
        return ""
    if len(lines) == 1:
        return f"> {lines[0]}"
    out = ["> *One of:*", ">"]
    out += [f"> - {line}" for line in lines]
    return "\n".join(out)


def _b_choice(block, ctx, _depth):
    """The label goes in BOLD, not as the link text. What the player read is the label;
    the target is machinery, and making the label a link says the words themselves lead
    somewhere. The player profile has already had target, guard and outcomes blanked by
    `amd_blocks_filter`, so this renders the bare line for them.

    A choice is `- [label](target)` in the source, which is valid CommonMark pointing at
    a KEY rather than a path - left alone, all 44 in the corpus are broken links."""
    label = f"**{_esc(block.get('label') or '')}**"
    target, guard = block.get("target"), block.get("guard")
    outcomes = block.get("outcomes") or ()
    bits = [f"- {label}"]
    if target:
        bits.append(f"-> {_ref_link(target, ctx)}")
    if guard:
        bits.append(f"*(if {_esc(guard)})*")
    for outcome in outcomes:
        bits.append(f"*({_esc(' '.join(str(t) for t in outcome))})*")
    return " ".join(bits)


def _b_link(block, ctx, _depth):
    return _ref_link(block.get("target") or "", ctx, block.get("display"))


def _b_media(block, ctx, _depth):
    fn = ctx.get("media")
    rendered = fn(block, ctx) if fn else None
    if rendered is not None:
        return rendered
    # No compositor / no resolver: say what was meant to be here. A broken image tag
    # claims the art exists and failed to load, which is a different and wrong story.
    ns = block.get("ns") or "media"
    url = block.get("url") or block.get("alt") or ""
    article = "an" if ns[:1].lower() in "aeiou" else "a"
    return f"*({article} {_esc(ns)}: `{url}`)*"


def _b_transclude(block, ctx, depth):
    """`![[key]]` - the referenced record's blocks, quoted. Unresolved, it still says
    something was meant to be here, the way the linter reports the same target as
    dangling rather than closing the gap silently."""
    if not block.get("resolved"):
        reason = block.get("reason") or "unresolved"
        return _admonition("failure", f"{block.get('target') or ''} ({reason})",
                           ["This record could not be included."], ctx)
    inner = amd_markdown_blocks(block.get("blocks") or (), ctx, depth + 1)
    quoted = "\n".join(f"> {line}" if line else ">" for line in inner.splitlines())
    title = block.get("display") or block.get("target") or ""
    return f"> **{_esc(title)}**\n>\n{quoted}" if quoted else f"> **{_esc(title)}**"


_BLOCKS = {
    "paragraph": _b_paragraph, "rule": _b_rule, "synopsis": _b_synopsis,
    "callout": _b_callout, "list": _b_list, "table": _b_table, "cue": _b_cue,
    "direction": _b_direction, "transition": _b_transition, "speech": _b_speech,
    "choice": _b_choice, "link": _b_link, "media": _b_media,
    "transclude": _b_transclude,
}


# --- links ------------------------------------------------------------------

def amd_markdown_resolve(target, ctx):
    """`key -> AmdNode | None`, document first then mission-wide.

    `from_node` MATTERS and is passed: `AmdDocument.resolve_target` resolves a bare key
    nearest-scope-first and returns None on an ambiguous one rather than guessing."""
    doc, page = ctx.get("doc"), ctx.get("page") or {}
    owner = (page.get("nodes") or [None])[0]
    node = None
    if doc is not None:
        node = doc.resolve_target(target, owner)
    if node is None and ctx.get("resolve") is not None:
        node = ctx["resolve"](target)
    return node


def amd_markdown_href(node, ctx):
    """The URL for a node from the current page, or None when it has no page - a link
    to a record this build did not emit would be a 404, so it degrades to plain text."""
    fn = ctx.get("link")
    if fn is not None:
        return fn(node, ctx)
    page = (ctx.get("page_of") or {}).get(id(node))
    if page is None:
        return None
    anchor = amd_markdown_anchor(node)
    if page is ctx.get("page"):
        return f"#{anchor}"
    here = posixpath.dirname(ctx["page"]["path"])
    return f"{posixpath.relpath(page['path'], here or '.')}#{anchor}"


def _ref_link(target, ctx, display=None):
    target = str(target or "").strip()
    if not target:
        return ""
    node = amd_markdown_resolve(target, ctx)
    href = amd_markdown_href(node, ctx) if node is not None else None
    text = display or (getattr(node, "display", None) if node is not None else None) \
        or target
    if href is None:
        ctx.setdefault("dangling", []).append(target)
        return f"`{target}`" if display is None else _esc(text)
    return f"[{_esc(text)}]({href})"


def _inline(text, ctx):
    """Escape, then substitute `[[wikilinks]]`.

    In that order, and on the ORIGINAL offsets: escaping after substitution would eat
    the markdown this function just produced."""
    raw = str(text or "")
    links = amd_wikilinks(raw)
    if not links:
        return _esc(raw)
    out, at = [], 0
    for target, alias, start, end in links:
        out.append(_esc(raw[at:start]))
        node = amd_markdown_resolve(target, ctx)
        href = amd_markdown_href(node, ctx) if node is not None else None
        label = alias or (getattr(node, "display", None) if node is not None
                          else None) or target
        if href is None:
            ctx.setdefault("dangling", []).append(target)
            out.append(_esc(label))
        else:
            out.append(f"[{_esc(label)}]({href})")
        at = end
    out.append(_esc(raw[at:]))
    return "".join(out)


# --- markdown spelling ------------------------------------------------------

def _esc(text):
    """Escape markdown metacharacters in AUTHORED prose.

    A record's body is fiction, not markup: an asterisk in `*sigh*` is a character
    speaking and a `[` in stage directions is punctuation. Anything that really is
    markup arrives as its own block type and never comes through here.

    Escaping only what can actually change the parse, because over-escaping is not
    free: `enemies_low` written `enemies\\_low` renders correctly and makes the
    generated markdown unreadable as markdown - and these files are committed, diffed
    and reviewed by people. Intra-word underscores need no escape (neither CommonMark
    nor Python-Markdown emphasizes them), and `#`, `-`, `+` and `.` are only structural
    at the START of a line."""
    s = str(text or "")
    s = _MD_INLINE.sub(r"\\\1", s)
    s = _MD_PAIRED_US.sub(r"\\_", s)
    return _MD_LEADER.sub(r"\\\1", s)


def _admonition(kind, title, lines, ctx):
    """Material's `!!! note` form. GitHub's `> [!NOTE]` spelling - which is what AMD
    itself uses - is NOT parsed by Material, so a callout left as authored renders as a
    plain blockquote with a stray `[!NOTE]` in it."""
    head = f'!!! {kind} "{_esc(title)}"' if title else f"!!! {kind}"
    body = [f"    {_inline(line, ctx)}" for line in lines if str(line).strip()]
    return "\n".join([head, ""] + body) if body else head


def _table(rows, aligns=None):
    rows = [tuple("" if c is None else str(c).replace("|", "\\|").replace("\n", " ")
                  for c in r) for r in rows if r]
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    rows = [r + ("",) * (width - len(r)) for r in rows]
    sep = []
    for i in range(width):
        a = (aligns or [None] * width)[i] if aligns and i < len(aligns) else None
        sep.append({"left": ":---", "center": ":---:", "right": "---:"}.get(a, "---"))
    out = ["| " + " | ".join(rows[0]) + " |", "|" + "|".join(sep) + "|"]
    out += ["| " + " | ".join(r) + " |" for r in rows[1:]]
    return "\n".join(out)


def _title(label):
    s = str(label or "").replace("_", " ").strip()
    return s[:1].upper() + s[1:] if s else s


def _slug(text):
    return _SLUG_STRIP.sub("-", str(text or "").lower()).strip("-") or "record"
