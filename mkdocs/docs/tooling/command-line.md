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
| `profile=<name>` | load `profiles/<name>.yaml` over the mission's settings. Several, comma separated, merge left to right |
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
  <  a mod's settings_set_mod_default()
  <  the mission's settings.yaml
  <  profile=<name>          ->  <mission>/profiles/<name>.yaml
                             ->  common_data/profiles/<name>.yaml
     profile=<a>,<b>            several merge left to right, last wins
  <  the COSMOS_SETTINGS environment variable
  <  var.NAME= on the command line
```

`var.` comes last because typing it is the most deliberate thing in the list.

## Switching missions

Launch arguments belong to the **process**, and restarting into a *different* mission
(the pause screen's `mission_select`, `remote_mission_pick`) does not change them. Most
of them mean something about one particular mission, so they are dropped once you
switch:

| dropped on a switch | kept |
|---|---|
| `profile=` `map=` `console=` `var.NAME=` | `seed=` `run=` `record=` `test=` |

Restarting the **same** mission changes nothing - that is the common case, and a
profile keeps applying to every restart, indefinitely.

Each dropped argument says so in the log rather than vanishing. The comparison needs
`defaultmission=` to know what you started with; without it nothing is dropped.


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

A profile is not only settings: it can also add and remove **add-ons** and **art packs**
relative to `story.json`, which is how the same mission runs with the Artemis 2.8 skies
instead of the stock ones. See **[Profiles](profiles.md)**.

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
