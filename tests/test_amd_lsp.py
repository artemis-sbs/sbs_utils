"""amd_lsp - the AMD language server, driven over in-memory byte streams.

Frames an initialize + didOpen(broken doc) + shutdown/exit session, runs `serve`,
and asserts a publishDiagnostics with the expected range - no real editor needed.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import io
import json
import os
import tempfile
import unittest
from pathlib import Path

from sbs_utils.procedural.amd_lsp import serve, _uri_to_path


def _frame(msg):
    data = json.dumps(msg).encode("utf-8")
    return b"Content-Length: " + str(len(data)).encode() + b"\r\n\r\n" + data


def _parse_frames(raw):
    out, i = [], 0
    while i < len(raw):
        j = raw.find(b"\r\n\r\n", i)
        if j < 0:
            break
        header = raw[i:j].decode()
        length = 0
        for line in header.split("\r\n"):
            if line.lower().startswith("content-length:"):
                length = int(line.split(":", 1)[1].strip())
        body = raw[j + 4:j + 4 + length]
        out.append(json.loads(body.decode()))
        i = j + 4 + length
    return out


class TestLsp(unittest.TestCase):
    def _run(self, doc_text, uri="file:///tmp/x.amd"):
        stream = (
            _frame({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
            + _frame({"jsonrpc": "2.0", "method": "textDocument/didOpen",
                      "params": {"textDocument": {"uri": uri, "text": doc_text}}})
            + _frame({"jsonrpc": "2.0", "id": 2, "method": "shutdown"})
            + _frame({"jsonrpc": "2.0", "method": "exit"})
        )
        out = io.BytesIO()
        serve(stdin=io.BytesIO(stream), stdout=out)
        return _parse_frames(out.getvalue())

    def test_initialize_and_diagnostics(self):
        doc = "# [Root](root)\n## [Dialogue](dialogue)\n### [A](a)\n% hi\n- [go](nope)\n"
        msgs = self._run(doc)

        init = next(m for m in msgs if m.get("id") == 1)
        self.assertEqual(init["result"]["capabilities"]["textDocumentSync"], 1)

        pub = next(m for m in msgs if m.get("method") == "textDocument/publishDiagnostics")
        diags = pub["params"]["diagnostics"]
        self.assertEqual(len(diags), 1)
        d = diags[0]
        self.assertEqual(d["code"], "dangling-choice")
        self.assertEqual(d["severity"], 2)               # warning
        self.assertEqual(d["source"], "amd")
        # 0-based range spanning `nope` on line 5 (LSP line 4), cols 7..11
        self.assertEqual(d["range"]["start"], {"line": 4, "character": 7})
        self.assertEqual(d["range"]["end"], {"line": 4, "character": 11})

    def test_structural_error_is_severity_1(self):
        doc = "# [Root](root)\n## [Voice](ep1_scan\nbody\n"
        msgs = self._run(doc)
        pub = next(m for m in msgs if m.get("method") == "textDocument/publishDiagnostics")
        codes = {d["code"]: d for d in pub["params"]["diagnostics"]}
        self.assertIn("broken-heading", codes)
        self.assertEqual(codes["broken-heading"]["severity"], 1)   # error

    def test_clean_doc_publishes_empty(self):
        doc = "# [Root](root)\n## [Dialogue](dialogue)\n### [A](a)\n% hi\n- [go](a)\n"
        msgs = self._run(doc)
        pub = next(m for m in msgs if m.get("method") == "textDocument/publishDiagnostics")
        self.assertEqual(pub["params"]["diagnostics"], [])

    def test_uri_to_path_windows_drive(self):
        # file:///f:/a/x.amd -> f:/a/x.amd (drive-letter leading slash stripped on nt)
        p = _uri_to_path("file:///f:/a/x.amd")
        self.assertTrue(p.endswith("a/x.amd"))
        self.assertNotIn(":/f", p)


# A doc with a resolvable choice target `a -> b`, and a heading tree for symbols.
_DOC = "# [Root](root)\n## [Dialogue](dialogue)\n### [A](a)\n% hi\n- [go](b)\n### [B](b)\n% there\n"


class TestProviders(unittest.TestCase):
    def _request(self, method, params, doc=_DOC, uri="file:///tmp/x.amd"):
        stream = (
            _frame({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
            + _frame({"jsonrpc": "2.0", "method": "textDocument/didOpen",
                      "params": {"textDocument": {"uri": uri, "text": doc}}})
            + _frame({"jsonrpc": "2.0", "id": 2, "method": method, "params": params})
            + _frame({"jsonrpc": "2.0", "method": "exit"})
        )
        out = io.BytesIO()
        serve(stdin=io.BytesIO(stream), stdout=out)
        msgs = _parse_frames(out.getvalue())
        return next(m for m in msgs if m.get("id") == 2)["result"]

    def test_initialize_advertises_providers(self):
        stream = (_frame({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
                  + _frame({"jsonrpc": "2.0", "method": "exit"}))
        out = io.BytesIO()
        serve(stdin=io.BytesIO(stream), stdout=out)
        caps = next(m for m in _parse_frames(out.getvalue()) if m.get("id") == 1)["result"]["capabilities"]
        self.assertTrue(caps["definitionProvider"])
        self.assertTrue(caps["documentSymbolProvider"])
        self.assertTrue(caps["hoverProvider"])
        self.assertIn("completionProvider", caps)

    def test_definition_jumps_to_target_node(self):
        uri = "file:///tmp/x.amd"
        # position on the `b` inside `- [go](b)` (line 5 -> LSP 4, col 7)
        loc = self._request("textDocument/definition",
                            {"textDocument": {"uri": uri}, "position": {"line": 4, "character": 7}})
        self.assertEqual(loc["uri"], uri)
        # `### [B](b)` is source line 6 -> LSP line 5
        self.assertEqual(loc["range"]["start"]["line"], 5)

    def test_definition_none_off_a_reference(self):
        loc = self._request("textDocument/definition",
                            {"textDocument": {"uri": "file:///tmp/x.amd"},
                             "position": {"line": 3, "character": 0}})  # the `% hi` line
        self.assertIsNone(loc)

    def test_document_symbols_tree(self):
        syms = self._request("textDocument/documentSymbol", {"textDocument": {"uri": "file:///tmp/x.amd"}})
        self.assertEqual([s["name"] for s in syms], ["Root"])
        dialogue = syms[0]["children"][0]
        self.assertEqual(dialogue["detail"], "dialogue")
        self.assertEqual({c["detail"] for c in dialogue["children"]}, {"a", "b"})

    def test_completion_offers_keys(self):
        comp = self._request("textDocument/completion",
                             {"textDocument": {"uri": "file:///tmp/x.amd"}, "position": {"line": 4, "character": 7}})
        labels = {i["label"] for i in comp["items"]}
        self.assertTrue({"root", "dialogue", "a", "b"} <= labels)

    def test_hover_shows_target(self):
        hov = self._request("textDocument/hover",
                            {"textDocument": {"uri": "file:///tmp/x.amd"}, "position": {"line": 4, "character": 7}})
        self.assertIn("b", hov["contents"]["value"])

    def test_formatting_returns_edit(self):
        edits = self._request("textDocument/formatting",
                              {"textDocument": {"uri": "file:///tmp/x.amd"}, "options": {}},
                              doc="#   [Root](root)   \nbody\n")
        self.assertEqual(len(edits), 1)
        self.assertTrue(edits[0]["newText"].startswith("# [Root](root)\n"))

    def test_formatting_clean_doc_no_edits(self):
        edits = self._request("textDocument/formatting",
                              {"textDocument": {"uri": "file:///tmp/x.amd"}, "options": {}},
                              doc="# [Root](root)\nbody\n")
        self.assertEqual(edits, [])

    def test_references_from_a_choice(self):
        # cursor on `b` in `- [go](b)` -> its declaration + the one reference
        uri = "file:///tmp/x.amd"
        locs = self._request("textDocument/references",
                             {"textDocument": {"uri": uri}, "position": {"line": 4, "character": 7},
                              "context": {"includeDeclaration": True}})
        lines = sorted(l["range"]["start"]["line"] for l in locs)
        # `### [B](b)` decl on source line 6 (LSP 5) + the choice ref on line 5 (LSP 4)
        self.assertEqual(lines, [4, 5])

    def test_references_exclude_declaration(self):
        uri = "file:///tmp/x.amd"
        locs = self._request("textDocument/references",
                             {"textDocument": {"uri": uri}, "position": {"line": 4, "character": 7},
                              "context": {"includeDeclaration": False}})
        self.assertEqual([l["range"]["start"]["line"] for l in locs], [4])  # ref only

    def test_rename_updates_declaration_and_references(self):
        uri = "file:///tmp/x.amd"
        we = self._request("textDocument/rename",
                           {"textDocument": {"uri": uri}, "position": {"line": 5, "character": 8},
                            "newName": "bravo"})   # cursor on the `### [B](b)` heading key
        edits = we["changes"][uri]
        self.assertEqual(len(edits), 2)                       # decl + one reference
        self.assertTrue(all(e["newText"] == "bravo" for e in edits))


class TestCodeActions(unittest.TestCase):
    """Quick fixes: 'Change to <near key>' and 'Create node'."""

    # `- [go](ndoe)` is a typo of `node` (defined below); one char transposed.
    _DOC = ("# [Root](root)\n## [Dialogue](dialogue)\n### [A](a)\n% hi\n"
            "- [go](ndoe)\n### [Node](node)\n% there\n")

    def _actions(self, doc, drange, code, uri="file:///tmp/x.amd"):
        diag = {"range": drange, "code": code, "severity": 2, "message": "x"}
        stream = (
            _frame({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
            + _frame({"jsonrpc": "2.0", "method": "textDocument/didOpen",
                      "params": {"textDocument": {"uri": uri, "text": doc}}})
            + _frame({"jsonrpc": "2.0", "id": 2, "method": "textDocument/codeAction",
                      "params": {"textDocument": {"uri": uri},
                                 "range": drange, "context": {"diagnostics": [diag]}}})
            + _frame({"jsonrpc": "2.0", "method": "exit"})
        )
        out = io.BytesIO()
        serve(stdin=io.BytesIO(stream), stdout=out)
        return next(m for m in _parse_frames(out.getvalue()) if m.get("id") == 2)["result"], uri

    def test_did_you_mean_and_create(self):
        # `ndoe` is on line 5 (LSP 4), cols 7..11
        drange = {"start": {"line": 4, "character": 7}, "end": {"line": 4, "character": 11}}
        actions, uri = self._actions(self._DOC, drange, "dangling-choice")
        titles = [a["title"] for a in actions]
        self.assertIn("Change to `node`", titles)
        self.assertTrue(any(t.startswith("Create node") for t in titles))
        # the 'Change to node' fix replaces the bad token with the suggestion
        fix = next(a for a in actions if a["title"] == "Change to `node`")
        edit = fix["edit"]["changes"][uri][0]
        self.assertEqual(edit["newText"], "node")
        self.assertEqual(edit["range"], drange)
        self.assertTrue(fix["isPreferred"])

    def test_capability_advertised(self):
        stream = (_frame({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
                  + _frame({"jsonrpc": "2.0", "method": "exit"}))
        out = io.BytesIO()
        serve(stdin=io.BytesIO(stream), stdout=out)
        caps = next(m for m in _parse_frames(out.getvalue()) if m.get("id") == 1)["result"]["capabilities"]
        self.assertIn("codeActionProvider", caps)


class TestLenses(unittest.TestCase):
    """CodeLens (reference count), color swatches, inlay hints."""

    _DOC = ("# [Root](root)\n## [Dialogue](dialogue)\n### [A](a)\n"
            "---\nColor: #6cf\n---\n% hi\n- [go](b)\n### [Big B](b)\n% there\n")

    def _req(self, method, extra=None, uri="file:///tmp/x.amd"):
        params = {"textDocument": {"uri": uri}}
        params.update(extra or {})
        stream = (
            _frame({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
            + _frame({"jsonrpc": "2.0", "method": "textDocument/didOpen",
                      "params": {"textDocument": {"uri": uri, "text": self._DOC}}})
            + _frame({"jsonrpc": "2.0", "id": 2, "method": method, "params": params})
            + _frame({"jsonrpc": "2.0", "method": "exit"})
        )
        out = io.BytesIO()
        serve(stdin=io.BytesIO(stream), stdout=out)
        return next(m for m in _parse_frames(out.getvalue()) if m.get("id") == 2)["result"]

    def test_code_lens_reference_count(self):
        lenses = self._req("textDocument/codeLens")
        # node `b` is referenced once (by the choice) -> a "1 reference(s)" lens
        titles = [l["command"]["title"] for l in lenses]
        self.assertIn("1 reference(s)", titles)
        lens = next(l for l in lenses if l["command"]["title"] == "1 reference(s)")
        self.assertEqual(lens["command"]["command"], "editor.action.showReferences")

    def test_document_color(self):
        colors = self._req("textDocument/documentColor")
        self.assertEqual(len(colors), 1)
        c = colors[0]["color"]
        # #6cf -> #66ccff
        self.assertAlmostEqual(c["red"], 0x66 / 255, places=3)
        self.assertAlmostEqual(c["green"], 0xcc / 255, places=3)
        self.assertAlmostEqual(c["blue"], 0xff / 255, places=3)

    def test_color_presentation(self):
        # request color presentation for pure red
        uri = "file:///tmp/x.amd"
        stream = (_frame({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
                  + _frame({"jsonrpc": "2.0", "id": 2, "method": "textDocument/colorPresentation",
                            "params": {"textDocument": {"uri": uri},
                                       "color": {"red": 1.0, "green": 0.0, "blue": 0.0, "alpha": 1.0},
                                       "range": {"start": {"line": 0, "character": 0},
                                                 "end": {"line": 0, "character": 0}}}})
                  + _frame({"jsonrpc": "2.0", "method": "exit"}))
        out = io.BytesIO()
        serve(stdin=io.BytesIO(stream), stdout=out)
        res = next(m for m in _parse_frames(out.getvalue()) if m.get("id") == 2)["result"]
        self.assertEqual(res[0]["label"], "#ff0000")

    def test_inlay_hint_shows_display(self):
        hints = self._req("textDocument/inlayHint",
                          {"range": {"start": {"line": 0, "character": 0},
                                     "end": {"line": 20, "character": 0}}})
        # the choice `](b)` gets a ghosted " Big B" (node b's display)
        labels = [h["label"] for h in hints]
        self.assertIn(" Big B", labels)


class TestWorkspace(unittest.TestCase):
    """Whole-mission indexing: cross-file resolution matches `sbs lint`."""

    def _mission(self, tmp):
        os.mkdir(os.path.join(tmp, "m"))
        root = os.path.join(tmp, "m")
        with open(os.path.join(root, "story.json"), "w") as f:
            f.write("{}")
        # b.amd defines the dialogue scene `talk`
        with open(os.path.join(root, "b.amd"), "w") as f:
            f.write("# [R](rb)\n## [Dialogue](dialogue)\n### [Talk](talk)\n% hi\n")
        # a.amd references it cross-file via Scene:
        a = os.path.join(root, "a.amd")
        with open(a, "w") as f:
            f.write("# [R](ra)\n## [Lifeforms](lifeforms)\n### [S](storm)\n"
                    "---\nScene: talk\n---\nbody\n")
        return root, a

    def _drive(self, msgs):
        out = io.BytesIO()
        serve(stdin=io.BytesIO(b"".join(_frame(m) for m in msgs)), stdout=out)
        return _parse_frames(out.getvalue())

    def test_cross_file_definition(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, a = self._mission(tmp)
            uri = Path(a).as_uri()
            out = self._drive([
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                {"jsonrpc": "2.0", "method": "textDocument/didOpen",
                 "params": {"textDocument": {"uri": uri, "text": Path(a).read_text()}}},
                {"jsonrpc": "2.0", "id": 2, "method": "textDocument/definition",
                 "params": {"textDocument": {"uri": uri}, "position": {"line": 4, "character": 7}}},
                {"jsonrpc": "2.0", "method": "exit"},
            ])
            loc = next(m for m in out if m.get("id") == 2)["result"]
            self.assertTrue(loc["uri"].endswith("b.amd"))     # jumped to the other file
            self.assertEqual(loc["range"]["start"]["line"], 2)  # `### [Talk](talk)`

    def test_cross_file_diagnostics_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, a = self._mission(tmp)
            uri = Path(a).as_uri()
            out = self._drive([
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                {"jsonrpc": "2.0", "method": "textDocument/didOpen",
                 "params": {"textDocument": {"uri": uri, "text": Path(a).read_text()}}},
                {"jsonrpc": "2.0", "method": "exit"},
            ])
            pub = next(m for m in out if m.get("method") == "textDocument/publishDiagnostics")
            codes = [d["code"] for d in pub["params"]["diagnostics"]]
            self.assertNotIn("dangling-scene", codes)          # resolved via b.amd

    def test_mission_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = os.path.join(tmp, "m")
            os.mkdir(root)
            with open(os.path.join(root, "story.json"), "w") as f:
                f.write("{}")
            with open(os.path.join(root, "map.amd"), "w") as f:
                f.write("# [R](r)\n"
                        "## [Regions](regions)\n### [Marches](marches)\n"
                        "---\nCenter: 0, -1\nRadius: 8\nColor: #86c\n---\nb\n"
                        "## [Landmarks](landmarks)\n### [Ruin](ruin)\n"
                        "---\nAt: 2, -1\nKind: derelict\n---\nb\n")
            uri = Path(os.path.join(root, "map.amd")).as_uri()
            out = self._drive([
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                {"jsonrpc": "2.0", "method": "textDocument/didOpen",
                 "params": {"textDocument": {"uri": uri, "text": Path(os.path.join(root, "map.amd")).read_text()}}},
                {"jsonrpc": "2.0", "id": 2, "method": "amd/map",
                 "params": {"textDocument": {"uri": uri}}},
                {"jsonrpc": "2.0", "method": "exit"},
            ])
            m = next(x for x in out if x.get("id") == 2)["result"]
            self.assertEqual(len(m["landmarks"]), 1)
            self.assertEqual((m["landmarks"][0]["i"], m["landmarks"][0]["j"]), (2, -1))
            self.assertEqual(m["landmarks"][0]["kind"], "derelict")
            self.assertEqual(len(m["regions"]), 1)
            self.assertEqual(m["regions"][0]["radius"], 8.0)
            self.assertEqual(m["regions"][0]["color"], "#86c")
            # the landmark carries the editable range of its `At:` value
            ar = m["landmarks"][0]["atRange"]
            self.assertEqual(ar["start"]["line"], 12)   # `At: 2, -1` source line 13 -> LSP 12
            self.assertGreater(ar["end"]["character"], ar["start"]["character"])

    def test_mission_graph(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = os.path.join(tmp, "m")
            os.mkdir(root)
            with open(os.path.join(root, "story.json"), "w") as f:
                f.write("{}")
            with open(os.path.join(root, "d.amd"), "w") as f:
                f.write("# [R](r)\n## [Dialogue](dialogue)\n"
                        "### [A](a)\n% hi\n- [to B](b)\n- [to C](c)\n"
                        "### [B](b)\n% b\n- [back](a)\n"
                        "### [C](c)\n% c\n")
            uri = Path(os.path.join(root, "d.amd")).as_uri()
            out = self._drive([
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                {"jsonrpc": "2.0", "method": "textDocument/didOpen",
                 "params": {"textDocument": {"uri": uri, "text": Path(os.path.join(root, "d.amd")).read_text()}}},
                {"jsonrpc": "2.0", "id": 2, "method": "amd/graph",
                 "params": {"textDocument": {"uri": uri}}},
                {"jsonrpc": "2.0", "method": "exit"},
            ])
            g = next(x for x in out if x.get("id") == 2)["result"]
            keys = {n["key"] for n in g["nodes"]}
            self.assertTrue({"a", "b", "c"} <= keys)
            pairs = {(e["from"], e["to"]) for e in g["edges"]}
            self.assertEqual(pairs, {("a", "b"), ("a", "c"), ("b", "a")})
            na = next(n for n in g["nodes"] if n["key"] == "a")
            self.assertEqual(na["section"], "dialogue")
            # `A` body ends right before `### [B](b)` (source line 7 -> insert at line 6)
            self.assertEqual(na["addLine"], 6)

    def test_cross_file_references(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, a = self._mission(tmp)
            uri = Path(a).as_uri()
            out = self._drive([
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                {"jsonrpc": "2.0", "method": "textDocument/didOpen",
                 "params": {"textDocument": {"uri": uri, "text": Path(a).read_text()}}},
                {"jsonrpc": "2.0", "id": 2, "method": "textDocument/references",
                 "params": {"textDocument": {"uri": uri}, "position": {"line": 4, "character": 7},
                            "context": {"includeDeclaration": True}}},
                {"jsonrpc": "2.0", "method": "exit"},
            ])
            locs = next(m for m in out if m.get("id") == 2)["result"]
            uris = {os.path.basename(_uri_to_path(l["uri"])) for l in locs}
            self.assertEqual(uris, {"a.amd", "b.amd"})          # ref in a, decl in b


if __name__ == "__main__":
    unittest.main()
