# Debugging your mission

Ever had a mission where the comms menu doesn't appear, a value comes out wrong, or a
scene fires at the wrong moment — and you're left sprinkling `print` lines to guess what
happened? The **MAST debugger** lets you **pause your mission while it plays and look
inside it**: which line it's on, what every value is, and how it got there. Then you can
walk through it one line at a time and watch your story unfold.

It runs right inside VS Code, using the familiar debugger toolbar (▶ ⏸ ⏭).

!!! note "You don't need to be a programmer"
    This is for **mission writers**. You put a pause point on a line of your `.mast`,
    play your mission, and it stops there so you can look around. No Python required.

## Set it up once

Install the **Artemis AMD** extension in VS Code: open the **Extensions** view, search
for *Artemis AMD*, and click **Install**. That's the whole setup — it already knows how
to find your Cosmos install.

## Debug a mission — the one-click way

1. Open your mission folder in VS Code.
2. Go to the **Run and Debug** panel (the ▶🐞 icon on the left bar), choose
   **"MAST: Debug mission (one click)"** in the dropdown, and press the green **▶**.
   Your mission starts and the game window opens in your browser, just like normal.
3. **Set a pause point.** Open a `.mast` file and click in the **left margin** next to a
   line — a red dot appears. That's a *breakpoint*: your mission will pause when it
   reaches that line.
4. **Play your mission** in the game window until it reaches that line. It **pauses**, and
   VS Code jumps to the exact line with a yellow arrow.
5. **Look around** (see below), **step** through line by line, or press **Continue (▶)**
   to run on to the next pause point.
6. When you're done, press **Stop (⏹)**. The mission shuts down and tidies up after
   itself — nothing left running for you to clean up.

!!! tip "A pause point only catches lines that run *while you're watching*"
    If a line ran once at the very start and never again, pausing there won't trigger
    until that code runs again. The one-click config handles the usual case (it waits for
    you before starting the map). Otherwise, put your pause point on something you can
    re-trigger — a comms button, a scene you can reach, a check that repeats.

## What you can do while paused

The panels on the left show everything about that frozen moment.

**See your values.** The **Variables** panel lists what your mission is tracking, grouped
by where each value lives:

- **Task** — variables in the task that's running right now (the everyday ones).
- **Shared** — your `shared` variables, visible across the whole mission.
- **Global** — mission-wide and built-in names.
- **Frame** — short-lived values inside the current block.

Want to try a "what if"? **Double-click a value, type a new one, press Enter** — the
mission carries on with your change.

**Walk through the story** with the toolbar:

- **Step Over** — run this line, stop on the next one.
- **Step Into** — go *inside* a label or block this line calls.
- **Step Out** — finish the current block and stop back where it was called from.
- **Continue (▶)** — run until the next pause point.

**See how you got here.** The **Call Stack** panel shows the trail of labels that led to
the current line.

**Keep an eye on something.** In the **Watch** panel, add an expression like `hp < 20` or
`player.name` and its value updates as you step.

!!! note "It pauses *just before* the line runs"
    A pause point stops the mission the instant it *reaches* a line — before that line
    does its work. So if you pause on `hp = hp - 10`, `hp` still shows the old number;
    step once and you'll watch it change.

## Smarter pause points

Right-click a red dot and choose **Edit Breakpoint** to make it do more:

- **Only pause sometimes** — give a condition like `hp < 20`. It pauses only when that's
  true.
- **Pause on the Nth time** — a count like `3` (the third time it's hit), `>5`, or `%2`
  (every other time).
- **Just take a note, don't pause** — a *log point*. Type a message with values in braces,
  e.g. `enemy hp is {hp}`. Every time the line runs it prints that to the Debug Console and
  keeps going — like a temporary `print` you never have to remember to delete.

## Good to know

- **The game keeps moving while you're paused.** Your *story* is frozen and safe to read,
  but ships in the practice sim keep drifting. So the values are trustworthy; positions may
  have moved on by the time you continue.
- **Map files come alive as you reach them.** A map like `siege.mast` only loads when its
  map starts, so its pause points become active then. The Debug Console notes files as they
  load.
- **Stop tidies up.** Pressing Stop shuts down the mission and its game window — you never
  have to hunt for a leftover process.

## Peeking into the engine (optional, advanced)

Sometimes a MAST line calls a built-in like `terrain_to_value(...)` and you want to see
what happens *inside* it. **Step Into** on such a line drops you into the engine's own
code (read-only) with its values, then **Step Out** brings you back to your story. Most
writers never need this — it's there for chasing something deep. If it's switched off for
how your mission was started, the Debug Console will say so.

## Debug a single script file (advanced)

For a standalone logic `.mast` that runs start-to-finish (not a full mission), open it and
press **F5** — the extension runs just that file and stops at your pause points. Full
missions (with comms, maps, and GUI) use the one-click flow above.

## When something looks off

- **No red dots, or it doesn't say "MAST"** — make sure the file ends in `.mast` and the
  Artemis AMD extension is installed (the language is shown at the bottom-right of the
  editor).
- **It never pauses** — the line probably already ran; try a pause point on something you
  can re-trigger.
- **Read the Debug Console** (bottom panel, the "MAST: Debug mission" session) — it prints
  friendly notes about what loaded and what's happening.

!!! info "It doesn't slow your mission down"
    The debugger only does anything when you're actively debugging. Normal mission runs —
    and the shipped game — are completely unaffected.

See also: [Testing missions](testing.md) · [The sbs command](cli.md).
