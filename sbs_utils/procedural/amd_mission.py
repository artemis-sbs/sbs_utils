"""Combined per-mission AMD vocabulary - one parser that understands the standard content
sections (quests + science scans + landmarks) so a mission can author them all in ONE .amd
file (the amd_doc table-of-contents model) instead of a file per subsystem.

Each `##` section is then handed to its own loader:
    doc = document_get_amd_file(path, data_parser=amd_mission_data)
    quest_grant_amd(agent, amd_section(doc, "quests"))
    science_define_scan_amd(amd_section(doc, "scans"))
    landmarks_spawn(amd_section(doc, "landmarks"))

Mirrors how Open Universe composes one universe.amd from the quest vocabulary plus its own
labels. Sides are intentionally NOT chained here (they are usually a mission-global concern,
not per-map content); use amd_chain to build a different combination if you need one.
"""
from sbs_utils.procedural.amd import amd_parse_facts, amd_chain
from sbs_utils.procedural.amd_quest import amd_quest_facts
from sbs_utils.procedural.amd_science import amd_scan_facts
from sbs_utils.procedural.amd_landmarks import amd_landmark_facts


def amd_mission_facts(aliases=None):
    """The chained handler: quest, then science-scan, then landmark vocabularies."""
    return amd_chain(amd_quest_facts(aliases), amd_scan_facts(), amd_landmark_facts())


def amd_mission_data(text, aliases=None):
    """Parse one fence with the combined quest+scan+landmark vocabulary. Use as the
    ``data_parser`` for a consolidated mission .amd."""
    return amd_parse_facts(text, amd_mission_facts(aliases))
