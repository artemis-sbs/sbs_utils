---
name: authoring-amd
description: Writing and maintaining AMD, the markdown-shaped content format for Artemis Cosmos missions - `.amd` files holding quests/jobs/beats/arcs, dialogue and hails, science scans, sides, regions, landmarks, lifeforms/cast/crew, theaters, items, drops, relics, images/icons - and the sbs_utils code behind it (the `amd_*` modules in `sbs_utils/procedural/`, `document_get_amd_file` and its `data_parser`, the `amd_schema` field registry, archetypes, kind lines, traits, a mission's own `*_amd.py` vocabulary). Use when writing or editing any `.amd` file, loading AMD from MAST, adding or renaming an AMD field or archetype, a quest/dialogue/scan written in AMD that "does nothing", running `sbs lint` / `sbs fmt` / `sbs site` / `sbs lint --missing` on AMD, changing the AMD parser or linter, or working on the VS Code AMD extension / language server.
---

AMD is **content as data**: a tree of records, each a `# [Display](key)` heading, an
optional `---` fence of facts, and a prose body. The MAST keeps the logic that reacts to
it. It is a **writer's format** - the people it is for write stories, not code - and
every rule below is in service of keeping it that way while making silent failures loud.

Already covered elsewhere - do not repeat, read them:

- `mkdocs/docs/build/amd-format.md` - the format reference: headings, fence rules
  (wrap vs nest), body marks (`= `, `/* */`, `[[key]]`, `@Cue`, callouts, `![[key]]`,
  `Aka:`, title page, transitions), kind lines, screenplay words (`Beat`/`Arc`/`Cue`),
  traits (`Also:`), quest fields, `Action:` verbs, older spellings, images/icons.
- `mkdocs/docs/build/quests.md` - quest fields, console gating, triggers, the mission
  tree, deadline reminders.
- `mkdocs/docs/build/sides-lifeforms.md`, `mkdocs/docs/tooling/amd-tools.md` (editor
  views), `mkdocs/docs/tooling/amd-docs.md` (`sbs site`).
- `DESIGN_RECORD.md` s1-s4 - why the fence dialects, body sigils, stage directions and
  urges are shaped the way they are, with the corpus counts that decided them.

---

## Where things live

| What | Where |
|---|---|
| Shared grammar (regexes, value coercion, `amd_parse_facts`, kind line) | `procedural/amd.py` |
| Tooling model (spans on every node/ref; what lint/LSP/fmt read) | `procedural/amd_core.py` |
| **Game reader** | `procedural/quest.py` `_document_get_amd_file` / `document_get_amd_file` |
| Field registry: `field()`, `enum()`, `amd_register_fields()`, archetypes, discriminators | `procedural/amd_schema.py` |
| Multi-file docs: `amd_document`, `amd_section`, `File:` splice, `amd_records` | `procedural/amd_doc.py` |
| Quest vocabulary + trigger grammar | `procedural/amd_quest.py` (driver: `quest_driver.py`) |
| Dialogue scenes, guards, outcomes | `procedural/amd_dialogue.py` (surfaces: `hail.py`, `messages.py`) |
| Stage directions (`Action:` verbs) | `procedural/amd_action.py` |
| Domain readers | `amd_sides`, `amd_landmarks`, `amd_lifeforms`, `amd_crew`, `amd_items`, `amd_drops`, `amd_theater`, `amd_relics`, `amd_science`, `amd_cutscene`, `amd_images`, `amd_urge`, `amd_effects`, `amd_chatter`, ... |
| Consolidated mission parser (quest + landmark) | `procedural/amd_mission.py` `amd_mission_data` |
| Lint / formatter / LSP / site emitter | `amd_lint.py`, `amd_fmt.py`, `amd_lsp.py`, `amd_markdown.py` |
| Loading a mission's own vocabulary before lint | `procedural/amd_vocab.py` (`*_amd.py`, `*_dialogue.py`) |
| CLI | `sbs_cli/src/lint_cmd.py`, `fmt_cmd.py`, `site_cmd.py`, `docs_cmd.py` |
| VS Code extension | `sbs_cli/editors/vscode/` |

**Two readers, always.** `amd_core.parse` is the tooling's model; `_document_get_amd_file`
is what the game runs. They share `amd.py`'s grammar and `amd_schema`'s kind resolution,
but a feature that hides or reinterprets a line in one and not the other is the first bug
to look for when "lint is clean but the game ignores it" (or the reverse).

---

## Loading AMD: the `data_parser` decides what the fence means

`document_get_amd_file(path, data_parser=...)` returns a dict tree
(`key`, `display_text`, `description`, `data`, `children`). **Which vocabulary turns fence
lines into runtime keys is the `data_parser` you pass**, and there is no error for the
wrong one - just a dict with the wrong keys:

```
doc = document_get_amd_file(path)                                # schema only
doc = document_get_amd_file(path, data_parser=amd_quest_data)    # quest handler
doc = document_get_amd_file(path, data_parser=amd_mission_data)  # quest + landmark
```

Measured on the same `Done when: scan 2 anomalies` fence: with no parser it stays
`{'goal': 'scan 2 anomalies'}` (a string - no `on_scan` trigger, the quest never
completes); with `amd_quest_data` it becomes `{'on_scan': {...}, 'objective': ...}`.
Follow what shipped missions do:

```
# LM siege.mast
quest_grant_amd(SHARED, document_get_amd_file(get_mission_dir_filename("maps/siege_quests.amd"), data_parser=amd_quest_data))
# LM peacetime_remastered.mast - one file, many sections
shared PR_DOC = document_get_amd_file(get_mission_dir_filename("maps/peacetime_remastered.amd"), data_parser=amd_mission_data)
science_define_scan_amd(amd_section(PR_DOC, "scans"))
```

`amd_document(content, data_parser=...)` is the from-a-string twin, used with
`media_read_relative_file(...)` for addon content. A table-of-contents file keeps
sections slim with `File: jobs.amd` (or `Files:` comma list) in a section's fence; it is
**one level deep** - an included file holds entries, not further `File:` lines.

**Keyed, not flagged.** Landmarks and characters are created against their key, checked
against the live game, so loading a section twice returns what exists and re-creates what
was destroyed. Do not wrap AMD loading in your own "already loaded" latch - that is the
thing that breaks run 2 and restarts.

---

## Saying what a record is (and the `Kind:` trap)

Resolution order (`amd_schema.amd_resolve_kind` / `amd_resolve_kind_chain`), closest wins:

1. the record's own **kind line** - a bare one-word noun on the fence's FIRST line
2. the nearest ancestor's kind line (sections inherit downward)
3. a document-level kind line (fence before the first heading)
4. the section name (`Jobs`, `Characters`, `Landmarks`, `Scans`, `Dialogue`, `Relics`,
   ... singular or plural; a mission can add its own with `amd_register_section_names`)
5. the first **discriminating field** (`_DISCRIMINATORS`: `Done when:` -> quest,
   `Scan of:` -> scan, `Enemies:` -> side, `At:`/`Kind:` -> landmark, `Speaker:` ->
   dialogue, ...)

Traps:

- **`Kind: Arc` is NOT a kind line.** `Kind:` is a landmark DOMAIN field (`Kind: derelict`,
  `station`). With no kind line or section name above it, it hits the
  `("kind", "landmark")` discriminator and types the record - and every descendant - as a
  landmark. Write the bare word: first fence line `Arc`.
- A kind line must be ONE word with no colon. `Colour red` (forgotten colon) is not
  swallowed as a kind; it is a fence error.
- **The kind changes VALUES, not just warnings.** A mistyped record reads fields through
  the wrong archetype - a root `Universe` line once typed every record in a file as `map`,
  and `Center: 5, -4` stayed a string instead of `[5, -4]`.
- A section resolves to ONE archetype. Two concepts that must share a section have to be
  one archetype (cutscene shots group by `Cutscene:`; `Scene:` is already a lifeform field).
- Kind words imply defaults (`amd_kind_defaults`): a `Beat` is shared and already
  running, a `Job` waits on the board, an `Objective` is the crew's and live. "The word has
  to be on the record" - a section kind line types its records but the defaults come from
  each record's own word.

---

## Quests

### `Starts when:` / `Done when:` / `Fails when:` - one trigger grammar, three questions

- **`When:` is an alias of `Starts when:`, the START trigger** - never completion
  (`Goal:` is the old spelling of `Done when:`). Docs taught this wrong three times; a
  quest written that way arms and then waits forever on a `Done when:` it does not have.
- In a **dialogue** record `When:` is unrelated: it names the surface (`comms` / `hail`).
- `Starts when: accepted` / `revealed` / `at once` set the initial state; any other
  trigger becomes a `start_trigger`, and the quest swaps in its own `Done when:` once it
  fires.
- Trigger verbs (`amd_quest.TRIGGER_VERBS`): `destroy`/`kill`, `scan`/`survey`, `dock`,
  `reach`/`travel` (`reach 6, 4` a cell, `reach <role> <radius>`), `recover`/`collect`/
  `gather`, `tow`/`haul`, `signal <name>`, a duration (`5 minutes`), `all dead <role>`.
- Only a doable verb fills a missing `Objective:`; `signal`/timers never do, and an
  explicit `Objective:` is never overwritten.

### Role tokens are singularized - and matched exactly

`_resolve_role` singularizes via `_singular` (fixed 2026-09-18): `-ies` -> `-y`
(`anomalies` -> `anomaly`), `-xes/-ches/-shes/-zzes` drop `es`, a word ending `ss`/`us`/`is`
is left alone (`bus`, `nimbus`), otherwise one trailing `s` goes (`raiders`, `bases`). The
driver then matches with `has_role`, which is exact. Still not caught by `sbs lint`:

- Irregular plurals (`destroy 2 mice`) and singulars the rules misread (`scan 1 lens`
  -> `len`) never match. Write the role's exact singular, or suffix the role
  (`lens_target`) - do not emit the mangled spelling, a human will "correct" it back.
- Before the fix, `-ies` produced `anomalie` and a lone-`s` word lost its `s`; content
  written as `scan 3 anomaly` for that reason still works.
- Applies to `destroy`/`kill`, `scan`/`survey`, `dock`, `reach <role> <radius>`,
  `all dead <role>`, `Fail on all dead:`. `Scan of:` in a scan record is read raw.

### `Then:` and `Action:`

- `Then:` fires on COMPLETION and accepts only `reveal <key>` and `signal <name>`
  (`THEN_VERBS`). **A bare or unknown value is a reveal target**: `Then: hail brief` means
  "reveal a quest called `hail brief`". Lint flags `unknown-then-verb` / `dangling-reveal`.
- `Action:` fires when the beat STARTS (`becomes`, `is no longer`, `joins`, `arrives`,
  `departs`, `hails`). All lines happen at once - sequence is a second beat. Use `Action:`
  only when the beat causes the change, not when a change causes the beat (see the arrow
  table in amd-format.md). Event-like verbs are keyed so beat re-entry does not double-spawn.

### Scan text: `Scan says:` (current), `Reveals:` / `Scan text:` (older, still work)

The quest driver reads `data["reveal_scan"]`. `Scan says:` used to be dead - it landed as
`scan_says` because `_CANONICAL_TO_LEGACY` had no entry - which silenced LM
peacetime_remastered's survey job. Fixed 2026-09-18 (`"scan_says": "reveals"`); all three
spellings now reach `reveal_scan` (test: `test_SCAN_SAYS_REACHES_THE_DRIVER`). The fix
lives in the sbslib, so an older installed sbslib still drops it. Do not confuse it with
`Then: reveal`, which unlocks a quest.

### Holders, nesting, gating

- `Scope: shared` grants to the SHARED agent; `Held by: <actor>` names a landmark/role.
  Without `Held by:`, **children are granted against the passed-in agent and resolve their
  own scope** - a `scope: shared` Arc with a plain (ship-scoped) child needs the parent's
  node on the ship, so the child is silently dropped. Give nested steps the same holder
  as their parent (or use `Held by:`, whose steps follow the parent).
- `Accept On:` / `Manage On:` and `Engage On:` restrict which consoles show
  Accept/Abandon and Engage for this quest, overriding `QUEST_ACCEPT_CONSOLES`
  (default `comms,admiral`) / `QUEST_ENGAGE_CONSOLES` (default `helm`). The data lands in
  the quest's `data` dict - read it with `quest_get_data`, not `quest_get_key`.
- `Show:` (`always` / `when done` / `with children` / `never`) controls listing only;
  `Starts when: revealed` also stops the triggers. Not interchangeable.
- `At start: posting` lists a job with no working Accept button - the only way in is
  answering the hail that offers it.

---

## Dialogue, hails and message replies

A scene is a record with `Speaker:` (or `@Cue` lines in the body), `When: comms|hail`,
`%` random variant lines, and choices:

```
- [Offer a cut](ashfang_deal) if credits >= 200 ; costs 200 credits
- [Take the case]() ; completes florbin/brief
```

- **Guards are `name op integer` only** (`_GUARD`). The mission supplies the number via
  `dialogue_set_metric_resolver`; with no resolver the left side is 0. A guard that does
  not match the pattern evaluates **False - the choice silently disappears**. `%{gate}`
  gates a variant line the same way.
- **Outcome verbs are registered per mission.** Built in: `signal`. `quest_driver`
  registers `accepts`, `completes`, `fails`; `boarding` registers `learn`; **`costs` and
  `earns` exist only in OpenUniverse** (`universe_dialogue.py`). An unregistered verb is
  skipped at runtime with no message - `sbs lint` reports it as `unknown-outcome-verb`.
  A handler returning `False` refuses the whole pick.
- **`; signal name` carries NO payload.** `dialogue_apply` does a bare `signal_emit(name)`
  (plus `quest_signal` with `SIGNAL_NAME`, so `Done when: signal name` matches). A
  `//signal/name` route therefore has no `MESSAGE_*` / `HAIL_*` context - reading one is a
  NameError, and a failing expression ends the handler silently. For message replies,
  route on the system's own `message_reply` signal (`MESSAGE_ID`, `MESSAGE_CHOICE`,
  `MESSAGE_TARGET`, `MESSAGE_CONSOLE`, `MESSAGE_FROM`), dispatch on `MESSAGE_TARGET`, and
  no-op on targets you do not own. `signal-no-route` is satisfied by `//shared/signal/X`.
- **What the `(target)` does depends on the surface.** In a hail it walks to that scene;
  in a message reply it is only passed along as `MESSAGE_TARGET` (so it is free to name a
  heading you look up yourself, which also clears `dangling-choice`). `dialogue_apply`
  itself reads only the outcomes.
- **`await hail_ask(...)` resolves on the answer that ENDS the conversation** (changed
  2026-09-17). A choice with a target is a branch, not an ending. Every other ending
  (declined/closed/cancelled) resolves with `value` None, so nothing hangs.
- **`answer.value` is the chosen LABEL - a copy of AMD prose.** `if answer.value == "..."`
  in MAST silently breaks the day a writer rewords the choice. Declare the string once
  (`default shared LP_ACCEPT = "..."`), log loudly when an answer matches nothing, and add
  a test that reads the real `.amd` and the real `.mast` and fails on drift.
- Hail lint rules worth knowing: `hail-no-entry`, `hail-unknown-scene`,
  `hail-speaker-mismatch`, `hail-too-many-choices`, `dangling-speaker`, `dangling-scene`.

**Guardrail - dialogue is a writer's script, not a language.** Speakers, lines, `%`
variants, a few choices with simple guards, light outcomes. No loops, expressions,
variables or procedural logic; anything procedural stays in MAST. If a request pushes
dialogue AMD toward control flow, push back.

---

## Science scans

Only the dialogue-native form exists (the flat `Scan:`/`Intel:` fence form is retired):

```
## [Scans](scans)
### [Poacher](poacher_scan)
---
Scan of: poacher
Tab: scan
---
% Light freighter running without a transponder.
% Hull patched with salvage plating.
```

One heading per (role, tab); tabs are `scan`/`status`/`intel`/`mat`/`bio` (`unknown-scan-tab`
catches typos); each `%` line is a random variant; `{key}` placeholders fill from the
object's inventory at scan time (unknown left literal). Register with
`science_define_scan_amd(amd_section(doc, "scans"))`; per-object inventory `scan_<tab>`
overrides the role default. A quest's `Reveals:` text is the other path (the driver makes
the `on_scan` target scannable only while such a quest is active; re-scanning the same
object does not over-count).

**The old `{`-in-a-fence trap is gone** (older notes contradicted by code):
`amd_is_yaml_flow` is now per-VALUE - only a value that *starts* with `{` or `[` is parsed
as YAML flow. `Intel: Captain {captain}` stays a string under key `intel`, and `Color: #86c`
survives in the same fence as a flow value.

---

## Extending the vocabulary

- **New syntax needs the user's explicit confirmation.** Suggest it; never just add it.
  Shape it like markdown: `# [Display](key)` headings, `[label](target)` links (with
  `(key?a=b)` query params for attributes), `---` fences, `//` comments. Every new body
  mark needs a forcing character (why cues are `@Name`, not Fountain ALL-CAPS - real
  bodies open with `COMMS:`), and an unclaimed body line stays prose forever, so an older
  sbslib renders a newer mark as text.
- **Prefer declarative.** Per-item config belongs in `metadata:` blocks and `.amd`
  records, not in a Python dict every new item must be added to.
- **New fields** go through `amd_register_fields(archetype, {...}, domain=...)` - keyed by
  ARCHETYPE (the same label means different things on different kinds). Growth rules are
  at the end of amd-format.md.
- **A mission's vocabulary lives in a file named `*_amd.py` (or `*_dialogue.py`)** -
  `amd_vocab.load_mission_vocabulary` finds it by filename, in folders and mastlibs, for
  `sbs lint`, the LSP and the `--test` gate. Without that, lint reported 174 `unknown-field`
  warnings across LM+OU instead of 2.
- **One owner per concept.** `amd_register_fields` raises on a re-declaration that
  disagrees. LM once declared `call sign` in both `lm_amd.py` and the casino; it is now
  fixed (the casino owns it in `casino/casino_amd.py`), but the rule is the same as addon
  function prefixes: never let two co-loaded files declare one field.
- **Import schema helpers INSIDE the declaring function.** MAST merges imported `.py`
  modules into one namespace and sbs_utils has several modules named `text`; a
  module-level `from ... import text` gets shadowed and fails at runtime with
  `'module' object is not callable`.
- **Vocabulary is process-global and NOT on the reset ledger** (a mission's `*_amd.py` is
  not re-executed on an in-process recompile, so clearing it loses the words for good).
  AMD *content* caches do reset. Anything that imports a mission's vocabulary in a process
  that then runs the mission must bracket it with `amd_vocabulary_snapshot()` /
  `amd_vocabulary_restore()`; `sbs site` refuses a second mission per process, and tests
  that load two vocabularies use subprocesses.
- **A new function is not MAST-callable until its module is registered** in
  `sbs_utils/mast_sbs/mast_sbs_procedural.py` (`MastGlobals.import_python_module(...)`).
  `cutscene_*` once shipped tested and invisible. Monkeypatching a module function does not
  affect MAST either - `MastGlobals` holds the original.

---

## Tooling

| Command | Use |
|---|---|
| `sbs lint <mission>` | Mission-aware: all `.amd` + MAST labels + LM/OU mastlib routes/emits. Exit 1 on errors |
| `--strict` / `--no-cross` / `--no-signals` / `--format text\|compact\|json` | Warnings fail / skip cross-file refs / skip signal checks / output shape |
| `sbs lint <mission> --missing` | Work list of referenced-but-unwritten keys; always exits 0 |
| `python -m sbs_utils.procedural.amd_lint <file>` | Single file - false-positives every cross-file reference |
| `sbs fmt` | Prose-safe, idempotent; invariant `parse(fmt(x))` keeps keys and refs |
| `sbs site --emit includes\|records\|site`, `--check` | Generated docs pages (committed in LM/OU; CI runs `--check`). `sbs docs` prints one document |
| `sbs lint --lsp` | The language server the VS Code extension spawns |

Severity: structural = ERROR (`broken-heading`, `unclosed-data-fence`, `heading-level-jump`,
`fence-syntax`); references = WARNING (`dangling-choice`, `dangling-reveal`,
`dangling-parent`, `ambiguous-reference`, `duplicate-key`); cross-file (`signal-no-route`,
`unfired-signal`, `reach-no-landmark`); vocabulary (`unknown-field`,
`unknown-enum-value`, `unknown-action-verb`, `unknown-outcome-verb`); `non-ascii` (the
engine renders ASCII only). A dynamic emit the linter cannot see is declared with
`emits: [a]` / `handles: [b]` in any `metadata:` block.

**What lint cannot see:** a wrong `data_parser`, a singularized role that matches nothing,
a guard that does not parse, `answer.value` drift.
Lint clean is not "works" - run the mission headless (`headless-testing` skill) and probe
state after the run, since a PASS does not prove an event-triggered path ran.

**VS Code extension** (`sbs_cli/editors/vscode/`) registers no providers of its own: it is
a `vscode-languageclient` running `<cosmos>/PyRuntime/python.exe sbs.pyz lint --lsp`, and
`lint_cmd._prefer_working_tree_sbs_utils` makes it use the working-tree sbs_utils. So a
language-service change is Python in `amd_lsp.py` and goes live on a window reload; only
TypeScript (grammar, webviews) needs a rebuild/`npx vsce package`. Webviews post an
intent, the extension applies an edit on a server-provided span, and the `.amd` stays
canonical. Scan-line parsing is inlined in `amd_lsp` on purpose - importing `amd_science`
there drags in the science/story_nodes chain and circular-imports.

---

## Changing the parser or a reader

- **No authored `.amd` may parse differently.** `tests/test_amd_parse_golden.py` pins
  every field of a deterministic corpus (`tests/amd_corpus.py`); regenerating the golden
  is a deliberate, reviewed act, never a way to go green. For anything bigger, snapshot
  every corpus `.amd` (LM, OU, the a2x conversions) through BOTH readers, change, and
  diff - that caught a regression the unit suite missed. For a new mark with zero corpus
  occurrences, any diff is a regression.
- **Count the demand before designing vocabulary.** Twice a corpus count overturned a
  design (see DESIGN_RECORD); measure, never assert, what the corpus does.
- Corpus sources are Python strings, not checked-in `.amd`, because `core.autocrlf`
  rewrites line endings and CRLF handling is part of what must be pinned.
- Fence values come from `amd_core` / `amd.amd_parse_facts`, never raw YAML (YAML reads
  `Color: #86c` as a comment). Keys are normalized (lowercase, spaces -> `_`).
- `node.data` holds RUNTIME keys (`goal`, `parent`); anything that shows fields to an
  author titles them with `amd_schema.amd_authored_label` and reads values from
  `node.fence_lines`.
- A fence-aware conversion script must track fence LENGTH (4-backtick fences), not toggle.

---

## Neighbors: declarative map metadata

Not AMD, but the same direction and often asked together - `@map` metadata beside
`Properties:`:

- **`Defaults:`** - `VAR: value`, applied set-if-absent to SHARED (`map_apply_defaults`),
  both when the Properties panel is presented and when the map task starts (AUTO_START and
  `--map` skip the panel). **Any map-local var a Properties widget interpolates in its
  style string needs a `Defaults:` entry** - undefaulted, the engine raises NameError and
  then a misleading `MemoryError: bad allocation` in `send_gui_dropdown`. Quote yes/no
  defaults (`"yes"`); bare `yes` is a YAML boolean.
- **`Crew:`** - `hull:` / `side:`, applied as the map is selected (see MAST_CLAUDE.md).

---

## Checklist before calling AMD work done

1. Kind resolves as intended (kind line or section name, never `Kind:` for an archetype).
2. Loaded with the right `data_parser`; the runtime keys you expect are in `node["data"]`.
3. Every trigger role survives singularization (no irregular plurals; check `_singular`).
4. Scan text written as `Scan says:` (needs an sbslib from 2026-09-18 or later).
5. Every outcome verb is registered in THIS mission; guards match `name op integer`.
6. Nothing in MAST compares against a copy of AMD prose without a drift test.
7. `sbs lint <mission>` clean, then a headless run that probes the state the AMD should
   have changed.
8. If the parser changed: golden test green without regenerating, corpus diff empty.
