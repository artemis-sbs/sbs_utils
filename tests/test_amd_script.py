"""The AMD body layer - synopsis, boneyard and inline `[[links]]`.

The body half of the format, borrowed from Fountain (a synopsis and cut text) and
Obsidian (inline links into a reference graph). The rule these all obey: **a body
line the grammar does not claim is prose, forever** - so every test here also
guards what must NOT change.

Both readers are exercised. `amd_core.parse` is the tooling model (spans, refs) and
`document_get_amd_file` is what the game actually renders; a feature that hides a
line from one and not the other is the exact bug this file exists to catch.
`test_set_exe_dir()` is required at module scope for `unittest discover`.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from sbs_utils.procedural.amd import (BoneyardScanner, amd_body_synopsis,
                                      amd_body_transition, amd_render_wikilinks,
                                      amd_wikilinks)
from sbs_utils.procedural.amd_callout import (_CALLOUT_KINDS, amd_callout_blocks,
                                              amd_callout_render)
from sbs_utils.procedural.amd_core import parse
from sbs_utils.procedural.amd_cutscene import amd_cutscenes
from sbs_utils.procedural.amd_dialogue import (amd_register_directions, dialogue_beats,
                                               dialogue_direction, dialogue_parse,
                                               dialogue_speakers)
from sbs_utils.procedural.amd_lint import (amd_lint_callouts, amd_lint_missing,
                                           amd_lint_references)
from sbs_utils.procedural.quest import document_get_amd_file


def _node(doc, key):
    return next(n for n in doc.nodes if n.key == key)


def _rt(content):
    """The runtime tree, flattened to {key: node}."""
    out = {}

    def walk(n):
        if n.get("key"):
            out[n.get("key")] = n
        for c in n.get("children", []):
            walk(c)

    walk(document_get_amd_file(None, "Doc", content=content))
    return out


class TestSynopsis(unittest.TestCase):
    """`= ` is the author's note about what a beat is FOR. Never rendered."""

    SRC = ("# [Identify the Kidnapper](trail)\n"
           "= Midpoint. The crew learns Florbin is alive.\n"
           "---\n"
           "State: active\n"
           "---\n"
           "Follow the cargo trail.\n")

    def test_captured_and_kept_out_of_the_body(self):
        node = _node(parse(self.SRC), "trail")
        self.assertEqual(node.synopsis, "Midpoint. The crew learns Florbin is alive.")
        self.assertNotIn("Midpoint", "\n".join(r for _l, r in node.body_lines))

    def test_does_not_become_the_summary(self):
        """The trap: `summary` is the first non-choice body line, so without an
        explicit exclusion every synopsized record would show the author's private
        note as its description."""
        node = _node(parse(self.SRC), "trail")
        self.assertEqual(node.summary, "Follow the cargo trail.")

    def test_runtime_never_renders_it(self):
        node = _rt(self.SRC)["trail"]
        self.assertNotIn("Midpoint", node.get("description"))
        self.assertIn("Follow the cargo trail.", node.get("description"))
        self.assertEqual(node.get("synopsis"),
                         "Midpoint. The crew learns Florbin is alive.")

    def test_between_heading_and_fence_the_fence_still_opens(self):
        """A synopsis sits where a writer puts it - under the title, above the data.
        That must not stop the `---` below it from being a fence.

        Asserted as PARITY rather than a literal: the field registry normalizes the
        value (`State: active` is stored as the runtime spelling), and both readers
        must agree on whatever that is."""
        tooled = _node(parse(self.SRC), "trail").data.get("state")
        runtime = _rt(self.SRC)["trail"].get("data", {}).get("state")
        self.assertTrue(tooled, "the fence did not open under a synopsis line")
        self.assertEqual(tooled, runtime)

    def test_style_declaration_is_untouched(self):
        """`=$name style` is the line-style declaration - 14 uses in the corpus. The
        REQUIRED space after `=` is the whole reason this is safe."""
        self.assertIsNone(amd_body_synopsis("=$test font:gui-6;color:yellow"))
        self.assertIsNone(amd_body_synopsis("=$h1 font:gui-5; | I > 0;"))
        src = "# [Doc](doc)\n=$test font:gui-6;color:yellow\ntext\n"
        self.assertEqual(_node(parse(src), "doc").synopsis, "")
        self.assertIn("=$test", _rt(src)["doc"].get("description"))

    def test_bare_equals_and_math_stay_prose(self):
        self.assertIsNone(amd_body_synopsis("="))
        self.assertIsNone(amd_body_synopsis("==="))
        self.assertIsNone(amd_body_synopsis("=x is 4"))
        self.assertEqual(amd_body_synopsis("= a note"), "a note")

    def test_multiple_lines_join(self):
        node = _node(parse("# [A](a)\n= first\n= second\nbody\n"), "a")
        self.assertEqual(node.synopsis, "first second")


class TestBoneyard(unittest.TestCase):
    """`/* ... */` is cut text - a writer removes a scene far more often than a line."""

    def test_cuts_a_whole_record_from_both_readers(self):
        src = ("# [Keep](keep)\nkept\n"
               "/*\n# [Cut](cut)\n---\nState: active\n---\ngone\n*/\n"
               "# [Also](also)\nalso kept\n")
        doc = parse(src)
        self.assertEqual(doc.keys, {"keep", "also"})
        self.assertEqual(set(_rt(src)) - {"__root__"}, {"keep", "also"})

    def test_single_line_form(self):
        src = "# [A](a)\nbefore\n/* cut this */\nafter\n"
        body = "\n".join(r for _l, r in _node(parse(src), "a").body_lines)
        self.assertIn("before", body)
        self.assertIn("after", body)
        self.assertNotIn("cut this", body)
        self.assertNotIn("cut this", _rt(src)["a"].get("description"))

    def test_text_after_the_closer_survives(self):
        """Nothing is silently eaten - the tail after `*/` is handed back."""
        scanner = BoneyardScanner()
        self.assertEqual(scanner.feed("/* note */ real text"), (False, " real text"))
        scanner = BoneyardScanner()
        self.assertEqual(scanner.feed("/* open"), (True, None))
        self.assertEqual(scanner.feed("still cut"), (True, None))
        self.assertEqual(scanner.feed("*/ tail"), (False, " tail"))

    def test_mid_sentence_slash_star_is_prose(self):
        """The opener must START a line, or an arithmetic or path-like sentence
        would vanish."""
        src = "# [A](a)\nthe ratio a/*b is fine\n"
        self.assertIn("a/*b", "\n".join(r for _l, r in _node(parse(src), "a").body_lines))

    def test_unclosed_is_reported(self):
        doc = parse("# [A](a)\n/* forgot to close\nmore\n")
        self.assertTrue(any("never closed" in msg for _ln, msg in doc.errors))


class TestWikiLinks(unittest.TestCase):
    """`[[key]]` lets PROSE carry a reference - narrative text could not before."""

    SRC = ("# [Brief](brief)\n"
           "Talk to [[vell]] before you reach [[ds1|the station]].\n"
           "# [Commander Vell](vell)\n"
           "A tired officer.\n"
           "# [Deep Space 1](ds1)\n"
           "A station.\n")

    def test_emits_ordinary_refs(self):
        """Plain `AmdRef`s, so references / rename / graph / timeline get them free."""
        doc = parse(self.SRC)
        links = [r for r in doc.refs if r.kind == "link"]
        self.assertEqual([r.value for r in links], ["vell", "ds1"])
        self.assertEqual([r.owner for r in links], ["brief", "brief"])

    def test_span_covers_the_whole_token(self):
        ref = next(r for r in parse(self.SRC).refs if r.value == "vell")
        line = self.SRC.splitlines()[1]
        self.assertEqual(line[ref.span.col:ref.span.end_col], "[[vell]]")

    def test_renders_display_text_and_alias(self):
        desc = _rt(self.SRC)["brief"].get("description")
        self.assertIn("Talk to Commander Vell", desc)
        self.assertIn("reach the station", desc)
        self.assertNotIn("[[", desc)

    def test_forward_and_backward_links_behave_the_same(self):
        """The render is a POST-pass precisely so a link written before its target
        resolves like one written after."""
        src = ("# [Target](t)\n[[later]] and plain text\n"
               "# [Later Thing](later)\nx\n")
        self.assertIn("Later Thing", _rt(src)["t"].get("description"))

    def test_unwritten_target_renders_as_the_key_and_warns(self):
        src = "# [Brief](brief)\nFind [[the_wreck]].\n"
        self.assertIn("Find the_wreck.", _rt(src)["brief"].get("description"))
        codes = [f.code for f in amd_lint_references(parse(src))]
        self.assertIn("dangling-link", codes)

    def test_missing_list_groups_by_target(self):
        """`sbs lint --missing` is a work list, not a failure."""
        src = ("# [A](a)\nsee [[ghost]]\n# [B](b)\nalso [[ghost]] and [[other]]\n")
        missing = amd_lint_missing(parse(src))
        self.assertEqual(set(missing), {"ghost", "other"})
        self.assertEqual(len(missing["ghost"]), 2)
        self.assertEqual({owner for _k, owner, _s in missing["ghost"]}, {"a", "b"})

    def test_resolved_links_are_not_missing(self):
        self.assertEqual(amd_lint_missing(parse(self.SRC)), {})

    def test_pure_helpers(self):
        self.assertEqual(amd_wikilinks("a [[x]] b [[y|z]]"),
                         [("x", None, 2, 7), ("y", "z", 10, 17)])
        self.assertEqual(amd_render_wikilinks("[[x]]", {"x": "Ex"}.get), "Ex")
        self.assertEqual(amd_render_wikilinks("[[x|words]]", {"x": "Ex"}.get), "words")
        self.assertEqual(amd_render_wikilinks("[[x]]", None), "x")

    def test_unclosed_brackets_stay_prose(self):
        """An unclosed `[[` must not swallow the rest of the document."""
        self.assertEqual(amd_wikilinks("open [[ and then\nmore"), [])
        self.assertEqual(amd_render_wikilinks("open [[ and then", None), "open [[ and then")

    def test_markdown_choice_links_are_untouched(self):
        """`- [Label](target)` keeps its own meaning - two link forms, two jobs."""
        doc = parse("# [S](s)\n- [Apologize](backoff)\n# [B](backoff)\nx\n")
        kinds = {r.kind for r in doc.refs}
        self.assertIn("choice", kinds)
        self.assertNotIn("link", kinds)


class TestCues(unittest.TestCase):
    """`@Speaker` puts the cue in the BODY, so one scene can hold a conversation."""

    SRC = ("# [The Standoff](standoff)\n"
           "---\n"
           "Speaker: ashfang\n"
           "When: comms\n"
           "---\n"
           "@Ashfang\n"
           "% You're a long way from friends, captain.\n"
           "% Brave or stupid, flying in here.\n"
           "\n"
           "@Vell (comms)\n"
           "(shaken)\n"
           "He means it, captain.\n"
           "\n"
           "- [Apologize](backoff)\n")

    def _scene(self, src=None):
        node = _rt(src or self.SRC)["standoff"]
        return dialogue_parse(node)

    def test_beats_group_lines_by_speaker(self):
        beats = self._scene()["beats"]
        self.assertEqual([b["speaker"] for b in beats], ["ashfang", "vell"])
        self.assertEqual(len(beats[0]["lines"]), 2)
        self.assertEqual(beats[1]["lines"][0][0], "He means it, captain.")

    def test_surface_and_direction_are_told_apart(self):
        """Both are written in parentheses because a screenwriter writes both that
        way; a registered word is the surface, anything else is direction."""
        beats = self._scene()["beats"]
        self.assertEqual(beats[1]["surface"], "comms")
        self.assertIsNone(beats[1]["direction"])
        self.assertEqual(beats[1]["lines"][0][2], "shaken")

    def test_choices_stay_scene_level(self):
        self.assertEqual([c["target"] for c in self._scene()["choices"]], ["backoff"])

    def test_flat_lines_still_hold_every_variant(self):
        """`lines` is what the shipped single-speaker corpus reads. It must keep
        seeing every spoken variant regardless of how many speakers there are."""
        self.assertEqual(len(self._scene()["lines"]), 3)

    def test_single_speaker_scene_is_unchanged(self):
        """`raider_hails.amd` shape: speaker in the fence, bare `%` lines, no cue."""
        src = ("# [Kralien](kralien)\n---\nSpeaker: kralien\nWhen: comms\n---\n"
               "% Pay rent or be destroyed.\n% Kraliens not listening.\n")
        scene = dialogue_parse(_rt(src)["kralien"])
        self.assertEqual(scene["speaker"], "kralien")
        self.assertEqual([t for t, _g in scene["lines"]],
                         ["Pay rent or be destroyed.", "Kraliens not listening."])
        self.assertEqual(len(scene["beats"]), 1)
        self.assertEqual(scene["beats"][0]["speaker"], "kralien")

    def test_lines_before_the_first_cue_use_the_fence_speaker(self):
        src = ("# [S](s)\n---\nSpeaker: narrator\n---\n"
               "An opening line.\n@Vell\nA reply.\n")
        beats = dialogue_parse(_rt(src)["s"])["beats"]
        self.assertEqual([b["speaker"] for b in beats], ["narrator", "vell"])

    def test_gates_still_work_inside_a_beat(self):
        src = "# [S](s)\n@Vell\n{fearsome > 20} Only when feared.\nAlways.\n"
        beat = dialogue_parse(_rt(src)["s"])["beats"][0]
        self.assertEqual(beat["lines"][0][:2], ("Only when feared.", "fearsome > 20"))
        self.assertEqual(beat["lines"][1][1], None)

    def test_cue_emits_a_ref_and_lints_when_nobody_answers(self):
        doc = parse(self.SRC)
        cues = [r for r in doc.refs if r.kind == "cue"]
        # The value normalizes to the slug; the span stays on the authored text.
        self.assertEqual([r.value for r in cues], ["ashfang", "vell"])
        line = self.SRC.splitlines()[5]
        self.assertEqual(line[cues[0].span.col:cues[0].span.end_col], "Ashfang")
        self.assertIn("dangling-speaker", [f.code for f in amd_lint_references(doc)])

    def test_known_cast_clears_the_warning(self):
        doc = parse(self.SRC)
        codes = [f.code for f in amd_lint_references(doc, known_keys={"ashfang", "vell"})]
        self.assertNotIn("dangling-speaker", codes)

    def test_cue_does_not_become_the_summary(self):
        self.assertEqual(_node(parse(self.SRC), "standoff").summary,
                         "% You're a long way from friends, captain.")

    def test_beats_pick_one_line_each(self):
        played = dialogue_beats(self._scene(), None)
        self.assertEqual([b.get("speaker") for b in played], ["ashfang", "vell"])
        self.assertEqual(played[1].get("surface"), "comms")
        self.assertEqual(played[1].get("direction"), "shaken")
        self.assertIn(played[0].get("text"),
                      ["You're a long way from friends, captain.",
                       "Brave or stupid, flying in here."])

    def test_speakers_listed_in_script_order(self):
        self.assertEqual(dialogue_speakers(self._scene()), ["ashfang", "vell"])

    def test_registered_direction_resolves_and_unknown_stays_flavor(self):
        amd_register_directions("test_amd_script", {"shaken": {"mood": "afraid"}})
        self.assertEqual(dialogue_direction("shaken"), {"mood": "afraid"})
        self.assertIsNone(dialogue_direction(
            "with the weariness of a man who has explained this twice"))

    def test_email_style_text_is_not_a_cue(self):
        """A cue is a whole line. Prose that merely contains `@` is prose."""
        src = "# [A](a)\nreach us at ops@fleet.example for details\n"
        self.assertEqual([r for r in parse(src).refs if r.kind == "cue"], [])


class TestTransitions(unittest.TestCase):
    """`FADE IN:` / `> CUT TO:` say how a shot ARRIVES - structure, not overlay text."""

    def test_bare_and_forced_forms(self):
        self.assertEqual(amd_body_transition("FADE IN:"), "FADE IN:")
        self.assertEqual(amd_body_transition("  cut to:  "), "CUT TO:")
        self.assertEqual(amd_body_transition("> CUT TO:"), "CUT TO:")
        self.assertEqual(amd_body_transition("> SLAM TO BLACK"), "SLAM TO BLACK")

    def test_prose_and_fence_lines_are_not_transitions(self):
        """The closed set is the point: an all-caps heuristic would eat prose, and
        `Cutscene:` is a fence label that starts with the letters of `CUT`."""
        for line in ("Cutscene: intro", "SCIENCE: scan her.",
                     "The ship cut to starboard.", "> [!NOTE] a callout"):
            self.assertIsNone(amd_body_transition(line), line)

    def test_shot_keeps_the_transition_out_of_its_overlay_text(self):
        section = {"children": [
            {"key": "s1", "display_text": "Open", "data": {
                "cutscene": "intro", "subject": "hero", "overlay": "lower_third"},
             "description": "FADE IN:\nAll quiet on the belt.\n", "children": []},
        ]}
        shots = amd_cutscenes(section)["cutscenes"]["intro"]["shots"]
        self.assertEqual(shots[0]["transition"], "FADE IN:")
        # `lower_third`'s primary field is `line` (see _KIND_PRIMARY_FIELD).
        self.assertEqual(shots[0]["overlay"]["line"], "All quiet on the belt.")

    def test_fence_wins_over_the_body(self):
        section = {"children": [
            {"key": "s1", "display_text": "Open", "data": {
                "cutscene": "intro", "subject": "hero", "transition": "DISSOLVE TO:"},
             "description": "> CUT TO:\n", "children": []},
        ]}
        shots = amd_cutscenes(section)["cutscenes"]["intro"]["shots"]
        self.assertEqual(shots[0]["transition"], "DISSOLVE TO:")

    def test_no_transition_is_none(self):
        section = {"children": [
            {"key": "s1", "display_text": "Open",
             "data": {"cutscene": "intro", "subject": "hero"},
             "description": "Just prose.\n", "children": []},
        ]}
        self.assertIsNone(
            amd_cutscenes(section)["cutscenes"]["intro"]["shots"][0]["transition"])


class TestCallouts(unittest.TestCase):
    """`> [!WARNING]` - in-fiction documents want in-fiction document formatting."""

    SRC = ("Read this first.\n"
           "> [!WARNING] Quarantine Notice\n"
           "> Do not dock.\n"
           "> Contact TSN Command on channel 4.\n"
           "Ordinary prose again.\n")

    def test_block_spans_its_continuation_lines(self):
        block = amd_callout_blocks(self.SRC)[0]
        self.assertEqual(block["kind"], "warning")
        self.assertEqual(block["title"], "Quarantine Notice")
        self.assertEqual(block["lines"], ["Do not dock.",
                                          "Contact TSN Command on channel 4."])
        self.assertEqual((block["start"], block["end"]), (1, 4))
        self.assertTrue(block["known"])

    def test_render_strips_markers_and_styles_only_the_block(self):
        text, styles = amd_callout_render(self.SRC)
        self.assertEqual(text.splitlines()[1], "Quarantine Notice")
        self.assertEqual(text.splitlines()[2], "Do not dock.")
        self.assertNotIn(">", text)
        self.assertIsNone(styles[0])          # prose above
        self.assertIsNone(styles[4])          # prose below
        self.assertEqual(styles[2]["background"], _CALLOUT_KINDS["warning"]["background"])
        self.assertEqual(styles[1]["background"], _CALLOUT_KINDS["warning"]["background"])

    def test_title_font_actually_wins(self):
        """A style string is LAST-WINS (`split_props`). Prepending the title's font
        let the kind's own `font:` override it, so the title rendered at body size -
        emphasis present in the source and absent on screen. Assert the EFFECTIVE
        font rather than the string, which is what made this invisible."""
        from sbs_utils.helpers import split_props
        _text, styles = amd_callout_render(self.SRC)
        title_font = split_props(styles[1]["style"], "font").get("font")
        body_font = split_props(styles[2]["style"], "font").get("font")
        self.assertEqual(title_font, "gui-3")
        self.assertEqual(body_font, "gui-2")
        self.assertNotEqual(title_font, body_font)

    def test_two_blocks_do_not_merge(self):
        src = "> [!NOTE] One\n> body\n> [!TIP] Two\n> body\n"
        kinds = [b["kind"] for b in amd_callout_blocks(src)]
        self.assertEqual(kinds, ["note", "tip"])

    def test_document_without_callouts_is_untouched(self):
        text, styles = amd_callout_render("plain\nprose\n")
        self.assertEqual(text, "plain\nprose\n")
        self.assertIsNone(styles)

    def test_unknown_kind_renders_as_a_quote_and_warns(self):
        src = "# [Doc](doc)\n> [!MYSTERY] Hmm\n> body\n"
        block = amd_callout_blocks("> [!MYSTERY] Hmm\n> body\n")[0]
        self.assertFalse(block["known"])
        text, styles = amd_callout_render("> [!MYSTERY] Hmm\n> body\n")
        self.assertEqual(text.splitlines()[0], "Hmm")
        self.assertIn("unknown-callout", [f.code for f in amd_lint_callouts(parse(src))])

    def test_gui_text_area_understands_them_natively(self):
        """The point of moving it into the widget: a callout works wherever text is
        rendered, without the caller knowing the feature exists. `document_screen`
        calls a bare `gui_text_area(t)`, so an opt-in transform would never have
        reached the two shipped prose files."""
        from sbs_utils.pages.layout.text_area import TextArea
        ta = TextArea("t", "x")
        src = ("Ordinary prose.\n"
               "> [!WARNING] Quarantine Notice\n"
               "> Do not dock.\n"
               "Prose resumes.\n")
        keys, style = [], ta.get_style("_")
        for line in src.splitlines():
            key, _text = ta.get_line_style(line, style)
            if isinstance(key, str):
                style = ta.get_style(key)
            keys.append(key if isinstance(key, str) else "(inherited)")
        self.assertEqual(keys[1], "callout_warning_title")
        self.assertEqual(keys[2], "callout_warning")

    def test_the_box_has_a_bottom(self):
        """A callout ENDS at the first non-`>` line. An unstyled line inherits the
        previous style, so without an explicit reset the background bled down the
        rest of the document."""
        from sbs_utils.pages.layout.text_area import TextArea
        ta = TextArea("t", "x")
        style = ta.get_style("_")
        for line in ["> [!DANGER] Breach", "> Leave now."]:
            key, _t = ta.get_line_style(line, style)
            style = ta.get_style(key)
        self.assertEqual(style.get("background"), _CALLOUT_KINDS["danger"]["background"])
        key, _t = ta.get_line_style("Ordinary prose again.", style)
        self.assertEqual(key, "_")
        self.assertIsNone(ta.get_style(key).get("background"))

    def test_a_plain_quote_is_still_prose(self):
        """`>` without an open callout keeps meaning exactly what it always did."""
        from sbs_utils.pages.layout.text_area import TextArea
        ta = TextArea("t", "x")
        prev = ta.get_style("_")
        key, text = ta.get_line_style("> just a quoted line", prev)
        self.assertNotIsInstance(key, str)      # inherited, i.e. untouched
        self.assertEqual(text, "> just a quoted line")

    def test_widget_and_pure_render_agree_on_colors(self):
        """One definition of what a callout looks like. The widget reads
        `amd_callout_style_table`; the pure renderer reads `_CALLOUT_KINDS`."""
        from sbs_utils.procedural.amd_callout import amd_callout_style_table
        table = amd_callout_style_table()
        for kind, spec in _CALLOUT_KINDS.items():
            self.assertEqual(table[f"callout_{kind}"]["background"], spec["background"])

    def test_ascii_only(self):
        """Engine-rendered strings carry no Unicode, so a callout is marked by color
        and indent - never by a glyph."""
        for spec in _CALLOUT_KINDS.values():
            for value in spec.values():
                if isinstance(value, str):
                    self.assertTrue(all(ord(c) < 128 for c in value), value)


class TestAliases(unittest.TestCase):
    """`Aka:` - other names a record answers to (Obsidian note aliases)."""

    SRC = ("# [The Florbin Affair](florbin)\n---\nAka: The Florbin Job, florbin_case\n---\n"
           "Body.\n\n# [Brief](brief)\nSee [[The Florbin Job]] and [[florbin_case]].\n")

    def test_aliases_resolve_like_keys(self):
        doc = parse(self.SRC)
        self.assertEqual(doc.resolve_target("florbin_case").key, "florbin")
        self.assertEqual(doc.resolve_target("The Florbin Job").key, "florbin")

    def test_an_aliased_link_is_not_dangling(self):
        self.assertEqual([f.code for f in amd_lint_references(parse(self.SRC))], [])

    def test_renders_the_target_display_name(self):
        desc = _rt(self.SRC)["brief"].get("description")
        self.assertIn("See The Florbin Affair and The Florbin Affair.", desc)

    def test_a_real_key_always_wins(self):
        """An alias must never shadow a record that actually has that key."""
        src = ("# [Decoy](real)\n---\nAka: taken\n---\nx\n"
               "# [Genuine](taken)\ny\n")
        self.assertEqual(parse(src).resolve_target("taken").key, "taken")

    def test_aka_is_not_also(self):
        """`Also:` is traits, `Aka:` is names. A syllable apart, and not the same."""
        doc = parse("# [X](x)\n---\nAlso: economy\n---\nbody\n")
        self.assertEqual(doc.aliases, {})


class TestTransclusion(unittest.TestCase):
    """`![[key]]` on its own line pulls that record's body in."""

    def test_splices_the_body(self):
        src = ("# [Docking](dock_help)\nHold at 2000 and hail.\n\n"
               "# [Station A](sta)\nApproach from the south.\n![[dock_help]]\nThen dock.\n")
        desc = _rt(src)["sta"].get("description")
        self.assertIn("Approach from the south.", desc)
        self.assertIn("Hold at 2000 and hail.", desc)
        self.assertIn("Then dock.", desc)
        self.assertNotIn("![[", desc)

    def test_a_cycle_is_reported_not_hung(self):
        src = "# [A](a)\ntop\n![[b]]\n# [B](b)\nmiddle\n![[a]]\n"
        self.assertIn("[circular include: a]", _rt(src)["a"].get("description"))

    def test_self_include_is_a_cycle(self):
        self.assertIn("[circular include: a]",
                      _rt("# [A](a)\nx\n![[a]]\n")["a"].get("description"))

    def test_missing_target_says_so(self):
        self.assertIn("[missing: nope]", _rt("# [A](a)\n![[nope]]\n")["a"].get("description"))

    def test_inline_links_and_embeds_coexist(self):
        """`[[x]]` must not swallow the `[[x]]` inside `![[x]]`, and vice versa."""
        src = "# [T](t)\nbody\n# [A](a)\nsee [[t]] and\n![[t]]\n"
        desc = _rt(src)["a"].get("description")
        self.assertIn("see T and", desc)      # the link rendered as a display name
        self.assertIn("body", desc)           # the embed spliced the body

    def test_embed_is_not_counted_as_a_link_ref(self):
        doc = parse("# [T](t)\nx\n# [A](a)\n![[t]]\n")
        self.assertEqual([r for r in doc.refs if r.kind == "link"], [])

    def test_mid_sentence_embed_is_prose(self):
        """A transclusion is a BLOCK; inline would splice paragraphs into a sentence."""
        src = "# [T](t)\nbody\n# [A](a)\ntext ![[t]] more\n"
        self.assertIn("![[t]]", _rt(src)["a"].get("description"))


class TestTitlePage(unittest.TestCase):
    """Fountain's title page IS the document fence - it already parsed; this pins it."""

    SRC = ("---\nTitle: The Florbin Affair\nAuthor: D. Reichard\nDraft: 3\n---\n\n"
           "# [Jobs](jobs)\n## [A Job](j1)\nbody\n")

    def test_reaches_root_data(self):
        from sbs_utils.procedural.amd_doc import amd_root_data
        data = amd_root_data(document_get_amd_file(None, "Doc", content=self.SRC))
        self.assertEqual(data.get("title"), "The Florbin Affair")
        self.assertEqual(data.get("author"), "D. Reichard")

    def test_does_not_warn(self):
        from sbs_utils.procedural.amd_lint import amd_lint_unknown_fields
        self.assertEqual(amd_lint_unknown_fields(parse(self.SRC)), [])


class TestMissingRequest(unittest.TestCase):
    """`amd/missing` - the editor's Missing panel, mission-wide and grouped by target.

    A different question from the Problems pane, which is per-FILE and asks "what is
    wrong here". This asks "what do I still have to write", so it crosses files and
    groups by the thing that does not exist yet."""

    def _index(self, sources):
        docs = [(name, f"file:///{name}", parse(text)) for name, text in sources.items()]
        known = set()
        for _p, _u, d in docs:
            known |= d.keys
        return {"docs": docs, "known": known}

    def test_groups_across_files_by_target(self):
        from sbs_utils.procedural.amd_lsp import _mission_missing
        res = _mission_missing(self._index({
            "a.amd": "# [Brief](brief)\nSee [[ghost]].\n",
            "b.amd": "# [Other](other)\nAlso [[ghost]] and [[lone]].\n",
        }))
        by_target = {e["target"]: e for e in res["missing"]}
        self.assertEqual(set(by_target), {"ghost", "lone"})
        self.assertEqual(len(by_target["ghost"]["uses"]), 2)
        self.assertEqual({u["owner"] for u in by_target["ghost"]["uses"]}, {"brief", "other"})
        self.assertEqual(res["total"], 3)
        self.assertEqual(res["files"], 2)

    def test_most_referenced_first(self):
        """What to write next is what the most things are waiting on."""
        from sbs_utils.procedural.amd_lsp import _mission_missing
        res = _mission_missing(self._index({
            "a.amd": "# [A](a)\n[[one]] [[two]] [[two]]\n",
        }))
        self.assertEqual([e["target"] for e in res["missing"]], ["two", "one"])

    def test_a_record_defined_anywhere_is_not_missing(self):
        from sbs_utils.procedural.amd_lsp import _mission_missing
        res = _mission_missing(self._index({
            "a.amd": "# [Brief](brief)\nSee [[vell]].\n",
            "cast.amd": "# [Vell](vell)\nA tired officer.\n",
        }))
        self.assertEqual(res["missing"], [])

    def test_cues_and_choices_count_too(self):
        from sbs_utils.procedural.amd_lsp import _mission_missing
        res = _mission_missing(self._index({
            "a.amd": "# [S](s)\n@Ashfang\n% hi\n- [Back](nowhere)\n",
        }))
        self.assertEqual({e["target"] for e in res["missing"]}, {"ashfang", "nowhere"})
        kinds = {u["kind"] for e in res["missing"] for u in e["uses"]}
        self.assertEqual(kinds, {"cue", "choice"})

    def test_uses_carry_a_jumpable_location(self):
        from sbs_utils.procedural.amd_lsp import _mission_missing
        res = _mission_missing(self._index({"a.amd": "# [A](a)\nx\nSee [[ghost]].\n"}))
        use = res["missing"][0]["uses"][0]
        self.assertEqual(use["uri"], "file:///a.amd")
        self.assertEqual(use["line"], 2)        # 0-based, for the editor
        self.assertGreaterEqual(use["col"], 0)


class TestProseIsProse(unittest.TestCase):
    """Law 1: an unclaimed body line means exactly what it always meant."""

    def test_field_shaped_prose_still_renders(self):
        """12 record bodies in the corpus open `COMMS:` / `SCIENCE:`. They are prose."""
        src = "# [A](a)\nCOMMS: hail the freighter.\nSCIENCE: scan her.\n"
        desc = _rt(src)["a"].get("description")
        self.assertIn("COMMS: hail the freighter.", desc)
        self.assertIn("SCIENCE: scan her.", desc)

    def test_dialogue_and_headings_in_prose_are_unaffected(self):
        src = "# [A](a)\n% a spoken variant\n> a quote\n# not a link heading\n"
        desc = _rt(src)["a"].get("description")
        for keep in ("% a spoken variant", "> a quote", "# not a link heading"):
            self.assertIn(keep, desc)


if __name__ == "__main__":
    unittest.main()
