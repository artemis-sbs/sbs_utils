"""AMD -> a self-contained HTML document, laid out for PRINT.

AMD is where a mission's design lives - the quests, the dialogue, the factions,
the lore, the help text - and until now the only thing that could read it was the
game. A writer reviewing dialogue, a modder looking up faction keys and a
playtester reading a mission bible all had to open a code editor and read markup.

The output is one HTML file with its CSS inlined and no external requests, sized
for paper: `@page` rules, controlled breaks, a table of contents. "Print to PDF"
in any browser is the PDF path, deliberately - there is no PDF library anywhere
in this stack and adding one to `sbs.pyz` would be a new dependency for a job the
browser already does.

**Four lenses, because AMD is three documents wearing one syntax.** A file with
no fence at all (`help_docs.amd`, `lore.amd`) is prose and converts almost
directly. A file whose content IS the fence (sides, items, drops) is a catalog,
and printing `Color: #ffcc44` as a line of text would be worthless - it wants a
swatch. A quest tree's meaning lives in `Parent:` / `Starts when:` / `Then:`, and
flattening it destroys exactly the thing a designer opened the document to see.
So the number of renderings is the number of AUDIENCES:

    prose       a manual or a story book - the reader wants sentences
    catalog     a sourcebook - the reader wants to look something up
    screenplay  a script - the reader wants to perform it
    bible       a design document - the reader wants to see the machine

**Two profiles.** `player` is a HARD filter, not a stylesheet class: an
author-only note must be ABSENT from the file, because "print to PDF" and "view
source" have to agree about what a player was told.

Stdlib only, like every other module here that ships inside `sbs.pyz`.
"""
import html

from sbs_utils.procedural import amd_schema
from sbs_utils.procedural.amd_blocks import amd_blocks
from sbs_utils.procedural.amd_core import path_of

LENSES = ("prose", "catalog", "screenplay", "bible")
PROFILES = ("author", "player")

# Fence fields that describe MACHINERY rather than story. A player-facing page
# drops them; the catalog and bible lenses keep them, because looking at the
# machine is the entire point of those two.
_MACHINERY = frozenset({
    "then", "starts when", "done when", "fails when", "fail on signal", "action",
    "scope", "show", "at start", "on kill", "on collect", "on scan", "on dock",
    "reveal", "reveals", "parent", "required", "critical", "aka", "tier", "goal",
    "win", "lose", "fail after",
})

# What a prose page shows beside the text when the reader is the author: the
# fields that are ABOUT the story rather than about how the story is wired.
_PROSE_FACTS = ("objective", "reward", "penalty", "scan says", "signal says",
                "speaker", "title", "side", "display", "when", "citation")


def esc(text):
    return html.escape("" if text is None else str(text), quote=True)


def slug(text):
    """A stable id fragment. Anchors are PATH-based, never bare keys: 40 of the
    corpus's 374 keys repeat, and one file alone holds three `recover` records."""
    out = []
    for ch in str(text or "").lower():
        out.append(ch if ch.isalnum() else "-")
    return "".join(out).strip("-") or "x"


_DOC_TOKENS = {}        # uri -> the short unique token used in its anchors


def doc_tokens(docs):
    """A short, unique id fragment per document.

    `slug(basename)` alone is not unique: five basenames repeat across the
    corpus, and `OpenUniverse` holds `captains/ashfang.amd` AND
    `dialogue/ashfang.amd`. Two files sharing an anchor prefix do not dangle -
    they do something worse, and aim a working link at the wrong record. So a
    collision walks back up the path until the token is unique."""
    tokens, used = {}, {}
    for uri, _doc in docs:
        parts = [p for p in str(uri or "").replace(chr(92), "/").split("/") if p]
        parts[-1:] = [parts[-1].rsplit(".", 1)[0]] if parts else ["doc"]
        token = slug(parts[-1]) if parts else "doc"
        depth = 1
        while token in used and used[token] != uri and depth < len(parts):
            depth += 1
            token = slug("-".join(parts[-depth:]))
        n = 2
        base = token
        while token in used and used[token] != uri:
            token = f"{base}-{n}"
            n += 1
        used[token] = uri
        tokens[uri] = token
    return tokens


def anchor_of(uri, node):
    return f"{_DOC_TOKENS.get(uri) or slug(_basename(uri))}--{slug(path_of(node))}"


def _basename(uri):
    return str(uri or "").replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]


# --- assets ------------------------------------------------------------------

class NoAssets:
    """The default asset resolver: resolves nothing, and says so on the page.

    A printed page should say "a face goes here, of an Arvonian" rather than
    silently closing the gap - a missing illustration the reader cannot see is a
    missing illustration nobody fixes."""

    def media(self, block):
        return None


def _media_html(block, assets, faces="canvas"):
    assets = assets or NoAssets()
    if (block.get("ns") or "") == "face" and _face_capable(assets, faces):
        # A face has no file, but it is not unresolvable: it names cells of a
        # race atlas, and `face.js` - the mock's compositor - exists to stack
        # them. The canvas is drawn on load by the bootstrap in `_face_script`.
        opts = block.get("options") or {}
        size = opts.get("height") or opts.get("size") or 120
        return (f'<figure class="art"><canvas class="face" width="{esc(size)}" '
                f'height="{esc(size)}" data-face="{esc(block.get("url", ""))}">'
                f'</canvas></figure>')
    src = assets.media(block)
    alt = block.get("alt") or block.get("url") or ""
    if src:
        return f'<figure class="art"><img src="{esc(src)}" alt="{esc(alt)}"></figure>'
    ns = block.get("ns") or "media"
    note = {"face": "a face", "ship": "a ship",
            "image": "an image"}.get(ns, f"a {ns}")
    return (f'<figure class="art art-missing"><span class="art-kind">{esc(note)}</span>'
            f'<code>{esc(block.get("url", ""))}</code></figure>')


# --- blocks -> html ----------------------------------------------------------

def blocks_html(blocks, ctx, depth=0):
    """Render a block list. `ctx` carries the document, profile and assets."""
    out = []
    for b in blocks or ():
        out.append(_block_html(b, ctx, depth))
    return "\n".join(x for x in out if x)


def _block_html(b, ctx, depth):
    kind = b.get("type")
    if kind == "paragraph":
        return f"<p>{_inline(b, ctx)}</p>"
    if kind == "synopsis":
        return f'<aside class="synopsis">{esc(b["text"])}</aside>'
    if kind == "speech":
        return _speech_html(b, ctx)
    if kind == "cue":
        ext = b.get("surface") or b.get("direction")
        tail = f' <span class="ext">({esc(ext)})</span>' if ext else ""
        return f'<p class="cue">{esc(b["speaker"]).upper()}{tail}</p>'
    if kind == "direction":
        return f'<p class="direction">({esc(b["text"])})</p>'
    if kind == "transition":
        return f'<p class="transition">{esc(b["text"])}</p>'
    if kind == "choice":
        return _choice_html(b, ctx)
    if kind == "callout":
        body = "".join(f"<p>{esc(t)}</p>" for t in b.get("lines", ()))
        title = esc(b.get("title") or b.get("kind", "").title())
        return (f'<div class="callout callout-{slug(b.get("kind"))}">'
                f'<p class="callout-title">{title}</p>{body}</div>')
    if kind == "list":
        tag = "ol" if b.get("ordered") else "ul"
        items = "".join(f"<li>{esc(x)}</li>" for x in b.get("items", ()))
        return f"<{tag}>{items}</{tag}>"
    if kind == "table":
        return _table_html(b)
    if kind == "media":
        return _media_html(b, ctx.get("assets"), ctx.get("faces", "canvas"))
    if kind == "link":
        return (f'<p class="xref"><a href="#{esc(_target_anchor(b["target"], ctx))}">'
                f'{esc(b["display"])}</a></p>')
    if kind == "rule":
        return "<hr>"
    if kind == "break":
        return '<p class="brk"></p>'
    if kind == "transclude":
        return _transclude_html(b, ctx, depth)
    if kind in ("style", "style_ref", "media_def"):
        return ""       # declarations, not content
    return ""


def _speech_html(b, ctx):
    rows = []
    for v in b.get("variants", ()):
        gate = v.get("gate")
        chip = f'<span class="gate">{esc(gate)}</span>' if gate else ""
        rows.append(f'<p class="speech">{chip}{esc(v.get("text", ""))}</p>')
    if len(rows) > 1:
        # Several variants are ONE thing said, chosen at random - a reader must
        # see that they are alternatives, not consecutive lines of a speech.
        return '<div class="variants">' + "".join(rows) + "</div>"
    return "".join(rows)


def _choice_html(b, ctx):
    bits = [f'<span class="choice-label">{esc(b["label"])}</span>']
    if b.get("guard"):
        bits.append(f'<span class="guard">if {esc(b["guard"])}</span>')
    for o in b.get("outcomes", ()):
        bits.append(f'<span class="outcome">{esc(" ".join(str(x) for x in o))}</span>')
    if b.get("target"):
        href = esc(_target_anchor(b["target"], ctx))
        bits.append(f'<a class="goto" href="#{href}">{esc(b["target"])}</a>')
    return '<p class="choice">' + " ".join(bits) + "</p>"


def _table_html(b):
    rows = b.get("rows") or []
    aligns = b.get("aligns") or []

    def cell(tag, text, i):
        a = aligns[i] if i < len(aligns) else "l"
        cls = {"c": "ta-c", "r": "ta-r"}.get(a, "")
        attr = f' class="{cls}"' if cls else ""
        return f"<{tag}{attr}>{esc(text)}</{tag}>"

    head = "".join(cell("th", c, i) for i, c in enumerate(rows[0])) if rows else ""
    body = "".join("<tr>" + "".join(cell("td", c, i) for i, c in enumerate(r))
                   + "</tr>" for r in rows[1:])
    return (f'<div class="tablewrap"><table><thead><tr>{head}</tr></thead>'
            f"<tbody>{body}</tbody></table></div>")


def _transclude_html(b, ctx, depth):
    if not b.get("resolved"):
        return (f'<p class="dangling">[{esc(b["target"])} - '
                f'{esc(b.get("reason", "not found"))}]</p>')
    inner = blocks_html(b.get("blocks", ()), ctx, depth + 1)
    return f'<blockquote class="transclude">{inner}</blockquote>'


def _inline(b, ctx):
    """A paragraph's text with `[[wikilinks]]` turned into anchors."""
    from sbs_utils.procedural.amd import RE_WIKILINK

    def sub(m):
        target = (m.group("target") or "").strip()
        alias = (m.group("alias") or "").strip()
        node = _resolve(target, ctx)
        shown = alias or (node.display if node is not None else target)
        if node is None:
            return f'<span class="dangling">{esc(shown)}</span>'
        return f'<a href="#{esc(_target_anchor(target, ctx))}">{esc(shown)}</a>'

    # Escape FIRST, then substitute, so a link's replacement HTML survives and
    # nothing in the prose can inject markup.
    escaped = esc(b.get("text", ""))
    return RE_WIKILINK.sub(sub, escaped)


def _resolve(target, ctx):
    doc = ctx.get("doc")
    node = doc.resolve_target(target) if doc is not None else None
    if node is None and ctx.get("resolve") is not None:
        node = ctx["resolve"](target)
    return node


def _target_anchor(target, ctx):
    node = _resolve(target, ctx)
    if node is None:
        return slug(target)
    return anchor_of(ctx.get("uri_of", lambda _n: ctx.get("uri"))(node), node)


# --- fence facts -> html -----------------------------------------------------

def _values(value):
    """A fence value as a list. The coercers already return lists for `csv`,
    `lines` and friends; a scalar becomes a one-item list so the renderers below
    do not each need the same isinstance dance."""
    if isinstance(value, (list, tuple)):
        return list(value)
    if isinstance(value, dict):
        return [f"{k}: {v}" for k, v in value.items()]
    return [value]


def _field_html(label, value, desc, ctx):
    """One fence field, rendered as its TYPE rather than as text.

    This is the whole reason the catalog lens is worth building. `amd_schema`
    already knows every field's type - so a color can be a swatch, a reference can
    be a working link and a coordinate can be a cell chip, instead of 615 records
    printing as `Label: value` and being no easier to read on paper than in the
    editor."""
    kind = (desc or {}).get("type", "text")
    if kind == "color":
        vals = []
        for v in _values(value):
            vals.append(f'<span class="swatch" style="background:{esc(v)}"></span>'
                        f"<code>{esc(v)}</code>")
        return " ".join(vals)
    if kind == "ref":
        out = []
        for v in _values(value):
            node = _resolve(str(v), ctx)
            if node is None:
                out.append(f'<span class="dangling">{esc(v)}</span>')
            else:
                out.append(f'<a href="#{esc(_target_anchor(str(v), ctx))}">'
                           f"{esc(node.display or v)}</a>")
        return ", ".join(out)
    if kind == "enum":
        accepts = set()
        try:
            accepts = {str(x).lower()
                       for x in (amd_schema.enum_accepts(label, ctx.get("arch")) or ())}
        except Exception:
            pass
        out = []
        for v in _values(value):
            known = (not accepts) or str(v).lower() in accepts
            cls = "pill" if known else "pill pill-unknown"
            out.append(f'<span class="{cls}">{esc(v)}</span>')
        return " ".join(out)
    if kind == "coord2":
        out = []
        for v in _values(value):
            cell = ", ".join(str(x) for x in v) if isinstance(v, (list, tuple)) else v
            out.append(f'<span class="cell">{esc(cell)}</span>')
        return " ".join(out)
    if kind == "signal":
        return " ".join(f'<code class="sig">{esc(v)}</code>' for v in _values(value))
    if kind == "face":
        return _media_html({"ns": "face", "url": str(value), "alt": label},
                           ctx.get("assets"), ctx.get("faces", "canvas"))
    if kind in ("csv", "lines", "reward"):
        return "<ul class=\"vals\">" + "".join(
            f"<li>{esc(v)}</li>" for v in _values(value)) + "</ul>"
    if kind == "multiline":
        return "".join(f"<p>{esc(v)}</p>" for v in _values(value))
    if kind in ("weighted", "makeup", "counted", "kv") and isinstance(value, dict):
        return "<dl class=\"kv\">" + "".join(
            f"<dt>{esc(k)}</dt><dd>{esc(v)}</dd>" for k, v in value.items()) + "</dl>"
    if kind == "int":
        return f'<span class="num">{esc(value)}</span>'
    return esc(", ".join(str(v) for v in _values(value)))


def facts_html(node, ctx, only=None, drop=None, css="facts"):
    """A record's fence as a definition list, in the schema's field order.

    Order comes from `amd_schema.template_fields`, not from what the author
    happened to type, so every card of a kind lists its fields the same way and a
    missing field reads as a gap rather than as a reshuffle. Fields the schema
    does not know follow, in authored order - which is how a mission's own
    registered vocabulary shows up."""
    data = dict(node.data or {})
    data.pop("__kind__", None)
    if not data:
        return ""
    arch = node.kind
    traits = ()
    try:
        traits = amd_schema.amd_traits_of(node.data or {}) or ()
    except Exception:
        pass
    ordered = [k for k in amd_schema.template_fields(arch) if k in data]
    ordered += [k for k in data if k not in ordered]
    rows = []
    inner = dict(ctx)
    inner["arch"] = arch
    for label in ordered:
        if only is not None and label not in only:
            continue
        if drop is not None and label in drop:
            continue
        desc = amd_schema.field_schema(label, arch, traits)
        if (desc or {}).get("internal") and not ctx.get("show_internal"):
            continue
        rows.append(f"<dt>{esc(label.title())}</dt>"
                    f"<dd>{_field_html(label, data[label], desc, inner)}</dd>")
    if not rows:
        return ""
    return f'<dl class="{css}">' + "".join(rows) + "</dl>"


# --- the prose lens ----------------------------------------------------------

def lens_prose(docs, ctx):
    """Every record, in document order, as a book.

    The lens the fence-less files were written for - `help_docs.amd`,
    `library_docs.amd`, `lore.amd` - where the body already IS markdown and the
    conversion is nearly a straight one."""
    out = []
    for uri, doc in docs:
        out.append(f'<section class="doc" id="{esc(slug(_basename(uri)))}">')
        out.append(f'<h1 class="doc-title">{esc(_doc_title(uri, doc))}</h1>')
        for node in doc.nodes:
            out.append(_prose_record(uri, doc, node, ctx))
        out.append("</section>")
    return "\n".join(out)


def _prose_record(uri, doc, node, ctx):
    inner = dict(ctx)
    inner["doc"] = doc
    inner["uri"] = uri
    level = min(6, max(2, (node.level or 1) + 1))
    aside = ""
    if ctx.get("profile") != "player":
        aside = facts_html(node, inner, only=_PROSE_FACTS, css="facts aside")
    body = blocks_html(amd_blocks(node, doc=doc, profile=ctx.get("profile", "author"),
                                  resolve=ctx.get("resolve")), inner)
    return (f'<article class="rec" id="{esc(anchor_of(uri, node))}">'
            f"<h{level}>{esc(node.display or node.key)}</h{level}>"
            f"{aside}{body}</article>")


def _doc_title(uri, doc):
    root = getattr(doc, "root", None)
    kids = getattr(root, "children", None) or []
    if len(kids) == 1 and kids[0].display:
        return kids[0].display
    return _basename(uri).rsplit(".", 1)[0].replace("_", " ").title()


# --- the page ----------------------------------------------------------------
# Both the modern `break-*` properties and the legacy `page-break-*` aliases are
# emitted: Chrome honors both, older print engines only the second.
#
# Running heads are emitted TWICE, for a reason worth stating rather than
# leaving to be discovered. `@page` margin boxes and `string-set` /
# `target-counter` are the correct mechanism, and are implemented by Prince and
# WeasyPrint - and by neither Chrome nor Edge. So the paged-media rules are here
# for anyone piping this through a real paged formatter (they cost nothing when
# ignored), and the browser path uses a `position: fixed` header/footer, which
# Chrome repeats on every printed sheet. Page NUMBERS in the browser path come
# from the browser's own print header/footer; faking them would need page
# positions no browser exposes.

CSS = """
:root { --ink:#111; --dim:#555; --rule:#bbb; --accent:#1a4f8a; --panel:#f4f4f4; }
* { box-sizing: border-box; }
body { margin:0; color:var(--ink); background:#fff;
       font:11pt/1.45 Georgia,"Times New Roman",serif; }
.sheet { max-width: 7.1in; margin: 0 auto; padding: 0.6in 0.4in 1in; }
h1,h2,h3,h4,h5,h6 { font-family:"Helvetica Neue",Arial,sans-serif; line-height:1.2;
  break-after:avoid; page-break-after:avoid; margin:1.2em 0 .4em; }
h1 { font-size:1.9em; } h2 { font-size:1.45em; } h3 { font-size:1.2em; }
h4,h5,h6 { font-size:1.05em; }
p { orphans:3; widows:3; margin:.5em 0; }
a { color:var(--accent); text-decoration:none; }
code,.sig { font-family:"Courier New",monospace; font-size:.9em; }
hr { border:0; border-top:1px solid var(--rule); margin:1.2em 0; }
.brk { margin:0; height:.6em; }
.dim { color:var(--dim); }
.titlepage { margin-bottom:2em; }

.doc { break-before:page; page-break-before:always; }
.doc:first-of-type { break-before:auto; page-break-before:auto; }
.doc-title { border-bottom:2px solid var(--ink); padding-bottom:.2em; }
.rec { break-inside:avoid-page; }

.synopsis { color:var(--dim); font-style:italic; border-left:3px solid var(--rule);
  padding-left:.7em; margin:.6em 0; }
.dangling { color:#a33; border-bottom:1px dotted #a33; }
.elsewhere { border-bottom:1px dotted var(--rule); }

dl.facts { display:grid; grid-template-columns:max-content 1fr; gap:.15em .8em;
  margin:.5em 0; font-family:"Helvetica Neue",Arial,sans-serif; font-size:.85em;
  break-inside:avoid; page-break-inside:avoid; }
dl.facts dt { color:var(--dim); text-transform:uppercase; letter-spacing:.04em;
  font-size:.85em; padding-top:.15em; }
dl.facts dd { margin:0; }
dl.facts.aside { background:var(--panel); padding:.5em .7em; border-radius:3px; }
dl.kv { margin:0; display:grid; grid-template-columns:max-content 1fr; gap:0 .6em; }
dl.kv dt { color:var(--dim); } dl.kv dd { margin:0; }
ul.vals { margin:0; padding-left:1.1em; }

.swatch { display:inline-block; width:.85em; height:.85em; border:1px solid var(--rule);
  vertical-align:-.1em; margin-right:.3em; }
.pill { display:inline-block; background:var(--panel); border:1px solid var(--rule);
  border-radius:999px; padding:0 .55em; font-size:.9em; }
.pill-unknown { border-style:dashed; color:#a33; }
.cell { display:inline-block; border:1px solid var(--rule); padding:0 .4em;
  font-family:"Courier New",monospace; font-size:.9em; }
.num { font-variant-numeric:tabular-nums; }

.callout { border-left:4px solid var(--accent); background:var(--panel);
  padding:.5em .8em; margin:.8em 0; break-inside:avoid; page-break-inside:avoid; }
.callout-title { font-weight:bold; margin:0 0 .2em; }
.callout p { margin:.2em 0; }
.callout-warning,.callout-caution { border-left-color:#b35; }
.callout-tip { border-left-color:#2a7; }

.tablewrap { overflow-x:auto; break-inside:avoid; page-break-inside:avoid; margin:.8em 0; }
table { border-collapse:collapse; width:100%; font-size:.92em; }
th,td { border:1px solid var(--rule); padding:.25em .5em; text-align:left; }
th { background:var(--panel); }
.ta-c { text-align:center; } .ta-r { text-align:right; }

.art { margin:.6em 0; text-align:center; break-inside:avoid; }
.art img { max-width:100%; }
.facepreload { position:absolute; width:0; height:0; overflow:hidden; }
canvas.face { max-width:100%; }
.art-missing { border:1px dashed var(--rule); color:var(--dim); padding:.5em;
  font-family:"Helvetica Neue",Arial,sans-serif; font-size:.85em; }
.art-kind { display:block; font-style:italic; }

.variants { border-left:2px dotted var(--rule); padding-left:.7em; }
.gate { display:inline-block; background:var(--panel); border-radius:3px;
  padding:0 .4em; margin-right:.4em; font-size:.8em; color:var(--dim);
  font-family:"Helvetica Neue",Arial,sans-serif; }
.choice { margin:.25em 0 .25em 1em; }
.choice-label { font-weight:bold; }
.choice-label::before { content:"> "; color:var(--dim); }
.guard,.outcome { font-size:.82em; color:var(--dim);
  font-family:"Helvetica Neue",Arial,sans-serif; }
.outcome::before { content:"; "; }
.goto { font-size:.82em; font-family:"Courier New",monospace; }
.transclude { border-left:3px solid var(--rule); margin:.6em 0; padding-left:.8em; }

/* PDF bookmarks - the outline a reader navigates by in the sidebar.
   `bookmark-level` is CSS GCPM: WeasyPrint (and Prince) build a real PDF
   outline from it, Chrome ignores it harmlessly. The browser path gets the
   same thing a different way - see the pypdf outline pass - because Chrome's
   print-to-pdf has no bookmark facility at all, though it does already emit
   /Link annotations with resolved destinations for every anchor. */
h1 { bookmark-level: 1; }
h2 { bookmark-level: 2; }
h3 { bookmark-level: 3; }
#toc, .titlepage, .runhead, .runfoot { bookmark-level: none; }

#toc { break-after:page; page-break-after:always; }
#toc ol { list-style:none; padding-left:1em; }
#toc > ol { padding-left:0; }
.toc-l2 { padding-left:1em; } .toc-l3 { padding-left:2em; }
#toc a::after { content: leader(dotted) target-counter(attr(href url), page); }

.runhead,.runfoot { display:none; }

@page { size: letter; margin: 0.9in 0.8in; }
@page :first { margin-top: 1.6in; }

@media print {
  body { font-size:10.5pt; }
  .sheet { max-width:none; margin:0; padding:0; }
  .runhead { display:block; position:fixed; top:-0.55in; left:0; right:0;
    font:9pt "Helvetica Neue",Arial,sans-serif; color:var(--dim);
    border-bottom:1px solid var(--rule); padding-bottom:2px; }
  .runfoot { display:block; position:fixed; bottom:-0.55in; left:0; right:0;
    font:8pt "Helvetica Neue",Arial,sans-serif; color:var(--dim); text-align:right; }
  a { color:var(--ink); }
  .goto, #toc a { color:var(--dim); }
}
"""


def _shell(title, subtitle, body, toc, extra_css=""):
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<style>{CSS}{extra_css}</style>
</head><body>
<div class="runhead">{esc(title)}</div>
<div class="runfoot">{esc(subtitle)}</div>
<div class="sheet">
<header class="titlepage"><h1>{esc(title)}</h1><p class="dim">{esc(subtitle)}</p></header>
{toc}
{body}
</div></body></html>
"""


def _relink(body, present):
    """Demote every `href="#x"` whose `x` this lens did not emit.

    A catalog card can reference a record that has no card; a screenplay scene
    can name a beat that is not spoken. The reference is still TRUE - it is just
    not in this edition - so the words stay and the link goes, rather than the
    page offering a jump that lands nowhere."""
    import re

    def sub(m):
        target, inner = m.group("t"), m.group("inner")
        if target in present:
            return m.group(0)
        return f'<span class="elsewhere">{inner}</span>'

    return re.sub(r'<a[^>]*href="#(?P<t>[^"]+)"[^>]*>(?P<inner>.*?)</a>',
                  sub, body, flags=re.S)


def _face_capable(assets, faces="canvas"):
    """Can a face actually be PAINTED, not merely resolved?

    Two things are needed and they come from different places: the sheets (from
    the asset resolver) and the compositor (`cosmos_dev/mockgui/face.js`).
    `cosmos_dev` is a dev-only package and never ships inside a mission's
    `.sbslib`, so a packaged deployment has the first and not the second.

    Emitting a canvas on the strength of the resolver alone produced the worst
    available outcome there: a permanently blank box, with no placeholder to say
    anything was meant to be in it. Both, or neither.

    `faces="placeholder"` is the third case: a formatter that runs no JavaScript
    at all. WeasyPrint is the one that matters - it types better than any browser
    and would paint every canvas blank, which is the same silent failure arrived
    at from the other direction. A caller that knows its renderer cannot script
    says so, and gets the honest figure instead."""
    if faces != "canvas":
        return False
    if not getattr(assets, "face_sheets", None):
        return False
    try:
        from sbs_utils.procedural.amd_assets import face_js_path
        return face_js_path() is not None
    except Exception:
        return False


def _face_script(body, assets):
    """The inline compositor for every `face://` canvas on the page, or "".

    `face.js` is REUSED, not reimplemented - it is the canonical copy, the mock
    server and the VS Code extension already share it, and its own header says
    hosts differ only in how an atlas basename becomes a URL. A printed page
    differs exactly that much: the sheets arrive as `data:` URIs.

    Nothing here comes from the document except face strings, which travel in an
    escaped `data-face` attribute and are read with `dataset` - never built into
    source. A page with no faces gets no script at all."""
    import re

    specs = re.findall(r'data-face="([^"]*)"', body or "")
    if not specs:
        return ""
    import html as _html
    sheets = assets.face_sheets([_html.unescape(s) for s in specs])
    if not sheets:
        return ""
    path = None
    try:
        from sbs_utils.procedural.amd_assets import face_js_path
        path = face_js_path()
    except Exception:
        pass
    if path is None:
        return ""
    with open(path, "r", encoding="utf-8") as f:
        face_js = f.read()
    if "</script" in face_js:
        return ""                   # refuse to emit anything that closes the tag
    import json
    # THREE parts, in this order, and the order is the whole mechanism:
    #   1. the compositor + the sheet resolver, so `FaceRender` exists;
    #   2. the preload images, whose `onload` calls into it;
    #   3. the paint bootstrap.
    # Emitting the images first looked tidier and was wrong: a `data:` URI can
    # decode before the parser reaches a later script, so `onload` would fire
    # against an undefined `FaceRender` and the warm would be lost - leaving
    # exactly the race this is here to remove.
    setup = ('(function(){var S=' + json.dumps(sheets) + ';'
             'FaceRender.setSheetResolver(function(n){return S[n]||"";});})();')
    paint = [
        '(function(){function paint(){document.querySelectorAll("canvas.face")',
        '.forEach(function(c){FaceRender.drawString(',
        'c,c.getContext("2d"),c.dataset.face||"");});}',
        'if(document.readyState==="complete"){paint();}',
        'else{window.addEventListener("load",paint);}',
        'window.addEventListener("beforeprint",paint);})();',
    ]
    tag = '</scr' + 'ipt>'
    return ('<script>' + face_js + chr(10) + setup + tag
            + _face_preload(sheets)
            + '<script>' + ''.join(paint) + tag)


def _face_preload(sheets):
    """Markup that makes every atlas decoded before `load` fires.

    These are PARSER-INSERTED `<img>` tags, and that is the entire point: the
    document's `load` event waits for them, where an `Image()` created in script
    carries no such guarantee. Each one hands its decoded self to
    `FaceRender.warm`, and `getSheet` then answers synchronously - so by the time
    `paint()` runs there is no pending load at all.

    That matters because of who else prints this page. A headless browser asked
    for a PDF will not wait for work it has no reason to expect; "the atlases
    happened to arrive in time" is a race that passes on a warm disk and fails on
    a cold one, or on a bigger document. This makes it a guarantee instead.

    One tag per ATLAS, not per face: six races is the ceiling however many
    characters a mission has."""
    from sbs_utils.procedural.amd_assets import face_alias_table
    by_file = {}
    for alias, name in (face_alias_table() or {}).items():
        by_file.setdefault(name, alias)
    tags = []
    for name, url in (sheets or {}).items():
        alias = by_file.get(name)
        if not alias:
            continue
        tags.append(f'<img src="{esc(url)}" alt="" '
                    f'onload="FaceRender.warm(&#39;{esc(alias)}&#39;,this)">')
    if not tags:
        return ""
    return '<div class="facepreload" aria-hidden="true">' + "".join(tags) + "</div>"


def _ids_in(html_text):
    """Every `id="..."` the rendered body actually emitted."""
    import re
    return set(re.findall(r'\sid="([^"]+)"', html_text or ""))


def _toc(docs, ctx, present):
    """Contents, built from the ids the body ACTUALLY emitted.

    Every lens renders a different subset - the catalog only takes records with a
    fence, the screenplay only what is spoken - so a contents list built from the
    document tree links to records that lens never printed. Filtering on what was
    emitted makes a dangling entry structurally impossible rather than a thing to
    remember per lens.

    Anchors are path-based, so a repeated key still lands on the right record."""
    out = ['<nav id="toc"><h2>Contents</h2><ol>']
    for uri, doc in docs:
        rows = []
        for node in doc.nodes:
            anchor = anchor_of(uri, node)
            if anchor not in present:
                continue
            depth = min(3, max(1, node.level or 1))
            rows.append(f'<li class="toc-l{depth}">'
                        f'<a href="#{esc(anchor)}">'
                        f"{esc(node.display or node.key)}</a></li>")
        if not rows:
            continue
        head = esc(_doc_title(uri, doc))
        doc_id = slug(_basename(uri))
        if doc_id in present:
            head = f'<a href="#{esc(doc_id)}">{head}</a>'
        out.append(f"<li>{head}<ol>")
        out.extend(rows)
        out.append("</ol></li>")
    out.append("</ol></nav>")
    return chr(10).join(out)


def amd_render_html(docs, lens="prose", profile="author", title=None,
                    assets=None, resolve=None, show_internal=False,
                    faces="canvas"):
    """`[(uri, AmdDocument)]` -> one self-contained HTML page.

    `lens` picks the audience (see the module docstring); `profile` is `author`
    or `player`. `resolve` is an optional mission-wide `key -> AmdNode` lookup so
    a reference that crosses a file still links - something a single document
    cannot do on its own."""
    if lens not in LENSES:
        raise ValueError(f"unknown lens {lens!r}; expected one of {', '.join(LENSES)}")
    if profile not in PROFILES:
        raise ValueError(f"unknown profile {profile!r}")
    if lens == "bible" and profile == "player":
        # Not a styling choice. The bible exists to show the machine - every
        # trigger, every hidden beat, every branch a player must never be handed.
        raise ValueError("the bible lens has no player profile: the bible IS the "
                         "spoiler. Use --lens prose for a player-facing document.")
    if resolve is None:
        resolve = _mission_resolver(docs)
    ctx = {"profile": profile, "assets": assets or NoAssets(), "resolve": resolve,
           "show_internal": show_internal, "uri_of": _uri_of(docs), "lens": lens,
           "faces": faces}
    global _DOC_TOKENS
    _DOC_TOKENS = doc_tokens(docs)
    body = _LENSES[lens](docs, ctx)
    present = _ids_in(body)
    body = _relink(body, present)
    name = title or "AMD"
    if faces == "canvas":
        body += _face_script(body, ctx["assets"])
    return _shell(name, f"{lens} edition - {profile} profile", body,
                  _toc(docs, ctx, present), _LENS_CSS.get(lens, ""))


def _mission_resolver(docs):
    """A mission-wide key lookup across every document. An ambiguous key resolves
    to nothing rather than to a guess, matching `AmdDocument.resolve_target`."""
    index = {}
    for _uri, doc in docs:
        for node in doc.nodes:
            index.setdefault(node.key, []).append(node)
            index.setdefault(path_of(node), []).append(node)

    def resolve(target):
        hits = index.get(str(target or "").strip(), ())
        return hits[0] if len(hits) == 1 else None
    return resolve


def _uri_of(docs):
    owner = {}
    for uri, doc in docs:
        for node in doc.nodes:
            owner[id(node)] = uri
    return lambda node: owner.get(id(node), "")


_LENS_CSS = {}
_LENSES = {"prose": lens_prose}


# --- the catalog lens --------------------------------------------------------
# The archetype order a sourcebook reads in: who exists, then where, then what,
# then how the mission is wired. Not alphabetical - a reader looking something up
# is looking for a KIND of thing, and the kinds have a natural order.
_CATALOG_ORDER = ("side", "lifeform", "landmark", "region", "map", "item", "drop",
                  "scan", "quest", "dialogue", "cutscene", "urge", "effect", "image")

_CATALOG_CSS = """
.cards { column-count:2; column-gap:.35in; }
@media print { .cards { column-gap:.3in; } }
.card { break-inside:avoid; page-break-inside:avoid; -webkit-column-break-inside:avoid;
  border:1px solid var(--rule); border-radius:3px; padding:.5em .7em; margin:0 0 .3in;
  display:inline-block; width:100%; }
.card h3 { margin:0 0 .3em; font-size:1.05em; }
.card .key { font-family:"Courier New",monospace; font-size:.78em; color:var(--dim);
  font-weight:normal; }
.card p { font-size:.9em; margin:.35em 0 0; }
.card dl.facts { font-size:.8em; }
.arch { break-before:page; page-break-before:always; border-bottom:2px solid var(--ink);
  column-span:all; }
.arch:first-of-type { break-before:auto; page-break-before:auto; }
.arch-count { float:right; font-weight:normal; color:var(--dim); font-size:.7em; }
"""


def lens_catalog(docs, ctx):
    """Every record that HAS a fence, grouped by archetype, as reference cards.

    This is the lens that proves the field registry was worth building: the fence
    is the content, so each field is rendered as its TYPE - a color as a swatch, a
    reference as a working link, a coordinate as a cell - rather than as the line
    of text it was typed as."""
    by_arch = {}
    for uri, doc in docs:
        for node in doc.nodes:
            if not (node.data or {}):
                continue
            by_arch.setdefault(node.kind or "other", []).append((uri, doc, node))
    order = [a for a in _CATALOG_ORDER if a in by_arch]
    order += sorted(a for a in by_arch if a not in order)
    out = []
    for arch in order:
        entries = by_arch[arch]
        out.append(f'<h2 class="arch" id="arch-{esc(slug(arch))}">{esc(arch.title())}'
                   f'<span class="arch-count">{len(entries)}</span></h2>')
        out.append('<div class="cards">')
        for uri, doc, node in entries:
            out.append(_card(uri, doc, node, ctx))
        out.append("</div>")
    return "\n".join(out)


def _card(uri, doc, node, ctx):
    inner = dict(ctx)
    inner["doc"], inner["uri"] = doc, uri
    drop = _MACHINERY if ctx.get("profile") == "player" else None
    facts = facts_html(node, inner, drop=drop)
    # A card with forty lines of prose breaks the grid, and a reference card is
    # not where anyone reads forty lines. The prose lens holds the whole thing.
    blocks = amd_blocks(node, doc=doc, profile=ctx.get("profile", "author"),
                        resolve=ctx.get("resolve"))
    prose = [b for b in blocks if b["type"] == "paragraph"][:2]
    body = "".join(f"<p>{_inline(b, inner)}</p>" for b in prose)
    return (f'<div class="card" id="{esc(anchor_of(uri, node))}">'
            f'<h3>{esc(node.display or node.key)} '
            f'<span class="key">{esc(node.key)}</span></h3>'
            f"{facts}{body}</div>")


# --- the screenplay lens -----------------------------------------------------
# Classic Fountain geometry, in inches from the text block's left edge. A reader
# recognizes a script by its shape before reading a word of it, so the shape is
# the feature.
_SCREENPLAY_CSS = """
.lens-screenplay { font:12pt/1 "Courier Prime","Courier New",Courier,monospace; }
.lens-screenplay .scene { break-before:page; page-break-before:always;
  font-weight:bold; text-transform:uppercase; margin:0 0 1em; }
.lens-screenplay .scene:first-of-type { break-before:auto; page-break-before:auto; }
.lens-screenplay .slug { color:var(--dim); font-weight:normal; text-transform:none;
  font-size:.85em; display:block; }
.lens-screenplay .cue { margin:1em 0 0 2.2in; text-transform:uppercase; }
.lens-screenplay .direction { margin:0 0 0 2.0in; font-style:italic; }
.lens-screenplay .speech { margin:0 0 0 1.0in; max-width:3.5in; }
.lens-screenplay .variants { margin-left:1.0in; border-left:2px solid var(--rule);
  padding-left:.3in; max-width:3.7in; }
.lens-screenplay .variants .speech { margin-left:0; }
.lens-screenplay .transition { text-align:right; text-transform:uppercase;
  margin:1em 0; }
.lens-screenplay p { margin:0 0 1em; }
/* The classic dangling-cue bug: a speaker's name alone at the foot of a page. */
.lens-screenplay .beat { break-inside:avoid; page-break-inside:avoid; }
.lens-screenplay .options { border:1px solid var(--rule); padding:.4em .7em;
  margin:1em 0 1em .8in; max-width:4.2in; break-inside:avoid; }
.lens-screenplay .options-title { font-size:.8em; letter-spacing:.1em;
  color:var(--dim); margin:0 0 .3em; }
"""

# The block types that make a record a scene rather than a page of prose.
_SCRIPTED = frozenset({"cue", "direction", "transition", "speech", "choice"})


def lens_screenplay(docs, ctx):
    """Dialogue and beats as a script someone could read aloud.

    Selection is by CONTENT as well as by archetype, and that second clause is
    what makes the lens work on the corpus that exists: not one shipped `.amd`
    contains a `@cue` or a `(direction)`. What they contain is `Speaker:` in the
    fence and bare `%` variant lines, so a record with speech and no cue prints
    its fence speaker as an implicit one."""
    out = []
    for uri, doc in docs:
        for node in doc.nodes:
            blocks = amd_blocks(node, doc=doc,
                                profile=ctx.get("profile", "author"),
                                resolve=ctx.get("resolve"))
            scripted = {b["type"] for b in blocks} & _SCRIPTED
            if node.kind not in ("dialogue", "cutscene") and not scripted:
                continue
            out.append(_scene(uri, doc, node, blocks, ctx))
    if not out:
        return ('<p class="dim">No dialogue, cutscenes or spoken lines in these '
                "files.</p>")
    return '<div class="lens-screenplay">' + chr(10).join(out) + "</div>"


def _scene(uri, doc, node, blocks, ctx):
    inner = dict(ctx)
    inner["doc"], inner["uri"] = doc, uri
    data = node.data or {}
    when = str(data.get("when") or "").lower()
    where = {"comms": "INT. COMMS - INCOMING",
             "hail": "INT. COMMS - OUTGOING"}.get(when, "")
    speaker = data.get("speaker")
    slug_bits = [b for b in (data.get("title"), data.get("side")) if b]
    if speaker:
        slug_bits.insert(0, f"speaker: {speaker}")
    head = (f'<p class="scene" id="{esc(anchor_of(uri, node))}">'
            f"{esc(node.display or node.key)}"
            + (f'<span class="slug">{esc(where)}</span>' if where else "")
            + (f'<span class="slug">{esc(" - ".join(str(b) for b in slug_bits))}'
               f"</span>" if slug_bits else "") + "</p>")

    body, choices, had_cue = [], [], False
    for b in blocks:
        if b["type"] == "cue":
            had_cue = True
        if b["type"] == "choice":
            choices.append(b)
            continue
        if b["type"] == "speech" and not had_cue and speaker:
            # No cue was written, so print the fence speaker once, as one would.
            body.append(f'<p class="cue">{esc(speaker).upper()}</p>')
            had_cue = True
        body.append(_block_html(b, inner, 0))
    inner_html = "\n".join(x for x in body if x)
    opts = ""
    if choices:
        rows = "".join(_choice_html(c, inner) for c in choices)
        opts = ('<div class="options"><p class="options-title">PLAYER OPTIONS</p>'
                + rows + "</div>")
    return f'<div class="beat">{head}{inner_html}{opts}</div>'


# --- the bible lens ----------------------------------------------------------
_BIBLE_CSS = """
.front dl { display:grid; grid-template-columns:max-content 1fr; gap:.1em .8em; }
.front dt { color:var(--dim); } .front dd { margin:0; }
.beatgroup { break-before:page; page-break-before:always; }
.beatgroup:first-of-type { break-before:auto; page-break-before:auto; }
.stat { border:1px solid var(--rule); border-left:4px solid var(--accent);
  padding:.5em .8em; margin:.6em 0; break-inside:avoid; page-break-inside:avoid; }
.stat.pool { border-left-color:var(--rule); }
.stat h3 { margin:0; font-size:1.05em; }
.stat .meta { color:var(--dim); font-size:.8em;
  font-family:"Helvetica Neue",Arial,sans-serif; }
.wires { display:grid; grid-template-columns:max-content 1fr; gap:.1em .7em;
  font-size:.82em; margin:.4em 0 0;
  font-family:"Helvetica Neue",Arial,sans-serif; }
.wires dt { color:var(--dim); } .wires dd { margin:0; }
.graphpage { break-before:page; page-break-before:always; page:bible-graph; }
.graph { width:100%; height:auto; border:1px solid var(--rule); }
.graph text { font:6px "Helvetica Neue",Arial,sans-serif; }
@page bible-graph { size: letter landscape; margin: 0.5in; }
"""

_EDGE_COLOR = {"parent": "#888", "signal": "#1a4f8a", "reveal": "#2a7",
               "choice": "#b35", "scene": "#95a"}


def lens_bible(docs, ctx):
    """The design document: the quest spine, its triggers, and the causal graph.

    Every structural fact here comes from `amd_timeline`, which already computes
    the beat ranking, the spine/pool split and the cross-file signal join. That
    join is the reason the module exists and the reason this lens cannot be done
    a document at a time: a signal emitted in one file is waited on in another."""
    from sbs_utils.procedural import amd_schema as _schema
    from sbs_utils.procedural import amd_timeline

    model = amd_timeline.timeline(docs, archetype_of=_schema.infer_archetype)
    items = model.get("items") or []
    by_uid = {i["uid"]: i for i in items}
    node_of = _node_index(docs)

    inbound, outbound = {}, {}
    for e in model.get("edges") or ():
        outbound.setdefault(e["fromUid"], []).append(e)
        inbound.setdefault(e["toUid"], []).append(e)

    out = [_bible_front(docs, model)]
    spine = [i for i in items if i.get("track") == "spine"]
    pool = [i for i in items if i.get("track") != "spine"]

    for beat in range(model.get("beats", 0) or 0):
        here = [i for i in spine if i.get("beat") == beat]
        if not here:
            continue
        out.append(f'<section class="beatgroup"><h2>Beat {beat + 1}</h2>')
        for item in sorted(here, key=lambda i: (i["groups"].get("arc") or "",
                                                i.get("path") or "")):
            out.append(_stat_block(item, inbound, outbound, by_uid, node_of, ctx))
        out.append("</section>")

    if pool:
        out.append('<section class="beatgroup"><h2>Pool</h2>'
                   '<p class="dim">Optional content, reachable but not on the '
                   "spine. Ordered by section.</p>")
        for item in sorted(pool, key=lambda i: (i["groups"].get("section") or "",
                                                i.get("path") or "")):
            out.append(_stat_block(item, inbound, outbound, by_uid, node_of, ctx))
        out.append("</section>")

    out.append(_bible_graph(model))
    out.append(_bible_cycles(model))
    return "\n".join(out)


def _node_index(docs):
    index = {}
    for uri, doc in docs:
        for node in doc.nodes:
            index[f"{uri}#{path_of(node)}"] = (uri, node)
    return index


def _bible_front(docs, model):
    items = model.get("items") or []
    arch = {}
    for i in items:
        arch[i.get("archetype") or "other"] = arch.get(i.get("archetype") or "other", 0) + 1
    rows = "".join(f"<dt>{esc(k)}</dt><dd>{v}</dd>"
                   for k, v in sorted(arch.items(), key=lambda kv: -kv[1]))
    spine = sum(1 for i in items if i.get("track") == "spine")
    return (f'<section class="front"><h2>The shape of it</h2><dl>'
            f"<dt>files</dt><dd>{len(docs)}</dd>"
            f"<dt>records</dt><dd>{len(items)}</dd>"
            f"<dt>spine / pool</dt><dd>{spine} / {len(items) - spine}</dd>"
            f'<dt>beats</dt><dd>{model.get("beats", 0)}</dd>'
            f'<dt>causal edges</dt><dd>{len(model.get("edges") or ())}</dd>'
            f"</dl><h3>By kind</h3><dl>{rows}</dl></section>")


def _stat_block(item, inbound, outbound, by_uid, node_of, ctx):
    uri_node = node_of.get(item["uid"])
    anchor = anchor_of(*uri_node) if uri_node else slug(item.get("path"))
    meta = [item.get("archetype") or "?"]
    if item.get("state"):
        meta.append(str(item["state"]))
    if item.get("required"):
        meta.append("required")
    if item.get("declared"):
        meta.append(str(item["declared"]))

    life = item.get("lifecycle") or {}
    wires = []
    for label, key in (("goal", "goal"), ("when", "when"),
                       ("on accept", "on_accept"), ("on complete", "on_complete"),
                       ("fail signal", "fail_signal")):
        if life.get(key):
            wires.append(f"<dt>{label}</dt><dd>{esc(life[key])}</dd>")
    wires.append(_edge_list("reached from", inbound.get(item["uid"]), by_uid,
                            node_of, "from"))
    wires.append(_edge_list("leads to", outbound.get(item["uid"]), by_uid,
                            node_of, "to"))
    # A record's OWN trigger fields. amd_timeline normalizes some of them into
    # `lifecycle` and leaves the rest in the fence, so reading only the lifecycle
    # silently dropped the wiring a designer opened this page to see.
    trig = ""
    if uri_node is not None:
        inner = dict(ctx)
        inner["doc"], inner["uri"] = None, uri_node[0]
        trig = facts_html(uri_node[1], inner, only=_MACHINERY, css="facts")
    cls = "stat" if item.get("track") == "spine" else "stat pool"
    return (f'<div class="{cls}" id="{esc(anchor)}">'
            f'<h3>{esc(item.get("display") or item.get("key"))}</h3>'
            f'<p class="meta">{esc(" - ".join(meta))} &middot; '
            f'<code>{esc(item.get("path"))}</code></p>{trig}'
            f'<dl class="wires">{"".join(w for w in wires if w)}</dl></div>')


def _edge_list(label, edges, by_uid, node_of, side):
    if not edges:
        return ""
    bits = []
    for e in edges:
        uid = e["fromUid"] if side == "from" else e["toUid"]
        other = by_uid.get(uid)
        shown = (other or {}).get("display") or e.get(side) or uid
        uri_node = node_of.get(uid)
        href = anchor_of(*uri_node) if uri_node else slug(shown)
        bits.append(f'<a href="#{esc(href)}">{esc(shown)}</a>'
                    f' <span class="dim">({esc(e.get("kind") or "")})</span>')
    return f"<dt>{label}</dt><dd>{', '.join(bits)}</dd>"


def _bible_graph(model):
    """One landscape page of the causal graph.

    No layout library, because the ranking already did the layout: the beat IS
    the x column and the arc lane IS the y row. Anything cleverer would be a
    second opinion about a structure the timeline already decided."""
    items = model.get("items") or []
    if not items:
        return ""
    lanes = (model.get("lanes") or {}).get("arc") or []
    lane_at = {name: n for n, name in enumerate(lanes)}
    beats = max(1, model.get("beats", 1) or 1)
    colw, rowh, pad = 150, 26, 20
    width = pad * 2 + colw * beats
    height = pad * 2 + rowh * max(1, len(lanes))
    pos = {}
    used = {}
    for i in items:
        col = i.get("beat", 0) or 0
        row = lane_at.get((i["groups"] or {}).get("arc"), 0)
        # Two records in the same cell would sit on top of each other; nudge.
        n = used.get((col, row), 0)
        used[(col, row)] = n + 1
        pos[i["uid"]] = (pad + col * colw + 8, pad + row * rowh + 12 + n * 9)

    svg = [f'<svg class="graph" viewBox="0 0 {width} {height}" '
           f'xmlns="http://www.w3.org/2000/svg">']
    for b in range(beats):
        x = pad + b * colw
        svg.append(f'<line x1="{x}" y1="{pad - 10}" x2="{x}" y2="{height - pad}" '
                   f'stroke="#eee"/>')
        svg.append(f'<text x="{x + 4}" y="{pad - 12}" fill="#999">beat {b + 1}</text>')
    for e in model.get("edges") or ():
        a, b = pos.get(e["fromUid"]), pos.get(e["toUid"])
        if not a or not b:
            continue
        mid = (a[0] + b[0]) / 2
        color = _EDGE_COLOR.get(e.get("kind"), "#999")
        svg.append(f'<path d="M{a[0]},{a[1]} C{mid},{a[1]} {mid},{b[1]} {b[0]},{b[1]}" '
                   f'fill="none" stroke="{color}" stroke-width="0.7" opacity="0.8"/>')
    for i in items:
        x, y = pos[i["uid"]]
        fill = "#1a4f8a" if i.get("track") == "spine" else "#bbb"
        svg.append(f'<circle cx="{x}" cy="{y}" r="2.2" fill="{fill}"/>')
        svg.append(f'<text x="{x + 4}" y="{y + 2}" fill="#333">'
                   f'{esc((i.get("display") or i.get("key") or "")[:26])}</text>')
    svg.append("</svg>")
    key = " ".join(f'<span style="color:{c}">&#9632; {esc(k)}</span>'
                   for k, c in _EDGE_COLOR.items())
    return ('<section class="graphpage"><h2>The graph</h2>'
            f'<p class="dim">{key}</p>' + "".join(svg) + "</section>")


def _bible_cycles(model):
    cycles = model.get("cycles") or []
    if not cycles:
        return ""
    rows = "".join(f"<li>{esc(c['from'])} &rarr; {esc(c['to'])}</li>" for c in cycles)
    return ('<section class="beatgroup"><h2>Loops</h2>'
            "<p>The ranking had to break these to put the story in an order. A loop "
            "is not necessarily a bug - it is often a hub a player returns to - but "
            "every one of them is a place where <em>what happens next</em> has more "
            f"than one answer.</p><ul>{rows}</ul></section>")


_LENS_CSS.update({"catalog": _CATALOG_CSS, "screenplay": _SCREENPLAY_CSS,
                  "bible": _BIBLE_CSS})
_LENSES.update({"catalog": lens_catalog, "screenplay": lens_screenplay,
                "bible": lens_bible})
