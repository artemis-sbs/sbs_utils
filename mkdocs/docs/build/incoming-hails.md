# Incoming hails

Comms is normally something the crew starts: they select a contact, and a menu opens.
An **incoming hail** is the other direction &mdash; the mission calls *them*. It waits in
a list on the comms console until somebody answers it, plays out as a short conversation,
and ends on a choice the crew makes.

That makes it the natural way to hand out work. Somebody calls, and taking the job is what
you say back.

## The shortest one

```
### [DS 1 Briefing](ds1_brief)
---
Speaker: ds1
When: hail
Title: Ambassador Kidnapped
Presentation: portrait
---
Artemis, DS 1. Ambassador Florbin was taken off this station inside a cargo container.

- [Take the case]()
- [Not now]()
```

That is the whole thing: who is calling, what the crew sees, what is said, and what they
can say back. `When: hail` is what marks it as a call rather than a menu the player opens.

Nothing has happened yet, though &mdash; a scene is words on a page until something places
the call.

## Placing the call

```
#### [Take the Case](brief)
---
Scope: shared
Starts when: at once
Action:
  - ds1 hails ds1_brief
---
```

`Action:` is what a beat *does* the moment it starts, so a beat that opens with a call
says exactly that. Written bare &mdash; `ds1 hails` &mdash; it opens that speaker's
`When: hail` scene, so a character with one call to make needs no key at all.

!!! warning "`Action:` fires the moment the beat goes active"
    For most records that is **when the quest is granted**, which is usually earlier than
    you want a call to arrive. If something has to happen first, write
    `Starts when: revealed` and reveal the step when the moment comes
    (`quest_reveal(SHARED, "florbin/brief")`). Peacetime's Florbin briefing does this so
    DS 1 calls *after* the Admiral has explained why anyone would be calling.

**Who gets called** follows `Scope:`, and you do not have to think about it:

| The beat is | It runs | The call goes to |
|---|---|---|
| `Scope: shared` | once, on the story agent | every player ship |
| `Scope: ship` | once per ship holding it | that ship |
| held by a station or a character | once | every player ship |

## What an answer means

Written on the choice, next to the words that earn it:

```
- [Take the case]() ; completes florbin/brief
- [Not now]()       ; signal ds1_declined
```

| After the `;` | What it does |
|---|---|
| `accepts <quest>` | Starts it &mdash; the same thing the Accept button does |
| `completes <quest>` | Finishes it, with its `Reward:` and its `Then:` |
| `fails <quest>` | Fails it, with its `Penalty:` |
| `signal <name>` | Fires a signal, for anything the three above do not cover |

An answer is resolved on the server and arbitrated, so it happens **exactly once** however
many consoles are connected. Two comms officers pressing in the same frame is safe, and
you do not have to write a `//shared/signal` route to make it so.

A choice with an **empty** target &mdash; `- [Take the case]()` &mdash; ends the
conversation. Give it a scene key instead and the conversation continues there:

```
- [Tell me more](ds1_detail)
- [Understood]()
```

!!! tip "A board you take by answering"
    `At start: posting` lists a quest without a working Accept button. The only way to
    take it is whatever else offers it &mdash; typically the call that just came in.

## What the crew sees

The comms console shows an **Incoming Hails** list, newest first, with a dial above it
choosing where the conversation is drawn: *Off*, *This Console*, *Main Screen*, or *Both*.

It starts on **Both** &mdash; a hail is a scene, and a bridge watches a scene together. The
dial is there so an officer can move either half away: *This Console* keeps the viewscreen
on the live view, *Main Screen* leaves comms its radar and drives the call from the choice
strip, *Off* shows the conversation nowhere and answers it from the strip alone. The
main-screen half belongs to the **ship**, so any comms console can move it and every dial
agrees about where the hail is; the other half is each console's own.

Answering opens the conversation. `Back` steps out of it without answering, so comms can
read a hail through and present it later, when the captain is ready. Answered
conversations stay in the info panel and can be replayed &mdash; a replay can never change
what was chosen.

`Presentation:` decides how it is drawn:

| Value | Shows | Also needs |
|---|---|---|
| `portrait` | the speaker's face | &mdash; |
| `still` | an image | `Backdrop:` |
| `orbit` | a 3D shot of a ship, like the science viewscreen | `Subject:` |

`Audio:` plays a recorded line when the conversation opens. There is an **Audio** checkbox
beside the dial; it defaults to on.

## Longer conversations

A scene is one beat. Several `@cue` blocks make several, played in order &mdash; the crew
presses `Continue` between them, and the answers appear at the end:

```
### [The Standoff](standoff)
---
Speaker: ashfang
When: hail
---
@Ashfang
% You are a long way from friends, captain.

@Vell
Captain, their weapons are hot.

- [Stand down](ashfang_backoff)
- [Pay them off](ashfang_deal) if credits >= 200 ; costs 200 credits
```

At most **four** answers are shown. Guarded ones (`if credits >= 200`) are not counted
against that, because a guard is how you write more than four and mean it; `sbs lint`
warns about a fifth unguarded choice, which nobody could ever press.

## A line the mission fills in

An authored paragraph can carry a `{slot}`:

```
The last three haulers to leave were:^^{suspects}^^If you hurry you may still catch them.
```

The mission registers what fills it, once:

```python
dialogue_register_slot("suspects", fb_suspects_text)   # fn(agent_id, speaker) -> str
```

Filled when the scene resolves, so a replay shows the words the crew actually heard. An
unknown `{name}` is left alone rather than emptied &mdash; a half-filled line is easier to
recognise than a missing one.

## From MAST instead

Everything above has a procedural twin, for a linear story that wants to *wait* on a hail
rather than hang it off a quest:

```
await hail_ask(artemis_id, scene="mission_briefing", speaker="tsn_command")
```

`hail_ask` blocks the task until the hail is answered and resolves to the choice; `hail_offer`
places one and moves on. Both read the scene's fence for everything it declares, so the
call site names a scene and a voice and nothing else &mdash; provided the document was
registered:

```
shared HTBM_SCENES = here_dialogue_load()      # calls dialogue_register_scenes(...)
```

*Here There Be Monsters* is written this way: twenty scenes in `dialogue/messages.amd`,
each named by one line of `story.mast`.

## Who is calling

`Speaker:` is a key, and the name and face come from whatever that key means in your
mission &mdash; a declared landmark, a cast character, or a role. A station spawned with
the role `ds1` is announced as **DS 1** because that is its name in the world.

When a mission wants to name its cast some other way, it registers a resolver:

```python
hail_set_speaker_resolver(fn)     # fn(speaker_key, ship_id) -> {name, face, color}
```

## What the linter checks

`sbs lint` catches the things that otherwise fail in silence &mdash; a call that never
goes out looks exactly like a call you have not reached yet:

| Finding | Means |
|---|---|
| `dangling-action-ref` | `ds1 hails ds1_breif` &mdash; nothing declares that key |
| `hail-unknown-scene` | the key names a record that is not a dialogue scene |
| `hail-no-entry` | bare `ds1 hails`, and `ds1` declares no `When: hail` scene |
| `hail-speaker-mismatch` | the scene is spoken by somebody else (the scene wins) |
| `hail-not-a-hail` | pushing a `When: comms` scene at the crew |
| `hail-missing-subject` / `hail-missing-backdrop` | `orbit` or `still` with nothing to draw |
| `hail-too-many-choices` | a fifth unguarded answer, which cannot be pressed |
| `hail-empty` | no lines and no choices &mdash; it opens and closes again |

## See also

- [The AMD file format](amd-format.md) &mdash; `Action:`, scenes, and the fence
- [Quests](quests.md) &mdash; `Scope:`, `Starts when:`, `Then:`, and the quest tab
- [Story & NPC messages](messages.md) &mdash; one-way narration, which is a different tool
