"""amd_lsp - the AMD language server, driven over in-memory byte streams.

Frames an initialize + didOpen(broken doc) + shutdown/exit session, runs `serve`,
and asserts a publishDiagnostics with the expected range - no real editor needed.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import io
import json
import unittest

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


if __name__ == "__main__":
    unittest.main()
