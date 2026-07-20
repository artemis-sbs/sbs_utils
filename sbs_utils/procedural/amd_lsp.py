"""A minimal AMD language server (LSP over stdio) - editor-agnostic diagnostics.

Speaks just enough LSP to publish `amd_lint` findings as live diagnostics: any
LSP-capable editor (VSCode, Neovim, Emacs, Sublime, JetBrains) points its client
at this server and gets squiggles as you type. Launch it via `sbs lint --lsp`
(which puts the right `sbs_utils` on the path) or `python -m
sbs_utils.procedural.amd_lsp`.

Dependency-free: hand-rolled JSON-RPC framing (no `pygls`), stdlib only, so it
ships inside `sbs.pyz` and runs under the Cosmos-bundled Python. It reuses the
`amd_core` model through `amd_lint`, and finds a document's mission root (walking
up to `story.json` / `story.mast`) to gather `.mast` for the cross-file checks.

Scope is deliberately diagnostics-only (textDocumentSync = Full). Navigation,
completion, symbols, and rename are natural follow-ons over the same model.
"""
import sys
import os
import re
import json
import glob
from urllib.parse import urlparse, unquote


# --- mission context --------------------------------------------------------
def _uri_to_path(uri):
    if not isinstance(uri, str):
        return ""       # tolerate a malformed request (e.g. a non-string uri) rather than crash the server
    parsed = urlparse(uri)
    path = unquote(parsed.path)
    # Windows: file:///c:/... -> /c:/... ; strip the leading slash.
    if os.name == "nt" and path.startswith("/") and len(path) > 2 and path[2] == ":":
        path = path[1:]
    return path


def _mission_root(path):
    """Walk up from an .amd file to the folder that marks a mission, or None."""
    d = os.path.dirname(os.path.abspath(path))
    for _ in range(24):
        for marker in ("story.json", "story.mast", "__lib__.json"):
            if os.path.isfile(os.path.join(d, marker)):
                return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return None


def _read(path):
    try:
        with open(path, "r") as f:
            return f.read()
    except Exception:
        return None


def _path_to_uri(path):
    from pathlib import Path
    return Path(os.path.abspath(path)).as_uri()


# --- workspace index (whole-mission awareness, so editor == `sbs lint`) ------
# Cached per mission root; cleared on any document mutation. An index holds the
# mission-wide symbol table, every .amd doc (parsed from the open buffer when a
# file is open, else disk), and the .mast/.py sources for the signal checks.
_index_cache = {}


def _invalidate():
    _index_cache.clear()


def _open_by_path(docs):
    """normcase(abspath) -> (text, uri) for every open document."""
    out = {}
    for uri, text in docs.items():
        out[os.path.normcase(os.path.abspath(_uri_to_path(uri)))] = (text, uri)
    return out


def _mission_index(root, docs):
    if root in _index_cache:
        return _index_cache[root]
    from sbs_utils.procedural.amd_core import parse
    open_by = _open_by_path(docs)
    amd_docs, known = [], set()
    for p in glob.glob(os.path.join(root, "**", "*.amd"), recursive=True):
        ap = os.path.normcase(os.path.abspath(p))
        text, uri = open_by.get(ap, (None, None))
        if text is None:
            text = _read(p)
        if text is None:
            continue
        doc = parse(text)
        doc.source = text
        amd_docs.append((ap, uri or _path_to_uri(p), doc))
        known |= doc.keys
    mast = []
    for pat in ("*.mast", "*.py"):
        for p in glob.glob(os.path.join(root, "**", pat), recursive=True):
            t = _read(p)
            if t is not None:
                mast.append(t)
    index = {"known": known, "docs": amd_docs, "mast": mast or None}
    _index_cache[root] = index
    return index


def _index_for(uri, docs):
    """The mission index for `uri`, or a single-file index if no mission root."""
    path = _uri_to_path(uri)
    root = _mission_root(path)
    if root:
        return _mission_index(root, docs)
    from sbs_utils.procedural.amd_core import parse
    doc = parse(docs.get(uri, ""))
    doc.source = docs.get(uri, "")
    ap = os.path.normcase(os.path.abspath(path))
    return {"known": set(doc.keys), "docs": [(ap, uri, doc)], "mast": None}


def _cur_doc(index, uri):
    """The parsed doc + canonical uri for `uri` within an index."""
    ap = os.path.normcase(os.path.abspath(_uri_to_path(uri)))
    for p, u, d in index["docs"]:
        if p == ap:
            return d, u
    return None, uri


def _diagnostics(text, index):
    """amd_lint findings for `text` (mission-aware) -> LSP Diagnostic dicts."""
    from sbs_utils.procedural.amd_lint import amd_lint
    findings = amd_lint(content=text, mast_sources=index["mast"],
                        known_keys=index["known"])
    lines = text.splitlines()
    diags = []
    for f in findings:
        l0 = max(0, (f.line or 1) - 1)
        if f.col is not None:
            start = {"line": l0, "character": f.col}
            end = {"line": max(0, (f.end_line or f.line) - 1),
                   "character": f.end_col if f.end_col is not None else f.col + 1}
        else:
            ln = lines[l0] if l0 < len(lines) else ""
            start = {"line": l0, "character": 0}
            end = {"line": l0, "character": max(1, len(ln))}
        diags.append({
            "range": {"start": start, "end": end},
            "severity": 1 if f.is_error() else 2,   # 1=Error, 2=Warning
            "source": "amd",
            "code": f.code,
            "message": f.message,
        })
    return diags


# --- JSON-RPC framing -------------------------------------------------------
def _read_message(stdin):
    length = None
    while True:
        raw = stdin.readline()
        if not raw:
            return None
        if raw in (b"\r\n", b"\n"):
            break
        s = raw.decode("utf-8", "replace")
        if s.lower().startswith("content-length:"):
            length = int(s.split(":", 1)[1].strip())
    if not length:
        return None
    body = stdin.read(length)
    if isinstance(body, bytes):
        body = body.decode("utf-8")
    try:
        return json.loads(body)
    except Exception:
        return {}


def _write_message(stdout, msg):
    data = json.dumps(msg).encode("utf-8")
    stdout.write(b"Content-Length: " + str(len(data)).encode("ascii") + b"\r\n\r\n")
    stdout.write(data)
    stdout.flush()


def _publish(stdout, uri, text, docs):
    try:
        diags = _diagnostics(text, _index_for(uri, docs))
    except Exception:
        diags = []
    _write_message(stdout, {"jsonrpc": "2.0", "method": "textDocument/publishDiagnostics",
                            "params": {"uri": uri, "diagnostics": diags}})


# --- navigation / symbols / completion / hover (all over the amd_core model) --
def _parse(text):
    from sbs_utils.procedural.amd_core import parse
    return parse(text or "")


def _node_range(node):
    s = node.span
    return {"start": {"line": s.line - 1, "character": s.col},
            "end": {"line": s.end_line - 1, "character": s.end_col}}


def _ref_at(doc, line0, char):
    """The reference whose span contains the 0-based (line, char), or None."""
    for r in doc.refs:
        if r.span.line - 1 == line0 and r.span.col <= char < r.span.end_col:
            return r
    return None


def _symbols(node):
    """Hierarchical DocumentSymbol[] for a node's children (kind 3 = Namespace)."""
    out = []
    for c in node.children:
        out.append({"name": c.display or c.key, "detail": c.key, "kind": 3,
                    "range": _node_range(c), "selectionRange": _node_range(c),
                    "children": _symbols(c)})
    return out


def _find_node(index, key):
    """The (uri, node) that defines `key` anywhere in the mission, or (None, None)."""
    for _p, u, d in index["docs"]:
        n = d.by_key.get(key)
        if n is not None:
            return u, n
    return None, None


def _definition(index, doc, pos):
    subject = _subject_key(doc, pos.get("line", 0), pos.get("character", 0))
    if not subject:
        return None
    uri, node = _find_node(index, subject)
    if node and node.key_span:
        s = node.key_span
        return {"uri": uri, "range": _lsp_range(s.line, s.col, s.end_col)}
    return None


def _hover(index, doc, pos):
    ref = _ref_at(doc, pos.get("line", 0), pos.get("character", 0))
    if not ref:
        return None
    leaf = str(ref.value).split("/")[-1]
    _uri, target = _find_node(index, leaf)
    val = f"**{ref.kind}** → `{ref.value}`"
    if target:
        val += f"\n\n**{target.display or target.key}**"
        if target.summary:
            val += f"\n\n{target.summary}"
    else:
        val += "\n\n*(unresolved)*"
    return {"contents": {"kind": "markdown", "value": val}}


def _completion(index):
    # Offer every node key across the mission. kind 6 = Variable.
    items = [{"label": k, "kind": 6} for k in sorted(index["known"])]
    return {"isIncomplete": False, "items": items}


# --- code actions (quick fixes) ---------------------------------------------
_FIXABLE_DANGLING = ("dangling-choice", "dangling-scene", "dangling-parent", "dangling-reveal")


def _levenshtein(a, b):
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _closest(word, keys, n=3):
    """Up to `n` keys nearest `word` (edit distance within a length-scaled bound)."""
    maxd = max(2, len(word) // 3)
    scored = sorted((( _levenshtein(word, k), k) for k in keys if k and k != word),
                    key=lambda x: (x[0], x[1]))
    return [k for d, k in scored if d <= maxd][:n]


def _end_pos(text):
    lines = text.split("\n")
    return {"line": len(lines) - 1, "character": len(lines[-1])}


def _code_actions(index, doc, text, uri, diagnostics):
    """Quick fixes for the diagnostics overlapping the request: 'Change to <near
    key>' (fuzzy match against the mission symbol table) and 'Create node'."""
    actions = []
    for d in diagnostics or []:
        if d.get("code") not in _FIXABLE_DANGLING:
            continue
        rng = d.get("range") or {}
        start = rng.get("start", {})
        ref = _ref_at(doc, start.get("line", -1), start.get("character", -1))
        value = ref.value if ref else None
        if not value:
            continue
        leaf = str(value).split("/")[-1]
        prefix = value[:-len(leaf)] if "/" in value else ""   # keep any path prefix

        for i, cand in enumerate(_closest(leaf, index["known"])):
            actions.append({
                "title": f"Change to `{cand}`",
                "kind": "quickfix",
                "diagnostics": [d],
                "isPreferred": i == 0,
                "edit": {"changes": {uri: [{"range": rng, "newText": prefix + cand}]}},
            })

        stub = f"\n### [{leaf}]({leaf})\n"
        actions.append({
            "title": f"Create node `{leaf}`",
            "kind": "quickfix",
            "diagnostics": [d],
            "edit": {"changes": {uri: [{"range": {"start": _end_pos(text),
                                                  "end": _end_pos(text)}, "newText": stub}]}},
        })
    return actions


# --- CodeLens: a clickable reference count above each node ------------------
def _code_lens(index, doc, uri):
    out = []
    for node in doc.nodes:
        locs = []
        for _p, u, d in index["docs"]:
            for rg in _key_ranges(d, node.key, include_decl=False):
                locs.append({"uri": u, "range": rg})
        if locs:
            pos = {"line": node.span.line - 1, "character": node.span.col}
            out.append({"range": _node_range(node),
                        "command": {"title": f"{len(locs)} reference(s)",
                                    "command": "editor.action.showReferences",
                                    "arguments": [uri, pos, locs]}})
    return out


# --- Color: swatches + picker for hex colors --------------------------------
_RE_HEX = re.compile(r"#([0-9A-Fa-f]{3,8})\b")


def _hex_to_rgba(h):
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    elif len(h) == 4:
        h = "".join(c * 2 for c in h)
    if len(h) not in (6, 8):
        return None
    try:
        vals = [int(h[i:i + 2], 16) / 255.0 for i in range(0, len(h), 2)]
    except ValueError:
        return None
    r, g, b = vals[0], vals[1], vals[2]
    a = vals[3] if len(vals) == 4 else 1.0
    return {"red": r, "green": g, "blue": b, "alpha": a}


def _document_colors(text):
    out = []
    for i, line in enumerate(text.split("\n")):
        for m in _RE_HEX.finditer(line):
            color = _hex_to_rgba(m.group(1))
            if color is None:
                continue
            out.append({"range": {"start": {"line": i, "character": m.start()},
                                  "end": {"line": i, "character": m.end()}},
                        "color": color})
    return out


def _color_presentations(color):
    to = lambda v: max(0, min(255, round((color.get(v, 0.0)) * 255)))
    hexstr = f"#{to('red'):02x}{to('green'):02x}{to('blue'):02x}"
    if color.get("alpha", 1.0) < 1.0:
        hexstr += f"{to('alpha'):02x}"
    return [{"label": hexstr}]


# --- Inlay hints: a reference's target display name, inline -----------------
def _inlay_hints(index, doc, rng):
    lo = rng.get("start", {}).get("line", 0)
    hi = rng.get("end", {}).get("line", 10 ** 9)
    out = []
    for ref in doc.refs:
        if ref.kind not in _KEY_REF_KINDS:
            continue
        if not (lo <= ref.span.line - 1 <= hi):
            continue
        leaf = str(ref.value).split("/")[-1]
        _u, node = _find_node(index, leaf)
        if node and node.display and node.display != leaf:
            out.append({"position": {"line": ref.span.line - 1, "character": ref.span.end_col},
                        "label": f" {node.display}", "paddingLeft": True, "kind": 2})
    return out


# The reference kinds that carry a renameable node key (not coords/signals).
_KEY_REF_KINDS = ("choice", "scene", "parent", "reveal")


def _node_at(doc, line0, char):
    """The node whose heading line contains the 0-based (line, char), or None."""
    for n in doc.nodes:
        s = n.span
        if s and s.line - 1 == line0 and s.col <= char <= s.end_col:
            return n
    return None


def _ref_segment(ref, char):
    """For a path ref (`a/b/c`), the segment key under the cursor; else the value."""
    val = str(ref.value)
    off = 0
    for seg in val.split("/"):
        start = ref.span.col + off
        if start <= char < start + len(seg):
            return seg
        off += len(seg) + 1
    return val.split("/")[-1]


def _subject_key(doc, line0, char):
    """The node key the cursor is on - via a key-carrying reference or a heading."""
    ref = _ref_at(doc, line0, char)
    if ref and ref.kind in _KEY_REF_KINDS:
        return _ref_segment(ref, char)
    node = _node_at(doc, line0, char)
    return node.key if node else None


def _lsp_range(line1, col, end_col):
    return {"start": {"line": line1 - 1, "character": col},
            "end": {"line": line1 - 1, "character": end_col}}


def _key_ranges(doc, subject, include_decl=True):
    """Every source range where node key `subject` appears - the heading
    declaration(s) and each matching path segment of a key-carrying reference."""
    decl, refs = [], []
    if include_decl:
        for n in doc.nodes:
            if n.key == subject and n.key_span:
                s = n.key_span
                decl.append(_lsp_range(s.line, s.col, s.end_col))
    for r in doc.refs:
        if r.kind not in _KEY_REF_KINDS:
            continue
        off = 0
        for seg in str(r.value).split("/"):
            if seg == subject:
                refs.append(_lsp_range(r.span.line, r.span.col + off, r.span.col + off + len(seg)))
            off += len(seg) + 1
    return decl + refs


def _references(index, doc, pos, include_decl):
    subject = _subject_key(doc, pos.get("line", 0), pos.get("character", 0))
    if not subject:
        return None
    out = []
    for _p, u, d in index["docs"]:
        for rg in _key_ranges(d, subject, include_decl=include_decl):
            out.append({"uri": u, "range": rg})
    return out


def _rename(index, doc, pos, new_name):
    subject = _subject_key(doc, pos.get("line", 0), pos.get("character", 0))
    if not subject or not new_name:
        return None
    changes = {}
    for _p, u, d in index["docs"]:
        edits = [{"range": rg, "newText": new_name}
                 for rg in _key_ranges(d, subject, include_decl=True)]
        if edits:
            changes[u] = edits
    return {"changes": changes} if changes else None


def _formatting(text):
    """A single whole-document TextEdit with the canonically formatted text."""
    from sbs_utils.procedural.amd_fmt import format_text
    formatted = format_text(text)
    if formatted == text:
        return []
    lines = text.split("\n")
    end = {"line": len(lines) - 1, "character": len(lines[-1])}
    return [{"range": {"start": {"line": 0, "character": 0}, "end": end},
             "newText": formatted}]


# --- mission map (custom `amd/map` request -> webview data) -----------------
def _dget(data, *names):
    low = {str(k).lower(): v for k, v in (data or {}).items()}
    for n in names:
        key = n.lower()
        if key in low:
            return low[key]
        if key.replace(" ", "_") in low:
            return low[key.replace(" ", "_")]
    return None


def _coord2(v):
    toks = [int(t) for t in str(v).replace(",", " ").split() if t.lstrip("-").isdigit()]
    return (toks[0], toks[1]) if len(toks) >= 2 else None


def _span_range(span):
    """An amd_core Span -> an LSP Range dict (for the editor to rewrite in place)."""
    return {"start": {"line": span.line - 1, "character": span.col},
            "end": {"line": span.end_line - 1, "character": span.end_col}}


def _mission_map(index):
    """Landmarks (`At: i,j`) and regions (`Center:`/`Radius:`) across the mission,
    for a map view. Each carries its source uri+line (to jump) and, for landmarks,
    the exact `atRange` of the `At:` value (so the view can drag-to-move it)."""
    problems = _problems_by_key(index)
    landmarks, regions = [], []
    for _p, u, d in index["docs"]:
        line_count = getattr(d, "line_count", 0)
        for i, n in enumerate(d.nodes):
            line = (n.span.line - 1) if n.span else 0
            nxt = d.nodes[i + 1] if i + 1 < len(d.nodes) else None
            add_line = (nxt.span.line - 1) if (nxt and nxt.span) else line_count
            at = _dget(n.data, "At")
            cell = _coord2(at) if at is not None else None
            if cell:
                at_ref = next((r for r in n.refs if r.kind == "at"), None)
                kind_ref = next((r for r in n.refs if r.kind == "kind"), None)
                landmarks.append({"key": n.key, "display": n.display or n.key,
                                  "i": cell[0], "j": cell[1],
                                  "kind": str(_dget(n.data, "Kind") or ""),
                                  "uri": u, "line": line, "addLine": add_line,
                                  "atRange": _span_range(at_ref.span) if at_ref else None,
                                  "kindRange": _span_range(kind_ref.span) if kind_ref else None,
                                  "problems": problems.get(n.key)})
            center, radius = _dget(n.data, "Center"), _dget(n.data, "Radius")
            c = _coord2(center) if center is not None else None
            if c is not None and radius is not None:
                try:
                    r = float(str(radius).strip())
                except ValueError:
                    r = 0.0
                center_ref = next((x for x in n.refs if x.kind == "center"), None)
                radius_ref = next((x for x in n.refs if x.kind == "radius"), None)
                regions.append({"key": n.key, "display": n.display or n.key,
                                "i": c[0], "j": c[1], "radius": r,
                                "color": str(_dget(n.data, "Color") or ""),
                                "uri": u, "line": line,
                                "centerRange": _span_range(center_ref.span) if center_ref else None,
                                "radiusRange": _span_range(radius_ref.span) if radius_ref else None})
    return {"landmarks": landmarks, "regions": regions}


def _section_of(node):
    """The `##` section key a node lives under (dialogue / narrative / ...)."""
    n = node
    while n.parent is not None and n.parent.key != "__root__" and n.level > 2:
        n = n.parent
    return n.key


def _face_random(race):
    """A random face string for a race, via sbs_utils.faces. '' if faces can't load
    (kept lazy + guarded so the server never hard-depends on it)."""
    try:
        import sbs_utils.faces as faces
    except Exception:
        return ""
    builders = {
        "terran female": lambda: faces.random_terran_female(),
        "terran male": lambda: faces.random_terran_male(),
        "terran": lambda: faces.random_terran(),
        "skaraan": faces.random_skaraan,
        "torgoth": faces.random_torgoth,
        "arvonian": faces.random_arvonian,
        "kralien": faces.random_kralien,
        "ximni": faces.random_ximni,
    }
    fn = builders.get(race)
    try:
        return fn() if fn else ""
    except Exception:
        return ""


def _face_meta():
    """Per-race feature specs for a face builder (from sbs_utils.faces)."""
    try:
        import sbs_utils.faces as faces
        return {"races": list(faces.FACE_FEATURES.keys()), "features": faces.FACE_FEATURES}
    except Exception:
        return {"races": [], "features": {}}


def _face_build(race, values, enables):
    """A face string from per-feature indices, via sbs_utils.faces.build_face."""
    try:
        import sbs_utils.faces as faces
        return faces.build_face(race, values, enables)
    except Exception:
        return ""


def _face_parse(face_string):
    """Recover {race, values, enables} from a face string so an editor can seed
    its controls from an existing face. None if it isn't a recognized face."""
    try:
        import sbs_utils.faces as faces
        return faces.parse_face(face_string)
    except Exception:
        return None


def _node_detail(index, key):
    """A node's editable detail for the inspector: display + metadata fields +
    body text, each with the exact range to rewrite. None if key not found."""
    for _p, u, d in index["docs"]:
        node = d.by_key.get(key)
        if node is None:
            continue
        nodes = d.nodes
        i = nodes.index(node)
        nxt = nodes[i + 1] if i + 1 < len(nodes) else None
        add_line = (nxt.span.line - 1) if (nxt and nxt.span) else getattr(d, "line_count", 0)

        fields, fl = [], node.fence_lines
        for _ln, raw in fl:
            s = raw.strip()
            if not s or s.startswith("//") or ":" not in raw:
                continue
            label, value = raw.split(":", 1)
            fields.append({"label": label.strip(), "value": value.strip()})

        # Type each field via the schema, so the Inspector renders a typed widget
        # (enum -> dropdown, ref -> key-picker, colour -> swatch, ...). The mission
        # symbol lists ride along once (candidates for the reference widgets).
        from sbs_utils.procedural.amd_schema import infer_archetype, field_schema
        arch = infer_archetype([f["label"] for f in fields], _section_of(node))
        for f in fields:
            f["schema"] = field_schema(f["label"], arch)

        fence_range = None
        if fl:
            fence_range = {"start": {"line": fl[0][0] - 1, "character": 0},
                           "end": {"line": fl[-1][0] - 1, "character": len(fl[-1][1])}}

        body = [raw for (ln, raw) in node.body_lines if (ln - 1) >= node.body_start]
        return {
            "key": node.key, "display": node.display, "uri": u,
            "archetype": arch,
            "displayRange": _span_range(node.display_span) if node.display_span else None,
            "fields": fields, "fenceRange": fence_range,
            "options": _mission_symbols(index),
            "bodyText": "\n".join(body),
            "bodyRange": {"start": {"line": node.body_start, "character": 0},
                          "end": {"line": add_line, "character": 0}},
        }
    return None


def _record_labels(node):
    """The fence field labels of a node (skipping `//` comments / label-less lines)."""
    out = []
    for _ln, raw in (node.fence_lines or []):
        if ":" in raw and not raw.strip().startswith("//"):
            lab = raw.split(":", 1)[0].strip()
            if lab:
                out.append(lab)
    return out


def _mission_symbols(index):
    """Candidate lists for the Inspector's reference widgets, mission-wide: every
    node key (`node`), the side keys (`side`), and the known signal names
    (`signal`) - so a `ref`/`signal` field renders as a combobox, not a bare box."""
    from sbs_utils.procedural.amd_schema import infer_archetype
    from sbs_utils.procedural.amd_lint import (
        _mast_routes, _emitted_from_sources, _declared_from_sources, DRIVER_SIGNALS)
    nodes = sorted(index["known"])
    sides = set()
    sig = set()
    for _p, _u, d in index["docs"]:
        for n in d.nodes:
            if infer_archetype(_record_labels(n), _section_of(n)) == "side":
                sides.add(n.key)
        for r in d.refs:
            if r.kind in ("signal", "wait_signal"):
                sig.add(r.value)
    mast = index.get("mast")
    decl_emits, decl_handles = _declared_from_sources(mast)
    sig |= (_mast_routes(mast) | decl_handles | decl_emits
            | _emitted_from_sources(mast) | set(DRIVER_SIGNALS))
    return {"node": nodes, "side": sorted(sides) or nodes, "signal": sorted(sig)}


_RE_CHOICE = re.compile(r"^\s*-\s*\[(?P<label>[^\]]*)\]\((?P<target>[^)]*)\)(?P<rest>.*)$")


def _choice_at(index, uri, line):
    """The choice on 0-based `line` broken into label / target / trailer (the raw
    ` if … ; …` after `)`) + the line range, for a choice editor. None if not one."""
    d, _u = _cur_doc(index, uri)
    if d is None:
        return None
    want = line + 1
    for n in d.nodes:
        for ln, raw in n.body_lines:
            if ln == want:
                m = _RE_CHOICE.match(raw)
                if not m:
                    return None
                return {"label": m.group("label"), "target": m.group("target"),
                        "trailer": m.group("rest"),
                        "range": {"start": {"line": line, "character": 0},
                                  "end": {"line": line, "character": len(raw)}}}
    return None


def _section_insert(index, uri, section):
    """Where to insert a new node under the `##` section with key `section`, in the
    doc for `uri`: the end of that section (before the next `##`/`#`, or EOF).
    `exists` is False when the section is absent (caller adds the header)."""
    d, _u = _cur_doc(index, uri)
    if d is None:
        return {"line": 0, "exists": False}
    nodes = d.nodes
    sec_idx = next((i for i, n in enumerate(nodes) if n.level == 2 and n.key == section), None)
    if sec_idx is None:
        return {"line": getattr(d, "line_count", 0), "exists": False}
    end_line = getattr(d, "line_count", 0)
    for n in nodes[sec_idx + 1:]:
        if n.level <= 2:
            end_line = (n.span.line - 1) if n.span else end_line
            break
    return {"line": end_line, "exists": True}


def _node_at_line(index, uri, line):
    """The editable detail of the node that owns `line` in `uri` — i.e. the
    nearest heading at or above the cursor. None if the line is above them all.
    Lets a docked inspector follow the caret."""
    doc, _u = _cur_doc(index, uri)
    if doc is None:
        return None
    best_key, best_line = None, -1
    for key, node in doc.by_key.items():
        if node.span is None:
            continue
        sl = node.span.line - 1
        if best_line < sl <= line:
            best_line, best_key = sl, key
    if best_key is None:
        return None
    return _node_detail(index, best_key)


def _node_schema(index, key):
    """The field SCHEMA for a node (via amd_schema): its resolved archetype plus a
    per-field descriptor (enum / node-ref / coord2 / colour / face / ...), so the
    Inspector can render a typed widget per field instead of a plain text box.
    None if the key isn't found."""
    from sbs_utils.procedural.amd_schema import record_schema
    for _p, _u, d in index["docs"]:
        node = d.by_key.get(key)
        if node is None:
            continue
        labels = []
        for _ln, raw in (node.fence_lines or []):
            if ":" not in raw or raw.strip().startswith("//"):
                continue
            label = raw.split(":", 1)[0].strip()
            if label:
                labels.append(label)
        return record_schema(labels, _section_of(node))
    return None


def _synth_record(node):
    """A dict-shaped view of an amd_core node for the pure content loaders
    (dialogue/scan), which read `.get('data')` / `.get('description')`. Returns
    (data_lowercased, body_text, record_dict)."""
    data = {}
    for _ln, raw in (node.fence_lines or []):
        if ":" in raw and not raw.strip().startswith("//"):
            k, v = raw.split(":", 1)
            if k.strip():
                data[k.strip().lower()] = v.strip()
    body = "\n".join(raw for (ln, raw) in node.body_lines if (ln - 1) >= node.body_start)
    return data, body, {"data": data, "description": body}


def _resolve_face(face_kw):
    """A face string from a Face keyword/string via sbs_utils.faces (guarded - the
    server never hard-depends on faces). Passes the raw value through on failure."""
    try:
        from sbs_utils.faces import face_resolve
        return face_resolve(face_kw)
    except Exception:
        return face_kw or ""


def _speaker_card(index, speaker_key):
    """Resolve a dialogue Speaker key to a display card {key,name,color,face} from
    the mission's lifeform/side records; defaults if unresolved. None for no key."""
    if not speaker_key:
        return None
    for _p, _u, d in index["docs"]:
        n = d.by_key.get(speaker_key)
        if n is None:
            continue
        data, _body, _rec = _synth_record(n)
        return {"key": speaker_key, "name": n.display or speaker_key,
                "color": data.get("color") or data.get("title color") or "#0cf",
                "face": _resolve_face(data.get("face"))}
    return {"key": speaker_key, "name": speaker_key, "color": "#0cf", "face": ""}


def _node_preview(index, key):
    """A render-preview payload for a node, so the editor draws it as it would
    appear in-game: a dialogue scene (speaker card + lines + choices), a science
    scan (tab + variant lines), or a lifeform face. Falls back to plain text.
    None if the key isn't found. Pure/offline - reuses the content loaders."""
    from sbs_utils.procedural.amd_dialogue import dialogue_parse
    from sbs_utils.procedural.amd_schema import infer_archetype
    for _p, _u, d in index["docs"]:
        node = d.by_key.get(key)
        if node is None:
            continue
        data, body, rec = _synth_record(node)
        arch = infer_archetype(list(data.keys()), _section_of(node))
        if "speaker" in data:
            scene = dialogue_parse(rec)
            return {"kind": "dialogue", "key": key,
                    "speaker": _speaker_card(index, scene.get("speaker")),
                    "when": scene.get("when"),
                    "lines": [t for (t, _g) in scene["lines"]],
                    "choices": [{"label": c["label"], "target": c["target"],
                                 "guard": c.get("guard")} for c in scene["choices"]]}
        if "scan of" in data or "scan_of" in data:
            # Scan variant lines (mirrors amd_science._scan_body_lines) - inlined so
            # the server stays dependency-light (importing amd_science drags the heavy
            # science / story_nodes chain and circular-imports under the LSP env).
            lines = []
            for raw in body.splitlines():
                s = raw.strip()
                if not s or s.startswith("//"):
                    continue
                lines.append(s[1:].strip() if s.startswith("%") else s)
            return {"kind": "scan", "key": key,
                    "role": data.get("scan of") or data.get("scan_of"),
                    "tab": data.get("tab", "scan"), "lines": lines}
        if arch == "lifeform" or "face" in data:
            return {"kind": "face", "key": key, "name": node.display or key,
                    "color": data.get("color") or data.get("title color") or "#0cf",
                    "face": _resolve_face(data.get("face"))}
        return {"kind": "text", "key": key, "display": node.display, "body": body}
    return None


def _archetype_template(archetype):
    """A 'new <archetype>' fence skeleton + its typed field descriptors, for the
    editor's New Record form. `{fields}` is ordered as authored in amd_schema."""
    from sbs_utils.procedural.amd_schema import template_fields, field_schema
    labels = template_fields(archetype)
    return {"archetype": archetype,
            "fields": [{"label": l, "schema": field_schema(l, archetype)} for l in labels]}


def _new_in_section(index, uri, section):
    """A ready-to-insert skeleton for a NEW record under `## section` in `uri`:
    resolve the section's archetype (by conventional name, else from an existing
    sibling), mint a unique key, and return the heading + a fence of that
    archetype's schema fields, with the insert line. When the section doesn't
    exist yet, the text is prefixed with its `##` header (`exists` is False).
    None if the doc can't be read. Backs the panels' per-section "+" add."""
    from sbs_utils.procedural.amd_schema import archetype_for_section, template_fields
    d, _u = _cur_doc(index, uri)
    if d is None:
        return None
    cap = lambda s: (s[:1].upper() + s[1:]) if s else s
    alias = archetype_for_section(section)
    # Skeleton fields: mirror a representative sibling in this section (its own
    # authored convention - leaner and correct even for archetype-less sections
    # like dialogue), falling back to the archetype's schema fields for an empty
    # section. `_record_labels` returns labels already cased as authored.
    sib = next((n for n in d.nodes
                if (n.level or 0) >= 3 and _section_of(n) == section and _record_labels(n)), None)
    if sib is not None:
        labels = _record_labels(sib)
    elif alias:
        labels = [cap(l) for l in template_fields(alias)]
    else:
        labels = []
    word = alias or (section.rstrip("s") or "node")
    base = "new_" + word
    known = set(index["known"])
    key, i = base, 2
    while key in known:
        key = "{}_{}".format(base, i)
        i += 1
    lines = ["### [New {}]({})".format(cap(word), key)]
    if labels:
        lines.append("---")
        lines += ["{}: ".format(l) for l in labels]
        lines.append("---")
    lines.append("Description.")
    ins = _section_insert(index, uri, section)
    text = "\n" + "\n".join(lines) + "\n"
    if not ins["exists"]:
        text = "\n## [{}]({})\n".format(cap(section), section) + text
    return {"line": ins["line"], "text": text, "key": key,
            "archetype": alias, "exists": ins["exists"]}


def _rename_by_key(index, key, new_name):
    """A mission-wide rename of node `key` (declaration + every reference) as an LSP
    WorkspaceEdit - the graph's right-click Rename. No-op if key/name missing."""
    if not key or not new_name:
        return {"changes": {}}
    changes = {}
    for _p, u, d in index["docs"]:
        edits = [{"range": rg, "newText": new_name} for rg in _key_ranges(d, key, include_decl=True)]
        if edits:
            changes[u] = edits
    return {"changes": changes}


def _problems_by_key(index):
    """{node key -> {error, warning}} from running the linter over each doc and
    bucketing findings by the node whose range contains them - for badges."""
    from sbs_utils.procedural.amd_lint import amd_lint
    out = {}
    for _p, _u, d in index["docs"]:
        src = getattr(d, "source", None)
        if src is None:
            continue
        nodes = d.nodes
        bounds = []
        for i, n in enumerate(nodes):
            start = (n.span.line - 1) if n.span else 0
            nxt = nodes[i + 1] if i + 1 < len(nodes) else None
            end = (nxt.span.line - 1) if (nxt and nxt.span) else getattr(d, "line_count", 1 << 30)
            bounds.append((start, end, n.key))
        for f in amd_lint(content=src, mast_sources=index["mast"], known_keys=index["known"]):
            if not f.line:
                continue
            line0 = f.line - 1
            key = next((k for (s, e, k) in bounds if s <= line0 < e), None)
            if key is None:
                continue
            b = out.setdefault(key, {"error": 0, "warning": 0})
            b["error" if f.is_error() else "warning"] += 1
    return out


def _mission_graph(index):
    """Nodes + reference edges (choice/scene/reveal/parent) across the mission -
    the data for a story graph. Nodes carry their section, source uri/line, and
    `addLine` = where to insert a new choice (end of the node's body), so the graph
    can add an edge by dragging one node to another."""
    problems = _problems_by_key(index)
    nodes, seen = [], set()
    for _p, u, d in index["docs"]:
        line_count = getattr(d, "line_count", 0)
        for i, n in enumerate(d.nodes):
            if (n.level or 0) <= 2:      # `#`/`##` = mission root + section groups, not story nodes
                continue
            if n.key in seen:
                continue
            seen.add(n.key)
            nxt = d.nodes[i + 1] if i + 1 < len(d.nodes) else None
            add_line = (nxt.span.line - 1) if (nxt and nxt.span) else line_count
            nodes.append({"key": n.key, "display": n.display or n.key,
                          "section": _section_of(n), "uri": u,
                          "line": (n.span.line - 1) if n.span else 0,
                          "addLine": add_line, "problems": problems.get(n.key)})
    known = {nd["key"] for nd in nodes}
    edges, edge_seen = [], set()
    for _p, u, d in index["docs"]:
        for r in d.refs:
            if r.kind not in ("choice", "scene", "reveal", "parent"):
                continue
            leaf = str(r.value).split("/")[-1]
            key = (r.owner, leaf, r.kind)
            if r.owner in known and leaf in known and r.owner != leaf and key not in edge_seen:
                edge_seen.add(key)
                edges.append({"from": r.owner, "to": leaf, "kind": r.kind,
                              "uri": u, "line": r.span.line - 1,
                              "targetRange": _span_range(r.span)})
    return {"nodes": nodes, "edges": edges}


def _mission_resolve(index):
    """The resolved AMD model for the Live Resolver: every heading as an entity
    (key/display/section/archetype/span/summary/fields/problems + inbound/outbound
    reference counts and an `orphan` flag), every reference with a `resolved` bool
    and any dangling lint code, and the mission-wide lint `issues` (structural +
    cross-file) each anchored to a source line. A serialization pass over the
    existing amd_core model + amd_lint output - no new resolution logic here."""
    from sbs_utils.procedural.amd_schema import infer_archetype
    from sbs_utils.procedural.amd_lint import amd_lint
    problems = _problems_by_key(index)
    known = set(index["known"])

    # inbound/outbound story-edge counts (choice/scene/reveal/parent).
    EDGE = ("choice", "scene", "reveal", "parent")
    inbound, outbound = {}, {}
    for _p, _u, d in index["docs"]:
        for r in d.refs:
            if r.kind not in EDGE:
                continue
            leaf = str(r.value).split("/")[-1]
            if r.owner in known:
                outbound[r.owner] = outbound.get(r.owner, 0) + 1
            if leaf in known:
                inbound[leaf] = inbound.get(leaf, 0) + 1

    # lint findings indexed by (uri, line) so refs pick up their dangling code; the
    # flat list becomes the panel's jump-to-source issue list.
    findings_by_uri, issues = {}, []
    for _p, u, d in index["docs"]:
        src = getattr(d, "source", None)
        if src is None:
            continue
        for f in amd_lint(content=src, mast_sources=index["mast"], known_keys=known):
            if not f.line:
                continue
            findings_by_uri.setdefault(u, {}).setdefault(f.line, []).append(f)
            issues.append({"uri": u, "line": f.line - 1, "col": max((f.col or 1) - 1, 0),
                           "severity": f.severity, "code": f.code, "message": f.message})

    entities, seen = [], set()
    for _p, u, d in index["docs"]:
        for n in d.nodes:
            if (n.level or 0) <= 2:      # `#`/`##` = mission root + section groups, not records
                continue
            if n.key in seen:
                continue
            seen.add(n.key)
            fields = []
            for _ln, raw in (n.fence_lines or []):
                if ":" not in raw or raw.strip().startswith("//") or not raw.strip():
                    continue
                label, value = raw.split(":", 1)
                fields.append({"label": label.strip(), "value": value.strip()})
            arch = infer_archetype([f["label"] for f in fields], _section_of(n))
            inn = inbound.get(n.key, 0)
            # "orphan" = unreachable, and only meaningful for narrative FLOW records
            # (quest/scan) — the things that must be *reached*. Data records
            # (lifeform/landmark/region/side/item/...) are placed or matched by the
            # engine, never reference-reached, so they are never orphans.
            # A flow record turns on one of three ways: REVEALED (an inbound
            # choice/scene/reveal/parent edge), TRIGGERED (a `When:`/`Accept on:`/
            # `Engage on:`/`Fail on signal:` condition, i.e. signal/reach/scan/timer),
            # or ACTIVE at start (`State: active`). Only one that is none of these is
            # a true orphan. A dead trigger signal is a separate red flag
            # (unfired-signal), so we don't double-count it here.
            labels = {f["label"] for f in fields}
            state = next((f["value"] for f in fields if f["label"] == "State"), "")
            triggered = bool(labels & {"When", "Fail on signal", "Accept on", "Engage on"}) \
                or state.strip().lower() == "active" \
                or any(r.kind in ("wait_signal", "reach") for r in n.refs)
            entities.append({
                "key": n.key, "display": n.display or n.key,
                "section": _section_of(n), "archetype": arch, "level": n.level,
                "uri": u, "line": (n.span.line - 1) if n.span else 0,
                "span": _span_range(n.span) if n.span else None,
                "summary": getattr(n, "summary", "") or "",
                "fields": fields, "problems": problems.get(n.key),
                "inbound": inn, "outbound": outbound.get(n.key, 0),
                "triggered": triggered,
                "orphan": arch in ("quest", "scan") and inn == 0 and not triggered,
            })

    _DANGLE = ("dangling", "signal-no-route", "unfired-signal", "reach-no-landmark")
    refs = []
    for _p, u, d in index["docs"]:
        fmap = findings_by_uri.get(u, {})
        for r in d.refs:
            leaf = str(r.value).split("/")[-1]
            key_kind = r.kind in EDGE       # targets a heading; others resolve cross-file
            resolved = (leaf in known) if key_kind else True
            code = None
            if r.span:
                for f in fmap.get(r.span.line, []):
                    if f.code and f.code.startswith(_DANGLE):
                        code = f.code
                        if not key_kind:
                            resolved = False
                        break
            refs.append({"kind": r.kind, "value": str(r.value), "owner": r.owner,
                         "uri": u, "line": (r.span.line - 1) if r.span else 0,
                         "span": _span_range(r.span) if r.span else None,
                         "resolved": resolved, "code": code})

    return {"entities": entities, "refs": refs, "issues": issues}


# --- server loop ------------------------------------------------------------
def serve(stdin=None, stdout=None):
    """Run the LSP loop until `exit` / EOF. `stdin`/`stdout` are binary streams
    (default: the process's); passing BytesIO makes this unit-testable."""
    stdin = stdin if stdin is not None else sys.stdin.buffer
    stdout = stdout if stdout is not None else sys.stdout.buffer
    docs = {}

    while True:
        msg = _read_message(stdin)
        if msg is None:
            break
        method = msg.get("method")
        mid = msg.get("id")

        if method == "exit":
            break
        try:
            if method == "initialize":
                _write_message(stdout, {"jsonrpc": "2.0", "id": mid, "result": {
                    "capabilities": {
                        "textDocumentSync": 1,               # 1 = Full
                        "definitionProvider": True,
                        "documentSymbolProvider": True,
                        "hoverProvider": True,
                        "completionProvider": {"triggerCharacters": ["(", " "]},
                        "documentFormattingProvider": True,
                        "referencesProvider": True,
                        "renameProvider": True,
                        "codeActionProvider": {"codeActionKinds": ["quickfix"]},
                        "codeLensProvider": {"resolveProvider": False},
                        "colorProvider": True,
                        "inlayHintProvider": True,
                    },
                    "serverInfo": {"name": "amd-lsp", "version": "0.1"}}})
            elif method == "initialized":
                pass
            elif method in ("textDocument/didOpen", "textDocument/didChange", "textDocument/didSave"):
                params = msg.get("params", {})
                td = params.get("textDocument", {})
                uri = td.get("uri", "")
                if method == "textDocument/didOpen":
                    text = td.get("text", "")
                elif method == "textDocument/didChange":
                    changes = params.get("contentChanges", [])
                    text = changes[-1].get("text", "") if changes else docs.get(uri, "")
                else:  # didSave
                    text = params.get("text") or docs.get(uri, "")
                docs[uri] = text
                _invalidate()                 # a buffer changed -> rebuild the index
                _publish(stdout, uri, text, docs)
            elif method == "textDocument/didClose":
                uri = msg.get("params", {}).get("textDocument", {}).get("uri", "")
                docs.pop(uri, None)
                _invalidate()
                _write_message(stdout, {"jsonrpc": "2.0", "method": "textDocument/publishDiagnostics",
                                        "params": {"uri": uri, "diagnostics": []}})
            elif method == "textDocument/formatting":
                uri = msg.get("params", {}).get("textDocument", {}).get("uri", "")
                _write_message(stdout, {"jsonrpc": "2.0", "id": mid,
                                        "result": _formatting(docs.get(uri, ""))})
            elif method == "textDocument/codeAction":
                params = msg.get("params", {})
                uri = params.get("textDocument", {}).get("uri", "")
                index = _index_for(uri, docs)
                doc, _u = _cur_doc(index, uri)
                if doc is None:
                    doc = _parse(docs.get(uri, ""))
                diags = params.get("context", {}).get("diagnostics", [])
                _write_message(stdout, {"jsonrpc": "2.0", "id": mid,
                                        "result": _code_actions(index, doc, docs.get(uri, ""), uri, diags)})
            elif method == "textDocument/colorPresentation":
                color = msg.get("params", {}).get("color", {})
                _write_message(stdout, {"jsonrpc": "2.0", "id": mid,
                                        "result": _color_presentations(color)})
            elif method in ("textDocument/codeLens", "textDocument/documentColor",
                            "textDocument/inlayHint"):
                params = msg.get("params", {})
                uri = params.get("textDocument", {}).get("uri", "")
                if method == "textDocument/documentColor":
                    result = _document_colors(docs.get(uri, ""))
                else:
                    index = _index_for(uri, docs)
                    doc, curi = _cur_doc(index, uri)
                    if doc is None:
                        doc = _parse(docs.get(uri, ""))
                    if method == "textDocument/codeLens":
                        result = _code_lens(index, doc, curi or uri)
                    else:  # inlayHint
                        result = _inlay_hints(index, doc, params.get("range", {}))
                _write_message(stdout, {"jsonrpc": "2.0", "id": mid, "result": result})
            elif method in ("textDocument/definition", "textDocument/documentSymbol",
                            "textDocument/hover", "textDocument/completion",
                            "textDocument/references", "textDocument/rename"):
                params = msg.get("params", {})
                uri = params.get("textDocument", {}).get("uri", "")
                index = _index_for(uri, docs)
                doc, _curi = _cur_doc(index, uri)
                if doc is None:
                    doc = _parse(docs.get(uri, ""))
                pos = params.get("position", {})
                if method == "textDocument/definition":
                    result = _definition(index, doc, pos)
                elif method == "textDocument/documentSymbol":
                    result = _symbols(doc.root)
                elif method == "textDocument/hover":
                    result = _hover(index, doc, pos)
                elif method == "textDocument/completion":
                    result = _completion(index)
                elif method == "textDocument/references":
                    include_decl = params.get("context", {}).get("includeDeclaration", True)
                    result = _references(index, doc, pos, include_decl)
                else:  # rename
                    result = _rename(index, doc, pos, params.get("newName", ""))
                _write_message(stdout, {"jsonrpc": "2.0", "id": mid, "result": result})
            elif method == "amd/map":
                uri = msg.get("params", {}).get("textDocument", {}).get("uri", "")
                _write_message(stdout, {"jsonrpc": "2.0", "id": mid,
                                        "result": _mission_map(_index_for(uri, docs))})
            elif method == "amd/graph":
                uri = msg.get("params", {}).get("textDocument", {}).get("uri", "")
                _write_message(stdout, {"jsonrpc": "2.0", "id": mid,
                                        "result": _mission_graph(_index_for(uri, docs))})
            elif method == "amd/resolve":
                uri = msg.get("params", {}).get("textDocument", {}).get("uri", "")
                _write_message(stdout, {"jsonrpc": "2.0", "id": mid,
                                        "result": _mission_resolve(_index_for(uri, docs))})
            elif method == "amd/rename":
                p = msg.get("params", {})
                uri = p.get("textDocument", {}).get("uri", "")
                _write_message(stdout, {"jsonrpc": "2.0", "id": mid,
                                        "result": _rename_by_key(_index_for(uri, docs),
                                                                 p.get("key", ""), p.get("newName", ""))})
            elif method == "amd/node":
                p = msg.get("params", {})
                uri = p.get("textDocument", {}).get("uri", "")
                _write_message(stdout, {"jsonrpc": "2.0", "id": mid,
                                        "result": _node_detail(_index_for(uri, docs), p.get("key", ""))})
            elif method == "amd/schema":
                p = msg.get("params", {})
                uri = p.get("textDocument", {}).get("uri", "")
                _write_message(stdout, {"jsonrpc": "2.0", "id": mid,
                                        "result": _node_schema(_index_for(uri, docs), p.get("key", ""))})
            elif method == "amd/template":
                _write_message(stdout, {"jsonrpc": "2.0", "id": mid,
                                        "result": _archetype_template(msg.get("params", {}).get("archetype", ""))})
            elif method == "amd/preview":
                p = msg.get("params", {})
                uri = p.get("textDocument", {}).get("uri", "")
                _write_message(stdout, {"jsonrpc": "2.0", "id": mid,
                                        "result": _node_preview(_index_for(uri, docs), p.get("key", ""))})
            elif method == "amd/nodeAtLine":
                p = msg.get("params", {})
                uri = p.get("textDocument", {}).get("uri", "")
                _write_message(stdout, {"jsonrpc": "2.0", "id": mid,
                                        "result": _node_at_line(_index_for(uri, docs), uri, p.get("line", -1))})
            elif method == "amd/sectionInsert":
                p = msg.get("params", {})
                uri = p.get("textDocument", {}).get("uri", "")
                _write_message(stdout, {"jsonrpc": "2.0", "id": mid,
                                        "result": _section_insert(_index_for(uri, docs), uri, p.get("section", ""))})
            elif method == "amd/newInSection":
                p = msg.get("params", {})
                uri = p.get("textDocument", {}).get("uri", "")
                _write_message(stdout, {"jsonrpc": "2.0", "id": mid,
                                        "result": _new_in_section(_index_for(uri, docs), uri, p.get("section", ""))})
            elif method == "amd/choice":
                p = msg.get("params", {})
                uri = p.get("textDocument", {}).get("uri", "")
                _write_message(stdout, {"jsonrpc": "2.0", "id": mid,
                                        "result": _choice_at(_index_for(uri, docs), uri, p.get("line", -1))})
            elif method == "amd/faceRandom":
                _write_message(stdout, {"jsonrpc": "2.0", "id": mid,
                                        "result": {"face": _face_random(msg.get("params", {}).get("race", ""))}})
            elif method == "amd/faceMeta":
                _write_message(stdout, {"jsonrpc": "2.0", "id": mid, "result": _face_meta()})
            elif method == "amd/faceBuild":
                p = msg.get("params", {})
                _write_message(stdout, {"jsonrpc": "2.0", "id": mid,
                                        "result": {"face": _face_build(p.get("race", ""), p.get("values", []), p.get("enables"))}})
            elif method == "amd/faceParse":
                _write_message(stdout, {"jsonrpc": "2.0", "id": mid,
                                        "result": _face_parse(msg.get("params", {}).get("face", ""))})
            elif method == "shutdown":
                _write_message(stdout, {"jsonrpc": "2.0", "id": mid, "result": None})
            elif mid is not None:
                _write_message(stdout, {"jsonrpc": "2.0", "id": mid,
                                        "error": {"code": -32601, "message": f"method not found: {method}"}})

        except Exception as _e:
            # A single bad request must never take the whole server down: log
            # it and reply with an error (for a request) instead of exiting.
            import traceback
            sys.stderr.write(
                "[amd-lsp] error handling %s: %s\n%s\n" % (method, _e, traceback.format_exc()))
            if mid is not None:
                _write_message(stdout, {"jsonrpc": "2.0", "id": mid,
                                        "error": {"code": -32603,
                                                  "message": "internal error: %s" % _e}})
    return 0


if __name__ == "__main__":
    raise SystemExit(serve())
