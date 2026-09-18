"""Two lint rules, and .mast diagnostics in the editor.

- ``await-block-stray-statement``: `sbs lint` / the editor surface the MAST compiler's
  own warning (a plain statement directly in an `await ...:` block never runs). It
  compiles the file and reads the compiler's records, so the two cannot disagree.
- ``trigger-role-plural``: a trigger target the role singularizer gets wrong -
  irregular plurals (`mice`), `-ves` plurals (`wolves` -> `wolve`), and a singular
  ending in `s` (`lens` -> `len`) when the mission never uses the singularized form.
- The language server now takes `.mast` documents: diagnostics only, and an empty
  answer to every other request, so AMD features never touch a MAST file.

    python -m unittest tests.test_lint_await_and_plurals
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import io
import unittest

from sbs_utils.mast.mast import Mast
from sbs_utils.procedural.amd_lint import amd_lint, mast_source_index
from sbs_utils.procedural.amd_lsp import serve
from sbs_utils.procedural.await_lint import await_lint

from tests.test_amd_lsp import _frame, _parse_frames

STRAY = ("== start ==\n"
         "    await delay_sim(1):\n"
         "        x = 1\n"
         "        + \"Go\":\n"
         "            y = 2\n"
         "    ->END\n")


class TestAwaitLint(unittest.TestCase):

    def test_A_STRAY_STATEMENT_IS_FOUND_ON_ITS_LINE(self):
        found = await_lint(content=STRAY)
        self.assertEqual([3], [f.line for f in found])
        self.assertEqual("await-block-stray-statement", found[0].code)
        self.assertFalse(found[0].is_error())

    def test_button_bodies_are_fine(self):
        self.assertEqual([], await_lint(content=(
            "== start ==\n"
            "    await gui():\n"
            "        + \"Go\":\n"
            "            x = 1\n"
            "    ->END\n")))

    def test_a_file_with_no_await_is_skipped_cheaply(self):
        self.assertEqual([], await_lint(content="== a ==\n    x = 1\n"))

    def test_lint_does_not_print_and_restores_the_switch(self):
        out = io.StringIO()
        import contextlib
        with contextlib.redirect_stdout(out):
            await_lint(content=STRAY)
        self.assertEqual("", out.getvalue())
        self.assertTrue(Mast.print_compile_warnings)

    def test_an_unloadable_import_is_not_noise(self):
        out = io.StringIO()
        import contextlib
        with contextlib.redirect_stdout(out):
            found = await_lint(content="import nowhere.mast\n" + STRAY)
        self.assertEqual("", out.getvalue())
        self.assertEqual(1, len(found))


PLURALS = """# Jobs

## [Hunt](hunt)
---
Done when: destroy 2 mice
---

## [Pack](pack)
---
Done when: destroy 3 wolves
---

## [Lens](lens)
---
Done when: scan 1 lens
---

## [Guns](guns)
---
Done when: destroy 2 guns
---

## [Anomalies](anomalies)
---
Done when: scan 3 anomalies
Fail on all dead: people
---
"""

SOURCES = ['npc_spawn(0, 0, 0, "L", "lens, station", "a", "b")\n'
           'n = len(things)\n'
           'add_role(g, "gun")\n']


def _plural_lines(findings):
    return sorted(f.line for f in findings if f.code == "trigger-role-plural")


class TestTriggerRolePlural(unittest.TestCase):

    def test_IRREGULAR_AND_VES_PLURALS_ARE_ALWAYS_FLAGGED(self):
        # mice (5), wolves (10), people (26) - no sources needed.
        self.assertEqual([5, 10, 26], _plural_lines(amd_lint(content=PLURALS)))

    def test_A_SINGULAR_ENDING_IN_S_NEEDS_THE_MISSIONS_EVIDENCE(self):
        """`lens` is flagged only when the mission uses `lens` and never `len` - and
        `len(` in CODE is not a use, only a string literal is."""
        found = _plural_lines(amd_lint(content=PLURALS,
                                       source_index=mast_source_index(SOURCES)))
        self.assertEqual([5, 10, 15, 26], found)

    def test_ordinary_plurals_are_never_flagged(self):
        found = amd_lint(content=PLURALS, source_index=mast_source_index(SOURCES))
        flagged = {f.line for f in found if f.code == "trigger-role-plural"}
        self.assertNotIn(20, flagged)          # guns -> gun
        self.assertNotIn(25, flagged)          # anomalies -> anomaly

    def test_the_message_names_the_real_singular(self):
        found = [f for f in amd_lint(content=PLURALS) if f.code == "trigger-role-plural"]
        self.assertIn("mouse", found[0].message)


class TestMastInTheLanguageServer(unittest.TestCase):

    def run_server(self, frames):
        stream = (_frame({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
                  + b"".join(_frame(f) for f in frames)
                  + _frame({"jsonrpc": "2.0", "id": 99, "method": "shutdown"})
                  + _frame({"jsonrpc": "2.0", "method": "exit"}))
        out = io.BytesIO()
        serve(stdin=io.BytesIO(stream), stdout=out)
        return _parse_frames(out.getvalue())

    def test_A_MAST_DOCUMENT_GETS_ITS_DIAGNOSTICS(self):
        uri = "file:///tmp/story.mast"
        msgs = self.run_server([{"jsonrpc": "2.0", "method": "textDocument/didOpen",
                                 "params": {"textDocument": {"uri": uri, "text": STRAY}}}])
        pub = [m for m in msgs if m.get("method") == "textDocument/publishDiagnostics"]
        self.assertEqual(1, len(pub))
        diags = pub[0]["params"]["diagnostics"]
        self.assertEqual(["await-block-stray-statement"], [d["code"] for d in diags])
        self.assertEqual(2, diags[0]["range"]["start"]["line"])      # 0-based line 3
        self.assertEqual("mast", diags[0]["source"])

    def test_OTHER_REQUESTS_ON_A_MAST_DOCUMENT_GET_NOTHING(self):
        uri = "file:///tmp/story.mast"
        msgs = self.run_server([
            {"jsonrpc": "2.0", "method": "textDocument/didOpen",
             "params": {"textDocument": {"uri": uri, "text": STRAY}}},
            {"jsonrpc": "2.0", "id": 5, "method": "textDocument/hover",
             "params": {"textDocument": {"uri": uri}, "position": {"line": 0, "character": 3}}},
            {"jsonrpc": "2.0", "id": 6, "method": "textDocument/completion",
             "params": {"textDocument": {"uri": uri}, "position": {"line": 0, "character": 3}}},
        ])
        for mid in (5, 6):
            reply = next(m for m in msgs if m.get("id") == mid)
            self.assertIsNone(reply["result"])

    def test_an_amd_document_still_gets_amd_answers(self):
        uri = "file:///tmp/x.amd"
        msgs = self.run_server([
            {"jsonrpc": "2.0", "method": "textDocument/didOpen",
             "params": {"textDocument": {"uri": uri, "text": "# [Root](root)\n"}}},
            {"jsonrpc": "2.0", "id": 5, "method": "textDocument/documentSymbol",
             "params": {"textDocument": {"uri": uri}}},
        ])
        reply = next(m for m in msgs if m.get("id") == 5)
        self.assertIsNotNone(reply["result"])


if __name__ == "__main__":
    unittest.main()
