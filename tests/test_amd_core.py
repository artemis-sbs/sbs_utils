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


if __name__ == "__main__":
    unittest.main()
