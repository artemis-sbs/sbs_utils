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
import json
import glob
from urllib.parse import urlparse, unquote


# --- mission context --------------------------------------------------------
def _uri_to_path(uri):
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


def _mast_sources(root):
    if not root:
        return None
    out = []
    for p in glob.glob(os.path.join(root, "**", "*.mast"), recursive=True):
        try:
            with open(p, "r") as f:
                out.append(f.read())
        except Exception:
            pass
    return out


def _diagnostics(text, path):
    """amd_lint findings for `text` -> LSP Diagnostic dicts (0-based positions)."""
    from sbs_utils.procedural.amd_lint import amd_lint
    findings = amd_lint(content=text, mast_sources=_mast_sources(_mission_root(path)))
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


def _publish(stdout, uri, text, path):
    try:
        diags = _diagnostics(text, path)
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


def _definition(doc, pos, uri):
    ref = _ref_at(doc, pos.get("line", 0), pos.get("character", 0))
    if not ref:
        return None
    target = doc.resolve_target(ref.value)
    if target and target.span:
        return {"uri": uri, "range": _node_range(target)}
    return None


def _hover(doc, pos):
    ref = _ref_at(doc, pos.get("line", 0), pos.get("character", 0))
    if not ref:
        return None
    target = doc.resolve_target(ref.value)
    val = f"**{ref.kind}** → `{ref.value}`"
    if target:
        val += f"\n\n**{target.display or target.key}**"
        if target.summary:
            val += f"\n\n{target.summary}"
    else:
        val += "\n\n*(unresolved)*"
    return {"contents": {"kind": "markdown", "value": val}}


def _completion(doc):
    # Offer every node key (choice/Scene/reveal targets). kind 6 = Variable.
    items = [{"label": k, "kind": 6} for k in sorted(doc.keys)]
    return {"isIncomplete": False, "items": items}


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

        if method == "initialize":
            _write_message(stdout, {"jsonrpc": "2.0", "id": mid, "result": {
                "capabilities": {
                    "textDocumentSync": 1,               # 1 = Full
                    "definitionProvider": True,
                    "documentSymbolProvider": True,
                    "hoverProvider": True,
                    "completionProvider": {"triggerCharacters": ["(", " "]},
                    "documentFormattingProvider": True,
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
            _publish(stdout, uri, text, _uri_to_path(uri))
        elif method == "textDocument/didClose":
            uri = msg.get("params", {}).get("textDocument", {}).get("uri", "")
            docs.pop(uri, None)
            _write_message(stdout, {"jsonrpc": "2.0", "method": "textDocument/publishDiagnostics",
                                    "params": {"uri": uri, "diagnostics": []}})
        elif method == "textDocument/formatting":
            uri = msg.get("params", {}).get("textDocument", {}).get("uri", "")
            _write_message(stdout, {"jsonrpc": "2.0", "id": mid,
                                    "result": _formatting(docs.get(uri, ""))})
        elif method in ("textDocument/definition", "textDocument/documentSymbol",
                        "textDocument/hover", "textDocument/completion"):
            params = msg.get("params", {})
            uri = params.get("textDocument", {}).get("uri", "")
            doc = _parse(docs.get(uri, ""))
            pos = params.get("position", {})
            if method == "textDocument/definition":
                result = _definition(doc, pos, uri)
            elif method == "textDocument/documentSymbol":
                result = _symbols(doc.root)
            elif method == "textDocument/hover":
                result = _hover(doc, pos)
            else:  # completion
                result = _completion(doc)
            _write_message(stdout, {"jsonrpc": "2.0", "id": mid, "result": result})
        elif method == "shutdown":
            _write_message(stdout, {"jsonrpc": "2.0", "id": mid, "result": None})
        elif method == "exit":
            break
        elif mid is not None:
            _write_message(stdout, {"jsonrpc": "2.0", "id": mid,
                                    "error": {"code": -32601, "message": f"method not found: {method}"}})

    return 0


if __name__ == "__main__":
    raise SystemExit(serve())
