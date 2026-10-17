---
name: mast-language
description: The MAST language itself - labels (==, ---, //, ///, @), jump/->END, yield, await, default/shared/temp scope, scope keywords as variable names, metadata blocks and their fence rules, addons (__init__.mast, provides/requires/suggests, the flat function namespace), routes and the //signal vs //shared/signal rule, comms (<<, >>, % lines, buttons), on-handlers and GUI task lifetime, built-in context variables, ~~ inline Python, tuple unpacking, PyMAST. Use before writing, reviewing or debugging any .mast file or MAST snippet, a compile error ("Unrecognized syntax", "Bad indentation", 0 labels), or a lesson that teaches MAST.
---

The full reference is `MAST_CLAUDE.md` at the root of this repo. **Read it before writing
or judging MAST** - it is long (about 58 KB), which is why it is no longer loaded into
every request; read the sections the task needs (its headings are a table of contents).

The traps it records that most often break a whole story (a story that does not compile
runs NOTHING: 0 labels, both logs empty):

- Never write `== main ==`; the main label is implicit.
- A `metadata:` block goes ABOVE any indented body line, fence at column 0.
- `shared` / `assigned` / `client` / `temp` are scope keywords, never variable names.
- `//signal` runs once per console; anything that spawns, saves, rewards or counts goes
  on `//shared/signal`.
- `<<[green]` with no space; a `%` line cannot wrap; `~~ ~~` is a statement, not an
  argument.
- Adding a top-level label to an existing file is never a safe append: labels fall
  through, so put a new one at the end.
