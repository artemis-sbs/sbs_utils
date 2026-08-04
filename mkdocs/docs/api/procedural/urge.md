# Urges

What an actor **keeps asking for**, said out loud. An urge is a recurring want held by
any agent — a lifeform, a station, a side: a condition, a cadence, a pool of authored
lines, and optionally an `Action:`. One shared ticker walks every actor that has urges,
picks at most one, and says it.

```
## [DS1 calls for resupply](ds1_calling)
---
Urge
Actor: DS1
Whenever: quest ds1_resupply active
Every: 5m
Escalates: with deadline
---
% DS1 requests a resupply run when someone has the tonnage.
%% DS1 is below reserve. We need that shipment.
%%% DS1 going to minimal power. Nobody is coming, are they.
```

## An urge carries no stakes of its own

The consequence belongs to the **quest it watches**. A quest already has a deadline
(`Fails when: after 30m`) and a consequence (`Reward:` / `Penalty:` / `Then:`) — what it
never had was a voice, so it counted down in silence.

That split is the whole design: one clock, one place to tune, and deleting an urge costs
the drama but not the mechanics. Give the quest to the thing it is about — a station's
resupply job is `Held by: ds1` — and the penalty lands on the world rather than on a
passing crew.

## Fields

| Field | Meaning |
|---|---|
| `Actor:` | who speaks — a declared landmark key, or a role |
| `Whenever:` | the recurring condition; true = eligible |
| `Every:` | minimum gap between firings. `5m`, or `3-5m` to jitter |
| `Until:` | retire permanently when true (optional) |
| `Weight:` | which of **this actor's** urges wins; 90+ is urgent |
| `Escalates:` | `with deadline` (stage from the bound quest's clock) or `yes` |
| `Title:` | the comms card header; defaults to the speaker's name |
| `Action:` | optional stage directions — the same grammar beats use |

The body is the line pool: one line per entry, `%` markers giving the stage.

## Escalation is the countdown

`Escalates: with deadline` takes the stage from how much of the bound quest's clock has
gone, so the drama curve **is** the countdown that already exists. The bound quest is the
one named in `Whenever:` — there is no second field to keep in agreement.

The marker count is the curve and `Fails when:` is the tempo:

```
% Doctor Voss is on the docking ring, if anyone is bound for the Verdant worlds.
%% Voss again. My window at the Verdant site closes, captain.
%%% Last call. I need to be on a hull today or not at all.
```

## The speech budget

The thing that decides whether autonomous speech is pleasant or unbearable is not
cleverness, it is restraint. Three floors, cheapest first:

| Gate | Default | Why |
|---|---|---|
| per-urge `Every:` | authored | this specific thing should not repeat |
| per-actor | ~45s | one actor should not monologue across its own urges |
| global | ~20s | five actors should not pile up after a jump |

A `Weight: 90+` urge bypasses the **global** floor only — an actor leaving forever
outranks politeness toward other speakers, but not its own self-restraint. The global
clock is shared with [`announce`](../../cosmos/overlays.md), because an announcement and
an urge are the same thing from the bridge's side: an unprompted voice. A player hailing
a station is deliberately *not* counted — that is traffic the player asked for, and
counting it would starve autonomous speech exactly when the crew is busy.

## Where the voice goes

Reach follows hosting, so nothing has to declare it:

| Actor | Surface |
|---|---|
| hosted on a player ship | an internal crew message, with the actor's own face |
| hosted elsewhere | a comms message from the host to the player ships |
| unhosted | a galaxy-wide comms message from the actor |

## What an urge is not

- **Not a brain.** A behavior tree re-decides continuously because the world moved; an
  urge's world changes on clocks and events. Grid lifeforms (damcons) keep their brains —
  they have position and paths and are correctly a tree.
- **Not a goal selector.** `Weight:` arbitrates one actor's own urges — the same
  fixed-priority fallback every brain root already does. It never arbitrates between two
  actors.
- **It never invents words.** An urge selects among authored lines.

## Installing

`urges_install(section)` resolves each record's `Actor:` by name — right for a cast
declared up front. `urges_install_on(agent, section, key)` is the identity path, for when
you already hold the character (you just spawned or boarded them).

## API

::: sbs_utils.procedural.urge

::: sbs_utils.procedural.amd_urge
