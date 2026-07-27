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

    # A scan node under a conventionally-named `## [Science]` section, so the schema
    # resolves it to the `scan` archetype and types each field.
    _SCHEMA_DOC = ("# [Root](root)\n## [Science](science)\n### [Hull](hull)\n---\n"
                   "Scan of: derelict\nTab: scan\n---\n% wreck\n")

    def test_schema_types_a_scan_node(self):
        res = self._request("amd/schema",
                            {"textDocument": {"uri": "file:///tmp/x.amd"}, "key": "hull"},
                            doc=self._SCHEMA_DOC)
        self.assertEqual(res["archetype"], "scan")
        self.assertEqual(res["fields"]["Tab"]["type"], "enum")
        self.assertEqual(res["fields"]["Scan of"]["ref"], "role")

    def test_schema_none_for_missing_key(self):
        res = self._request("amd/schema",
                            {"textDocument": {"uri": "file:///tmp/x.amd"}, "key": "nope"},
                            doc=self._SCHEMA_DOC)
        self.assertIsNone(res)

    def test_template_returns_ordered_typed_fields(self):
        res = self._request("amd/template", {"archetype": "item"})
        self.assertEqual(res["archetype"], "item")
        labels = [f["label"] for f in res["fields"]]
        self.assertEqual(labels[0], "type")
        mode = next(f for f in res["fields"] if f["label"] == "mode")
        self.assertEqual(mode["schema"]["values"], ["consumable", "install", "resource"])

    # A cast character + a dialogue scene that names it as Speaker, for amd/preview.
    _PREVIEW_DOC = (
        "# [Root](root)\n"
        "## [Cast](cast)\n"
        "### [Ashfang](ashfang)\n---\nFace: skaraan\nColor: #f33\n---\nA raider captain.\n"
        "## [Dialogue](dialogue)\n"
        "### [Ashfang Hail](ashfang_hail)\n---\nSpeaker: ashfang\nWhen: comms\n---\n"
        "% You are a long way from friends.\n"
        "- [Apologize](ashfang_backoff)\n")

    def test_preview_dialogue_scene(self):
        res = self._request("amd/preview",
                            {"textDocument": {"uri": "file:///tmp/x.amd"}, "key": "ashfang_hail"},
                            doc=self._PREVIEW_DOC)
        self.assertEqual(res["kind"], "dialogue")
        self.assertEqual(res["speaker"]["name"], "Ashfang")     # resolved from the cast record
        self.assertEqual(res["speaker"]["color"], "#f33")
        self.assertIn("You are a long way from friends.", res["lines"])
        self.assertEqual(res["choices"][0]["target"], "ashfang_backoff")

    def test_preview_scan_node(self):
        doc = ("# [Root](root)\n## [Science](science)\n### [Hull](hull)\n---\n"
               "Scan of: derelict\nTab: intel\n---\n% Gutted wreckage.\n% Still smoking.\n")
        res = self._request("amd/preview",
                            {"textDocument": {"uri": "file:///tmp/x.amd"}, "key": "hull"}, doc=doc)
        self.assertEqual(res["kind"], "scan")
        self.assertEqual(res["tab"], "intel")
        self.assertEqual(len(res["lines"]), 2)

    def test_preview_missing_key(self):
        res = self._request("amd/preview",
                            {"textDocument": {"uri": "file:///tmp/x.amd"}, "key": "nope"},
                            doc=self._PREVIEW_DOC)
        self.assertIsNone(res)


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
            # region carries editable Center/Radius ranges (source lines 5, 6 -> LSP 4, 5)
            self.assertEqual(m["regions"][0]["centerRange"]["start"]["line"], 4)
            self.assertEqual(m["regions"][0]["radiusRange"]["start"]["line"], 5)
            # the landmark carries the editable range of its `At:` value
            lm = m["landmarks"][0]
            ar = lm["atRange"]
            self.assertEqual(ar["start"]["line"], 12)   # `At: 2, -1` source line 13 -> LSP 12
            self.assertGreater(ar["end"]["character"], ar["start"]["character"])
            # plus a Kind range (source line 14 -> LSP 13) and a delete point (EOF)
            self.assertEqual(lm["kindRange"]["start"]["line"], 13)
            self.assertGreaterEqual(lm["addLine"], 13)

    def _mission_with(self, tmp, amd):
        root = os.path.join(tmp, "m")
        os.mkdir(root)
        with open(os.path.join(root, "story.json"), "w") as f:
            f.write("{}")
        path = os.path.join(root, "d.amd")
        with open(path, "w") as f:
            f.write(amd)
        return path

    def _mission_request(self, amd, method):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._mission_with(tmp, amd)
            uri = Path(path).as_uri()
            out = self._drive([
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                {"jsonrpc": "2.0", "method": "textDocument/didOpen",
                 "params": {"textDocument": {"uri": uri, "text": Path(path).read_text()}}},
                {"jsonrpc": "2.0", "id": 2, "method": method,
                 "params": {"textDocument": {"uri": uri}}},
                {"jsonrpc": "2.0", "method": "exit"},
            ])
            return next(x for x in out if x.get("id") == 2)["result"]

    # `alarm` emits a signal `respond` waits on - the edge the Graph was blind to.
    _SIGNAL_AMD = ("# [R](r)\n## [Quests](quests)\n"
                   "### [Alarm](alarm)\n---\nState: active\nThen: signal breach\n---\nx\n"
                   "### [Respond](respond)\n---\nState: secret\nWhen: signal breach\n---\ny\n")

    def test_mission_graph_includes_signal_edges(self):
        g = self._mission_request(self._SIGNAL_AMD, "amd/graph")
        self.assertIn(("alarm", "respond", "signal"),
                      {(e["from"], e["to"], e["kind"]) for e in g["edges"]})

    def test_signal_reached_node_is_not_an_orphan(self):
        """A signal is a real "reached by", so a node a signal turns on must stop
        reporting as unreachable."""
        r = self._mission_request(self._SIGNAL_AMD, "amd/resolve")
        respond = next(e for e in r["entities"] if e["key"] == "respond")
        self.assertEqual(respond["inbound"], 1)
        self.assertFalse(respond["orphan"])

    def test_mission_timeline(self):
        amd = ("# [R](r)\n## [Quests](quests)\n"
               "### [One](one)\n---\nState: active\nThen: reveal two\n---\nx\n"
               "### [Two](two)\n---\nState: secret\nFail after: 6 minutes\n---\ny\n"
               "## [Jobs](jobs)\n"
               "### [Odd Job](odd)\n---\nState: idle\nGoal: signal never_fired\n---\nz\n")
        tl = self._mission_request(amd, "amd/timeline")
        by_key = {i["key"]: i for i in tl["items"]}
        self.assertEqual((by_key["one"]["beat"], by_key["two"]["beat"]), (0, 1))
        self.assertEqual(by_key["two"]["declared"]["seconds"], 360)
        self.assertEqual(by_key["odd"]["track"], "pool")
        self.assertEqual(by_key["one"]["archetype"], "quest")
        self.assertEqual(tl["beats"], 2)
        self.assertEqual(tl["lanes"]["section"], ["quests", "jobs"])

    # Two jobs, each with a step called `scan`, plus a flat second file whose records
    # are `#` headings (a per-section file handed straight to a loader).
    _DUP_AMD = ("# [R](r)\n## [Jobs](jobs)\n"
                "### [Ghost](job_ghost)\n---\nState: idle\n---\nx\n"
                "#### [Scan the Derelict](scan)\n---\nState: secret\n---\na\n"
                "### [Sweep](job_sweep)\n---\nState: idle\n---\ny\n"
                "#### [Scan the Contact](scan)\n---\nState: secret\n---\nb\n")
    _FLAT_AMD = ("# [Patrol Sweep](patrol)\n---\nState: idle\n---\np\n"
                 "# [Standing Bounty](bounty)\n---\nState: idle\n---\nq\n")

    def _dup_mission(self, method):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._mission_with(tmp, self._DUP_AMD)
            with open(os.path.join(os.path.dirname(path), "flat.amd"), "w") as f:
                f.write(self._FLAT_AMD)
            uri = Path(path).as_uri()
            out = self._drive([
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                {"jsonrpc": "2.0", "method": "textDocument/didOpen",
                 "params": {"textDocument": {"uri": uri, "text": Path(path).read_text()}}},
                {"jsonrpc": "2.0", "id": 2, "method": method,
                 "params": {"textDocument": {"uri": uri}}},
                {"jsonrpc": "2.0", "method": "exit"},
            ])
            return next(x for x in out if x.get("id") == 2)["result"]

    def test_graph_keeps_both_records_that_share_a_key(self):
        """Keying on the bare key dropped one of them - and a record no panel can show
        is the silent failure this tooling exists to end."""
        g = self._dup_mission("amd/graph")
        scans = [n for n in g["nodes"] if n["key"] == "scan"]
        self.assertEqual(len(scans), 2)
        self.assertEqual({n["path"] for n in scans},
                         {"r/jobs/job_ghost/scan", "r/jobs/job_sweep/scan"})

    def test_graph_reads_flat_single_section_files(self):
        """A per-section file has no `#` root or `##` group; its records ARE the `#`
        headings, and the old level filter read the whole file as zero records."""
        keys = {n["key"] for n in self._dup_mission("amd/graph")["nodes"]}
        self.assertTrue({"patrol", "bounty"} <= keys)

    def test_resolver_sees_both_and_flat_files(self):
        r = self._dup_mission("amd/resolve")
        keys = [e["key"] for e in r["entities"]]
        self.assertEqual(keys.count("scan"), 2)
        self.assertIn("patrol", keys)
        self.assertEqual(len({e["uid"] for e in r["entities"]}), len(r["entities"]))

    def test_a_step_is_not_an_orphan(self):
        """A record nested inside another is reached THROUGH its parent (often by a
        MAST sequencer, not an AMD edge), so it must not read as unreachable."""
        r = self._dup_mission("amd/resolve")
        for e in r["entities"]:
            if e["key"] == "scan":
                self.assertFalse(e["orphan"], e["path"])

    def test_node_detail_line_disambiguates_a_reused_key(self):
        """Two jobs can each own a step called `scan`. Without a line, `amd/node` falls
        back to a bare-key lookup and the inspector edits whichever namesake wins - so
        the panel passes the heading's line and must get THAT record."""
        amd = ("# [R](r)\n## [Jobs](jobs)\n"
               "### [Ghost](job_ghost)\n---\nState: idle\n---\nx\n"
               "#### [Scan the Derelict](scan)\n---\nState: secret\n---\na\n"
               "### [Sweep](job_sweep)\n---\nState: idle\n---\ny\n"
               "#### [Scan the Contact](scan)\n---\nState: secret\n---\nb\n")
        with tempfile.TemporaryDirectory() as tmp:
            path = self._mission_with(tmp, amd)
            uri = Path(path).as_uri()
            tl_req = {"jsonrpc": "2.0", "id": 2, "method": "amd/timeline",
                      "params": {"textDocument": {"uri": uri}}}
            out = self._drive([
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                {"jsonrpc": "2.0", "method": "textDocument/didOpen",
                 "params": {"textDocument": {"uri": uri, "text": Path(path).read_text()}}},
                tl_req,
                {"jsonrpc": "2.0", "method": "exit"},
            ])
            tl = next(x for x in out if x.get("id") == 2)["result"]
            wanted = next(i for i in tl["items"] if i["display"] == "Scan the Contact")

            out = self._drive([
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                {"jsonrpc": "2.0", "method": "textDocument/didOpen",
                 "params": {"textDocument": {"uri": uri, "text": Path(path).read_text()}}},
                {"jsonrpc": "2.0", "id": 3, "method": "amd/node",
                 "params": {"textDocument": {"uri": uri}, "key": "scan", "line": wanted["line"]}},
                {"jsonrpc": "2.0", "method": "exit"},
            ])
            detail = next(x for x in out if x.get("id") == 3)["result"]
            self.assertEqual(detail["display"], "Scan the Contact")

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
            # each edge carries its source line + target range (for delete/rewire)
            eab = next(e for e in g["edges"] if e["from"] == "a" and e["to"] == "b")
            self.assertIn("targetRange", eab)
            self.assertIsInstance(eab["line"], int)

    def test_new_in_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = os.path.join(tmp, "m")
            os.mkdir(root)
            with open(os.path.join(root, "story.json"), "w") as f:
                f.write("{}")
            with open(os.path.join(root, "d.amd"), "w") as f:
                f.write("# [R](r)\n"
                        "## [Dialogue](dialogue)\n"
                        "### [Hail](hail)\n---\nSpeaker: bob\nWhen: comms\n---\n% hi\n")
            uri = Path(os.path.join(root, "d.amd")).as_uri()

            def ask(section):
                out = self._drive([
                    {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                    {"jsonrpc": "2.0", "method": "textDocument/didOpen",
                     "params": {"textDocument": {"uri": uri, "text": Path(os.path.join(root, "d.amd")).read_text()}}},
                    {"jsonrpc": "2.0", "id": 2, "method": "amd/newInSection",
                     "params": {"textDocument": {"uri": uri}, "section": section}},
                    {"jsonrpc": "2.0", "method": "exit"},
                ])
                return next(x for x in out if x.get("id") == 2)["result"]

            # An existing (archetype-less) section mirrors a sibling's fields and
            # gets a unique key; no `##` header is prepended.
            r = ask("dialogue")
            self.assertEqual(r["key"], "new_dialogue")
            self.assertTrue(r["exists"])
            self.assertIn("### [New Dialogue](new_dialogue)", r["text"])
            self.assertIn("Speaker:", r["text"])
            self.assertIn("When:", r["text"])
            self.assertNotIn("## [Dialogue]", r["text"])   # section already present

            # A missing conventional section falls back to the schema fields and
            # prepends its `##` header.
            r2 = ask("lifeforms")
            self.assertFalse(r2["exists"])
            self.assertEqual(r2["archetype"], "lifeform")
            self.assertIn("## [Lifeforms](lifeforms)", r2["text"])
            self.assertIn("Face:", r2["text"])

    def test_mission_resolve(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = os.path.join(tmp, "m")
            os.mkdir(root)
            with open(os.path.join(root, "story.json"), "w") as f:
                f.write("{}")
            # A (active) resolves to B (good) and to a missing target (dangling);
            # C is a secret quest nobody reveals (orphan); D is unreferenced but
            # `When:`-triggered; guy is a lifeform data record (never an orphan).
            with open(os.path.join(root, "d.amd"), "w") as f:
                f.write("# [R](r)\n## [Narrative](narrative)\n"
                        "### [A](a)\n---\nState: active\n---\nhi\n- [to B](b)\n- [to gone](nowhere)\n"
                        "### [B](b)\n---\nState: secret\n---\nb\n"
                        "### [C](c)\n---\nState: secret\n---\nc\n"
                        "### [D](d)\n---\nWhen: reach 1, 1\n---\nd\n"
                        "## [Lifeforms](lifeforms)\n"
                        "### [Guy](guy)\n---\nSide: friendly\n---\na guy\n")
            uri = Path(os.path.join(root, "d.amd")).as_uri()
            out = self._drive([
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                {"jsonrpc": "2.0", "method": "textDocument/didOpen",
                 "params": {"textDocument": {"uri": uri, "text": Path(os.path.join(root, "d.amd")).read_text()}}},
                {"jsonrpc": "2.0", "id": 2, "method": "amd/resolve",
                 "params": {"textDocument": {"uri": uri}}},
                {"jsonrpc": "2.0", "method": "exit"},
            ])
            m = next(x for x in out if x.get("id") == 2)["result"]
            ents = {e["key"]: e for e in m["entities"]}
            self.assertTrue({"a", "b", "c", "d", "guy"} <= set(ents))
            # section/group headings (`#`/`##`) are not entities.
            self.assertNotIn("r", ents)
            self.assertNotIn("narrative", ents)
            self.assertNotIn("lifeforms", ents)
            # C is a secret quest nothing reveals or triggers -> orphan. A starts
            # active, B is revealed by a choice, D is `When:`-triggered -> none orphan.
            self.assertTrue(ents["c"]["orphan"])
            self.assertFalse(ents["a"]["orphan"])
            self.assertFalse(ents["b"]["orphan"])
            self.assertEqual(ents["b"]["inbound"], 1)
            self.assertEqual(ents["d"]["inbound"], 0)
            self.assertTrue(ents["d"]["triggered"])
            self.assertFalse(ents["d"]["orphan"])
            # a data record (lifeform) is never an orphan, even with no inbound edge.
            self.assertEqual(ents["guy"]["archetype"], "lifeform")
            self.assertEqual(ents["guy"]["inbound"], 0)
            self.assertFalse(ents["guy"]["orphan"])
            # the good ref resolves; the dangling one is flagged with a lint code.
            good = next(r for r in m["refs"] if r["value"] == "b" and r["kind"] == "choice")
            gone = next(r for r in m["refs"] if r["value"] == "nowhere")
            self.assertTrue(good["resolved"])
            self.assertFalse(gone["resolved"])
            self.assertTrue((gone["code"] or "").startswith("dangling"))
            # a dangling choice surfaces in the issue list too, anchored to a line.
            self.assertTrue(any(i["code"] and i["code"].startswith("dangling") for i in m["issues"]))

    def test_bad_request_does_not_crash_server(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = os.path.join(tmp, "m")
            os.mkdir(root)
            with open(os.path.join(root, "story.json"), "w") as f:
                f.write("{}")
            with open(os.path.join(root, "d.amd"), "w") as f:
                f.write("# [R](r)\n## [N](narrative)\n### [A](a)\n---\nState: active\n---\nhi\n")
            uri = Path(os.path.join(root, "d.amd")).as_uri()
            out = self._drive([
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                {"jsonrpc": "2.0", "method": "textDocument/didOpen",
                 "params": {"textDocument": {"uri": uri, "text": Path(os.path.join(root, "d.amd")).read_text()}}},
                # malformed params (a string, not an object) makes the handler raise
                {"jsonrpc": "2.0", "id": 2, "method": "amd/graph", "params": "not-a-dict"},
                # the server must survive and still answer the next request
                {"jsonrpc": "2.0", "id": 3, "method": "amd/graph",
                 "params": {"textDocument": {"uri": uri}}},
                {"jsonrpc": "2.0", "method": "exit"},
            ])
            bad = next(x for x in out if x.get("id") == 2)
            self.assertIn("error", bad)              # replied with an error instead of crashing
            good = next(x for x in out if x.get("id") == 3)
            self.assertIn("result", good)            # and kept serving
            self.assertTrue(any(n["key"] == "a" for n in good["result"]["nodes"]))

    def test_node_detail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = os.path.join(tmp, "m")
            os.mkdir(root)
            with open(os.path.join(root, "story.json"), "w") as f:
                f.write("{}")
            doc = ("# [R](r)\n## [N](narrative)\n### [Quest One](q1)\n"
                   "---\nState: active\nWhen: reach 2, -1\n---\n"
                   "The first quest.\nGo to the ruin.\n"
                   "### [Q2](q2)\nx\n")
            with open(os.path.join(root, "a.amd"), "w") as f:
                f.write(doc)
            uri = Path(os.path.join(root, "a.amd")).as_uri()
            out = self._drive([
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                {"jsonrpc": "2.0", "method": "textDocument/didOpen",
                 "params": {"textDocument": {"uri": uri, "text": doc}}},
                {"jsonrpc": "2.0", "id": 2, "method": "amd/node",
                 "params": {"textDocument": {"uri": uri}, "key": "q1"}},
                {"jsonrpc": "2.0", "method": "exit"},
            ])
            n = next(x for x in out if x.get("id") == 2)["result"]
            self.assertEqual(n["display"], "Quest One")
            self.assertEqual([(f["label"], f["value"]) for f in n["fields"]],
                             [("State", "active"), ("When", "reach 2, -1")])
            self.assertEqual(n["bodyText"], "The first quest.\nGo to the ruin.")
            # body range ends where the next node (### [Q2]) begins (source line 10 -> 9)
            self.assertEqual(n["bodyRange"]["end"]["line"], 9)

    def test_choice_at(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = os.path.join(tmp, "m")
            os.mkdir(root)
            with open(os.path.join(root, "story.json"), "w") as f:
                f.write("{}")
            doc = ("# [R](r)\n## [Dialogue](dialogue)\n### [A](a)\n% hi\n"
                   "- [Buy it](sold) if credits >= 10 ; costs 10 credits, signal buy\n")
            with open(os.path.join(root, "a.amd"), "w") as f:
                f.write(doc)
            uri = Path(os.path.join(root, "a.amd")).as_uri()
            out = self._drive([
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                {"jsonrpc": "2.0", "method": "textDocument/didOpen",
                 "params": {"textDocument": {"uri": uri, "text": doc}}},
                {"jsonrpc": "2.0", "id": 2, "method": "amd/choice",
                 "params": {"textDocument": {"uri": uri}, "line": 4}},   # the choice line
                {"jsonrpc": "2.0", "method": "exit"},
            ])
            c = next(x for x in out if x.get("id") == 2)["result"]
            self.assertEqual(c["label"], "Buy it")
            self.assertEqual(c["target"], "sold")
            self.assertEqual(c["trailer"], " if credits >= 10 ; costs 10 credits, signal buy")

    def test_section_insert(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = os.path.join(tmp, "m")
            os.mkdir(root)
            with open(os.path.join(root, "story.json"), "w") as f:
                f.write("{}")
            doc = ("# [R](r)\n## [Dialogue](dialogue)\n### [A](a)\n% hi\n"
                   "## [Narrative](narrative)\n### [Q](q)\nx\n")
            with open(os.path.join(root, "a.amd"), "w") as f:
                f.write(doc)
            uri = Path(os.path.join(root, "a.amd")).as_uri()

            def ask(section):
                out = self._drive([
                    {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                    {"jsonrpc": "2.0", "method": "textDocument/didOpen",
                     "params": {"textDocument": {"uri": uri, "text": doc}}},
                    {"jsonrpc": "2.0", "id": 2, "method": "amd/sectionInsert",
                     "params": {"textDocument": {"uri": uri}, "section": section}},
                    {"jsonrpc": "2.0", "method": "exit"},
                ])
                return next(x for x in out if x.get("id") == 2)["result"]

            d = ask("dialogue")   # end of Dialogue = before ## Narrative (source line 5 -> 4)
            self.assertEqual((d["line"], d["exists"]), (4, True))
            g = ask("goals")      # missing -> EOF, exists False
            self.assertFalse(g["exists"])

    def test_rename_by_key_cross_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, a = self._mission(tmp)   # a.amd Scene: talk -> b.amd ### [Talk](talk)
            uri = Path(a).as_uri()
            out = self._drive([
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                {"jsonrpc": "2.0", "method": "textDocument/didOpen",
                 "params": {"textDocument": {"uri": uri, "text": Path(a).read_text()}}},
                {"jsonrpc": "2.0", "id": 2, "method": "amd/rename",
                 "params": {"textDocument": {"uri": uri}, "key": "talk", "newName": "chat"}},
                {"jsonrpc": "2.0", "method": "exit"},
            ])
            changes = next(x for x in out if x.get("id") == 2)["result"]["changes"]
            bases = {os.path.basename(_uri_to_path(u)) for u in changes}
            self.assertEqual(bases, {"a.amd", "b.amd"})   # ref in a, decl in b both edited
            self.assertTrue(all(e["newText"] == "chat" for edits in changes.values() for e in edits))

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


class TestNodeAtLine(unittest.TestCase):
    """_node_at_line maps a cursor line to the node that owns it (nearest
    heading at or above) — the docked inspector's cursor-follow lookup."""

    def test_node_at_line(self):
        from sbs_utils.procedural.amd_lsp import _index_for, _node_at_line
        amd = (
            "# [My Mission](my_mission)\n---\nDisplay: My Mission\n---\nIntro.\n\n"
            "## [Scene One](scene_one)\nDialogue.\n- [go](scene_two)\n\n"
            "## [Scene Two](scene_two)\nMore.\n"
        )
        uri = "file:///m/story.amd"
        idx = _index_for(uri, {uri: amd})
        cases = {0: "my_mission", 3: "my_mission", 6: "scene_one",
                 8: "scene_one", 11: "scene_two"}
        for line, key in cases.items():
            d = _node_at_line(idx, uri, line)
            self.assertIsNotNone(d, f"line {line}")
            self.assertEqual(d["key"], key, f"line {line}")


if __name__ == "__main__":
    unittest.main()
