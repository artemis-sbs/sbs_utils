# Command-line arguments

Cosmos can be launched with arguments, and **a mission can read them**. That means a
shortcut, a batch file or a CI job can start the game on a particular map, with particular
settings, without anyone clicking anything.

Engine 1.3.5 and later.

```
Artemis3-x64-release.exe autostartserver defaultmission=LegendaryMissions map=sandbox
```

Most of the time you will not type this yourself — [`sbs run`](cli.md#running-a-mission)
composes it for you.

## The engine's own arguments

| argument | does |
|---|---|
| `autostartserver` | start as the server, skip the launcher menu |
| `autostartclient` | start as a client |
| `clientautoconnectip=<ip>` | which server to connect to |
| `defaultmission=<folder>` | boot this mission, without editing `preferences.json` |

## The ones sbs_utils understands

These are **not** engine flags. The engine passes any `key=value` it does not recognize
through to script, which is what lets a mission define its own.

| argument | does |
|---|---|
| `map=<name>` | start this map, skipping the picker. Index, path, display name, or an unambiguous part of one |
| `console=<name>` | this client opens on that console |
| `profile=<name>` | load `profiles/<name>.yaml` over the mission's settings |
| `var.NAME=value` | override one setting |
| `var.A.B=value` | override a nested setting |
| `seed=<n>` | fix the random seed, so a run can be repeated |
| `run=<tag>` | label this launch, for naming logs and artifacts |
| `record=<name>` | write a transcript of everything clicked |
| `test=<seconds>` | play for that long, then write a pass/fail verdict |

Anything that matches nothing **says so** in the log rather than quietly doing nothing —
a mistyped argument is otherwise invisible.

## Settings: the file carries the bulk, the argument names it

Settings are merged in this order, each beating the one before:

```
built-in defaults
  <  the mission's settings.yaml
  <  profile=<name>          ->  <mission>/profiles/<name>.yaml
  <  the COSMOS_SETTINGS environment variable
  <  var.NAME= on the command line
```

`var.` comes last because typing it is the most deliberate thing in the list.

A profile is an ordinary settings file under `profiles/`:

```yaml title="missions/MyMission/profiles/soak.yaml"
DIFFICULTY: 11
MAP_SIZE: Huge
AUTO_PLAY:
  enable: true
```

```
Artemis3-x64-release.exe autostartserver defaultmission=MyMission profile=soak
```

**Why a file and not more arguments.** A command line is capped at 8191 characters on
Windows, shortcuts truncate it, quoting around spaces and `=` is awkward, and none of it
can be commented, reviewed or diffed. A file is all of those things. So put the twenty
settings in a profile and use the command line to name it — plus a `var.` or two for
whatever you are changing right now:

```
... profile=soak var.DIFFICULTY=3
```

Values are typed the obvious way: `3` is a number, `true` is a boolean, anything else is
text. Lists and dictionaries belong in the profile.

!!! note "Profiles are per mission"
    `profiles/` is read from the mission folder only. Two missions that want the same
    profile need a copy each.

### A profile can also select add-ons

Beyond settings, a profile can add and remove **add-ons** and **media packs** relative to
`story.json` — so "the Artemis 2.8 skies instead of the stock ones", or "the TNG art and
only the TNG races", is one named profile rather than an edited `story.json`.

```yaml title="missions/LegendaryMissions/profiles/a28_skies.yaml"
addons:
    exclude:
        - basic_random_skybox      # the eight stock skies
    include:
        - a28_skyboxes             # the thirty 2.8 ones

media:
    include:
        - A28-Skybox-Mod.media     # ...and their art, or every label fails its file test

PLAYABLE_RACES: "USFP"             # plain settings keys still work, unchanged
```

```
Artemis3-x64-release.exe autostartserver defaultmission=LegendaryMissions profile=a28_skies
python -m cosmos_dev.mission_runner . --test 20 --map 0 --profile a28_skies
```

**Name the folder, never the version.** `a28_skyboxes`, not
`artemis-sbs.A28-Skybox-Mod.a28_skyboxes.v1.0.0.mastlib`. A version belongs in
`story.json`; a profile that spelled one would break on the next release of the pack. An
`include` resolves the same way a declared lib does — a mission-local source folder first,
then the newest matching `.mastlib` in `__lib__`. Media packs match on a substring for the
same reason.

Every add and every drop is **printed by name**. That is not decoration: an add-on that
vanished silently is indistinguishable from one the mission never declared, and the
symptom is a story that compiles to zero labels while still reporting `PASS`.

!!! warning "Excluding an add-on that another one `requires` empties the whole story"
    `requires` is a hard compile barrier, so dropping `gamemaster` while `gamemaster_comms`
    is loaded compiles **nothing** — no labels, no output. The error names the profile and
    what it removed, so the cause is in the message rather than something to deduce.

    The softer version of the same trap has no error at all: exclude the add-on that owns
    your `@media/music` labels and the game simply goes quiet. Watch for an add-on that
    owns more than its name suggests.

## Turning on autoplay from a shortcut

`AUTO_PLAY` is a nested setting, which is what the dotted form is for:

```
... defaultmission=LegendaryMissions map=siege var.AUTO_PLAY.enable=true
```

## Recording what you click

```
... record=session
```

Writes `<mission>/records/session.jsonl`, a line per interaction, naming the **widget** —
`the button labelled "Fire"` — not just its internal tag. Tags are handed out in page
order, so they change whenever a screen is edited; a label does not.

Useful for describing a bug exactly. It is a script of what happened, not a recording that
can be played back: physics does not run to the same clock twice, and selecting an object
does not survive a restart.

## A verdict from a real engine run

```
... map=0 test=30 run=nightly
```

The mission plays for 30 sim-seconds and writes `<mission>/records/verdict.json`:

```json
{
  "runtime": "engine",
  "version": "1.3.5",
  "sim_seconds": 30.1,
  "reached": true,
  "errors": 0,
  "verdict": "PASS"
}
```

A launcher starts the game, waits, reads the file and stops the process — the engine has no
way to exit on its own, so the verdict is a file rather than an exit code.

`reached` and `errors` are separate on purpose. A mission that died immediately still has
no runtime errors, so a zero error count is not a pass by itself.

!!! warning "This is the weaker check"
    It counts runtime errors. It does **not** measure how much of your MAST actually ran —
    that needs `sbs debug . --test`, which runs headless and knows about coverage. Use this
    for what only the real engine can tell you, and that for whether your mission did
    anything.

## Reading them yourself

```python
from sbs_utils.procedural.command_line import (
    command_line_get, command_line_has, command_line_dict, command_line_list)

quality = command_line_get("quality", "high")   # your own argument, no engine change
if command_line_has("autostartserver"):
    ...
```

`command_line_get` handles `key=value`; bare flags need `command_line_has`. Everything
returns empty when there is no command line, so a mission behaves the same launched by hand
or under `sbs debug`.
