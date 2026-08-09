r"""A deterministic .amd corpus, and a flat rendering of how it parses.

Feeds tests/test_amd_parse_golden.py. The point is a byte-exact net under the
AMD reader BEFORE it grows a schema memo, a document cache and a generation
counter -- every one of which is a change to a hot path that could shift a
parsed field somewhere nobody looks. The corpus covers the parts that INTERACT,
since those are what a refactor breaks: heading nesting and the stack unwind,
fence data through the archetype/kind chain, the value coercers, cut text,
transclusion and wikilinks (which run as post-passes over the whole tree),
synopsis extraction, and query-string keys.

The sources are PYTHON STRINGS, not checked-in .amd files, and that is
deliberate. `core.autocrlf=true` on Windows rewrites the line endings of a
checked-in text file, so a `.amd` fixture's bytes would be decided by the
developer's git config -- and CRLF-vs-LF handling is exactly what this corpus
has to pin (see the comment on RE_HEADING in procedural/amd.py, where one file
read two ways produced two different documents). A literal \r\n in a Python
string is the same on every machine.
"""
import json

from sbs_utils.procedural.quest import document_get_amd_file
from sbs_utils.procedural.amd_quest import amd_quest_data


# --- the sources ------------------------------------------------------------

QUEST_ARC = """\
# [Silver Reach](silver_reach)
---
Arc
---
The frontier run.

## [Escort the convoy](escort)
---
Job
Starts when: signal convoy_ready
Done when: destroy 3 raiders
Fails when: 5 minutes
Reward: 250 credits
Scope: ship
Accept on: comms, science
---
The convoy needs cover.

### [Clear the lane](escort/clear)
---
Done when: scan 2 mines
Then: reveal escort/paid
---

### [Collect payment](escort/paid)
---
State: secret
Done when: dock silver_station
Reward: 100 credits
---

## [Hold the line](hold)
---
Beat
Done when: signal line_held
Action: raider_camp becomes hostile
---
Back at the top level.
"""

DIALOGUE = """\
# [Officers](officers)
Dialogue

## [Ashfang](ashfang)
---
Speaker: ashfang
Face: skaraan/male/01
Color: #86c
---
@greeting
% Well met, captain.
% You again.
% State your business.

@threat if reputation < 0
% You have no friends here.
"""

BONEYARD_LINKS = """\
# [Docking](docking)
How docking works: request, approach, hold.

/* This paragraph is cut text. It must not reach any description,
   and it must not hide the heading below it. */

# [Resupply](resupply)
![[docking]]
See also [[docking]] and [[missing_key]].
"""

# Same shape as a QUEST_ARC record, but CRLF on every line.
CRLF = "\r\n".join([
    "# [Escort](escort)",
    "---",
    "Kind: Job",
    "Done when: destroy 3 raiders",
    "Reward: 250 credits",
    "---",
    "Body line one.",
    "Body line two.",
    "",
])

NONASCII = """\
# [Cafe Verdant](verdant)
The cafe's owner -- Rene -- keeps a 30 degree list to port.
Prices in euros. Naive travellers pay double.
"""

QUERY_AND_SYNOPSIS = """\
# [Board](board?tab=jobs&sort=tier)
= Why this exists: the job board is the mission's front door.
Pick up work here.

## [Fine print](board/fine)
= Never rendered.
Rendered.
"""

URGE_AND_DROP = """\
# [Scavengers](scavengers)
---
Urge
---

## [Loot the wreck](loot)
---
Whenever: 2 salvage
Until: quest looted complete
Weight: 3
---

# [Raider drops](raider_drops)
Kind: Drop

## [Common](raider_common)
---
Drops: salvage 40%, plating 25%, nothing 35%
---
"""

LANDMARKS = """\
# [Silver Station](silver_station)
---
Landmark
Kind: station
At: 12000, 0, -4000
Makeup: 2 raider, 1 destroyer
Color: white
---
"""

DEEP_UNWIND = """\
# [A](a)
## [two](a/b)
### [three](a/b/c)
## [back to two](d)
# [E](e)
"""

CASES = [
    ("quest_arc", QUEST_ARC, {}),
    ("dialogue", DIALOGUE, {}),
    ("boneyard_links", BONEYARD_LINKS, {}),
    ("crlf", CRLF, {}),
    ("nonascii", NONASCII, {}),
    ("query_and_synopsis", QUERY_AND_SYNOPSIS, {}),
    ("urge_and_drop", URGE_AND_DROP, {}),
    ("landmarks", LANDMARKS, {}),
    ("deep_unwind", DEEP_UNWIND, {}),
    # The same source read with the OTHER two reader options, because both
    # change which lines become records.
    ("quest_arc.bare_headings", QUEST_ARC, {"allow_bare_headings": True}),
    ("boneyard_links.keep_comments", BONEYARD_LINKS, {"strip_comments": False}),
    # ...and through the quest fence parser, which is the path quests actually take.
    ("quest_arc.quest_data", QUEST_ARC, {"data_parser": amd_quest_data}),
    ("urge_and_drop.quest_data", URGE_AND_DROP, {"data_parser": amd_quest_data}),
]


# --- flattening -------------------------------------------------------------

def _val(v):
    """One value, rendered so a diff points at what moved. `default=str` keeps
    an unexpected object (an Exception, a MastDataObject) from failing the dump
    -- the golden line then SHOWS it, which is the signal we want."""
    return json.dumps(v, sort_keys=True, default=str, ensure_ascii=False)


def _walk(node, case, path, out):
    key = node.get("key")
    here = f"{path}/{key}" if path else str(key)
    for field in sorted(k for k in node.keys() if k != "children"):
        out.append(f"{case}|{here}|{field}={_val(node.get(field))}")
    kids = node.get("children") or []
    out.append(f"{case}|{here}|#children={len(kids)}")
    for child in kids:
        _walk(child, case, here, out)


def parse_lines():
    """Every case, flattened to one line per node field."""
    out = []
    for name, content, kwargs in CASES:
        tree = document_get_amd_file(None, "root", content=content, **kwargs)
        _walk(tree, name, "", out)
    return out
