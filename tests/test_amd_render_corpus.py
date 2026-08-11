"""Every lens over every shipped `.amd`, as a net under the renderer.

The unit tests pin behavior against fixtures small enough to reason about. This
one asks a different question: does it survive the corpus? 615 records across
LegendaryMissions, OpenUniverse, StormsBeacon, HereThereBeMonsters, the test
ranges and the control gallery, written by hand over a long time, containing
every shape a fixture author would not think of.

It SKIPS when the sibling missions are not checked out, because sbs_utils is
cloned on its own often enough that a hard failure there would be noise rather
than signal - and skipping is honest, where quietly passing on zero files is not.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import glob
import os
import unittest
from html.parser import HTMLParser

from sbs_utils.procedural.amd_core import parse
from sbs_utils.procedural.amd_render import LENSES, amd_render_html

_VOID = {"br", "hr", "img", "meta", "link", "input", "area", "base", "col",
         "embed", "param", "source", "track", "wbr",
         "path", "circle", "line", "text", "svg"}

# sbs_utils sits beside the missions it serves.
_MISSIONS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def corpus():
    out = []
    for path in sorted(glob.glob(os.path.join(_MISSIONS, "*", "**", "*.amd"),
                                 recursive=True)):
        if os.sep + "__docs__" + os.sep in path:
            continue
        out.append(path)
    return out


class _Doc(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.ids, self.hrefs, self.unbalanced = [], set(), [], []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if d.get("id"):
            self.ids.add(d["id"])
        if d.get("href", "").startswith("#"):
            self.hrefs.append(d["href"][1:])
        if tag not in _VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in _VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            self.unbalanced.append(tag)
            if tag in self.stack:
                while self.stack and self.stack.pop() != tag:
                    pass
        else:
            self.stack.pop()


class TestCorpus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        paths = corpus()
        if len(paths) < 5:
            raise unittest.SkipTest(
                f"only {len(paths)} .amd files beside sbs_utils - the sibling "
                "missions are not checked out")
        cls.docs = []
        for path in paths:
            cls.docs.append((path, parse(None, file_path=path)))

    def test_every_lens_renders_the_whole_corpus(self):
        for lens in LENSES:
            for profile in ("author", "player"):
                if lens == "bible" and profile == "player":
                    continue        # refused by design
                with self.subTest(lens=lens, profile=profile):
                    html = amd_render_html(self.docs, lens=lens, profile=profile,
                                           title="Corpus")
                    d = _Doc()
                    d.feed(html)
                    self.assertEqual(d.unbalanced, [], f"{lens}/{profile}: unbalanced")
                    self.assertEqual(d.stack, [], f"{lens}/{profile}: left open")
                    missing = sorted({h for h in d.hrefs if h not in d.ids})
                    self.assertEqual(missing[:8], [],
                                     f"{lens}/{profile}: dangling anchors")

    def test_nothing_in_the_corpus_becomes_live_markup(self):
        # Every one of these files is hand-written prose. If any of it can reach
        # the page as a tag, so can anything.
        html = amd_render_html(self.docs, lens="prose", title="Corpus")
        for tag in ("<script", "<iframe", "<object", "onerror=", "onload="):
            self.assertNotIn(tag, html, f"live {tag} reached the page")


if __name__ == "__main__":
    unittest.main()
