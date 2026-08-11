"""amd_render - AMD -> a printable HTML document.

These are STRUCTURAL assertions, not golden HTML. A golden page would fail on
every CSS tweak while catching nothing, so what is pinned here is what has to be
true of any rendering:

  * every `href="#x"` has a matching `id="x"` - a printed contents list that
    points at nothing is worse than no contents list, and each lens renders a
    different SUBSET of records, so this is easy to get wrong per lens;
  * tags balance - a stray unclosed `<div>` silently swallows the rest of a book;
  * text from the document cannot become markup;
  * `player` is a HARD filter: the withheld text must be ABSENT from the bytes,
    because "print to PDF" and "view source" have to agree.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest
from html.parser import HTMLParser

from sbs_utils.procedural.amd_core import parse
from sbs_utils.procedural.amd_render import LENSES, amd_render_html

_VOID = {"br", "hr", "img", "meta", "link", "input", "area", "base", "col",
         "embed", "param", "source", "track", "wbr",
         "path", "circle", "line", "text", "svg"}


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


def check(html_text):
    d = _Doc()
    d.feed(html_text)
    return d


# One record of every shape the lenses select on, in one document.
SOURCE = """\
# [The Silver Reach](reach)
---
Universe
Display: The Silver Reach
---
= the reach is a trap, and the Combine knows it
A ribbon of frontier stars beyond the last patrol line.

## [Sides](sides)

### [The Lantern Combine](lantern)
---
Color: #ffcc44
Disposition: neutral
Home: -4, 2
---
Convoy families who keep the freight lanes lit.

## [Jobs](jobs)

### [Convoy Escort](escort)
---
Scope: shared
State: active
Reward: 260 credits
Done when: signal convoy_safe
---
See the convoy safe to port.

## [Talk](talk)

### [Lantern Welcome](hail)
---
Speaker: lantern
When: comms
---
% Well met, captain.
%{standing < -20} You again.

- [Trade a kind word](warm) if standing > 0 ; earns lantern kind 5
- [Move along](bye)

### [A Warm Word](warm)
---
Speaker: lantern
---
% Kindness costs nothing out here.

### [Goodbye](bye)
---
Speaker: lantern
---
% Safe travels.
"""


def render(lens="prose", profile="author", source=SOURCE):
    doc = parse(source, file_path="reach.amd")
    return amd_render_html([("reach.amd", doc)], lens=lens, profile=profile,
                           title="Test")


class TestEveryLensIsWellFormed(unittest.TestCase):
    def test_tags_balance(self):
        for lens in LENSES:
            with self.subTest(lens=lens):
                d = check(render(lens))
                self.assertEqual(d.unbalanced, [], f"{lens}: unbalanced tags")
                self.assertEqual(d.stack, [], f"{lens}: left open")

    def test_no_anchor_dangles(self):
        # The contents list is built from the ids the body EMITTED, so a lens
        # that renders a subset cannot link to what it left out.
        for lens in LENSES:
            with self.subTest(lens=lens):
                d = check(render(lens))
                missing = sorted({h for h in d.hrefs if h not in d.ids})
                self.assertEqual(missing, [], f"{lens}: dangling anchors")

    def test_each_lens_selects_what_it_should(self):
        self.assertIn("Convoy Escort", render("prose"))
        # The catalog takes only records that HAVE a fence.
        catalog = render("catalog")
        self.assertIn("The Lantern Combine", catalog)
        self.assertNotIn(">Sides<", catalog)
        # The screenplay takes what is spoken - and nothing else.
        script = render("screenplay")
        self.assertIn("Well met, captain.", script)
        self.assertNotIn("freight lanes lit", script)

    def test_a_color_field_becomes_a_swatch(self):
        # The whole reason the catalog lens exists: the fence is the content, so
        # a field renders as its TYPE rather than as the line it was typed as.
        self.assertIn("#ffcc44", render("catalog"))
        self.assertIn('class="swatch"', render("catalog"))


class TestEscaping(unittest.TestCase):
    NASTY = ('# [<script>alert(1)</script>](x)' + chr(10)
             + 'and <img src=z onerror=alert(2)> in the body' + chr(10))

    def test_document_text_cannot_become_markup(self):
        for lens in ("prose", "catalog", "screenplay", "bible"):
            with self.subTest(lens=lens):
                out = render(lens, source=self.NASTY)
                self.assertNotIn("<script", out)
                self.assertNotIn("<img", out)

    def test_the_escaped_text_still_reads_as_prose(self):
        # Escaping must neuter the markup without eating the sentence. Only
        # the prose lens prints bodies, so only it can be asked this - and a
        # test that renders NOTHING would pass the assertions above for the
        # wrong reason, so this is the one that proves they mean something.
        out = render("prose", source=self.NASTY)
        self.assertIn("&lt;img", out)
        self.assertIn("in the body", out)


class TestAnchorsArePathBased(unittest.TestCase):
    def test_a_repeated_key_gets_distinct_ids(self):
        # Bare keys are not unique - 40 of the corpus's 374 repeat, and one file
        # holds three `recover` records. Anchors are paths for that reason.
        src = ("# [A](a)\n## [Recover](recover)\nfirst\n"
               "# [B](b)\n## [Recover](recover)\nsecond\n")
        d = check(render("prose", source=src))
        recovers = [i for i in d.ids if i.endswith("recover")]
        self.assertEqual(len(recovers), 2, f"ids: {sorted(d.ids)}")


class TestPlayerProfile(unittest.TestCase):
    """Absent, not hidden."""

    def test_author_only_text_is_not_in_the_bytes(self):
        player = render("screenplay", profile="player")
        for secret in ("the reach is a trap",      # the `= ` synopsis
                       "standing &gt; 0",          # a choice guard
                       "standing &lt; -20",        # a speech gate
                       "earns lantern kind 5"):    # a choice outcome
            self.assertNotIn(secret, player, f"leaked: {secret}")

    def test_the_author_edition_still_has_all_of_it(self):
        author = render("screenplay")
        self.assertIn("earns lantern kind 5", author)
        self.assertIn("standing &gt; 0", author)

    def test_player_keeps_what_a_player_read(self):
        player = render("screenplay", profile="player")
        self.assertIn("Well met, captain.", player)
        self.assertIn("Trade a kind word", player)

    def test_machinery_fields_are_dropped_from_a_player_catalog(self):
        # `Done when:` normalizes to `Goal` - the label the schema produces,
        # which is what a reader actually sees on the page.
        self.assertNotIn("Goal", render("catalog", profile="player"))
        self.assertIn("Goal", render("catalog"))

    def test_the_bible_refuses_a_player_profile(self):
        # Not styling. The bible exists to show the machine.
        with self.assertRaises(ValueError) as cm:
            render("bible", profile="player")
        self.assertIn("bible IS the spoiler", str(cm.exception))


class TestBible(unittest.TestCase):
    def test_it_reports_the_shape_and_the_wiring(self):
        out = render("bible")
        self.assertIn("records", out)
        self.assertIn("Beat 1", out)
        self.assertIn("<svg", out)      # the graph, laid out by beat rank

    def test_a_trigger_is_shown(self):
        self.assertIn("convoy_safe", render("bible"))


class TestFaces(unittest.TestCase):
    """A face has no file, but it is not unresolvable - it names cells of a
    race atlas. `face.js` is the canonical compositor and is REUSED here, so
    what these pin is the seam, not a second implementation."""

    FACE = '# [Cast](cast)' + chr(10) + '![](face://arv #ffffff 0 0;arv #ffffff 0 2)' + chr(10)

    class _Atlas:
        """Stands in for MissionAssets without needing an engine install."""
        def media(self, block):
            return None

        def face_sheets(self, specs):
            return {'Arvonian': 'data:image/png;base64,AA'}

    def test_a_face_becomes_a_canvas_the_compositor_paints(self):
        doc = parse(self.FACE, file_path='cast.amd')
        out = amd_render_html([('cast.amd', doc)], assets=self._Atlas())
        self.assertIn("canvas class=&quot;face&quot;".replace("&quot;", chr(34)), out)
        self.assertIn("FaceRender", out)
        # `.art-missing` is always DEFINED in the stylesheet; what matters
        # is that no placeholder was USED.
        self.assertNotIn(chr(62) + "a face" + chr(60), out)

    def test_without_the_compositor_a_face_placeholds_instead(self):
        # cosmos_dev is dev-only and never ships in a mission .sbslib, so a
        # packaged deployment can resolve the SHEETS and still have no
        # face.js. Emitting a canvas on the resolver alone left a blank box
        # with nothing to say something was meant to be in it.
        from sbs_utils.procedural import amd_assets
        real = amd_assets.face_js_path
        amd_assets.face_js_path = lambda: None
        try:
            doc = parse(self.FACE, file_path='cast.amd')
            out = amd_render_html([('cast.amd', doc)],
                                  assets=self._Atlas())
        finally:
            amd_assets.face_js_path = real
        self.assertNotIn("canvas class=", out)
        self.assertNotIn("FaceRender", out)
        self.assertIn(chr(62) + "a face" + chr(60), out)

    def test_no_faces_means_no_script_at_all(self):
        # The compositor is emitted only when there is something to composite.
        self.assertNotIn("<script", render("prose"))

    def test_the_face_string_travels_as_data_not_as_source(self):
        # It reaches the page in an escaped attribute and is read with
        # `dataset` - never built into the script, which is what keeps a
        # document from writing code.
        nasty = ('# [C](c)' + chr(10)
                 + '![](face://arv #fff 0 0");alert(1);//)' + chr(10))
        doc = parse(nasty, file_path='c.amd')
        out = amd_render_html([('c.amd', doc)], assets=self._Atlas())
        # The text survives - escaped - because it is DATA. What must not
        # exist is a raw quote that could close the attribute, and the
        # script must not carry the face string at all.
        self.assertIn("&quot;);alert", out)
        self.assertNotIn(chr(34) + ");alert", out)
        self.assertNotIn("alert", out.split("<script")[1])


class TestArguments(unittest.TestCase):
    def test_unknown_lens_and_profile_are_refused(self):
        doc = parse(SOURCE, file_path="reach.amd")
        with self.assertRaises(ValueError):
            amd_render_html([("reach.amd", doc)], lens="nope")
        with self.assertRaises(ValueError):
            amd_render_html([("reach.amd", doc)], profile="nope")

    def test_an_empty_document_still_renders(self):
        out = amd_render_html([("empty.amd", parse("", file_path="empty.amd"))])
        self.assertEqual(check(out).unbalanced, [])


if __name__ == "__main__":
    unittest.main()
