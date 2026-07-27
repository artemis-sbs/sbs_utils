"""Story-FLOW analysis over a parsed AMD document set - the model behind the
Story Timeline view, and the shared source of the **signal edges** the Story Graph
and the Resolver also read.

Two things live here that `amd_core` (per-document, position-tracking) can't do
because they are mission-wide joins:

1. **Signal edges.** `Then: signal X` (or a choice's `... signal X`) in one node and
   `When: signal X` / `Goal: signal X` / `Fail on signal: X` in another is a real
   causal link, but the two halves are usually in different files, so no per-document
   pass can see it. Without it a signal-driven mission looks like disconnected
   confetti - every node a root. `causal_edges` joins them.

2. **Beat ranking.** AMD has no clock; what it has is causal order. `timeline` ranks
   every node by longest path from the start set, so "beat 3" means *at least three
   things must happen first* - act structure, not seconds. The only real duration in
   the language is `Fail after:` / `Complete after:`, carried per item as `declared`
   so a view can draw a deadline without pretending to know a bar's width.

Edge DIRECTION is normalized to causal order, which is not always the direction the
reference is written in: `Parent: X` is written child->parent but means parent-then-
child, so it is emitted reversed. `Scene:`/`Then: reveal`/choices/signals all already
point the way time runs.

Dependency-light like the rest of the AMD tooling: the shared vocabulary primitives
(`amd.py`) and the parser (`amd_core`), nothing from the engine - so it ships in
`sbs.pyz`, unit-tests offline, and can't drag engine imports into the language server.
"""
from sbs_utils.procedural.amd import amd_signal_name, amd_duration_seconds
from sbs_utils.procedural.amd_core import section_of, span_range
from sbs_utils.procedural.amd_quest import amd_console_list

# Reference kinds that carry story flow, and whether the written direction already
# matches causal order (`Parent:` is the one that doesn't - see the module docstring).
_FLOW_KINDS = {"choice": True, "scene": True, "reveal": True, "parent": False}

# Fence labels whose truthiness puts a record on the SPINE (the critical path) rather
# than in the optional pool.
_SPINE_FLAGS = ("Required", "Critical", "Win", "Lose")

_FALSE = ("false", "no", "0")


def _flag(lut, label):
    """A spine flag's truth, read the way `amd_quest` reads it: `Required:`/`Critical:`
    are bare flags (only an explicit true/yes/1/empty counts), while `Win:`/`Lose:`
    accept end-screen prose after them, so anything but an explicit false counts."""
    value = _field(lut, label)
    if value is None:
        return False
    low = str(value).strip().lower()
    if label in ("Win", "Lose"):
        return low not in _FALSE
    return low in ("", "true", "yes", "1")


def _fields(node):
    """`Label: value` pairs from a node's `---` fence, in source order. Reads the raw
    fence lines (not the coerced `data` dict) so a view can round-trip what was typed."""
    out = []
    for _ln, raw in (node.fence_lines or []):
        s = raw.strip()
        if not s or s.startswith("//") or ":" not in raw:
            continue
        label, value = raw.split(":", 1)
        out.append((label.strip(), value.strip()))
    return out


def _field(lut, label):
    """A fence value by label, from the record's prebuilt lower-cased lookup. Tolerant
    of the underscore spelling (`fail_after` == `Fail after`), so callers never have to
    pass both - forgetting the variant used to fail silently as "field absent"."""
    low = label.lower()
    if low in lut:
        return lut[low]
    return lut.get(low.replace(" ", "_"), lut.get(low.replace("_", " ")))


def _record_level(doc):
    """The heading level this document's RECORDS live at.

    Two file shapes are both legal and both in production. In the table-of-contents
    model (one `.amd` per mission) `#` is the mission root, `##` are section groups and
    records start at `###`. But a per-section file - `jobs.amd`, `bridge_stories.amd`,
    handed to a loader whole - has no root or group at all: its records are the `#`
    headings. Keying off "does anything nest deeper than a section?" tells the two
    apart, so a flat file isn't silently read as zero records."""
    return 3 if any((n.level or 0) > 2 for n in doc.nodes) else 1


def _file_section(uri):
    """A flat file's implied section: its own name (`.../jobs.amd` -> `jobs`), which is
    exactly the key its loader is handed (`amd_section(doc, "jobs")`)."""
    stem = str(uri).replace("\\", "/").rstrip("/").split("/")[-1]
    return stem[:-4] if stem.lower().endswith(".amd") else stem


def _path_of(node):
    """A record's PATH - the heading keys from the file root down to it, joined with
    `/` (`job_ghost/scan`). This, not the bare key, is what identifies a record: nested
    records are addressed by path, so sibling keys must be unique but cousins need not
    be, and three different `scan` steps under three different jobs are three records."""
    parts, walk = [], node
    while walk is not None and walk.key != "__root__":
        parts.append(walk.key)
        walk = walk.parent
    return "/".join(reversed(parts))


def _story_nodes(docs):
    """Every story record across the set as `(uri, doc, node, section, path)`.

    De-duplicated by (uri, PATH), not by bare key. Keying on the bare key silently
    drops a record whose key is reused elsewhere - which is not a rare edge case: it
    loses three of Peacetime's job steps (`job_sweep/scan`, `job_sweep/recover`,
    `job_cache/recover`, each shadowed by a namesake under a different job) and eight
    Open Universe records. A dropped record is invisible in every view that reads this,
    which is exactly the silent failure the AMD tooling exists to end.
    """
    out, seen = [], set()
    for uri, doc in docs:
        level = _record_level(doc)
        for n in doc.nodes:
            if (n.level or 0) < level:
                continue
            path = _path_of(n)                 # walked once, reused by every later pass
            if (uri, path) in seen:
                continue
            seen.add((uri, path))
            out.append((uri, doc, n, section_of(n) if level > 1 else _file_section(uri), path))
    return out


def records(docs):
    """Records plus the indexes every pass needs, keyed by a unique **uid**
    (`<uri>#<path>`) so two `scan` steps under two different jobs stay two records.

    Public because it is the single definition of *what a record is* - the language
    server's Graph and Resolver read it too, so all three views agree on which headings
    exist (they each used to re-derive it, and each dropped the same records).

    Each record carries its fence `fields` parsed ONCE (with a lower-cased lookup
    table): the item pass reads ~17 labels per record, and re-deriving that map per
    lookup was the single largest cost in the profile."""
    recs = []
    for uri, doc, node, section, path in _story_nodes(docs):
        fields = _fields(node)
        recs.append({"uid": uri + "#" + path, "uri": uri, "doc": doc, "node": node,
                     "section": section, "path": path,
                     "fields": fields, "lut": {l.lower(): v for l, v in fields}})
    by_key = {}
    for r in recs:
        by_key.setdefault(r["node"].key, []).append(r["uid"])
    return recs, {r["uid"]: r for r in recs}, by_key


def _uid_by_node(recs):
    """`id(AmdNode) -> uid`, so a parent lookup is a dict hit rather than another walk
    up the heading chain."""
    return {id(r["node"]): r["uid"] for r in recs}


def resolve_ref(value, by_key, by_uid, prefer_uri=None):
    """The record a reference points at, as a uid - or None if it can't be pinned down.

    A reference is written as a bare key (`trail`) or a path (`florbin/trail`). A path
    is matched as a path SUFFIX, which is what makes duplicate leaf keys workable: the
    three `recover` steps are told apart by `florbin/recover` vs `job_cache/recover`.
    An ambiguous bare key resolves to nothing rather than to a coin-flip - a wrong edge
    would move a beat, and a silently wrong timeline is worse than a missing line.
    """
    segs = [s for s in str(value).split("/") if s]
    if not segs:
        return None
    cands = list(by_key.get(segs[-1], ()))
    if len(segs) > 1:
        suffix = "/".join(segs)
        exact = [u for u in cands
                 if by_uid[u]["path"] == suffix or by_uid[u]["path"].endswith("/" + suffix)]
        if exact:
            cands = exact
    if len(cands) == 1:
        return cands[0]
    if prefer_uri:                     # a same-file namesake beats a cousin elsewhere
        same = [u for u in cands if by_uid[u]["uri"] == prefer_uri]
        if len(same) == 1:
            return same[0]
    return None


def signal_edges(docs):
    """Emitter -> waiter edges for every signal name emitted by one record and waited
    on by another. Anchored at the EMIT site (that's the line an editor jumps to when
    asked "where does this get triggered from?").

    Each edge carries both bare keys (`from`/`to`, what the Graph indexes by) and uids
    (`fromUid`/`toUid`, what the Timeline ranks by).

    Self-edges are dropped: a node that emits and waits on the same name is a loop the
    author wrote on purpose (a repeatable job), not a beat ordering.
    """
    return signal_edges_for(records(docs)[0])


def signal_edges_for(recs):
    """`signal_edges` over an already-built record set - so one request walks the
    mission once instead of once per public entry point. Public because the language
    server's Graph and Resolver both need it over the record set they already hold."""
    emits, waits = {}, {}
    for rec in recs:
        for r in rec["node"].refs:
            name = amd_signal_name(r.value)
            if r.kind == "signal":
                emits.setdefault(name, []).append((rec, r))
            elif r.kind == "wait_signal":
                waits.setdefault(name, []).append((rec, r))
    edges, seen = [], set()
    for name, srcs in emits.items():
        for rec, r in srcs:
            for wrec, _w in waits.get(name, ()):
                key = (rec["uid"], wrec["uid"], name)
                if rec["uid"] == wrec["uid"] or key in seen:
                    continue
                seen.add(key)
                edges.append({"from": rec["node"].key, "to": wrec["node"].key,
                              "fromUid": rec["uid"], "toUid": wrec["uid"],
                              "kind": "signal", "name": name, "uri": rec["uri"],
                              "line": (r.span.line - 1) if r.span else 0,
                              "targetRange": span_range(r.span) if r.span else None})
    return edges


def causal_edges(docs, known=None):
    """Every flow edge in the set, in causal order: reference edges (choice / scene /
    reveal / parent, the last one reversed) plus the mission-wide signal join.

    Each edge carries bare keys AND uids - see `signal_edges`."""
    return _causal_edges(*records(docs), known=known)


def _causal_edges(recs, by_uid, by_key, known=None):
    """`causal_edges` over an already-built record set (see `_signal_edges`)."""
    known = set(known) if known is not None else set(by_key)
    edges, seen = [], set()
    for rec in recs:
        for r in rec["node"].refs:
            forward = _FLOW_KINDS.get(r.kind)
            if forward is None:
                continue
            target = resolve_ref(r.value, by_key, by_uid, prefer_uri=rec["uri"])
            if target is None or target == rec["uid"]:
                continue
            if rec["node"].key not in known or by_uid[target]["node"].key not in known:
                continue
            src, dst = (rec["uid"], target) if forward else (target, rec["uid"])
            key = (src, dst, r.kind)
            if key in seen:
                continue
            seen.add(key)
            edges.append({"from": by_uid[src]["node"].key, "to": by_uid[dst]["node"].key,
                          "fromUid": src, "toUid": dst, "kind": r.kind, "uri": rec["uri"],
                          "line": (r.span.line - 1) if r.span else 0,
                          "targetRange": span_range(r.span) if r.span else None})
    edges.extend(e for e in signal_edges_for(recs) if e["from"] in known and e["to"] in known)
    return edges


def _rank(keys, edges):
    """Longest-path beat rank per key, plus the back edges that had to be dropped.

    A story can legitimately loop (a hub scene you return to), and a loop has no
    topological order - so DFS finds the back edges, reports them as `cycles` for the
    view to badge, and ranks the remaining DAG. Longest path (not shortest) because a
    beat can only happen once EVERY prerequisite has, so the latest one governs.
    """
    out = {k: [] for k in keys}
    for e in edges:
        if e["from"] in out and e["to"] in out:
            out[e["from"]].append(e["to"])

    # Iterative DFS (missions nest deeper than is comfortable for recursion).
    WHITE, GREY, BLACK = 0, 1, 2
    color = {k: WHITE for k in keys}
    back = set()
    for root in keys:
        if color[root] != WHITE:
            continue
        stack = [(root, iter(out[root]))]
        color[root] = GREY
        while stack:
            node, it = stack[-1]
            nxt = next(it, None)
            if nxt is None:
                color[node] = BLACK
                stack.pop()
                continue
            if color[nxt] == GREY:
                back.add((node, nxt))
            elif color[nxt] == WHITE:
                color[nxt] = GREY
                stack.append((nxt, iter(out[nxt])))

    dag = [e for e in edges if (e["from"], e["to"]) not in back
           and e["from"] in out and e["to"] in out]
    indeg = {k: 0 for k in keys}
    adj = {k: [] for k in keys}
    for e in dag:
        adj[e["from"]].append(e["to"])
        indeg[e["to"]] += 1
    rank = {k: 0 for k in keys}
    queue = [k for k in keys if indeg[k] == 0]
    while queue:
        k = queue.pop()
        for nxt in adj[k]:
            if rank[k] + 1 > rank[nxt]:
                rank[nxt] = rank[k] + 1
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
    cycles = [{"from": a, "to": b} for a, b in sorted(back)]
    return rank, cycles


def declared_duration(lut):
    """Seconds declared by `Fail after:` / `Complete after:`, or None.

    Parsed EXACTLY as `amd_quest.amd_quest_facts` parses it (first integer token; the
    unit is minutes unless the text says "second") so the timeline can never disagree
    with the clock the engine actually runs.
    """
    for label in ("Fail after", "Complete after"):
        value = _field(lut, label)
        if value is None:
            continue
        seconds = amd_duration_seconds(value)
        if seconds is None:
            continue
        return {"seconds": seconds, "label": str(value).strip(), "field": label,
                "fail": label == "Fail after"}
    return None


def _consoles(lut, archetype):
    """Which console(s) this record gives work to - the lane that answers "is Science
    idle for the whole second act?". Declared consoles only (`Accept on:`/`Engage on:`),
    plus science for anything scan-shaped, because that IS where a scan happens. A scan
    record's `Tab:` is deliberately NOT read: those are science TAB names (mat / bio /
    intel), not consoles, and folding them in invents lanes nobody's sitting at."""
    out = []
    for label in ("Accept on", "Engage on"):
        value = _field(lut, label)
        if value:
            out.extend(amd_console_list(value))
    goal = str(_field(lut, "Goal") or "").split()
    if goal and goal[0].lower() in ("scan", "survey"):
        out.append("science")
    if archetype == "scan":
        out.append("science")
    seen, uniq = set(), []
    for c in out:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
    return uniq


def _arcs(nodes, parents):
    """Each record's story ARC - a different question from its section. The arc is the
    top of the record's own chain: an explicit `Parent:` root if it has one, else its
    outermost enclosing RECORD (`#### brief` inside `### florbin` -> `florbin`).

    A one-record arc says nothing, so it collapses back to the section - otherwise a
    job board renders as a dozen lanes of one, which reads as structure that isn't
    there. `parents` maps key -> explicit `Parent:` key.
    """
    label = {}
    arc = {}
    for rec in nodes:
        uid, n, section = rec["uid"], rec["node"], rec["section"]
        label[uid] = section
        seen, cur = {uid}, uid
        while parents.get(cur) and parents[cur] not in seen:
            cur = parents[cur]
            seen.add(cur)
        if cur == uid:                        # no `Parent:` chain - use heading nesting
            walk = n
            while (walk.parent is not None and walk.parent.key != "__root__"
                   and (walk.parent.level or 0) > 2):
                walk = walk.parent
            cur = (rec["uri"] + "#" + _path_of(walk)) if walk.key != n.key else None
        arc[uid] = cur
    # Name the arc by its ROOT RECORD's key (what a writer calls it), not its uid.
    named = {uid: (label[uid] if root is None else _arc_name(root))
             for uid, root in arc.items()}
    counts = {}
    for value in named.values():
        counts[value] = counts.get(value, 0) + 1
    return {u: (v if counts[v] > 1 else label[u]) for u, v in named.items()}


def _arc_name(uid):
    """The display name of an arc identified by uid - its last path segment."""
    return uid.split("#")[-1].split("/")[-1]


def _steps(nodes, edges):
    """Local step order INSIDE each container record (a job with sub-steps).

    A container's children are its steps, but their order is often not declared: the
    four multi-step Peacetime jobs carry no `Then: reveal` chain at all - the order
    lives in a MAST sequencer replaying them in the order they are WRITTEN ("Work the
    steps in order", `pr_ghost_seq`). So:

      * if the children have declared edges between them, rank by those (an author who
        wrote the order gets the order they wrote);
      * if they have NONE, fall back to document order and flag it `inferred`, so the
        view can draw those connectors as assumed rather than asserting them.

    Never mixes the two: a container with SOME edges leaves its unconstrained children
    at step 0 rather than pushing them down the list (Florbin's `alive` is a standing
    fail-condition, not the fifth step), because inventing a position for them is
    exactly the kind of guess the flag exists to avoid.

    Returns `(kids, step, inferred)` - children per container in document order, each
    child's local rank, and the containers whose ranking is a document-order guess.
    """
    uid_of = _uid_by_node(nodes)
    kids, parent_of = {}, {}
    for rec in nodes:
        puid = uid_of.get(id(rec["node"].parent))
        if puid is not None:
            kids.setdefault(puid, []).append(rec["uid"])
            parent_of[rec["uid"]] = puid
    # Bucket the edges by the container they sit inside, once, rather than re-scanning
    # the whole edge list per container.
    local_edges = {}
    for e in edges:
        p = parent_of.get(e["fromUid"])
        if p is not None and parent_of.get(e["toUid"]) == p:
            local_edges.setdefault(p, []).append({"from": e["fromUid"], "to": e["toUid"]})
    step, inferred = {}, set()
    for parent, children in kids.items():
        local = local_edges.get(parent, ())
        if local:
            rank, _cycles = _rank(children, local)
            for k in children:
                step[k] = rank.get(k, 0)
        else:
            inferred.add(parent)
            for i, k in enumerate(children):
                step[k] = i
    return kids, step, inferred, parent_of


# Fence labels that describe a record's own LIFECYCLE - what starts it, what finishes
# it, what kills it. A single-step job has no sub-steps to draw, but it does have this
# shape, and it is where `Fail after:` finally has a real axis (t=0 is acceptance).
_LIFECYCLE = (("goal", "Goal"), ("when", "When"), ("on_accept", "On accept"),
              ("on_complete", "On complete"), ("fail_signal", "Fail on signal"))


def _lifecycle(lut):
    out = {}
    for key, label in _LIFECYCLE:
        value = _field(lut, label)
        out[key] = str(value).strip() if value else None
    return out


def timeline(docs, known=None, archetype_of=None, problems=None):
    """The Story Timeline model.

    `docs` is `[(uri, AmdDocument), ...]`. `archetype_of(key, labels, section)` is the
    optional archetype resolver (`amd_schema.infer_archetype`, injected so this module
    stays dependency-light); `problems` maps key -> lint badge.

    Returns `{items, beats, lanes, edges, cycles}`:
      * **items** - one per record: its `beat` (causal rank), `track` (spine | pool),
        `groups` (the four lane modes), `declared` duration, source position.
      * **beats** - how many columns the view needs.
      * **lanes** - ordered lane values per mode, so the view doesn't re-derive them.
      * **edges** / **cycles** - the causal graph the ranking used, and the loops it
        had to break to rank at all.
    """
    recs, by_uid, by_key = records(docs)
    uids = [r["uid"] for r in recs]
    known = set(known) if known is not None else set(by_key)
    edges = _causal_edges(recs, by_uid, by_key, known)
    # Rank on uids, not keys: two records that share a key are two beats.
    uid_edges = [{"from": e["fromUid"], "to": e["toUid"]} for e in edges]
    rank, cycles = _rank(uids, uid_edges)
    in_cycle = {c["from"] for c in cycles} | {c["to"] for c in cycles}
    # Report loops in the writer's vocabulary (bare keys), uids alongside for precision.
    cycles = [{"from": by_uid[c["from"]]["node"].key, "to": by_uid[c["to"]]["node"].key,
               "fromUid": c["from"], "toUid": c["to"]} for c in cycles]

    degree = {u: 0 for u in uids}
    for e in uid_edges:
        if e["from"] in degree:
            degree[e["from"]] += 1
        if e["to"] in degree:
            degree[e["to"]] += 1

    parents = {}
    for rec in recs:
        value = _field(rec["lut"], "Parent")
        if value:
            target = resolve_ref(value, by_key, by_uid, prefer_uri=rec["uri"])
            if target:
                parents[rec["uid"]] = target
    arcs = _arcs(recs, parents)
    kids, step, step_inferred, parent_of = _steps(recs, edges)

    items = []
    for rec in recs:
        uri, n, section = rec["uri"], rec["node"], rec["section"]
        uid, lut = rec["uid"], rec["lut"]
        labels = [l for l, _v in rec["fields"]]
        arch = archetype_of(labels, section) if archetype_of else None
        state = (_field(lut, "State") or "").strip().lower()
        required = any(_flag(lut, f) for f in _SPINE_FLAGS)
        # SPINE vs POOL. A job board is a dozen `State: idle` records with no edges
        # between them - laying them out as a sequence would invent an order the author
        # never wrote. So only content that is on the critical path (flagged), live at
        # the start (`State: active`), or actually chained to something else gets a beat
        # column; everything else goes to the pool as an availability band.
        spine = required or state == "active" or degree.get(uid, 0) > 0
        items.append({
            "uid": uid, "path": rec["path"],
            "key": n.key, "display": n.display or n.key, "section": section,
            "archetype": arch, "uri": uri,
            "line": (n.span.line - 1) if n.span else 0,
            "beat": rank.get(uid, 0) if spine else 0,
            "track": "spine" if spine else "pool",
            "state": state, "required": required,
            "cycle": uid in in_cycle,
            "declared": declared_duration(lut),
            "problems": (problems or {}).get(n.key),
            # Drill-down: a container's own steps, and this record's place in its
            # parent's. `stepsInferred` says the order below is document order, not
            # something the file declared.
            "steps": len(kids.get(uid, ())),
            "stepsInferred": uid in step_inferred,
            "parent": parent_of.get(uid),
            "step": step.get(uid),
            "stepInferred": parent_of.get(uid) in step_inferred,
            "lifecycle": _lifecycle(lut),
            "groups": {"section": section, "arc": arcs.get(uid, section),
                       "side": (_field(lut, "Side") or "").strip() or None,
                       "console": _consoles(lut, arch)},
        })

    lanes = {}
    for mode in ("section", "arc", "side", "console"):
        seen, order = set(), []
        for it in items:
            value = it["groups"][mode]
            for v in (value if isinstance(value, list) else [value]):
                if v and v not in seen:
                    seen.add(v)
                    order.append(v)
        lanes[mode] = order

    beats = max([it["beat"] for it in items if it["track"] == "spine"] or [0]) + 1
    return {"items": items, "beats": beats, "lanes": lanes,
            "edges": edges, "cycles": cycles}
