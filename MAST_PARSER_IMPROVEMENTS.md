# MAST Parser — Performance & Robustness Improvements

Tracking doc for proposed and applied changes to the MAST compiler
(`sbs_utils/mast/`). Started 2026-06-23.

The hand-rolled tokenizer lives in `Mast._compile()` ([mast.py](sbs_utils/mast/mast.py)).
It scans source line-by-line, trying each registered node's regex in order until
one matches. None of the changes below alter MAST language semantics
(backward-compatibility constraint).

---

## Status overview

All 11 items are complete. Commits on branch `new-lint`:
`be6b664` (#1,#3), `57e59a2` (#2), `eec6eaf` (#5,#6,#7), `f5cf2d6` (#4,#10,#11),
`261c2be` (#8), `+#9`.

| # | Item | Type | Status |
|---|------|------|--------|
| 1 | pos-cursor instead of O(n²) source slicing | perf | ✅ Done |
| 2 | First-char/prefix node dispatch (cut O(nodes×lines)) | perf | ✅ Done |
| 3 | Hoist logger + guard per-line debug f-string | perf | ✅ Done |
| 4 | Log `FileHandler` leak per `Mast()` construction | perf/robust | ✅ Done |
| 5 | Latent `NoneType` deref on indent (`prev_node.is_inline_label`) | robust | ✅ Done |
| 6 | `raise "<string>"` in assign.py yaml paths (TypeError masks error) | robust | ✅ Done |
| 7 | Bare `except:` in `content_from_lib_or_file` hides load errors | robust | ✅ Done |
| 8 | Per-compile state object (if/match/await chains are class-level) | robust | ✅ Done |
| 9 | Inconsistent error recovery (some bail, some continue) | robust | ✅ Done |
| 10 | Regex typo `STRING_REGEX_NAMED_3` — stray `"` in group name | robust | ✅ Done |
| 11 | `compile_formatted_string` breaks on `"""` in user text | robust | ✅ Done |

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

## ✅ Done — #8 per-compile block state (`CompileContext`)

### The bug
Six block-tracking containers were **class attributes shared across every
compile**: `IfStatements.if_chains`, `MatchStatements.chains`, `Await.stack`,
`OnChange.stack`, `OnSignal.stack`, `LoopStart.loop_stack`. Two ways this bites:
- An aborted compile (the compiler bails on the first error) leaves entries
  behind that corrupt the **next** mission's compile.
- Imports compile **recursively mid-parse**, so a nested import shared the same
  containers as the outer compile.

(`if_chains`/`loop_stack` keyed only by indent could also alias unrelated blocks
at the same column.)

### The fix
- New **`CompileContext`** ([mast.py](sbs_utils/mast/mast.py)) holds all six
  containers. `_compile()` creates one per call and exposes it on the local
  `CompileInfo` class (`compile_info.ctx`), so every node in a compile shares it
  and each compile (including nested imports) is isolated.
- The node types ([conditional.py](sbs_utils/mast/core_nodes/conditional.py),
  [await_cmd.py](sbs_utils/mast/core_nodes/await_cmd.py),
  [on_change.py](sbs_utils/mast/core_nodes/on_change.py),
  [on_signal.py](sbs_utils/mast/core_nodes/on_signal.py),
  [loop.py](sbs_utils/mast/core_nodes/loop.py),
  [button.py](sbs_utils/mast_sbs/story_nodes/button.py)) now read/write
  `compile_info.ctx.<container>` instead of the class attribute, and the
  `create_end_node` methods pass `compile_info` into the end-nodes they build.
  The class attributes are removed; the obsolete commented cleanup block is gone.

### Validation
- New [tests/test_mast_compile_context.py](tests/test_mast_compile_context.py):
  asserts the class attributes are gone, that contexts are distinct per compile,
  and the decisive functional check — a compile aborted **inside an open `await`**
  followed by a clean compile, verifying the second compile's button does **not**
  pick up the stale await (`await_node is None`). This fails on the old
  shared-state code and passes now.
- `python -m unittest discover -s tests` → **348 tests OK** (344 + 4 new).

---

## ✅ Done — #9 error-recovery consistency

The compiler bailed (`return errors`) on the first construction/indentation
error, so authors saw one problem per compile. The recoverable error sites
(expression/node-construction failures and the pre-mutation indentation checks)
now **append the error and continue** instead of returning. This is safe because
at those points the offending line is already consumed (`pos` advanced) and no
per-block state was mutated yet, so dropping the bad line and carrying on doesn't
corrupt the parse. A whole file's independent errors are reported in one pass.

Also: the unhelpful `"Error at first newline index"` fallback now reads
`"Unrecognized syntax; no MAST node matched this line"` **and includes the
offending line text**.

The deeper, post-mutation failures (the inner dedent-loop and the outer
catch-all) still bail — continuing there could cascade off corrupted state, and
that's a worse experience than a clean stop.

### Validation
- [tests/test_mast.py](tests/test_mast.py): new `test_collects_multiple_errors`
  (three bad expressions → three errors) and `test_valid_after_error_still_zero`
  (recovery never invents errors for valid code). `test_assign_expect_error`
  updated: one keyword-assignment problem now yields **one** clean located
  message (was 2 — the old code appended a redundant bare-exception copy).
- `python -m unittest discover -s tests` → **350 tests OK**.

---

## Suggested priority — all complete

| Effort | Payoff | Item |
|---|---|---|
| ~~Medium~~ | ~~High~~ | ✅ #1 pos-cursor |
| ~~Low~~ | ~~Med~~ | ✅ #2 first-char dispatch |
| ~~Medium~~ | ~~High~~ | ✅ #8 per-compile state |
| ~~Low~~ | ~~Med~~ | ✅ #5, #6, #7 latent crashes/masks |
| ~~Low~~ | ~~Low~~ | ✅ #3, #4 logging; #10, #11 regex/format |
| ~~Low~~ | ~~Low~~ | ✅ #9 error-recovery consistency |
