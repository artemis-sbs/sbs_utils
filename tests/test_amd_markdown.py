"""AMD records as Markdown (procedural.amd_markdown).

One emitter feeds both the mkdocs pages and the standalone HTML site, so a bug here
is a bug in both - which is the point of there being one. These tests hold the two
properties that a renderer silently loses:

  * the PLAYER profile is a hard filter. An author note or a choice's outcome must be
    ABSENT from the bytes, because "view source" and the rendered page have to agree
    about what a player was told;
  * a fact table must publish the word an author should TYPE and the value the file
    actually SAYS - which are two different sources, and getting either from the wrong
    one publishes something false.

Fixtures are Python strings, not checked-in .amd files: a committed fixture's bytes
depend on `autocrlf`, so a test asserting on them asserts on whatever git handed the
machine (see tests/amd_corpus.py).
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural import amd_blocks, amd_core, amd_markdown as M

SOURCE = """\
# [The Reach](reach)
---
Display: The Reach
Color: #cc2244
---
A lane of cold water between two lanterns. See [[warlord]] for the trouble.

= An author note nobody in the fiction can hear.

> [!warning] Mind the gap
> The lane narrows here.

@warlord (comms)
% Turn back.
% You should not have come.

- [Pay the toll](warlord) if credits > 200; signal toll_paid

# [Warlord](warlord)
---
Quest
Goal: destroy 1 warlord
Parent: reach
Difficulty: +1
Required: true
---
A raider warlord. Underscores like enemies_low must survive, and *asterisks*.

- a bullet
- another

<hr>
<br>

> INT. BRIDGE - NIGHT

(the lights dim)

| Hull | Count |
|---|---|
| kralien | 2 |

=$raider red, white
[hull]: image://kralien_dreadnought

## [Detail](detail)
---
Quest
---
Nested under the warlord.

![[reach]]

[Back to the Reach](ref://reach)

[](style://font:gui-6)

[art](image://ball)
"""


def _doc(text=SOURCE, rel="maps/bosses/warlord.amd"):
    doc = amd_core.parse(text)
    doc.rel_path = rel
    return doc


def _render(text=SOURCE, profile="author", rel="maps/bosses/warlord.amd"):
    pages = M.amd_markdown_site([_doc(text, rel)])
    ctx = M.amd_markdown_context(pages, pages[0], profile=profile)
    return M.amd_markdown_page(pages[0], ctx), ctx


class TestThePageModel(unittest.TestCase):
    def test_one_file_is_one_page(self):
        pages = M.amd_markdown_site([_doc()])
        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0]["path"], "maps/bosses/warlord.md")

    def test_every_record_is_an_anchor_on_it(self):
        # `{: #id}`, not `{#id}` - attr_list reads both identically, but mkdocs runs
        # pages through the macros plugin first and Jinja reads a bare `{#` as the start
        # of a comment. Every generated heading used to open one that never closed, so
        # every site build logged a macro error per records page.
        out, _ = _render()
        for anchor in ("{: #reach}", "{: #warlord}", "{: #warlord-detail}"):
            self.assertIn(anchor, out)
        self.assertNotIn("{#", out, "a bare {# is a Jinja comment opener")

    def test_anchors_come_from_the_path_not_the_key(self):
        # Bare keys repeat across the corpus (40 of 374); `path_of` does not.
        pages = M.amd_markdown_site([_doc()])
        anchors = [M.amd_markdown_anchor(n) for n in pages[0]["nodes"]]
        self.assertEqual(len(anchors), len(set(anchors)))
        self.assertIn("warlord-detail", anchors)

    def test_a_lone_titled_root_owns_the_h1(self):
        one = "# [Solo](solo)\n---\nQuest\n---\nBody.\n"
        out, _ = _render(one, rel="solo.amd")
        self.assertEqual(out.splitlines()[0], "# Solo {: #solo}")
        self.assertEqual(out.count("\n# "), 0)   # no second h1

    def test_several_roots_get_a_synthetic_h1_and_become_h2(self):
        # 7 one-line hails or 4 bar patrons have no single record that IS the page.
        two = ("# [A](a)\n---\nQuest\n---\nFirst.\n\n"
               "# [B](b)\n---\nQuest\n---\nSecond.\n")
        out, _ = _render(two, rel="raider_hails.amd")
        self.assertEqual(out.splitlines()[0], "# Raider Hails")
        self.assertIn("## A {: #a}", out)
        self.assertIn("## B {: #b}", out)

    def test_a_split_is_declared_never_inferred(self):
        # A record-count threshold would silently change a page's URL the day a file
        # grows past it.
        pages = M.amd_markdown_site([_doc()], layout={"split": ["maps/bosses/warlord.amd"]})
        self.assertGreater(len(pages), 1)
        self.assertEqual(pages[0]["path"], "maps/bosses/warlord/index.md")

    def test_children_are_never_inlined_into_their_parent(self):
        # The in-game reader shows a record's OWN body only; a page that inlined the
        # subtree would say the same words twice.
        out, _ = _render()
        self.assertEqual(out.count("Nested under the warlord."), 1)


class TestFacts(unittest.TestCase):
    def test_the_label_is_the_word_an_author_should_type(self):
        # The file says `Goal:` and `Parent:`; both are retired spellings. A table that
        # echoed them would teach the words the rename existed to remove.
        out, _ = _render()
        self.assertIn("| Done when |", out)
        self.assertIn("| Part of |", out)
        self.assertNotIn("| Goal |", out)
        self.assertNotIn("| Parent |", out)

    def test_the_value_is_what_the_file_actually_says(self):
        # `Difficulty: +1` parses to the integer 1, losing relative-vs-absolute - the
        # only distinction the field exists to make. Values come from the source lines.
        out, _ = _render()
        self.assertIn("+1", out)
        self.assertNotIn("| Difficulty | 1 |", out)

    def test_the_bare_kind_line_is_not_a_fact(self):
        out, _ = _render()
        self.assertNotIn("| Quest |", out)

    def test_facts_follow_the_schemas_order_not_the_files(self):
        out, _ = _render()
        body = [r for r in out.splitlines() if r.startswith("| ")]
        labels = [r.split("|")[1].strip() for r in body]
        self.assertLess(labels.index("Done when"), labels.index("Part of"))

    def test_a_record_with_no_fence_has_no_table(self):
        out, _ = _render("# [Bare](bare)\nJust prose.\n", rel="bare.amd")
        self.assertNotIn("| Fact |", out)

    def test_the_kind_is_inferred_when_the_record_does_not_declare_one(self):
        """Most records never write a bare kind line.

        A beat under `## Narrative` is a quest because of the words in its fence, and
        reading `__kind__` alone leaves the archetype None for every one of those -
        which silently switches the whole typed layer off for the records that make up
        most of a story. `State:` stays `State:` instead of `At start:`, and
        `Then: reveal x` renders as flat text instead of a link to x."""
        source = ("# [Narrative](narrative)\n\n"
                  "## [A Cold Lane](beat_1)\n"
                  "---\n"
                  "Scope: shared\n"
                  "State: active\n"
                  "Done when: reach -4, 2\n"
                  "Then: reveal beat_2\n"
                  "---\n"
                  "Prose.\n\n"
                  "## [Ash on the Manifest](beat_2)\n"
                  "---\n"
                  "Scope: shared\n"
                  "---\n"
                  "More prose.\n")
        out, _ = _render(source, rel="story.amd")
        self.assertIn("| At start |", out)          # canonicalized
        self.assertNotIn("| State |", out)
        self.assertIn("`reveal` [Ash on the Manifest](#narrative-beat-2)", out)


class TestThePlayerProfile(unittest.TestCase):
    """A hard filter, not a stylesheet class."""

    def test_the_author_note_is_absent_from_the_bytes(self):
        author, _ = _render(profile="author")
        player, _ = _render(profile="player")
        self.assertIn("author note nobody in the fiction", author)
        self.assertNotIn("author note nobody in the fiction", player)

    def test_a_choices_machinery_is_absent(self):
        player, _ = _render(profile="player")
        self.assertIn("Pay the toll", player)      # the words the player read
        self.assertNotIn("toll_paid", player)      # the outcome they did not
        self.assertNotIn("credits > 200", player)  # nor the guard


class TestBlocks(unittest.TestCase):
    def test_every_block_type_renders_something(self):
        # Catches "a new block type was added and this module silently drops it" -
        # which loses authored content with nothing to say it went.
        known = set(M._BLOCKS) | set(M.SILENT)
        produced = set()
        for node in _doc().nodes:
            for b in amd_blocks.amd_blocks(node, doc=None):
                produced.add(b["type"])
        self.assertTrue(produced)
        self.assertLessEqual(produced, known,
                             f"unhandled block type(s): {produced - known}")
        ctx = M.amd_markdown_context([{"path": "x.md", "nodes": []}],
                                     {"path": "x.md", "nodes": []})
        for kind in produced - set(M.SILENT):
            for node in _doc().nodes:
                for b in amd_blocks.amd_blocks(node, doc=None):
                    if b["type"] == kind:
                        self.assertTrue(M._block(b, ctx, 0).strip(),
                                        f"{kind} rendered empty")
                        break

    def test_engine_styling_renders_to_nothing(self):
        # `[](style:font:gui-6)` is a font name, not art. Treating these as pictures
        # printed three "an image goes here" placeholders into the shipped corpus.
        ctx = M.amd_markdown_context([{"path": "x.md", "nodes": []}],
                                     {"path": "x.md", "nodes": []})
        for kind in ("style", "style_ref", "media_def", "break"):
            self.assertEqual(M._block({"type": kind}, ctx, 0), "")

    def test_a_callout_becomes_a_material_admonition(self):
        # Material does not parse the GitHub `> [!WARNING]` form AMD is authored in;
        # left alone it renders as a blockquote with a stray marker in it.
        out, _ = _render()
        self.assertIn('!!! warning "Mind the gap"', out)
        self.assertNotIn("[!warning]", out)

    def test_several_speech_variants_are_alternatives_not_tabs(self):
        # Tabs say the reader chooses; these say the engine rolls. Different claim.
        out, _ = _render()
        self.assertIn("> *One of:*", out)
        self.assertIn("> - Turn back.", out)

    def test_a_cue_names_the_speaker_and_the_surface(self):
        out, _ = _render()
        self.assertIn("**WARLORD** *(comms)*", out)

    def test_a_choice_bolds_the_label_and_links_the_target(self):
        # The label is what the player read; the target is machinery. Making the label
        # the link text says the words themselves lead somewhere.
        out, _ = _render()
        self.assertIn("**Pay the toll**", out)
        self.assertNotIn("[Pay the toll](warlord)", out)


class TestLinks(unittest.TestCase):
    def test_a_wikilink_becomes_a_real_link(self):
        out, _ = _render()
        self.assertIn("[Warlord](#warlord)", out)

    def test_an_unresolved_target_is_plain_text_and_is_reported(self):
        # A link to a record this build did not emit is a 404. `mkdocs build --strict`
        # would fail on it, which is exactly the right outcome for a REAL dangling
        # reference and the wrong one for a MAST label that simply is not an AMD node.
        out, ctx = _render("# [A](a)\n---\nQuest\n---\nSee [[nowhere]].\n", rel="a.amd")
        self.assertNotIn("](", out)
        self.assertIn("nowhere", ctx["dangling"])

    def test_an_injected_link_that_returns_None_degrades_to_text(self):
        pages = M.amd_markdown_site([_doc()])
        ctx = M.amd_markdown_context(pages, pages[0], link=lambda n, c: None)
        out = M.amd_markdown_page(pages[0], ctx)
        self.assertNotIn("](#", out)
        self.assertIn("Warlord", out)

    def test_the_injected_link_is_the_only_thing_the_two_sites_differ_by(self):
        # The HTML site does not get its own emitter; it renders THIS markdown. So a
        # divergence between the two can only come through `link`/`media`.
        pages = M.amd_markdown_site([_doc()])
        md = M.amd_markdown_page(pages[0], M.amd_markdown_context(pages, pages[0]))
        html = M.amd_markdown_page(
            pages[0], M.amd_markdown_context(
                pages, pages[0],
                link=lambda n, c: "#" + M.amd_markdown_anchor(n)))
        self.assertEqual(md, html)

    def test_a_cross_page_link_is_relative_to_the_current_page(self):
        a, b = _doc(rel="deep/one.amd"), _doc(rel="two.amd")
        # give the second document a distinct key so the first can point at it
        pages = M.amd_markdown_site([a, b])
        ctx = M.amd_markdown_context(pages, pages[0])
        href = M.amd_markdown_href(pages[1]["nodes"][0], ctx)
        self.assertTrue(href.startswith("../"), href)


class TestEscaping(unittest.TestCase):
    def test_prose_punctuation_survives_a_round_trip(self):
        out, _ = _render()
        self.assertIn(r"\*asterisks\*", out)

    def test_an_intra_word_underscore_is_left_alone(self):
        # Over-escaping is not free: these files are committed, diffed and read by
        # people, and `enemies\_low` renders right while making the source unreadable.
        out, _ = _render()
        self.assertIn("enemies_low", out)
        self.assertNotIn(r"enemies\_low", out)

    def test_a_leading_marker_is_escaped_but_a_signed_number_is_not(self):
        self.assertEqual(M._esc("- item"), r"\- item")
        self.assertEqual(M._esc("+1"), "+1")
        self.assertEqual(M._esc("-3 degrees"), "-3 degrees")

    def test_a_pipe_cannot_break_a_table_row(self):
        rows = [("A", "B"), ("x|y", "z")]
        self.assertIn(r"x\|y", M._table(rows))

    def test_a_heading_in_prose_cannot_become_a_heading(self):
        self.assertEqual(M._esc("# not a heading"), r"\# not a heading")
        self.assertEqual(M._esc("#5 in the list"), "#5 in the list")


class TestIdempotence(unittest.TestCase):
    def test_rendering_twice_gives_the_same_bytes(self):
        # The generated pages are committed, so a renderer that varies run to run
        # produces a diff on every regeneration and nobody reads them any more.
        first, _ = _render()
        second, _ = _render()
        self.assertEqual(first, second)

    def test_the_page_ends_with_exactly_one_newline(self):
        out, _ = _render()
        self.assertTrue(out.endswith("\n"))
        self.assertFalse(out.endswith("\n\n"))


if __name__ == "__main__":
    unittest.main()
