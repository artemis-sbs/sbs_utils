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


class TestFieldValues(unittest.TestCase):
    """Phase 2b - schema-driven enum-value checking (unknown-enum-value)."""

    def test_typoed_state_warns(self):
        doc = ("# [Jobs](jobs)\n"
               "## [Jobs](jobs)\n"
               "### [Patrol](patrol)\n"
               "---\n"
               "State: activ\n"
               "---\n"
               "body\n")
        findings = amd_lint(content=doc)
        bad = _by_code(findings, "unknown-enum-value")
        self.assertEqual(len(bad), 1)
        self.assertEqual(bad[0].severity, WARNING)
        self.assertIn("State", bad[0].message)

    def test_valid_state_is_clean(self):
        for good in ("active", "idle", "secret"):
            doc = ("## [Jobs](jobs)\n### [Patrol](patrol)\n---\n"
                   f"State: {good}\n---\nbody\n")
            self.assertEqual(_by_code(amd_lint(content=doc), "unknown-enum-value"), [])

    def test_open_kind_enum_does_not_warn(self):
        # Kind is an open enum: npc/antimatter are legitimate, must not warn.
        doc = ("## [Landmarks](landmarks)\n### [X](x)\n---\n"
               "Kind: antimatter\nAt: 3, 4\n---\nbody\n")
        self.assertEqual(_by_code(amd_lint(content=doc), "unknown-enum-value"), [])

    def test_bad_scan_tab_warns(self):
        doc = ("## [Science](science)\n### [Hull](hull)\n---\n"
               "Scan of: derelict\nTab: scna\n---\n% wreck\n")
        # Both the scan-label pass and the schema pass can catch this; assert at
        # least the schema value-check fires with the right value.
        bad = _by_code(amd_lint(content=doc), "unknown-enum-value")
        self.assertTrue(any("scna" in f.message for f in bad))


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

    def test_prebuilt_source_index_gives_identical_findings(self):
        """A whole-mission run derives the MAST route/emit sets ONCE and passes them to
        every file's lint. That shortcut must not change a single finding - it is the
        difference between one scan of the mission's .mast and one scan per .amd."""
        from sbs_utils.procedural.amd_lint import mast_source_index
        doc = ("# [Root](root)\n## [Jobs](jobs)\n"
               "### [Q](q)\n---\nGoal: signal never_emitted\nWhen: signal briefed\n---\nb\n"
               "### [R](r)\n---\nThen: signal orphaned\n---\nb\n")
        mast = ['signal_emit("quest_signal", {"SIGNAL_NAME": "briefed"})\n',
                '//signal/orphaned\n    pass\n']
        slow = amd_lint(content=doc, mast_sources=mast)
        fast = amd_lint(content=doc, mast_sources=mast,
                        source_index=mast_source_index(mast))
        self.assertEqual([(f.line, f.code, f.message) for f in slow],
                         [(f.line, f.code, f.message) for f in fast])
        self.assertTrue(any(f.code == "unfired-signal" for f in fast))

    def test_goal_signal_is_checked_like_when_signal(self):
        # `Goal: signal [N] X` completes a job, so an X nothing emits is an
        # unfinishable job - the same defect `When: signal X` already reported.
        doc = ("# [Root](root)\n## [Jobs](jobs)\n### [Q](q)\n"
               "---\nGoal: signal 4 never_emitted\n---\nbody\n")
        f = _by_code(amd_lint(content=doc, mast_sources=["// empty mast\n"]), "unfired-signal")
        self.assertEqual(len(f), 1)

    def test_wait_signal_satisfied_by_quest_credit_signal(self):
        # quest_credit_signal()/quest_on_signal() advance a quest DIRECTLY, without
        # ever calling signal_emit - so they count as emitting the name.
        doc = ("# [Root](root)\n## [Jobs](jobs)\n### [Q](q)\n"
               "---\nGoal: signal 4 customs_cleared\n---\nbody\n")
        mast = ['    quest_credit_signal(COMMS_ORIGIN_ID, "customs_cleared")\n']
        self.assertEqual(_by_code(amd_lint(content=doc, mast_sources=mast), "unfired-signal"), [])
        mast = ['    quest_on_signal("customs_cleared")\n']
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
    """Scan-vocabulary check - a typo'd `Tab:` is silently swallowed and never renders. Only
    the dialogue-native `Scan of:` fence is a scan fence (the flat form was retired)."""

    def test_dialogue_native_bad_tab_flagged(self):
        doc = ("# [Hull](hull)\n---\nScan of: wreck\nTab: scna\n---\n% Wreckage.\n")
        f = _by_code(amd_lint(content=doc, cross_file=False), "unknown-scan-tab")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0].line, 4)   # the Tab: line

    def test_dialogue_native_good_tab_clean(self):
        doc = ("# [Hull](hull)\n---\nScan of: wreck\nTab: mat\n---\n% Salvage: 1.3 kt.\n")
        self.assertEqual(_by_code(amd_lint(content=doc, cross_file=False), "unknown-scan-tab"), [])

    def test_default_tab_clean(self):
        # `Scan of:` with no `Tab:` defaults to the scan tab - not a typo, no finding
        doc = ("# [Hull](hull)\n---\nScan of: wreck\n---\n% Wreckage.\n")
        self.assertEqual(_by_code(amd_lint(content=doc, cross_file=False), "unknown-scan-tab"), [])

    def test_lone_scan_named_label_not_treated_as_scan(self):
        # a fence whose only label collides with a tab name (e.g. a rumor reveal `Intel:`) is
        # NOT a scan fence - with the flat form retired, the linter never guesses from tab names
        doc = ("# [Rumor](r)\n---\nIntel: The tip was solid.\n---\nWord on the dock.\n")
        self.assertEqual(_by_code(amd_lint(content=doc, cross_file=False), "unknown-scan-tab"), [])
        self.assertEqual(_by_code(amd_lint(content=doc, cross_file=False), "unknown-scan-label"), [])


class TestFenceSyntaxDiagnostics(unittest.TestCase):
    """The reader collects its complaints in a writer's terms; until this pass
    existed nothing ever asked for them, so they were all thrown away."""

    def test_a_colonless_fence_line_is_reported_at_its_real_line(self):
        doc = ("# [A](a)\n"
               "---\n"
               "State: active\n"
               "Colour red\n"          # line 4 - no colon
               "---\n"
               "body\n")
        found = _by_code(amd_lint(content=doc), "fence-syntax")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].line, 4)          # FILE line, not block line
        self.assertIn("Label: value", found[0].message)
        self.assertTrue(found[0].is_error())

    def test_a_misplaced_kind_line_says_where_it_belongs(self):
        doc = "# [A](a)\n---\nState: active\nCharacters\n---\nbody\n"
        found = _by_code(amd_lint(content=doc), "fence-syntax")
        self.assertEqual(len(found), 1)
        self.assertIn("first line", found[0].message)

    def test_a_clean_fence_reports_nothing(self):
        doc = "# [A](a)\n---\nCharacters\nColor: #07F\n---\nbody\n"
        self.assertEqual(_by_code(amd_lint(content=doc), "fence-syntax"), [])


class TestUnknownFieldDiagnostics(unittest.TestCase):
    """Growth rule 1: an unknown field is kept and never fatal - but the author
    is told, because silence is how a typo survives."""

    def test_an_unknown_field_warns_when_the_kind_is_known(self):
        doc = ("# [Doc](doc)\n## [Jobs](jobs)\n### [Sweep](sweep)\n"
               "---\nState: active\nPayz: 200 credits\n---\nbody\n")
        found = _by_code(amd_lint(content=doc), "unknown-field")
        self.assertEqual(len(found), 1)
        self.assertIn("Payz", found[0].message)
        self.assertFalse(found[0].is_error())      # warning, never fatal

    def test_a_declared_field_is_silent(self):
        doc = ("# [Doc](doc)\n## [Jobs](jobs)\n### [Sweep](sweep)\n"
               "---\nState: active\nPays: 200 credits\n---\nbody\n")
        self.assertEqual(_by_code(amd_lint(content=doc), "unknown-field"), [])

    def test_a_renamed_spelling_is_silent(self):
        # `Goal:` is an alias of `Done when:` - a rename must not create warnings
        doc = ("# [Doc](doc)\n## [Jobs](jobs)\n### [Sweep](sweep)\n"
               "---\nGoal: signal x\nStarts when: signal y\n---\nbody\n")
        self.assertEqual(_by_code(amd_lint(content=doc), "unknown-field"), [])

    def test_nested_block_keys_are_not_fields(self):
        # a recipe's Properties/Defaults inner names belong to the mission
        doc = ("# [Doc](doc)\n## [Recipes](recipes)\n### [Bio](bio)\n"
               "---\nOutput: Beacon\nProperties:\n  Monster: 'x'\n  Mode: 'y'\n---\nb\n")
        self.assertEqual(_by_code(amd_lint(content=doc), "unknown-field"), [])

    def test_nothing_is_flagged_when_the_kind_is_unknown(self):
        # with no archetype there is nothing to be unknown against
        doc = "# [A](a)\n---\nWibble: 3\n---\nbody\n"
        self.assertEqual(_by_code(amd_lint(content=doc), "unknown-field"), [])


if __name__ == "__main__":
    unittest.main()


class TestUnknownFieldHonorsTraits(unittest.TestCase):
    """`Also:` lends a record its trait's fields - the linter has to know that too, or
    the trait mechanism works everywhere except in the tool that reports on it."""

    def _unknown(self, src):
        from sbs_utils.procedural.amd_lint import amd_lint
        return [f.message for f in amd_lint(content=src, cross_file=False)
                if f.code == "unknown-field"]

    WORLDLET = """# [Universe](u)

## [Landmarks](landmarks)

### [Cinder World](cinder)
---
Also: economy
Yields: ore 8
Reserve: 4000
---
"""

    def test_a_claimed_trait_declares_its_fields(self):
        self.assertEqual(self._unknown(self.WORLDLET), [])

    def test_without_the_claim_they_are_still_unknown(self):
        found = self._unknown(self.WORLDLET.replace("Also: economy\n", ""))
        self.assertEqual(len(found), 2)
        self.assertTrue(any("Yields" in m for m in found))
