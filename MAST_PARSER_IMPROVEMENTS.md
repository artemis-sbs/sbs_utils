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
| 1 | pos-cursor instead of O(n²) source slicing | perf | ✅ Done (uncommitted) |
| 2 | First-char/prefix node dispatch (cut O(nodes×lines)) | perf | ⬜ Proposed |
| 3 | Hoist logger + guard per-line debug f-string | perf | ✅ Done (uncommitted) |
| 4 | Log `FileHandler` leak per `Mast()` construction | perf/robust | ⬜ Proposed |
| 5 | Latent `NoneType` deref on indent (`prev_node.is_inline_label`) | robust | ⬜ Proposed |
| 6 | `raise "<string>"` in assign.py yaml paths (TypeError masks error) | robust | ⬜ Proposed |
| 7 | Bare `except:` in `content_from_lib_or_file` hides load errors | robust | ⬜ Proposed |
| 8 | Per-compile state object (if/match/await chains are class-level) | robust | ⬜ Proposed |
| 9 | Inconsistent error recovery (some bail, some continue) | robust | ⬜ Proposed |
| 10 | Regex typo `STRING_REGEX_NAMED_3` — stray `"` in group name | robust | ⬜ Proposed |
| 11 | `compile_formatted_string` breaks on `"""` in user text | robust | ⬜ Proposed |

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

## ⬜ Proposed — performance

### #2 First-character / prefix node dispatch
Each source line tries node regexes in registration order until one hits; the
catch-alls (`Assign`, `FuncCommand`) are last, so an ordinary call runs ~15 failed
matches first. Add a cheap first-char → candidate-list table (`#`, `==`/`??`,
`---`, `//`, `///`, `@`, `~~`, `metadata:`, `match`/`case`/`if`/`elif`/`else`/
`await`/`jump`/`yield`/`->`). Must preserve the "first match wins" ordering
pitfall within each bucket. **Biggest remaining constant-factor win.** More
invasive — do as its own tested step.

### #4 Log handler leak per `Mast()`
`__init__` ([mast.py:186-194](sbs_utils/mast/mast.py#L186)) opens two `FileHandler`s
and `addHandler`s them on every non-import construction; handlers are never removed,
so repeated compiles stack duplicate handlers and multiply log writes. Guard with an
"already configured" check or remove existing handlers first.

---

## ⬜ Proposed — robustness / correctness

### #5 Latent `NoneType` deref on indent
[mast.py ~916](sbs_utils/mast/mast.py): inside `if prev_node is None or not
prev_node.is_indentable():` the next line does `if not prev_node.is_inline_label:`,
which dereferences `None` when `prev_node is None`. Guard `prev_node is not None`
and emit a clean "unexpected indentation" error.

### #6 `raise "<string>"` in assign.py yaml paths
[assign.py:86](sbs_utils/mast/core_nodes/assign.py#L86) and
[:90](sbs_utils/mast/core_nodes/assign.py#L90) raise a `str` (TypeError in Py3,
masking the real diagnostic); the first isn't even an f-string. Use
`raise Exception(f"...")`.

### #7 Bare `except:` hides load failures
[mast.py:578](sbs_utils/mast/mast.py#L578) catches everything (incl.
`KeyboardInterrupt`) and collapses it to a generic "Cannot load file" with no cause.
Use `except Exception as e:` and include `e`.

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

### #10 Regex typo `STRING_REGEX_NAMED_3`
[mast_node.py ~91](sbs_utils/mast/mast_node.py#L91): `(?P<{name}">.*?)` has a stray
`"` in the group name. Dormant if unused; will bite the next caller.

### #11 `compile_formatted_string` fragile on `"""`
[mast_node.py ~48](sbs_utils/mast/mast_node.py#L48) wraps text as `f"""{message}"""`;
any `"""` (or trailing backslash) in user text breaks compilation with a confusing
error. Escape or build via `ast`.

---

## Suggested priority

| Effort | Payoff | Item |
|---|---|---|
| ~~Medium~~ | ~~High~~ | ✅ #1 pos-cursor (done) |
| Medium | High | #8 per-compile state (correctness on re-compile) |
| Low | Med | #2 first-char dispatch |
| Low | Med | #5, #6, #7 latent crashes/masks |
| Low | Low | ✅ #3 (done), #4 logging hygiene |
