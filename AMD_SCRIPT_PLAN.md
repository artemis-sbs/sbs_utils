# AMD as a screenplay and a graph

> **Status: DONE (2026-08-09).** All 12 phases, gates run (2731 -> 2780 tests). The two items
> section 5 listed as "yes, later" also landed: `Aka:` (`amd_core.py:114-228`) and `![[key]]`
> transclusion (`amd.py:64-71`). `amd_callout.py` ships; `amd_lint.py` emits
> `dangling-speaker`, `dangling-link` and `unknown-callout`; `sbs lint --missing` and the
> `amd.showMissing` VS Code command are live.
>
> Kept for the sigil-collision survey in sections 2-4, which is what justifies `= ` vs `=$`.

`AMD_PLAN.md` settled the **data layer** - one fence reader, a field-descriptor
registry, kind resolution, path-indexed headings, a vocabulary that passes the
read-aloud test. That work is done.

This plan settles the **body layer** - the prose half of the file, which is still
almost entirely unstructured, and the **reference graph**, which today exists only
between typed fields and never through narrative text.

Two prior formats already solved these, and they solved different halves:

- **Fountain** (screenplay markup): *the plain text IS the document.* Auto-detect
  structure, always provide a one-character forcing escape, and anything
  unrecognized degrades to prose rather than failing. A non-technical collaborator
  reads the file cold, with no tool.
- **Obsidian** (linked markdown notes): *the document is a node in a graph.* Links
  are first-class and inline, an unresolved link is a legitimate to-do rather than
  an error, and most of the tooling's value comes from reading the graph back.

AMD is decent on the Fountain half and weak on the Obsidian half. Prime directive
is unchanged and inherited: **AMD is for sci-fi authors, not programmers.** Every
naming choice below is settled by reading it aloud.

---

## 1. What is already true

Not re-litigated here; listed so the plan builds on facts rather than assumptions.

| Fact | Where |
|---|---|
| One fence reader, registry-driven, alias + type + runtime key in one entry | `amd_schema.field()` / `enum()` / `amd_register_fields()`; `amd.amd_parse_facts` |
| Headings are `#+ [Display](key)` with optional `?query`, path-indexed | `amd.RE_HEADING`, `amd_core.parse` |
| Bodies are already captured line-by-line with real line numbers | `amd_core.parse` -> `node.body_lines` |
| Choice links `- [Label](target)` are already extracted as references | `amd_core._extract_choice_refs`, `_RE_CHOICE` |
| Dangling references are **already WARNING, not ERROR** | `amd_lint.amd_lint_references` -> `dangling-scene`, `dangling-parent` |
| A `Speaker:` key already resolves to a face/name/color card | `amd_lifeforms.lifeform_speaker` |
| Cutscene shots are already ordinary records with `Lens:` / `Move:` / `Seconds:` | `amd_cutscene.py` |
| Comments are `//`, skipped in bodies | `amd_core.parse` |
| `%` is the dialogue variant sigil; `%%` / `%%%` is urge escalation | `amd_dialogue.dialogue_parse`, `amd_urge.py` |
| **A full LSP server already exists, in Python** - diagnostics, definition, hover, completion, references, rename, symbols, formatting, quick-fix code actions, code lens, document color, inlay hints | `amd_lsp.py` (1696 lines) |
| **The VS Code extension is a LanguageClient**, not a provider host - it spawns bundled `PyRuntime/python` + `sbs.pyz` and registers zero providers of its own | `editors/vscode/src/extension.ts`, dep `vscode-languageclient` |
| **Story Graph, Timeline, Outline, Resolver, Map, Preview, Mission Inspector already ship** as extension commands | `package.json` `contributes.commands` |
| Find-all-references and rename already work over `AmdRef`s | `amd_lsp._references`, `_rename` |

The severity change people expect from "unresolved links should be a to-do" is
**already done**. What is missing is the tooling that makes a warning useful, and
the inline link syntax that would produce most of them.

---

## 2. Collision survey

Every proposed sigil was grepped across all `.amd` in the missions tree plus the
34-file a2x corpus at `F:/a/Cosmos-a2x-test/data`, at line start.

| Sigil | Uses today | Verdict |
|---|---|---|
| `@` | 0 | free |
| `(` | 0 | free |
| `/*` | 0 | free |
| `[[` | 0 | free |
| `> [!` | 0 | free |
| `~` | 0 | free, but **rejected** - reads as MAST inline-Python in this tree |
| `=` | **14** | **COLLIDES** - all 14 are `=$name font:...;color:...`, the line-style declaration (`doc_viewer/doc.amd`, `documents/quest.amd`) |

**Ruling on `=`:** a synopsis is `=` followed by a **space**. `=$` stays exactly
what it is. Zero existing lines match `^=\s`, so the split is clean and needs no
migration.

---

## 3. The two laws

Everything below is an instance of one of these. They are the durable part of the
plan; the sigils are negotiable.

### Law 1 - Strict inside the fence, forgiving in the body

Inside `---`, an unrecognized line is an **error**: a dropped field silently loses
authored data, which is the exact bug `AMD_PLAN.md` was written to kill.

In a body, an unrecognized line is **prose, forever, with no exceptions**. This is
Fountain's rule and it is why Fountain survived a decade with no version field and
no schema. It also means every future body sigil is automatically backward
compatible in the direction that matters: an older `sbslib` reading a newer
mission renders `@Ashfang` as a literal line of text instead of failing to load.

### Law 2 - Every ambiguity gets a forcing character

Auto-detect the common case, always provide a one-character override. Fountain's
real invention is not any single sigil, it is this discipline. `AMD_PLAN.md`
already reserves `!` at value-start; promoting it to a stated law turns the
features below from five special cases into five instances of one pattern.

Corollary, applied immediately: **do not adopt Fountain's ALL-CAPS character-cue
detection.** Fountain can afford caps-sniffing because screenplay prose is
stylized. AMD bodies are arbitrary sci-fi prose, and 12 record bodies already open
with a field-shaped line (`COMMS: hail the freighter.`). The cue is always `@`.

---

## 4. The additions, settled

### 4.1 Character cues - `@Speaker`

Today a scene carries one `Speaker:` in its fence, so a two-hander needs two
headings and a choice link between them. Fountain puts the cue in the body:

```
# [The Standoff](standoff)
---
Dialogue
When: comms
---
@Ashfang
% You're a long way from friends, captain.
% Brave or stupid, flying in here.

@Vell
He means it, captain.

- [Apologize](ashfang_backoff)
- [Offer a cut](ashfang_deal) if credits >= 200 ; costs 200 credits
```

- A body line matching `^@<key>` opens a **speech block**. Following `%` lines and
  plain lines belong to that speaker until the next `@`, the next choice list, or
  the end of the body.
- `Speaker:` in the fence stays as the single-speaker shorthand and remains the
  default speaker for any lines that appear **before** the first `@`. The entire
  `raider_hails.amd` corpus is untouched.
- The key resolves through `amd_lifeforms.lifeform_speaker` - the same path
  `Speaker:` already uses, so faces, names and colors come free.
- `@Ashfang` normalizes like any label (`amd_norm`), so `@Ashfang` and `@ashfang`
  are the same cast member.
- An `@key` with no cast record is a **dangling-speaker** WARNING carrying the same
  quick-fix as 4.7.

Lands in: `amd_dialogue.dialogue_parse` (which already walks body lines splitting
`%` from `- [](...)`), returning `lines` grouped per speaker instead of flat. The
existing flat shape stays available for single-speaker scenes so
`dialogue_pick_line` does not change for the shipped corpus.

### 4.2 Parentheticals - delivery direction

Fountain's `(quietly)` under a cue. AMD has faces, moods and style strings sitting
right there with no authored way to reach them.

```
@Vell
(shaken)
He means it, captain.
```

- A body line that is entirely `(...)` inside a speech block is a **direction**
  attached to the next line, not spoken text.
- Directions resolve through a registry, `amd_register_directions(domain, table)`,
  mirroring `amd_register_fields`. A direction maps to any combination of face
  mood, color style, and delivery timing.
- **An unknown direction warns and is preserved as flavor.** A writer must be able
  to type `(with the weariness of a man who has explained this twice)` without the
  linter arguing. This is the read-aloud test applied to a feature rather than a
  field name.

Highest ratio of author expressiveness to implementation cost in this plan.

### 4.3 Character extensions - the surface, written by the writer

Fountain's `(V.O.)` / `(O.S.)` become Cosmos delivery surfaces:

```
@Vell (comms)         -> comms_message
@Ashfang (over)       -> info panel chatter
@Narrator (card)      -> info card
@Vell                 -> the scene's default surface
```

Per the standing preference (comms_message > info card > text waterfall), this
decision currently lives in mission Python. Putting it on the cue puts it in front
of the person already deciding who says what. Extensions register in the same
table as 4.2 and are distinguished by being a **known surface name**; anything else
in parentheses on the cue line is a direction.

### 4.4 Synopsis - `= ` , the author-only line

AMD has player-facing text (`Objective:`), player-facing prose (the body), and
nothing at all for *what this beat is for*.

```
### [Identify the Kidnapper](trail)
= Midpoint. The crew learns Florbin is alive; raises stakes before the boarding.
---
Starts when: revealed
Done when: signal suspect_identified
---
Follow the cargo trail: interview stations and bio-scan suspect holds.
```

- `= ` (equals **space**) at line start, anywhere in a record, before or after the
  fence. `=$` is untouched (see section 2).
- **Never rendered.** Feeds LSP hover, the Inspector outline, and `amd_timeline`.
- **Must not become `node.summary`.** `amd_core.parse` currently sets `summary` to
  the first non-choice body line; a synopsis line has to be excluded there or every
  synopsized record's summary becomes the author's private note. Named because it
  is the one place this feature can silently do damage.

### 4.5 Callouts - `> [!NOTE]`

Un-parks the existing text_area admonition work. `help_docs.amd` and
`library_docs.amd` are the only two AMD files that have actually **shipped**, and
they are pure prose - so this is the single highest-value body feature for real
players today.

```
> [!WARNING] Quarantine Notice
> Do not dock. Contact TSN Command on channel 4.
```

In-fiction documents want in-fiction document formatting. Blocked on the known gap:
`gui_text_area` has per-line styles but no **block grouping**, so a multi-line
callout cannot currently share one background. That gap is the actual work; the AMD
side is a five-line parse. Sequenced late for that reason.

Kinds are ASCII and registry-driven: `NOTE`, `TIP`, `WARNING`, `DANGER`, plus
whatever a domain registers. Unknown kind renders as a plain quote and warns.

### 4.6 Inline references - `[[key]]`

Keep `[Display](key)` for headings and `- [Label](target)` for choices; both need
display text foregrounded. Add Obsidian's inline form so that **prose can carry
references**:

```
Follow the cargo trail. [[cmdr_vell]] has the manifest; it ends at [[ds1]].
```

- `[[key]]` renders as the target's **display name**; `[[key|other words]]`
  renders the given words.
- Resolution uses the scope rule already settled in `AMD_PLAN.md` section 2.5:
  self -> siblings -> ancestors -> global, erroring on ambiguity rather than
  silently taking the last.
- Extraction is one function beside `_extract_choice_refs` in `amd_core.parse`,
  emitting ordinary `AmdRef`s. Everything downstream - lint, LSP, Inspector,
  timeline - reads the existing ref list and gets this for free.

Three payoffs: the linter gets a reference graph out of narrative text, the
Inspector gets real backlinks, and a writer can gesture at a character or a place
without inventing a field for it.

### 4.7 An unresolved link is a stub, not a mistake

Obsidian's most underrated design decision, and the one that changes the workflow
rather than the file.

Severity is already right (`amd_lint_references` warns). What is missing:

1. **A `Create this record` quick-fix** in the VS Code extension - inserts a
   heading at the correct level with the referenced key, in the current file or a
   chosen one.
2. **A Missing panel** - every unresolved `[[link]]`, `Then: reveal`, `Scene:` and
   `@speaker` in the document set, grouped by target, i.e. Obsidian's unresolved
   links pane.
3. **`sbs lint --missing`** - the same list on the command line, exit 0. It is a
   to-do list, not a failure.

Combined with 4.6 this is a genuinely new way to write a mission: **draft the whole
thing as prose with `[[]]` links to records that do not exist yet, then let
`sbs lint` hand you the list of what to write next.** That is a better pitch for
AMD than any individual field, and it costs no runtime code.

### 4.8 Boneyard - `/* ... */`

`//` handles a line. Writers cut **scenes**, constantly, and want them back next
week. A block comment costs almost nothing and collides with nothing.

Must be handled in `amd_core.parse` at the same level as the `//` skip, and must
work **inside a fence as well as in a body** - a commented-out scene usually takes
its data block with it. Unclosed at EOF is an error with the same writer-facing
phrasing as the unclosed-fence message.

---

## 5. Designed, deferred - ALL LANDED

Not in the first pass, but decided, so they do not get re-argued.

| Feature | Source | Decision |
|---|---|---|
| **Record aliases** - `Aka: The Florbin Job` | Obsidian `aliases:` | Yes, later. AMD has `aka=` at the FIELD level, nothing at the RECORD level. Lets a2x-generated keys be renamed without breaking cross-file refs. Name it `Aka:` - `Also:` is already archetype traits and must not be overloaded |
| ~~Backlinks + story graph~~ | Obsidian graph view | **Not deferred - already built.** `amd.showGraph` / `showTimeline` / `showStoryOutline` ship today, and `amd_lsp._references` is find-all-references over `AmdRef`s. Inline `[[links]]` in 4.6 emit ordinary `AmdRef`s, so they light up every one of those surfaces with no new view. See section 9 |
| **Transclusion `![[key]]`** | Obsidian embeds | Yes, later. Shared paragraph across help docs, a shared line pool pulled into a scene. Needs cycle detection. `![[image.png\|300]]` sizing is a good fit given the existing `image://` support |
| **Fountain title-page vocabulary** | Fountain | Yes, cheap. The document-level fence is already the config home; spell its fields `Title:` / `Author:` / `Draft:` because writers already know those exact words |
| **Fountain transitions in cutscenes** | Fountain | Yes, with 4.1-4.3. `FADE IN:` / `> CUT TO:` as shot boundaries inside one `Cutscene:` record, so a cutscene file reads as a screenplay. See section 8 |

---

## 6. Held in reserve, and rejected

| Idea | Ruling |
|---|---|
| **Dataview inline fields, `Pays:: 200 credits`** | **Reserve, do not ship.** `::` is precisely the disambiguator that would have let AMD drop the `---` fence, because it cannot collide with `COMMS: hail the freighter.` But the fence was just settled, and two ways to write a field is worse than one. Hold it exactly as `AMD_PLAN.md` holds the blank-line separator: the documented answer *if* the fence ever proves too heavy |
| **Obsidian `#tags`** | **Reject.** Redundant with `Also:` traits, and `#` at line start collides with headings. Inline-only would be safe but earns little |
| **Block references `^id`** | **Reject.** Addressing an individual dialogue line is over-engineering for narrative |
| **Dual dialogue `^`, page break `===`, lyrics `~`** | **Reject.** `~` in particular reads as MAST inline-Python to anyone working in this tree |
| **Obsidian `%%comment%%`** | **Reject, actively harmful.** `%` is the dialogue variant sigil and `%%` / `%%%` is urge escalation. Comments stay `//`, plus `/* */` from 4.8 |
| **Fountain ALL-CAPS cue detection** | **Reject.** See Law 2 corollary |
| **Fountain scene headings (`INT. BRIDGE - DAY`)** | **Reject.** The link-form heading already does this job and carries the key. The slugline vocabulary can inform cutscene shot naming, nothing more |

---

## 7. Backward compatibility

Inherits the `AMD_PLAN.md` growth rules and adds one:

**Every addition in section 4 is body-level, and Law 1 makes body-level additions
free in both directions.** A newer `sbslib` reading an old file finds no `@`, no
`= `, no `[[` - 0 occurrences across the entire corpus and the a2x output, per
section 2 - and behaves identically. An older `sbslib` reading a new file renders
the new sigils as literal prose: degraded, never broken.

The one exception is `=`, which is disambiguated by a required trailing space and
verified against all 14 existing `=$` uses.

No existing file needs migration. That is the test this plan had to pass.

---

## 8. Worked example - the shooting script

The reason to do all of this at once rather than as six unrelated features. A
cutscene `.amd` that is a readable screenplay and the shot list the engine plays,
in the same bytes:

```
# [Florbin, Recovered](florbin_recover)
= Act 3 button. Payoff for the whole arc; last beat before the debrief.
---
Cutscene: finale
Subject: hero
Lens: 0, 400, -3000
Seconds: 6
---
FADE IN:

@Vell (comms)
(relieved)
% We have him, captain. He's shaken but whole.
% He's aboard. Rattled, but he's aboard.

The [[florbin]] transport slips its mooring at [[ds1]] and turns for home.

> CUT TO:

@Ashfang (over)
(cold)
This isn't finished.
```

Fountain gives it the voice. Obsidian gives it the graph. The AMD heading and fence
give it the key and the camera the engine addresses. One file is simultaneously the
thing you email a collaborator, the thing `sbs lint` checks, and the thing that
renders in-engine.

---

## 9. Where the editor work actually lives

The VS Code extension is **a LanguageClient, not a provider host**. `extension.ts`
registers no `CodeActionProvider`, `HoverProvider`, `CompletionItemProvider`,
`DefinitionProvider` or `DiagnosticCollection` at all - it spawns bundled
`PyRuntime/python` with `sbs.pyz` and lets `amd_lsp.py` answer. So the sentence
"update the VS Code extension" splits three ways, and two of the three are Python
in this repo:

| Work | Lives in | Repo |
|---|---|---|
| Diagnostics, hover, completion, definition, references, rename, quick-fixes, code lens, inlay hints | `amd_lsp.py` handlers (`_hover`, `_completion`, `_code_actions`, `_references`, `_rename`) | **sbs_utils** |
| Lint rules and `sbs lint --missing` | `amd_lint.py` + `sbs_cli/src/lint_cmd.py` | sbs_utils, sbs_cli |
| Syntax coloring, new webview panels, new commands | `syntaxes/amd.tmLanguage.json`, `src/extension.ts` | sbs_cli |

Three consequences that change the phase plan:

**1. Most features arrive through the LSP for free.** `[[key]]` refs (4.6) emit
ordinary `AmdRef`s, and `_references` / `_rename` / `showGraph` / `showTimeline` /
`showStoryOutline` all already read refs. Adding the extraction in phase 2 lights
up find-all-references, rename, the story graph, the timeline and the outline
**without touching TypeScript**. This is the strongest practical argument for the
inline link syntax and it was understated in the first draft of this plan.

**2. The grammar is small and must roughly double.**
`amd.tmLanguage.json` has exactly six patterns today - `comment` (`//.*$`),
`fence`, `heading`, `choice`, `dialogue` (`^[ \t]*%`), `color`. Every body sigil in
section 4 needs one: `cue` (`^@`), `direction` (`^\(...\)$`), `synopsis`
(`^=\s`), `wikilink` (`\[\[...\]\]`), `boneyard` (`/* */`), `callout`
(`^>\s*\[!`). The synopsis pattern must be `^=\s` so it cannot shadow the existing
`=$` style declarations, which the grammar does not currently color either way.

**3. Completion trigger characters need extending.** `amd_lsp` advertises
`triggerCharacters: ["(", " "]`. `@` (cast completion) and `[` (record-key
completion inside `[[`) have to be added, and `(` conveniently already fires -
which is what makes direction completion in 4.2 nearly free.

**Which layer is live, and which needs a rebuild.** `lint_cmd._prefer_working_tree_sbs_utils`
puts a working-tree `sbs_utils/` sitting beside the missions folder **first on
`sys.path`**, so on this machine an edit to `amd_lsp.py` or `amd_lint.py` is live
after a window reload - no `sbs.pyz` rebuild needed to iterate. The rebuild is a
**distribution** step, for anyone without the working tree.

The TypeScript layer is the opposite: `extension.ts`, the grammar and the webviews
need an F5 dev host or a repackaged `.vsix` to be seen at all. So phases 10 and 11
carry the packaging cost and phases 3 and 9 do not - which is another reason to
front-load the Python-side work.

---

## 10. Phases

Each phase ends green on the full suite and with `sbs lint` clean across LM, OU,
StormsBeacon and the a2x corpus.

| # | Phase | Touches | Status |
|---|---|---|---|
| 1 | **Law 1 as code** - body sigils claim a line in ONE place per reader; everything else is prose | `amd.py`, `amd_core`, `quest` | **DONE** |
| 2 | **`[[key]]` inline refs** - extraction beside `_extract_choice_refs`, display-name and `\|alias` render, `dangling-link` lint | `amd.py`, `amd_core`, `amd_lint`, `quest` | **DONE** |
| 3 | **Stub tooling** - `sbs lint --missing`, `amd_lint_missing`, new codes registered as fixable | `amd_lint`, `amd_lsp`, `sbs_cli/lint_cmd` | **DONE** |
| 4 | **`= ` synopsis** - parse, **excluded from `node.summary`**, carried on the runtime node, shown on hover | `amd.py`, `amd_core`, `quest`, `amd_lsp` | **DONE** |
| 5 | **`/* */` boneyard** - pre-pass in BOTH readers, unclosed-at-EOF error | `amd.py`, `amd_core`, `quest` | **DONE** |
| 6 | **`@cue` + `(direction)` + `(surface)`** - `beats` in `dialogue_parse`, `dialogue_beats`, registries, `dangling-speaker` lint | `amd.py`, `amd_dialogue`, `amd_core`, `amd_lint` | **DONE** |
| 7 | **Cutscene transitions** - `FADE IN:` / `> CUT TO:` become a shot's `transition`, out of the overlay text | `amd.py`, `amd_cutscene` | **DONE** |
| 8 | **Callouts** - native in `gui_text_area`'s mini-markdown; `unknown-callout` lint | `amd_callout` (new), `pages/layout/text_area`, `amd_lint` | **DONE, ENGINE-VERIFIED** |
| 9 | **LSP surface** - `@` / `[` triggers, cast + link-target + direction completion, synopsis on hover | `amd_lsp` | **DONE** |
| 10 | **TextMate grammar** - six new patterns | `sbs_cli/editors/vscode` | **DONE** |
| 11 | **Missing panel** - `amd/missing` + the webview | `amd_lsp`, `sbs_cli/editors/vscode` | **DONE** |
| 12 | **Docs** | `mkdocs` | **DONE + deployed** |

### What the code corrected about this plan

- **The quick-fix already existed.** `amd_lsp._code_actions` has offered "Change to
  `<near key>`" and "Create node" since the schema work; it is gated by
  `_FIXABLE_DANGLING`. Phase 3's editor half was therefore *registering two codes*,
  not building a feature. Both `dangling-link` and `dangling-speaker` now get it.
- **Phase 11 was NOT redundant, and I argued twice that it was.** The Problems
  pane is per-FILE and answers "what is wrong here"; the Missing panel is
  per-TARGET, crosses files, and answers "what do I still have to write". That is
  the workflow the inline-link syntax exists for, and without the panel it lived
  only on the CLI. Built as `amd/missing` + a webview.
- **Callouts belong in the RENDERER, not in an AMD-side transform.** They shipped
  first as `amd_callout_render(text) -> (text, line_styles)`, which a caller had to
  opt into - and LM's `document_screen` renders a doc body with a bare
  `gui_text_area(t)`, so `help_docs.amd` and `library_docs.amd`, the only shipped
  prose AMD and the entire point of the feature, would never have gotten it. Moved
  into `get_markdown_line_style` beside `#`/`-`/`1.`. General rule: when a feature
  has to reach text a caller already renders, put it in the renderer.
- **The "block grouping missing" blocker was wrong.** Per-line backgrounds abut by
  construction - the render loop advances `bounds.top = bounds.bottom` - and
  `doc_viewer/doc.amd` already shipped `background:#115;`. Engine-verified.
  The real bug was the opposite: a callout must END at the first non-`>` line, or
  the background bleeds down the document. A box with no bottom.

### Gates, actually run

- **Corpus no-op:** 136 `.amd` files across the missions tree and the a2x corpus,
  parsed through BOTH readers before and after. **0 differences**, re-run after each
  phase.
- **Tests:** 2731 -> 2780, **OK**, no failures at any point. 49 new tests in
  `tests/test_amd_script.py`.
- **`sbs lint`:** LegendaryMissions 1 finding, OpenUniverse 2, Storm's Beacon 0 -
  **identical counts with the changes stashed**, so all three are pre-existing
  (a `.gitattributes` packaging warning, an OU `Patience` unknown field, an OU
  signal with no route).

---

## 11. Verification

Per phase: unit tests, then `sbs lint` over every `.amd` in the tree, then a
headless `--test` run of LM `peacetime_remastered` and OU, then the user's browser
pass wherever a GUI surface is involved (phases 6-8).

Editor phases additionally: phases 3 and 9 verify by reloading the window (the
working-tree shim makes them live); phases 10 and 11 need an F5 dev host or a
repackaged `.vsix`, and a `sbs.pyz` rebuild before anyone without the working tree
sees them. The existing `editors/vscode/test/*.test.js` pattern covers the
TypeScript side.

Two additional gates specific to this plan:

1. **A no-op corpus diff.** Parse every `.amd` in the missions tree plus the a2x
   corpus before and after each phase and diff the resulting node trees. Phases 1-5
   must produce **byte-identical** output on the existing corpus - every new sigil
   has 0 occurrences today, so any diff at all is a regression. This is the
   snapshot-and-diff technique that caught the root-kind mistyping bug that tests
   missed.
2. **The read-aloud test on every new name.** `Speaker`, `Scene`, `Aka`, `Title`,
   `Draft` pass. Any direction or surface name that a novelist would not write
   unprompted does not go in the default table.
