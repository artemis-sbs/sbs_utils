"""AMD linter (procedural.amd_lint) - structural, reference, and cross-file passes.

Phase 1 (structural) is pure-stdlib and needs no engine; Phases 2/3 reuse the real
`document_get_amd_file` parser via `amd_lint`. `test_set_exe_dir()` is required at
module scope so path resolution works under `unittest discover`.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from sbs_utils.procedural.amd_lint import (
    amd_lint, amd_lint_structural, ERROR, WARNING,
)


def _codes(findings):
    return [f.code for f in findings]


def _by_code(findings, code):
    return [f for f in findings if f.code == code]


class TestStructural(unittest.TestCase):
    """Phase 1 - the silent-failure class, source-level."""

    def test_clean_document(self):
        doc = (
            "# [Root](root)\n"
            "Prose.\n"
            "## [Child](child)\n"
            "## Objective\n"          # legit body markdown heading
            "- a bullet\n"
        )
        self.assertEqual(amd_lint_structural(content=doc), [])

    def test_broken_heading_vanishing_node(self):
        # Missing close paren: the parser drops it into body text, node vanishes.
        doc = "# [Root](root)\n## [Voice](ep1_scan\nbody\n"
        f = _by_code(amd_lint_structural(content=doc), "broken-heading")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0].severity, ERROR)
        self.assertEqual(f[0].line, 2)

    def test_prose_heading_with_parens_not_flagged(self):
        # A body heading that merely contains parentheses must NOT false-positive.
        doc = "# [Root](root)\n## The Cipher (older than the ruins)\nbody (2, -1)\n"
        self.assertEqual(amd_lint_structural(content=doc), [])

    def test_suspect_heading_is_warning(self):
        doc = "# [Root](root)\n## [Looks Like A Heading]\nbody\n"
        f = _by_code(amd_lint_structural(content=doc), "suspect-heading")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0].severity, WARNING)

    def test_unclosed_data_fence(self):
        doc = "# [Root](root)\n---\nCenter: 0, 0\ntail never closed\n"
        f = _by_code(amd_lint_structural(content=doc), "unclosed-data-fence")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0].severity, ERROR)
        self.assertEqual(f[0].line, 2)

    def test_closed_fence_ok(self):
        doc = "# [Root](root)\n---\nCenter: 0, 0\n---\nbody\n"
        self.assertNotIn("unclosed-data-fence", _codes(amd_lint_structural(content=doc)))

    def test_heading_level_jump(self):
        doc = "# [Root](root)\n### [Too Deep](deep)\nbody\n"
        f = _by_code(amd_lint_structural(content=doc), "heading-level-jump")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0].severity, ERROR)


class TestAscii(unittest.TestCase):
    """The engine renders ASCII only - flag non-ASCII author text."""

    def test_flags_smart_quotes_and_emoji(self):
        doc = "# [Root](root)\n% Don’t panic \U0001f600\n"   # smart apostrophe + emoji
        f = _by_code(amd_lint(content=doc), "non-ascii")
        self.assertTrue(f)
        self.assertTrue(all(x.severity == WARNING for x in f))

    def test_clean_ascii(self):
        doc = "# [Root](root)\n% Don't panic - all good.\n"
        self.assertEqual(_by_code(amd_lint(content=doc), "non-ascii"), [])

    def test_comment_exempt(self):
        doc = "# [Root](root)\n// a note with an em-dash — fine in comments\n"
        self.assertEqual(_by_code(amd_lint(content=doc), "non-ascii"), [])


class TestReferences(unittest.TestCase):
    """Phase 2 - intra-document danglers (all WARNING)."""

    def test_clean_references(self):
        doc = (
            "# [Root](root)\n"
            "## [Dialogue](dialogue)\n"
            "### [A](a)\n"
            "% hi\n"
            "- [go](b)\n"
            "### [B](b)\n"
            "% there\n"
        )
        refs = [f for f in amd_lint(content=doc, cross_file=False)
                if f.code.startswith("dangling")]
        self.assertEqual(refs, [])

    def test_dangling_choice_target(self):
        doc = ("# [Root](root)\n## [Dialogue](dialogue)\n### [A](a)\n"
               "% hi\n- [go](nope)\n")
        f = _by_code(amd_lint(content=doc, cross_file=False), "dangling-choice")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0].severity, WARNING)

    def test_route_target_not_flagged(self):
        # A `//route` choice target is not an intra-doc node - must be ignored.
        doc = ("# [Root](root)\n## [Dialogue](dialogue)\n### [A](a)\n"
               "% hi\n- [back](//comms)\n")
        self.assertEqual(_by_code(amd_lint(content=doc, cross_file=False), "dangling-choice"), [])

    def test_dangling_scene(self):
        doc = ("# [Root](root)\n## [Lifeforms](lifeforms)\n### [S](storm)\n"
               "---\nScene: no_such_scene\n---\nbody\n")
        f = _by_code(amd_lint(content=doc, cross_file=False), "dangling-scene")
        self.assertEqual(len(f), 1)

    def test_dangling_reveal_path(self):
        doc = ("# [Root](root)\n## [N](narrative)\n### [Arc](arc)\n"
               "#### [Go](go)\n---\nThen: reveal arc/missing\n---\nbody\n")
        f = _by_code(amd_lint(content=doc, cross_file=False), "dangling-reveal")
        self.assertEqual(len(f), 1)

    def test_valid_reveal_path_ok(self):
        doc = ("# [Root](root)\n## [N](narrative)\n### [Arc](arc)\n"
               "#### [Go](go)\n---\nThen: reveal arc/scan\n---\nb\n"
               "#### [Scan](scan)\nb\n")
        self.assertEqual(_by_code(amd_lint(content=doc, cross_file=False), "dangling-reveal"), [])

    def test_dangling_parent(self):
        doc = ("# [Root](root)\n## [N](narrative)\n### [Q](q)\n"
               "---\nParent: ghost\n---\nbody\n")
        f = _by_code(amd_lint(content=doc, cross_file=False), "dangling-parent")
        self.assertEqual(len(f), 1)

    def test_cross_file_scene_resolved_via_known_keys(self):
        # `Scene: talk` lives in another .amd -> flagged alone, resolved with known key.
        doc = ("# [Root](root)\n## [Lifeforms](lifeforms)\n### [S](storm)\n"
               "---\nScene: talk\n---\nbody\n")
        self.assertEqual(len(_by_code(amd_lint(content=doc, cross_file=False), "dangling-scene")), 1)
        clean = amd_lint(content=doc, cross_file=False, known_keys={"talk"})
        self.assertEqual(_by_code(clean, "dangling-scene"), [])

    def test_mast_label_target_not_flagged(self):
        # A choice target that is a MAST label (`== go_there ==`) must resolve.
        doc = ("# [Root](root)\n## [Dialogue](dialogue)\n### [A](a)\n"
               "% hi\n- [go](go_there)\n")
        clean = amd_lint(content=doc, mast_sources=["== go_there ==\n    ->END\n"])
        self.assertEqual(_by_code(clean, "dangling-choice"), [])


class TestCrossFile(unittest.TestCase):
    """Phase 3 - signals vs routes, reach vs landmark (all WARNING)."""

    def test_signal_without_route(self):
        doc = ("# [Root](root)\n## [Dialogue](dialogue)\n### [A](a)\n"
               "% hi\n- [buy](a) ; costs 10 credits, signal buy_ghost\n")
        f = _by_code(amd_lint(content=doc, mast_sources=["//comms\n    ->END\n"]),
                     "signal-no-route")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0].severity, WARNING)

    def test_signal_with_route_ok(self):
        doc = ("# [Root](root)\n## [Dialogue](dialogue)\n### [A](a)\n"
               "% hi\n- [buy](a) ; costs 10 credits, signal buy_real\n")
        mast = "//signal/buy_real\n    ->END\n"
        self.assertEqual(_by_code(amd_lint(content=doc, mast_sources=[mast]),
                                  "signal-no-route"), [])

    def test_driver_signal_allowlisted(self):
        doc = ("# [Root](root)\n## [Dialogue](dialogue)\n### [A](a)\n"
               "% hi\n- [x](a) ; signal game_over\n")
        self.assertEqual(_by_code(amd_lint(content=doc, mast_sources=[]),
                                  "signal-no-route"), [])

    def test_reach_without_landmark(self):
        doc = ("# [Root](root)\n## [N](narrative)\n### [Go](go)\n"
               "---\nWhen: reach 9, 9\n---\nbody\n")
        f = _by_code(amd_lint(content=doc, mast_sources=[]), "reach-no-landmark")
        self.assertEqual(len(f), 1)

    def test_reach_with_landmark_ok(self):
        doc = ("# [Root](root)\n"
               "## [N](narrative)\n### [Go](go)\n---\nWhen: reach 2, -1\n---\nb\n"
               "## [Landmarks](landmarks)\n### [Site](site)\n---\nAt: 2, -1\n---\nb\n")
        self.assertEqual(_by_code(amd_lint(content=doc, mast_sources=[]),
                                  "reach-no-landmark"), [])

    def test_signal_check_skipped_without_mast(self):
        # No mast_sources -> the signal->route check must not run (nothing to check against).
        doc = ("# [Root](root)\n## [Dialogue](dialogue)\n### [A](a)\n"
               "% hi\n- [buy](a) ; signal buy_ghost\n")
        self.assertEqual(_by_code(amd_lint(content=doc), "signal-no-route"), [])

    def test_wait_signal_unfired(self):
        # `When: signal X` with nothing emitting X -> unfired-signal warning.
        doc = ("# [Root](root)\n## [N](narrative)\n### [Q](q)\n"
               "---\nWhen: signal never_emitted\n---\nbody\n")
        f = _by_code(amd_lint(content=doc, mast_sources=["// empty mast\n"]), "unfired-signal")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0].severity, WARNING)

    def test_wait_signal_satisfied_by_signal_name_emit(self):
        # Emitted via the quest-signal plumbing in .mast -> no warning.
        doc = ("# [Root](root)\n## [N](narrative)\n### [Q](q)\n"
               "---\nWhen: signal briefed\n---\nbody\n")
        mast = ['signal_emit("quest_signal", {"SIGNAL_NAME": "briefed"})\n']
        self.assertEqual(_by_code(amd_lint(content=doc, mast_sources=mast), "unfired-signal"), [])

    def test_wait_signal_skipped_without_mast(self):
        doc = ("# [Root](root)\n## [N](narrative)\n### [Q](q)\n"
               "---\nWhen: signal x\n---\nbody\n")
        self.assertEqual(_by_code(amd_lint(content=doc), "unfired-signal"), [])

    def test_declared_emits_satisfies_wait_signal(self):
        # `emits: [foo]` in a metadata block asserts foo is emitted (Option A).
        doc = ("# [Root](root)\n## [N](narrative)\n### [Q](q)\n"
               "---\nWhen: signal foo\n---\nbody\n")
        mast = ["metadata block with\nemits: [foo]\n"]
        self.assertEqual(_by_code(amd_lint(content=doc, mast_sources=mast), "unfired-signal"), [])

    def test_declared_handles_satisfies_signal_route(self):
        # `handles: [bar]` counts as a handler, like a //signal/bar route.
        doc = ("# [Root](root)\n## [Dialogue](dialogue)\n### [A](a)\n"
               "% hi\n- [x](a) ; signal bar\n")
        mast = ["handles: [bar]\n"]
        self.assertEqual(_by_code(amd_lint(content=doc, mast_sources=mast), "signal-no-route"), [])


class TestSpans(unittest.TestCase):
    """Findings carry exact column ranges from the amd_core model (not line-only)."""

    def test_choice_target_span(self):
        doc = "# [Root](root)\n## [Dialogue](dialogue)\n### [A](a)\n% hi\n- [go](nope)\n"
        f = _by_code(amd_lint(content=doc, cross_file=False), "dangling-choice")[0]
        self.assertEqual((f.line, f.col, f.end_col), (5, 7, 11))  # "- [go](" -> target at 7

    def test_signal_span(self):
        doc = ("# [Root](root)\n## [Dialogue](dialogue)\n### [A](a)\n"
               "% hi\n- [buy](a) ; signal ghost_sig\n")
        f = _by_code(amd_lint(content=doc, mast_sources=[]), "signal-no-route")
        # driver allowlist empty here, no route -> flagged, with a real column
        self.assertTrue(f and f[0].col is not None and f[0].end_col > f[0].col)


class TestScanLabels(unittest.TestCase):
    """Scan-vocabulary check - a typo'd tab is silently swallowed and never renders."""

    def test_clean_scan_fence(self):
        doc = ("# [Rock](rock)\n---\nScan: A rock.\nMat: Salvageable.\nBio: No life.\n---\n")
        self.assertEqual(_by_code(amd_lint(content=doc, cross_file=False), "unknown-scan-label"), [])

    def test_typo_tab_flagged(self):
        doc = ("# [Rock](rock)\n---\nScan: A rock.\nScna: oops.\n---\n")
        f = _by_code(amd_lint(content=doc, cross_file=False), "unknown-scan-label")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0].line, 4)   # the Scna: line

    def test_placeholder_intel_is_clean(self):
        # a {placeholder} value (parses as YAML) must not trip the scan-label check
        doc = ("# [Ship](ship)\n---\nScan: A ship.\nIntel: Captain {captain}.\n---\n")
        self.assertEqual(_by_code(amd_lint(content=doc, cross_file=False), "unknown-scan-label"), [])

    def test_quest_fence_not_treated_as_scan(self):
        # a quest fence that happens to use Status: must not be judged as a scan fence
        doc = ("# [Q](q)\n---\nGoal: destroy 3 raiders\nStatus: anything\n---\n")
        self.assertEqual(_by_code(amd_lint(content=doc, cross_file=False), "unknown-scan-label"), [])


if __name__ == "__main__":
    unittest.main()
