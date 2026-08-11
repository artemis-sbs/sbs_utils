"""Generated blocks inside hand-written pages (procedural.amd_include).

The bug this module exists to prevent is not cosmetic. A documentation page taught
`When:` as the COMPLETION trigger; it is an alias of `Starts when:`, the START one, so
a quest written from that page arms on its trigger and then waits forever on a
`Done when:` it does not have. The copy did not look wrong - it looked like
documentation. `test_the_generated_table_says_which_trigger_is_which` is the pin.

Fixtures are Python strings written to a temp dir rather than checked-in `.amd` files:
a committed fixture's bytes depend on `autocrlf`, so a CRLF test asserting on one would
assert on whatever git handed the machine (see tests/amd_corpus.py).
"""
import os
import tempfile
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural import amd_include as inc

WARLORD = """\
// a leading comment, which a re-rendering would drop
# [Warlord](warlord)
---
Boss
Trigger: enemies_low
Low: 25%
---
A raider warlord warps in to break the defenders.

## [Defeat the Warlord](defeat_warlord)
---
Quest
Done when: destroy 1 warlord
Reward: 500 credits
---
Destroy the Warlord to break the siege.

### [Detail](warlord_detail)
---
Quest
---
A step under the objective.

## [Second](second)
---
Quest
---
Another objective.
"""


class _Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = self.tmp.name

    def write(self, rel, text=WARLORD, newline="\n"):
        path = os.path.join(self.base, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline=newline) as f:
            f.write(text)
        return path

    def render(self, directive):
        return inc.amd_include_render(directive, self.base)


class TestExcerpt(_Fixture):
    def test_a_whole_file_is_quoted_verbatim(self):
        self.write("bosses/warlord.amd")
        out = self.render("excerpt bosses/warlord.amd")
        self.assertTrue(out.startswith("```amd\n"))
        self.assertTrue(out.endswith("\n```"))
        # Including the comment: an excerpt quotes the SOURCE, not a re-rendering of
        # the parsed record, because the reader is being shown what to type.
        self.assertIn("// a leading comment", out)

    def test_one_record_stops_at_the_next_heading(self):
        self.write("bosses/warlord.amd")
        out = self.render("excerpt bosses/warlord.amd#warlord")
        self.assertIn("# [Warlord](warlord)", out)
        self.assertIn("Trigger: enemies_low", out)
        self.assertNotIn("Defeat the Warlord", out)
        # and not the comment above it - the excerpt starts AT the heading
        self.assertNotIn("// a leading comment", out)

    def test_with_children_stops_at_the_next_sibling_not_the_next_heading(self):
        self.write("bosses/warlord.amd")
        out = self.render("excerpt bosses/warlord.amd#defeat_warlord --with-children")
        self.assertIn("Defeat the Warlord", out)
        self.assertIn("Detail", out)          # the level-3 child came along
        self.assertNotIn("Second", out)       # the level-2 sibling did not

    def test_without_with_children_the_child_is_left_out(self):
        self.write("bosses/warlord.amd")
        out = self.render("excerpt bosses/warlord.amd#defeat_warlord")
        self.assertIn("Defeat the Warlord", out)
        self.assertNotIn("Detail", out)

    def test_the_last_record_runs_to_end_of_file(self):
        self.write("bosses/warlord.amd")
        out = self.render("excerpt bosses/warlord.amd#second")
        self.assertIn("Another objective.", out)

    def test_a_missing_file_names_itself(self):
        with self.assertRaises(inc.IncludeError) as ctx:
            self.render("excerpt bosses/nope.amd")
        self.assertIn("nope.amd", str(ctx.exception))

    def test_a_missing_record_names_itself(self):
        self.write("bosses/warlord.amd")
        with self.assertRaises(inc.IncludeError) as ctx:
            self.render("excerpt bosses/warlord.amd#no_such_key")
        self.assertIn("no_such_key", str(ctx.exception))


class TestFields(_Fixture):
    def test_the_generated_table_says_which_trigger_is_which(self):
        # THE regression pin. Two shipped pages taught `When:` as the completion
        # trigger. Generated from the schema, the table cannot say that: `When:` is
        # listed as another spelling of `Starts when:`, beside prose that says it arms.
        out = self.render("fields quest --only done when,starts when")
        rows = {r.split("|")[1].strip(): r for r in out.splitlines() if r.startswith("|")}
        self.assertIn("COMPLETION", rows["`Done when:`"])
        self.assertIn("`Goal:`", rows["`Done when:`"])
        self.assertIn("ARMS", rows["`Starts when:`"])
        self.assertIn("`When:`", rows["`Starts when:`"])

    def test_when_is_never_offered_as_a_field_of_its_own(self):
        # It is an alias, so it belongs in the "Also" column and nowhere else -
        # otherwise the table has two rows that look like two fields.
        out = self.render("fields quest")
        first_column = [r.split("|")[1].strip() for r in out.splitlines()
                        if r.startswith("| `")]
        self.assertNotIn("`When:`", first_column)
        self.assertIn("`Starts when:`", first_column)

    def test_the_same_label_generates_differently_per_archetype(self):
        # `When:` is a start trigger on a quest and a comms surface on dialogue. The
        # hand-written tables were flat and could not say this.
        quest = self.render("fields quest --only starts when")
        dialogue = self.render("fields dialogue --only when")
        self.assertIn("ARMS", quest)
        self.assertIn("SURFACE", dialogue)

    def test_only_filters_and_keeps_the_schemas_order(self):
        out = self.render("fields quest --only reward,objective")
        body = [r for r in out.splitlines() if r.startswith("| `")]
        self.assertEqual(len(body), 2)
        # QUEST declares objective before reward; --only selects, it does not reorder.
        self.assertIn("Objective", body[0])
        self.assertIn("Reward", body[1])

    def test_only_naming_an_undeclared_field_is_an_error(self):
        # Silently dropping it produces a table that is missing a row nobody asked
        # about - the same class of failure as the drift.
        with self.assertRaises(inc.IncludeError) as ctx:
            self.render("fields quest --only no_such_field")
        self.assertIn("no_such_field", str(ctx.exception))

    def test_an_unknown_archetype_is_an_error(self):
        with self.assertRaises(inc.IncludeError):
            self.render("fields nonesuch")

    def test_the_also_column_disappears_when_nothing_has_an_alias(self):
        out = self.render("fields quest --only objective")
        self.assertNotIn("Also", out)

    def test_internal_fields_are_not_published(self):
        # `on kill` is what `Done when:` compiles to. It must keep parsing and must
        # never be taught.
        out = self.render("fields quest")
        self.assertNotIn("On kill", out)
        self.assertNotIn("Fail after", out)


class TestIndex(_Fixture):
    def test_a_folder_lists_itself(self):
        self.write("bosses/warlord.amd")
        self.write("bosses/second.amd", WARLORD.replace("warlord", "kraken")
                   .replace("Warlord", "Kraken"))
        out = self.render("index bosses/*.amd --fields trigger")
        self.assertIn("| Name | Trigger | Summary |", out)
        self.assertIn("Warlord", out)
        self.assertIn("Kraken", out)
        self.assertIn("`enemies_low`", out)

    def test_only_the_named_level_is_listed(self):
        self.write("bosses/warlord.amd")
        out = self.render("index bosses/*.amd")
        self.assertIn("Warlord", out)
        self.assertNotIn("Defeat the Warlord", out)   # level 2

    def test_a_field_is_read_by_its_authored_name_not_its_stored_key(self):
        # `Done when:` stores as `goal`. An index must not have to know that.
        self.write("bosses/warlord.amd")
        out = self.render("index bosses/*.amd --level 2 --fields done when")
        self.assertIn("`destroy 1 warlord`", out)

    def test_a_glob_matching_nothing_is_an_error(self):
        with self.assertRaises(inc.IncludeError):
            self.render("index bosses/*.amd")


class TestTheSplice(_Fixture):
    PAGE = ("Some prose above.\n\n"
            "<!-- amd:begin fields quest --only objective -->\n"
            "STALE CONTENT\n"
            "<!-- amd:end -->\n\n"
            "Some prose below.\n")

    def test_only_the_span_between_the_markers_changes(self):
        out, _ = inc.amd_include_expand(self.PAGE, self.base)
        self.assertIn("Some prose above.", out)
        self.assertIn("Some prose below.", out)
        self.assertNotIn("STALE CONTENT", out)
        self.assertIn("`Objective:`", out)
        self.assertIn("<!-- amd:begin fields quest --only objective -->", out)
        self.assertIn("<!-- amd:end -->", out)

    def test_it_is_idempotent(self):
        once, _ = inc.amd_include_expand(self.PAGE, self.base)
        twice, report = inc.amd_include_expand(once, self.base)
        self.assertEqual(once, twice)
        self.assertFalse(any(changed for _, changed in report),
                         "a second run reported a change - --check would never pass")

    def test_it_reports_whether_each_block_actually_moved(self):
        _, report = inc.amd_include_expand(self.PAGE, self.base)
        self.assertEqual(len(report), 1)
        self.assertTrue(report[0][1])

    def test_crlf_survives(self):
        # These pages live in Windows repos with autocrlf. A generator that
        # normalizes line endings rewrites the whole file on its first run and buries
        # the one real change in an unreadable diff.
        out, _ = inc.amd_include_expand(self.PAGE.replace("\n", "\r\n"), self.base)
        self.assertIn("\r\n", out)
        self.assertNotIn("\n\n\r", out)
        self.assertEqual(out.count("\n"), out.count("\r\n"))

    def test_lf_stays_lf(self):
        out, _ = inc.amd_include_expand(self.PAGE, self.base)
        self.assertNotIn("\r", out)

    def test_several_blocks_in_one_page(self):
        page = (self.PAGE
                + "\n<!-- amd:begin fields quest --only reward -->\nx\n<!-- amd:end -->\n")
        out, report = inc.amd_include_expand(page, self.base)
        self.assertEqual(len(report), 2)
        self.assertIn("`Objective:`", out)
        self.assertIn("`Reward:`", out)

    def test_a_page_with_no_markers_is_returned_untouched(self):
        page = "nothing to see\n"
        out, report = inc.amd_include_expand(page, self.base)
        self.assertEqual(out, page)
        self.assertEqual(report, [])

    def test_an_unknown_directive_stops_the_build(self):
        # A page that silently keeps its stale copy is exactly the failure this
        # module exists to prevent, so it must not degrade to a warning.
        page = "<!-- amd:begin frobnicate x -->\nold\n<!-- amd:end -->\n"
        with self.assertRaises(inc.IncludeError) as ctx:
            inc.amd_include_expand(page, self.base)
        self.assertIn("frobnicate", str(ctx.exception))

    def test_directives_can_be_listed_without_rendering(self):
        self.assertEqual(inc.amd_include_directives(self.PAGE),
                         ["fields quest --only objective"])


class TestDocumentingTheSyntax(_Fixture):
    """A marker inside a code fence is an EXAMPLE, not an instruction.

    The page that documents this syntax has to show it. Without this the generator
    reads its own documentation as work to do - and then fails, because the example
    names a file that lives in some other repo. Found exactly that way."""

    FENCED = ("Use it like this:\n\n"
              "```markdown\n"
              "<!-- amd:begin excerpt maps/bosses/warlord.amd#warlord -->\n"
              "<!-- amd:end -->\n"
              "```\n")

    def test_a_marker_inside_a_fence_is_left_alone(self):
        out, report = inc.amd_include_expand(self.FENCED, self.base)
        self.assertEqual(out, self.FENCED)
        self.assertEqual(report, [])

    def test_it_is_not_listed_as_a_directive_either(self):
        self.assertEqual(inc.amd_include_directives(self.FENCED), [])

    def test_a_real_marker_after_a_fence_still_runs(self):
        page = (self.FENCED + "\n"
                "<!-- amd:begin fields quest --only objective -->\n"
                "old\n"
                "<!-- amd:end -->\n")
        out, report = inc.amd_include_expand(page, self.base)
        self.assertEqual(len(report), 1)
        self.assertIn("`Objective:`", out)
        self.assertIn("maps/bosses/warlord.amd", out)   # the example, untouched
        self.assertNotIn("old", out)

    def test_a_tilde_fence_counts_too(self):
        page = "~~~\n<!-- amd:begin fields quest -->\n<!-- amd:end -->\n~~~\n"
        self.assertEqual(inc.amd_include_directives(page), [])

    def test_an_unclosed_fence_swallows_the_rest_of_the_page(self):
        # Conservative on purpose: inside an unterminated fence everything reads as
        # example text, so the generator does nothing rather than acting on what may
        # be a listing.
        page = "```\n<!-- amd:begin fields quest -->\n<!-- amd:end -->\n"
        self.assertEqual(inc.amd_include_directives(page), [])


class TestTableBuilder(_Fixture):
    def test_a_pipe_in_a_cell_is_escaped(self):
        out = inc.amd_table([("A", "B"), ("x|y", "z")])
        self.assertIn(r"x\|y", out)

    def test_a_newline_in_a_cell_cannot_break_the_row(self):
        out = inc.amd_table([("A", "B"), ("x\ny", "z")])
        self.assertEqual(len([r for r in out.splitlines() if r.startswith("|")]), 3)

    def test_short_rows_are_padded_to_the_header(self):
        out = inc.amd_table([("A", "B", "C"), ("x",)])
        self.assertTrue(out.splitlines()[-1].startswith("| x |  |  |"))


if __name__ == "__main__":
    unittest.main()
