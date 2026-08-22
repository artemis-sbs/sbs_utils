"""Crew rosters authored as AMD - the reader.

    python -m unittest tests.test_amd_crew
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.procedural.amd_doc import amd_document
from sbs_utils.procedural.amd_crew import (amd_crew_data, crew_from_document, crew_from_section,
                                           crew_sections, crew_validate)


CAST = """# [Rosters](rosters)

## [Enterprise-D](tng_d)
---
crew
Hull: tng_fed_galaxy
Ship: Enterprise, Enterprise-D
Race: terran
Portraits: media/crew/tng
---
The Galaxy-class flagship's senior staff.

### [William Riker](riker)
---
Rank: Commander
Console: helm
---

### [Data](data)
---
Rank: Lt. Commander
Console: science
Portrait: data
---

### [Ensign Ro](ro)
---
Rank: Ensign
---
"""

GROUP = """# [Us](us)

## [Thursday Night Crew](thursday)
---
crew
By: person
Sheet: media/crew/thursday/faces
Cell: 256
Grid: 4, 2
---

### [Doug](doug)
---
Rank: Captain
At: 0, 0
---

### [Marty](marty)
---
At: 1, 0
---
"""


def _read(text):
    return crew_from_document(amd_document(text, data_parser=amd_crew_data))


class TestCrewReader(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())

    def test_a_cast_reads_its_members_in_order(self):
        rosters = _read(CAST)
        self.assertEqual(len(rosters), 1)
        r = rosters[0]
        self.assertEqual(r.key, "tng_d")
        self.assertEqual(r.name, "Enterprise-D")
        self.assertEqual([m.key for m in r.members], ["riker", "data", "ro"])
        self.assertEqual([m.name for m in r.members],
                         ["William Riker", "Data", "Ensign Ro"])

    def test_by_defaults_to_console_and_person_is_opt_in(self):
        self.assertEqual(_read(CAST)[0].by, "console")
        self.assertEqual(_read(GROUP)[0].by, "person")

    def test_the_section_fence_supplies_what_every_member_shares(self):
        r = _read(CAST)[0]
        self.assertEqual(r.hull, ["tng_fed_galaxy"])
        self.assertEqual(r.ship, ["Enterprise", "Enterprise-D"])
        self.assertEqual(r.race, "terran")
        self.assertEqual(r.portraits, "media/crew/tng")

    def test_a_member_says_only_what_differs(self):
        # Ro is a name and a rank. Everything else about her comes off the fence, which is
        # the whole point of the shape.
        ro = _read(CAST)[0].members[2]
        self.assertEqual(ro.rank, "Ensign")
        self.assertEqual(ro.console, "")
        self.assertEqual(ro.face, "")
        self.assertEqual(ro.portrait, "")

    def test_a_rank_is_text_not_a_number(self):
        # `amd_parse_facts` coerces unclaimed labels numerically. A rank of "1st Officer"
        # must survive as text, so `rank` is claimed explicitly.
        r = _read(CAST.replace("Rank: Ensign", "Rank: 1st Officer"))[0]
        self.assertEqual(r.members[2].rank, "1st Officer")

    def test_console_folds_to_lower_case(self):
        r = _read(CAST.replace("Console: helm", "Console: Helm"))[0]
        self.assertEqual(r.members[0].console, "helm")

    def test_a_sheet_roster_reads_its_cells(self):
        r = _read(GROUP)[0]
        self.assertEqual(r.sheet, "media/crew/thursday/faces")
        self.assertEqual(r.cell, (256, 256))     # one number means a square cell
        self.assertEqual(r.grid, (4, 2))
        self.assertEqual([m.at for m in r.members], [(0, 0), (1, 0)])

    def test_a_file_root_named_rosters_is_not_itself_a_roster(self):
        # `# [Rosters](rosters)` is a plausible file title AND a crew section word. A fence
        # that DECLARED the noun outright must win, or the root swallows every real roster
        # in the file and reads them as its own members.
        both = CAST + "\n" + GROUP.split("\n", 2)[2]
        rosters = _read(both)
        self.assertEqual([r.key for r in rosters], ["tng_d", "thursday"])

    def test_a_section_keyed_crew_still_works_without_the_noun(self):
        # The bare noun is the idiom, but `## [Crew](crew)` reads naturally and an author
        # should not have to say it twice.
        rosters = _read("# [Ship](ship)\n\n## [Crew](crew)\n---\nRace: terran\n---\n\n"
                        "### [Vega](vega)\n---\nConsole: helm\n---\n")
        self.assertEqual([r.key for r in rosters], ["crew"])
        self.assertEqual(rosters[0].members[0].name, "Vega")

    def test_a_file_with_no_roster_yields_nothing(self):
        self.assertEqual(_read("# [Notes](notes)\n\nJust prose.\n"), [])

    def test_crew_sections_does_not_descend_into_a_roster(self):
        # A roster's children are its MEMBERS. Descending would read each of them as an
        # empty roster of their own.
        found = crew_sections(amd_document(CAST, data_parser=amd_crew_data))
        self.assertEqual([n.get("key") for n in found], ["tng_d"])

    def test_from_section_is_what_from_document_returns(self):
        doc = amd_document(CAST, data_parser=amd_crew_data)
        node = crew_sections(doc)[0]
        self.assertEqual(crew_from_section(node)[0].key, _read(CAST)[0].key)

    def test_a_roster_carries_the_fields_the_shared_matcher_needs(self):
        # `maps.label_find_by_spec` matches on `.path` and `.display_name`, so a roster has
        # to answer to both or it cannot be found from a dropdown or a setting.
        r = _read(CAST)[0]
        self.assertEqual(r.path, "tng_d")
        self.assertEqual(r.display_name, "Enterprise-D")


class TestCrewValidate(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())

    def codes(self, text):
        return [c for _k, _sev, c, _m in crew_validate(_read(text), check_files=False)]

    def test_a_good_roster_is_quiet(self):
        self.assertEqual(self.codes(CAST), [])
        self.assertEqual(self.codes(GROUP), [])

    def test_at_without_a_sheet_is_an_error(self):
        self.assertIn("crew-at-without-sheet",
                      self.codes(GROUP.replace("Sheet: media/crew/thursday/faces\n", "")))

    def test_two_people_on_one_console_is_reported_but_allowed(self):
        # Not an error: a bridge really can have two science stations, and they fill in
        # declaration order. Worth saying out loud, though.
        text = CAST.replace("Console: science", "Console: helm")
        self.assertIn("crew-console-shared", self.codes(text))

    def test_an_empty_roster_is_flagged(self):
        self.assertIn("crew-empty-roster",
                      self.codes("# [R](r)\n\n## [Empty](empty)\n---\ncrew\n---\n"))


if __name__ == "__main__":
    unittest.main()
