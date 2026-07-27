"""amd_timeline - signal edges, beat ranking, and the spine/pool split.

Offline: parses AMD text and asserts the model, no LSP session and no engine.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from sbs_utils.procedural.amd_core import parse
from sbs_utils.procedural.amd_timeline import (causal_edges, declared_duration,
                                               signal_edges, timeline)


def _docs(*sources):
    """`(uri, AmdDocument)` pairs, one per source string."""
    return [("file:///m/f%d.amd" % i, parse(s)) for i, s in enumerate(sources)]


CHAIN = """# [R](r)
## [Quests](quests)
### [Step One](one)
---
State: active
Then: reveal two
---
First.

### [Step Two](two)
---
State: secret
Then: reveal three
---
Second.

### [Step Three](three)
---
State: secret
---
Third.
"""


class TestSignalEdges(unittest.TestCase):
    def test_emit_and_wait_join_across_files(self):
        """The two halves of a signal usually live in different files - the join is
        mission-wide, which is the whole reason it can't be a per-document ref walk."""
        a = ("# [R](r)\n## [Quests](quests)\n### [Alarm](alarm)\n"
             "---\nState: active\nThen: signal breach\n---\nRing it.\n")
        b = ("# [R2](r2)\n## [Quests](quests2)\n### [Respond](respond)\n"
             "---\nState: secret\nWhen: signal breach\n---\nGo.\n")
        edges = signal_edges(_docs(a, b))
        self.assertEqual([(e["from"], e["to"], e["kind"]) for e in edges],
                         [("alarm", "respond", "signal")])
        # anchored at the EMIT site, in the emitting file
        self.assertTrue(edges[0]["uri"].endswith("f0.amd"))

    def test_goal_signal_is_a_wait(self):
        """`Goal: signal [N] NAME` completes a job, so it is a wait like `When:` - and
        the optional count is stripped the way the engine strips it."""
        src = ("# [R](r)\n## [Quests](quests)\n"
               "### [Trigger](trigger)\n---\nThen: signal drone_down\n---\nx\n"
               "### [Gunnery](gunnery)\n---\nGoal: signal 5 drone_down\n---\ny\n")
        edges = signal_edges(_docs(src))
        self.assertEqual([(e["from"], e["to"]) for e in edges], [("trigger", "gunnery")])
        self.assertEqual(edges[0]["name"], "drone_down")

    def test_fail_on_signal_is_a_wait(self):
        src = ("# [R](r)\n## [Quests](quests)\n"
               "### [Boom](boom)\n---\nThen: signal ship_lost\n---\nx\n"
               "### [Escort](escort)\n---\nFail on signal: ship_lost\n---\ny\n")
        self.assertEqual([(e["from"], e["to"]) for e in signal_edges(_docs(src))],
                         [("boom", "escort")])

    def test_self_signal_is_not_an_edge(self):
        """A record that emits and waits on one name is a repeatable loop the author
        wrote on purpose, not an ordering."""
        src = ("# [R](r)\n## [Quests](quests)\n### [Loop](loop)\n"
               "---\nThen: signal again\nWhen: signal again\n---\nx\n")
        self.assertEqual(signal_edges(_docs(src)), [])

    def test_unmatched_signal_makes_no_edge(self):
        src = ("# [R](r)\n## [Quests](quests)\n### [Lonely](lonely)\n"
               "---\nThen: signal nobody_listens\n---\nx\n")
        self.assertEqual(signal_edges(_docs(src)), [])


class TestCausalEdges(unittest.TestCase):
    def test_parent_edge_is_reversed_into_causal_order(self):
        """`Parent: X` is written child->parent but means parent-then-child."""
        src = ("# [R](r)\n## [Quests](quests)\n### [Arc](arc)\n---\nState: active\n---\nx\n"
               "### [Step](step)\n---\nParent: arc\n---\ny\n")
        edges = [e for e in causal_edges(_docs(src)) if e["kind"] == "parent"]
        self.assertEqual([(e["from"], e["to"]) for e in edges], [("arc", "step")])

    def test_reveal_and_choice_keep_their_direction(self):
        src = ("# [R](r)\n## [Dialogue](dialogue)\n"
               "### [A](a)\n% hi\n- [go](b)\n### [B](b)\n% there\n")
        self.assertEqual([(e["from"], e["to"]) for e in causal_edges(_docs(src))],
                         [("a", "b")])


class TestBeats(unittest.TestCase):
    def test_reveal_chain_ranks_into_beats(self):
        tl = timeline(_docs(CHAIN))
        beat = {i["key"]: i["beat"] for i in tl["items"]}
        self.assertEqual((beat["one"], beat["two"], beat["three"]), (0, 1, 2))
        self.assertEqual(tl["beats"], 3)

    def test_longest_path_wins(self):
        """A beat can only happen once EVERY prerequisite has, so a node reachable by
        both a short and a long route ranks at the long one."""
        src = ("# [R](r)\n## [Quests](quests)\n"
               "### [A](a)\n---\nState: active\nThen: reveal b\n---\nx\n"
               "### [B](b)\n---\nThen: reveal c\n---\nx\n"
               "### [C](c)\n---\nThen: reveal d\n---\nx\n"
               "### [D](d)\n---\nx\n")
        extra = ("# [R2](r2)\n## [Quests](quests2)\n### [Shortcut](shortcut)\n"
                 "---\nParent: a\nThen: reveal d\n---\nx\n")
        beat = {i["key"]: i["beat"] for i in timeline(_docs(src, extra))["items"]}
        self.assertEqual(beat["d"], 3)          # a->b->c->d, not a->shortcut->d

    def test_cycle_is_broken_and_reported(self):
        """A dialogue hub you return to has no topological order; ranking must still
        terminate, and the loop is reported so the view can badge it."""
        src = ("# [R](r)\n## [Dialogue](dialogue)\n"
               "### [Hail](hail)\n% hi\n- [shop](shop)\n"
               "### [Shop](shop)\n% wares\n- [back](hail)\n")
        tl = timeline(_docs(src))
        self.assertEqual([(c["from"], c["to"]) for c in tl["cycles"]], [("shop", "hail")])
        self.assertTrue(all(i["cycle"] for i in tl["items"]))


class TestTracks(unittest.TestCase):
    JOBS = ("# [R](r)\n## [Jobs](jobs)\n"
            "### [Gunnery](job_gunnery)\n---\nState: idle\nGoal: signal 5 drone_down\n"
            "Pays: 200 credits\n---\nShoot the drones.\n"
            "### [Rocks](job_rocks)\n---\nState: idle\nGoal: signal 4 rock_cleared\n"
            "---\nClear the lane.\n")

    def test_unordered_job_board_goes_to_the_pool(self):
        """Laying a dozen independent `State: idle` jobs out as a sequence would invent
        an order the author never wrote."""
        tl = timeline(_docs(self.JOBS))
        self.assertEqual({i["track"] for i in tl["items"]}, {"pool"})
        self.assertEqual(tl["beats"], 1)

    def test_chained_and_active_content_is_spine(self):
        tl = timeline(_docs(CHAIN))
        self.assertEqual({i["track"] for i in tl["items"]}, {"spine"})

    def test_required_flag_forces_spine(self):
        src = ("# [R](r)\n## [Jobs](jobs)\n### [Must](must)\n"
               "---\nState: idle\nRequired: true\n---\nx\n")
        item = timeline(_docs(src))["items"][0]
        self.assertEqual(item["track"], "spine")
        self.assertTrue(item["required"])

    def test_win_prose_still_counts_as_a_flag(self):
        """`Win:` takes end-screen prose after it, so anything but an explicit false
        is a win flag - matching how amd_quest reads it."""
        src = ("# [R](r)\n## [Jobs](jobs)\n### [End](end)\n"
               "---\nState: idle\nWin: The sector is safe.\n---\nx\n")
        self.assertTrue(timeline(_docs(src))["items"][0]["required"])


class TestDeclaredDuration(unittest.TestCase):
    def test_minutes_and_seconds(self):
        self.assertEqual(declared_duration({"fail after": "6 minutes"})["seconds"], 360)
        self.assertEqual(declared_duration({"fail after": "90 seconds"})["seconds"], 90)

    def test_bare_number_is_minutes_like_the_engine(self):
        """`amd_quest` defaults the unit to minutes; the view must not disagree with
        the clock the engine actually runs."""
        self.assertEqual(declared_duration({"complete after": "2"})["seconds"], 120)

    def test_absent_is_none(self):
        self.assertIsNone(declared_duration({"state": "idle"}))


class TestLanes(unittest.TestCase):
    def test_console_lanes_come_from_declared_consoles_and_scan_goals(self):
        src = ("# [R](r)\n## [Jobs](jobs)\n"
               "### [Survey](survey)\n---\nState: idle\nGoal: scan 3 anomaly\n---\nx\n"
               "### [Dock Job](dockjob)\n---\nState: idle\nAccept on: comms, admiral\n---\nx\n")
        tl = timeline(_docs(src))
        groups = {i["key"]: i["groups"]["console"] for i in tl["items"]}
        self.assertEqual(groups["survey"], ["science"])
        self.assertEqual(groups["dockjob"], ["comms", "admiral"])
        self.assertEqual(tl["lanes"]["console"], ["science", "comms", "admiral"])

    def test_scan_tab_is_not_a_console_lane(self):
        """`Tab:` names a SCIENCE tab (mat / bio / intel), not a console - folding those
        in invents lanes nobody is sitting at."""
        src = ("# [R](r)\n## [Scans](scans)\n### [Hull](hull)\n"
               "---\nScan of: raider\nTab: mat\n---\nx\n")
        self.assertNotIn("mat", timeline(_docs(src))["lanes"]["console"])

    def test_single_record_arc_collapses_to_its_section(self):
        """A one-record arc says nothing; a board of them would render as a dozen lanes
        of one, which reads as structure that isn't there."""
        tl = timeline(_docs(TestTracks.JOBS))
        self.assertEqual(tl["lanes"]["arc"], ["jobs"])


class TestDuplicateKeys(unittest.TestCase):
    """A bare key is unique only among SIBLINGS - nested records are addressed by
    path, so two jobs can each own a step called `scan`."""
    DUP = ("# [R](r)\n## [Jobs](jobs)\n"
           "### [Ghost Freighter](job_ghost)\n---\nState: idle\n---\nx\n"
           "#### [Hail](hail)\n---\nState: secret\n---\na\n"
           "#### [Scan the Derelict](scan)\n---\nState: secret\n---\nb\n"
           "### [Sweep](job_sweep)\n---\nState: idle\n---\ny\n"
           "#### [Deploy](deploy)\n---\nState: secret\n---\nc\n"
           "#### [Scan the Contact](scan)\n---\nState: secret\n---\nd\n")

    def test_shadowed_records_are_not_dropped(self):
        """Keying on the bare key silently loses the second `scan` - and a record no
        view can show is the exact silent failure this tooling exists to end."""
        tl = timeline(_docs(self.DUP))
        scans = [i for i in tl["items"] if i["key"] == "scan"]
        self.assertEqual(len(scans), 2)
        self.assertEqual({i["display"] for i in scans},
                         {"Scan the Derelict", "Scan the Contact"})

    def test_each_scan_belongs_to_its_own_job(self):
        tl = timeline(_docs(self.DUP))
        by_display = {i["display"]: i for i in tl["items"]}
        parents = {i["uid"]: i["key"] for i in tl["items"]}
        self.assertEqual(parents[by_display["Scan the Derelict"]["parent"]], "job_ghost")
        self.assertEqual(parents[by_display["Scan the Contact"]["parent"]], "job_sweep")

    def test_uid_is_uri_plus_path(self):
        tl = timeline(_docs(self.DUP))
        derelict = next(i for i in tl["items"] if i["display"] == "Scan the Derelict")
        self.assertEqual(derelict["path"], "r/jobs/job_ghost/scan")
        self.assertTrue(derelict["uid"].endswith("#r/jobs/job_ghost/scan"))

    def test_path_reference_beats_an_ambiguous_bare_key(self):
        """`Then: reveal job_sweep/scan` must reach THAT scan, not the first namesake."""
        src = self.DUP + ("### [Trigger](trigger)\n---\nState: active\n"
                          "Then: reveal job_sweep/scan\n---\ne\n")
        tl = timeline(_docs(src))
        by_display = {i["display"]: i for i in tl["items"]}
        target = by_display["Scan the Contact"]["uid"]
        edge = next(e for e in tl["edges"] if e["kind"] == "reveal")
        self.assertEqual(edge["toUid"], target)

    def test_ambiguous_bare_key_makes_no_edge(self):
        """A wrong edge would move a beat; a silently wrong timeline is worse than a
        missing line, so an unresolvable bare key resolves to nothing."""
        src = self.DUP + ("### [Trigger](trigger)\n---\nState: active\n"
                          "Then: reveal scan\n---\ne\n")
        self.assertEqual([e for e in timeline(_docs(src))["edges"] if e["kind"] == "reveal"], [])


class TestSteps(unittest.TestCase):
    def test_undeclared_step_order_falls_back_to_document_order(self):
        """The multi-step Peacetime jobs carry no `Then: reveal` chain - the order is
        replayed by a MAST sequencer in the order the steps are WRITTEN."""
        src = ("# [R](r)\n## [Jobs](jobs)\n### [Ghost](job_ghost)\n---\nState: idle\n---\nx\n"
               "#### [Hail](hail)\n---\nState: secret\n---\na\n"
               "#### [Scan](scan)\n---\nState: secret\n---\nb\n"
               "#### [Tow](tow)\n---\nState: secret\n---\nc\n")
        tl = timeline(_docs(src))
        container = next(i for i in tl["items"] if i["key"] == "job_ghost")
        self.assertEqual(container["steps"], 3)
        self.assertTrue(container["stepsInferred"])
        steps = {i["key"]: i["step"] for i in tl["items"] if i["parent"] == container["uid"]}
        self.assertEqual(steps, {"hail": 0, "scan": 1, "tow": 2})
        self.assertTrue(all(i["stepInferred"] for i in tl["items"]
                            if i["parent"] == container["uid"]))

    def test_declared_edges_win_and_are_not_flagged_inferred(self):
        src = ("# [R](r)\n## [Q](quests)\n### [Case](case)\n---\nState: active\n---\nx\n"
               "#### [One](one)\n---\nThen: reveal case/two\n---\na\n"
               "#### [Two](two)\n---\nThen: reveal case/three\n---\nb\n"
               "#### [Three](three)\nc\n")
        tl = timeline(_docs(src))
        container = next(i for i in tl["items"] if i["key"] == "case")
        self.assertFalse(container["stepsInferred"])
        steps = {i["key"]: i["step"] for i in tl["items"] if i["parent"] == container["uid"]}
        self.assertEqual(steps, {"one": 0, "two": 1, "three": 2})

    def test_unconstrained_sibling_stays_at_step_zero(self):
        """Florbin's `alive` is a standing fail-condition, not the fifth step - so a
        container with SOME declared edges never invents a position for the rest."""
        src = ("# [R](r)\n## [Q](quests)\n### [Case](case)\n---\nState: active\n---\nx\n"
               "#### [One](one)\n---\nThen: reveal case/two\n---\na\n"
               "#### [Two](two)\nb\n"
               "#### [Keep Alive](alive)\n---\nFail on signal: died\n---\nc\n")
        tl = timeline(_docs(src))
        steps = {i["key"]: i["step"] for i in tl["items"] if i["parent"]}
        self.assertEqual(steps["alive"], 0)
        self.assertEqual(steps["two"], 1)

    def test_lifecycle_fields_are_carried(self):
        src = ("# [R](r)\n## [Jobs](jobs)\n### [Mercy](job_mercy)\n---\nState: idle\n"
               "On accept: toast Job accepted\nGoal: signal mercy_reached\n"
               "Fail after: 6 minutes\n---\nx\n")
        it = timeline(_docs(src))["items"][0]
        self.assertEqual(it["lifecycle"]["goal"], "signal mercy_reached")
        self.assertEqual(it["lifecycle"]["on_accept"], "toast Job accepted")
        self.assertIsNone(it["lifecycle"]["fail_signal"])
        self.assertEqual(it["declared"]["seconds"], 360)


class TestFlatFiles(unittest.TestCase):
    FLAT = ("# [Patrol Sweep](patrol)\n---\nState: idle\nGoal: signal patrol_done\n---\nx\n"
            "# [Standing Bounty](bounty)\n---\nState: idle\n---\ny\n")

    def test_records_at_hash_one_are_still_records(self):
        """A per-section file handed straight to a loader has no root or group heading -
        its records ARE the `#` headings, and reading it as zero records is how a whole
        file goes silently missing from a view."""
        tl = timeline([("file:///m/jobs.amd", parse(self.FLAT))])
        self.assertEqual({i["key"] for i in tl["items"]}, {"patrol", "bounty"})

    def test_flat_file_section_is_the_file_name(self):
        tl = timeline([("file:///m/jobs.amd", parse(self.FLAT))])
        self.assertEqual({i["groups"]["section"] for i in tl["items"]}, {"jobs"})

    def test_toc_model_still_skips_root_and_sections(self):
        tl = timeline(_docs(CHAIN))
        self.assertEqual({i["key"] for i in tl["items"]}, {"one", "two", "three"})


if __name__ == "__main__":
    unittest.main()
