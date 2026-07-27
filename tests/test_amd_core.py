"""amd_core - the span-tracking AMD parser behind the linter (and future tooling).

Covers the tree/level/parent shape, node + reference spans, and path resolution.
`test_set_exe_dir()` is required at module scope for `unittest discover`.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from sbs_utils.procedural.amd_core import parse


class TestTree(unittest.TestCase):
    def test_keys_levels_parents(self):
        doc = parse("# [Root](root)\n## [Child](child)\nbody\n### [Deep](deep)\nb\n")
        self.assertEqual(doc.keys, {"root", "child", "deep"})
        child = next(n for n in doc.nodes if n.key == "child")
        deep = next(n for n in doc.nodes if n.key == "deep")
        self.assertEqual(child.level, 2)
        self.assertEqual(child.parent.key, "root")
        self.assertEqual(deep.parent.key, "child")

    def test_node_span_is_heading_line(self):
        doc = parse("# [Root](root)\n## [Child](child)\n")
        child = next(n for n in doc.nodes if n.key == "child")
        self.assertEqual(child.span.line, 2)
        self.assertEqual(child.span.col, 0)

    def test_query_params(self):
        doc = parse("# [Root](root?scale=2&color=red)\n")
        root = next(n for n in doc.nodes if n.key == "root")
        self.assertEqual(root.query, {"scale": "2", "color": "red"})


class TestPathResolves(unittest.TestCase):
    def test_valid_and_invalid_paths(self):
        doc = parse("# [R](r)\n## [Arc](arc)\n### [Scan](scan)\nb\n")
        self.assertTrue(doc.path_resolves("arc/scan"))
        self.assertTrue(doc.path_resolves("arc"))
        self.assertFalse(doc.path_resolves("arc/nope"))
        self.assertFalse(doc.path_resolves("scan/arc"))  # right keys, wrong order


class TestRefs(unittest.TestCase):
    def test_choice_ref_span(self):
        doc = parse("# [R](r)\n## [D](d)\n### [A](a)\n% hi\n- [go](b)\n")
        choice = next(r for r in doc.refs if r.kind == "choice")
        self.assertEqual(choice.value, "b")
        self.assertEqual(choice.owner, "a")
        self.assertEqual((choice.span.line, choice.span.col), (5, 7))

    def test_data_refs_scene_reveal_reach_at(self):
        doc = parse(
            "# [R](r)\n"
            "## [L](lifeforms)\n### [S](s)\n---\nScene: talk\n---\nb\n"
            "## [N](narrative)\n### [Go](go)\n---\nWhen: reach 2, -1\nThen: reveal go2\n---\nb\n"
            "#### [Go2](go2)\nb\n"
            "## [Lm](landmarks)\n### [Site](site)\n---\nAt: 2, -1\n---\nb\n"
        )
        kinds = {r.kind for r in doc.refs}
        self.assertTrue({"scene", "reach", "reveal", "at"} <= kinds)
        reach = next(r for r in doc.refs if r.kind == "reach")
        self.assertEqual(reach.value, (2, -1))
        self.assertIn((2, -1), doc.landmark_cells)


class TestPathIndexAndAmbiguity(unittest.TestCase):
    """Keys are not unique - 40 of the corpus's 374 repeat, three within one file.
    The path is the unambiguous name."""

    # two jobs, each with a step called `recover` - exactly the real shape in
    # LegendaryMissions/maps/peacetime_remastered.amd
    SRC = ("# [Doc](doc)\n"
           "## [Jobs](jobs)\n"
           "### [Florbin](florbin)\n---\nState: active\n---\np\n"
           "#### [Recover Florbin](recover)\n---\nTier: 1\n---\np\n"
           "### [Cache](job_cache)\n---\nState: active\n---\np\n"
           "#### [Recover Cache](recover)\n---\nTier: 2\n---\np\n")

    def setUp(self):
        self.doc = parse(self.SRC)

    def test_path_of_names_a_record_exactly(self):
        from sbs_utils.procedural.amd_core import path_of
        paths = sorted(path_of(n) for n in self.doc.nodes)
        self.assertIn("doc/jobs/florbin/recover", paths)
        self.assertIn("doc/jobs/job_cache/recover", paths)

    def test_path_resolves_walks_real_parents(self):
        # the regression that made `sbs lint` report a FALSE error: the flat
        # parent_of map keeps only the LAST node for a repeated key
        self.assertTrue(self.doc.path_resolves("florbin/recover"))
        self.assertTrue(self.doc.path_resolves("job_cache/recover"))
        self.assertFalse(self.doc.path_resolves("nosuch/recover"))
        target = self.doc.resolve_target("florbin/recover")
        self.assertEqual(target.parent.key, "florbin")
        self.assertEqual(target.display, "Recover Florbin")

    def test_duplicates_are_reported(self):
        self.assertEqual(sorted(self.doc.duplicates), ["recover"])
        self.assertEqual(len(self.doc.nodes_for("recover")), 2)

    def test_bare_key_is_ambiguous_and_does_not_guess(self):
        self.assertTrue(self.doc.is_ambiguous("recover"))
        self.assertIsNone(self.doc.resolve_target("recover"))
        self.assertFalse(self.doc.is_ambiguous("florbin"))

    def test_bare_key_resolves_relatively_from_the_referring_node(self):
        # nearest scope first, which is what makes short step names correct
        florbin = self.doc.by_path["doc/jobs/florbin"]
        cache = self.doc.by_path["doc/jobs/job_cache"]
        self.assertEqual(self.doc.resolve_target("recover", from_node=florbin).display,
                         "Recover Florbin")
        self.assertEqual(self.doc.resolve_target("recover", from_node=cache).display,
                         "Recover Cache")


class TestKindResolution(unittest.TestCase):
    def test_kind_line_inherits_from_the_section(self):
        doc = parse("# [Doc](doc)\n## [Crew](crew)\n---\nCharacters\n---\n"
                             "### [Ana](ana)\n---\nColor: #07F\n---\np\n")
        self.assertEqual(doc.by_key["ana"].kind, "lifeform")

    def test_section_name_resolves_without_any_kind_line(self):
        # the common path: the section is already NAMED for what it holds
        doc = parse("# [Doc](doc)\n## [Landmarks](landmarks)\n"
                             "### [Ruin](ruin)\n---\nAt: 2, -1\n---\np\n")
        self.assertEqual(doc.by_key["ruin"].kind, "landmark")

    def test_a_record_may_override_its_section(self):
        doc = parse("# [Doc](doc)\n## [Crew](crew)\n---\nCharacters\n---\n"
                             "### [Ruin](ruin)\n---\nLandmark\nAt: 2, -1\n---\np\n")
        self.assertEqual(doc.by_key["ruin"].kind, "landmark")


if __name__ == "__main__":
    unittest.main()
