"""`sbs docs` prints what the WRITER typed, not what the runtime stores.

Three defects the C1-12 pilot found in a printed mission:

* fence labels came out as stored keys - `Goal`, `When`, `Parent`, `Scan_Of`,
  `Fails_When` - for the `Done when:` / `Starts when:` / `Part of:` / `Scan of:` /
  `Fails when:` the writer typed, teaching them the retired spellings;
* `Win:` and `Lose:` printed `Win False` / `Lose False`: the schema typed both as a
  yes/no flag, so the sentence (what the end screen shows) coerced to `False`;
* a `When: hail` scene was slugged `INT. COMMS - OUTGOING`. A hail is INCOMING - the
  mission calls the ship.

And the game reader must still read a `Win:` sentence as the end-screen line.
"""
import re
import unittest

from sbs_utils.fs import test_set_exe_dir

test_set_exe_dir()

from sbs_utils.procedural.amd_core import parse
from sbs_utils.procedural.amd_render import amd_render_html

SOURCE = """\
# [Quests](quests)

## [Find the Hulk](find_hulk)
---
Objective: Find the drifting hulk.
Starts when: at once
Done when: reach hulk 2000
Fails when: 10 minutes
Win: The hulk is found and the crew comes home.
Lose: The hulk is lost forever.
---
Fly out and find the hulk.

## [Step Two](step_two)
---
Part of: find_hulk
Done when: signal step_done
---
A step.

# [Scans](scans)

## [Hulk Scan](hulk_scan)
---
Scan of: hulk
Tab: scan
---
% Cold metal.

# [Dialogue](dialogue)

## [Captain Calls](captain_call)
---
Speaker: captain_call
When: hail
---
% We need help.

## [Station Desk](station_desk)
---
Speaker: station_desk
When: comms
---
% How can we help?
"""


def render(lens, profile="author"):
    doc = parse(SOURCE, file_path="mission.amd")
    return amd_render_html([("mission.amd", doc)], lens=lens, profile=profile,
                           title="Test")


def labels(html_text):
    return re.findall(r"<dt>([^<]*)</dt>", html_text)


class TestLabelsAreTheWritersWords(unittest.TestCase):
    def test_the_catalog_titles_fields_as_typed(self):
        got = labels(render("catalog"))
        for typed in ("Starts when", "Done when", "Fails when", "Part of", "Scan of"):
            self.assertIn(typed, got)
        for stored in ("Goal", "When", "Parent", "Scan_Of", "Scan Of", "Fails_When",
                       "Fails When"):
            if stored == "When":
                # A scene's `When: hail` IS typed `When` - only the quest's must not be.
                continue
            self.assertNotIn(stored, got)

    def test_the_bible_titles_fields_as_typed(self):
        out = render("bible")
        got = labels(out)
        self.assertIn("Done when", got)
        self.assertIn("Part of", got)
        self.assertNotIn("Goal", got)
        self.assertNotIn("goal", got)
        self.assertNotIn("Parent", got)

    def test_a_player_page_drops_the_quest_machinery_under_its_typed_name(self):
        page = render("catalog", profile="player")
        got = labels(page)
        for machinery in ("Starts when", "Done when", "Fails when", "Part of", "Win",
                          "Lose"):
            self.assertNotIn(machinery, got)
        self.assertIn("Objective", got)
        # The VALUES are gone too - `Starts when:` / `Fails when:` used to slip through,
        # because the drop list said `starts when` and the record said `when`.
        self.assertNotIn("at once", page)
        self.assertNotIn("10 minutes", page)


class TestWinAndLoseKeepTheirSentences(unittest.TestCase):
    def test_the_sentence_is_printed(self):
        out = render("catalog")
        self.assertIn("The hulk is found and the crew comes home.", out)
        self.assertIn("The hulk is lost forever.", out)
        self.assertNotIn("False", out)

    def test_the_parsed_record_holds_the_sentence(self):
        doc = parse(SOURCE, file_path="mission.amd")
        node = next(n for n in doc.nodes if n.key == "find_hulk")
        self.assertEqual("The hulk is found and the crew comes home.", node.data["win"])
        self.assertTrue(node.data["lose"])

    def test_a_bare_flag_is_still_a_flag(self):
        from sbs_utils.procedural.amd_schema import amd_read_field
        self.assertIs(True, amd_read_field("Win", "yes", "quest")[1])
        self.assertIs(False, amd_read_field("Lose", "no", "quest")[1])
        self.assertIs(True, amd_read_field("Win", "", "quest")[1])

    def test_the_game_reader_still_takes_the_sentence_as_the_end_screen_line(self):
        from sbs_utils.procedural.amd_quest import amd_quest_data
        from sbs_utils.procedural.quest import _document_get_amd_file
        doc = _document_get_amd_file(None, content=SOURCE, data_parser=amd_quest_data)

        def find(node, key):
            if node.get("key") == key:
                return node
            for kid in node.get("children") or ():
                hit = find(kid, key)
                if hit is not None:
                    return hit
            return None

        data = find(doc, "find_hulk")["data"]
        self.assertTrue(data["end_win"])
        self.assertEqual("The hulk is found and the crew comes home.", data["win_text"])
        self.assertTrue(data["end_lose"])
        self.assertEqual("The hulk is lost forever.", data["lose_text"])


class TestAHailIsIncoming(unittest.TestCase):
    def test_slugs(self):
        out = render("screenplay")
        def slug_of(name):
            m = re.search(r'<p class="scene"[^>]*>' + name + r'(.*?)</p>', out, re.S)
            self.assertIsNotNone(m, name)
            return m.group(1)
        hail = slug_of("Captain Calls")
        comms = slug_of("Station Desk")
        self.assertIn("INT. COMMS - INCOMING", hail)
        self.assertIn("INT. COMMS - OUTGOING", comms)


if __name__ == "__main__":
    unittest.main()
