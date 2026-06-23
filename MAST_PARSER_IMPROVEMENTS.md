# MAST Parser — Performance & Robustness Improvements

Tracking doc for proposed and applied changes to the MAST compiler
(`sbs_utils/mast/`). Started 2026-06-23.

The hand-rolled tokenizer lives in `Mast._compile()` ([mast.py](sbs_utils/mast/mast.py)).
It scans source line-by-line, trying each registered node's regex in order until
one matches. None of the changes below alter MAST language semantics
(backward-compatibility constraint).

---

## Status overview

| # | Item | Type | Status |
|---|------|------|--------|
| 1 | pos-cursor instead of O(n²) source slicing | perf | ✅ Done (committed `be6b664`) |
| 2 | First-char/prefix node dispatch (cut O(nodes×lines)) | perf | ✅ Done (uncommitted) |
| 3 | Hoist logger + guard per-line debug f-string | perf | ✅ Done (committed `be6b664`) |
| 4 | Log `FileHandler` leak per `Mast()` construction | perf/robust | ✅ Done (uncommitted) |
| 5 | Latent `NoneType` deref on indent (`prev_node.is_inline_label`) | robust | ✅ Done (uncommitted) |
| 6 | `raise "<string>"` in assign.py yaml paths (TypeError masks error) | robust | ✅ Done (uncommitted) |
| 7 | Bare `except:` in `content_from_lib_or_file` hides load errors | robust | ✅ Done (uncommitted) |
| 8 | Per-compile state object (if/match/await chains are class-level) | robust | ⬜ Proposed |
| 9 | Inconsistent error recovery (some bail, some continue) | robust | ⬜ Proposed |
| 10 | Regex typo `STRING_REGEX_NAMED_3` — stray `"` in group name | robust | ✅ Done (uncommitted) |
| 11 | `compile_formatted_string` breaks on `"""` in user text | robust | ✅ Done (uncommitted) |

---

## ✅ Done — #1 pos-cursor + #3 logging hygiene

### What changed (5 files, no language-semantics change)
- **[mast.py](sbs_utils/mast/mast.py)** — `_compile()` now walks an integer `pos`
  cursor using `rule.match(src, pos)` instead of re-slicing the remaining source
  on every token. Whitespace helpers (`first_non_whitespace_index`,
  `first_non_newline_index`, `first_newline_index`) take a `start` arg and return
  **absolute** indices. The per-line `logger.debug` f-string is now guarded by
  `isEnabledFor(DEBUG)` and the logger is hoisted out of the loop.
- **[mast_node.py](sbs_utils/mast/mast_node.py)**, **[yield_cmd.py](sbs_utils/mast/core_nodes/yield_cmd.py)**,
  **[with_cmd.py](sbs_utils/mast/core_nodes/with_cmd.py)**, **[on_signal.py](sbs_utils/mast/core_nodes/on_signal.py)**
  — `parse(cls, src, pos=0)`. Because `re.match(s, 0) ≡ re.match(s)`, every
  existing single-arg caller keeps working unchanged.

### Why it works
Each `lines = lines[...]` slice copied the entire rest of the file → O(n²) over a
mission. `match(src, pos)` anchors at `pos` with no copy, so the slice cost is gone
and only the matched token (small) is copied for error messages.

### Benchmark (synthetic missions: assigns, f-strings, if/elif/else, for, calls)

| labels | lines | size | old | new | speedup |
|---:|---:|---:|---:|---:|---:|
| 100 | 1.5K | 29 KB | 33 ms | 27 ms | 1.2× |
| 800 | 12K | 237 KB | 294 ms | 216 ms | 1.4× |
| 1600 | 24K | 478 KB | 724 ms | 447 ms | 1.6× |
| 3200 | 48K | 961 KB | **2567 ms** | **909 ms** | **2.8×** |

Per-doubling scaling factor (the real signal):
- Old: 1.87 → 2.12 → 2.25 → 2.46 → **3.55** (accelerating → O(n²))
- New: 2.04 → 1.95 → 2.04 → 2.07 → **2.03** (flat → O(n))

Win compounds with file size; the quadratic term is eliminated.

### Verification
- `python -m unittest discover -s tests` → **335 tests OK**
- Baseline numbers captured by `git stash` of the 5 files, re-running the bench,
  then `git stash pop`.

Benchmark script: `scratchpad/bench_compile.py` (session scratchpad, not in repo).

---

## ✅ Done — #2 first-character node dispatch

### What changed
- **New [first_chars.py](sbs_utils/mast/first_chars.py)** — `first_chars_for_pattern()`
  statically analyzes a compiled regex (via `re._parser`) and returns the set of
  characters it can match first, or `None` for "matches anything". **Safety
  invariant: never under-claim** — any uncertain construct (`.`, `\w`/categories,
  negated sets, anything unrecognized) collapses to `None` (never skip).
- **[mast.py](sbs_utils/mast/mast.py)** — the compile loop now tries only the
  nodes whose first-char set contains the line's first char (cached per char).
  This **only skips** nodes that provably can't match; it never reorders, so the
  "first match wins" ordering is preserved exactly.
- **New [tests/test_mast_dispatch.py](tests/test_mast_dispatch.py)** — walks a
  multi-node sample and asserts the full-scan winner is always a dispatch
  candidate (the under-claim guard), plus analyzer spot-checks.

### Why it's safe
Dispatch is a pure filter on the existing ordered loop: a node is skipped only
when its first-char set is non-`None` and excludes the current char. Correctness
therefore reduces to "first-char sets never under-claim", which the analyzer
guarantees by collapsing all uncertainty to `None`. The new test encodes this
invariant for regression.

### Validation
- Differential check over **all 245 `.mast` files in `data/missions`**
  (22,423 tokens): **0 under-claim violations**; the analyzer derived concrete
  sets for every node except the two genuine catch-alls (`FuncCommand`, `Assign`).
  It even tightened `Import` to `{f,i}` by unioning the optional `from ` prefix.
- Dispatch issues only **15.8% of the `parse()` calls** the full scan did
  (~6.3× fewer regex attempts per line).
- `python -m unittest discover -s tests` → **338 tests OK** (335 + 3 new).

### Benchmark (cumulative with #1)

| labels | orig | after #1 | after #1+#2 | total |
|---:|---:|---:|---:|---:|
| 100 | 33 ms | 27 ms | 18 ms | **1.8×** |
| 800 | 294 ms | 216 ms | 146 ms | **2.0×** |
| 1600 | 724 ms | 447 ms | 304 ms | **2.4×** |
| 3200 | 2567 ms | 909 ms | 631 ms | **4.1×** |

Scaling stays linear (2.0–2.1× per doubling). At ~1 MB the compiler is now
**4.1× faster** than the original.

---

## ✅ Done — #4/#10/#11 small robustness fixes

- **#4** [mast.py](sbs_utils/mast/mast.py) `Mast.__init__`: removed/closed any
  existing `FileHandler`s on the `mast.compile`/`mast.runtime` loggers before
  adding fresh ones, so repeated compiles no longer stack duplicate handlers or
  leak file handles.
- **#10** [mast_node.py](sbs_utils/mast/mast_node.py): fixed the stray `"` in
  `STRING_REGEX_NAMED_3`'s group name (`(?P<{name}">…)` → `(?P<{name}>…)`); it
  was an unused but compile-on-use landmine (invalid group name).
- **#11** [mast_node.py](sbs_utils/mast/mast_node.py): added a shared
  `compile_format_string()` that picks a triple-quote delimiter not present in
  the text (and not escaped by a trailing quote), and raises a clear error if it
  can't wrap safely. The three duplicated copies — `MastNode.compile_formatted_string`,
  [style.py](sbs_utils/procedural/style.py) `compile_formatted_string`, and
  [mastscheduler.py](sbs_utils/mast/mastscheduler.py) `compile_and_format_string`
  — now delegate to it. New [tests/test_mast_format.py](tests/test_mast_format.py).

All 344 tests pass (6 new).

---

## ✅ Done — #5/#6/#7 latent crashes & masked errors

Small, independent defensive fixes (no behavior change on the happy path):

- **#5** [mast.py](sbs_utils/mast/mast.py) indent handling: when `prev_node is
  None` the code dereferenced `prev_node.is_inline_label`. Now guarded
  (`prev_node is None or not prev_node.is_inline_label`) so indenting under
  nothing yields a clean "Bad indentation" error instead of an `AttributeError`.
- **#6** [assign.py](sbs_utils/mast/core_nodes/assign.py): the yaml-assign error
  paths did `raise "<str>"` (a `TypeError` in Py3 that masked the real message;
  one wasn't even an f-string). Now `raise Exception(f"...")`.
- **#7** [mast.py](sbs_utils/mast/mast.py) `content_from_lib_or_file`: bare
  `except:` → `except Exception as e:` and the cause `{e}` is appended to the
  message (no longer swallows `KeyboardInterrupt`/`SystemExit` or hides why a
  file failed to load).

All 338 tests pass.

---

## ⬜ Proposed — robustness / correctness

### #8 Per-compile state object
`IfStatements.if_chains` ([conditional.py:11](sbs_utils/mast/core_nodes/conditional.py#L11)),
`MatchStatements.chains` ([conditional.py:107](sbs_utils/mast/core_nodes/conditional.py#L107)),
and `Await.stack` are class-level, shared across all compiles. An aborted compile
leaves stale entries that corrupt the next mission's compile (the commented-out
cleanup block and manual `Await.stack.clear()` are symptoms). `if_chains` keyed only
by indent can alias unrelated blocks at the same column. Move into a per-compile
context passed via `compile_info`.

### #9 Inconsistent error recovery
Some errors `break` and continue the file; others `return errors` immediately. For a
more robust compiler, collect errors and resync at the next top-level label. The
`if not parsed` fallback message "Error at first newline index" should include the
offending text.

---

## Suggested priority

| Effort | Payoff | Item |
|---|---|---|
| ~~Medium~~ | ~~High~~ | ✅ #1 pos-cursor (done) |
| ~~Low~~ | ~~Med~~ | ✅ #2 first-char dispatch (done) |
| Medium | High | #8 per-compile state (correctness on re-compile) — **next** |
| ~~Low~~ | ~~Med~~ | ✅ #5, #6, #7 latent crashes/masks (done) |
| ~~Low~~ | ~~Low~~ | ✅ #3, #4 logging; #10, #11 regex/format (done) |
| Low | Low | #9 error-recovery consistency |
