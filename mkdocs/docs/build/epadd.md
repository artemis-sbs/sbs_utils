# The ePADD &mdash; one tab that holds the apps

The console tab strip was a junk drawer. A bridge console carries `help`, `library`,
`upgrade`, `quest` and, in a dev build, `debug` before Engineering adds `fabricate` and
`cargo` &mdash; seven of the eight slots the bar allows, after which the rest roll into
a `More (n)` dropdown. It could not be ordered either: position was `.mast` load order,
and the button label was the raw lowercase route path, so the bar read
`fabricate  upgrade  cargo`.

The **ePADD** replaces that with one button. Opening it gives a home screen of app
tiles &mdash; named, described, grouped, and scoped to the station that should see
them.

```
[ ePADD ][ back ]                                    Artemis        T+00:14:22

  Ship
   [ Boarding Party ]   [ Status  2 ]   [ Messages  3 ]   [ Cargo ]
   [ Fabricate 1 ] [ Upgrades ]

  Mission
   [ Quests  2 ]   [ Library ]     [ Help ]
```

A tile carries an icon, a title, a second line of description, and a **badge** &mdash; a
short live value (`3 unread`, `2 building`, `42/60`) that the crew read *without opening
anything*. That badge is the reason the apps carrying live state do not each need a
panel on the bridge.

---

## An app is a route

An app is a `//gui/app/<name>` route plus one registration. The route is the screen; the
registration is the tile.

```
//gui/app/cargo
    jump cargo_screen

gui_app_register("cargo", title="Cargo", icon="epadd.cargo",
                 consoles="engineering", group="Ship", sort=10,
                 description="Hold manifest")
```

The two answer different questions, which is why they are separate:

- The **route's own `if`** says whether the app is *available* &mdash; it is still the
  authority, exactly as a tab's condition always was. `//gui/app/boarding_team if
  boarding_relevant()` keeps the tile off a mission with no landing parties.
- The **registration** says how it is *presented*, which the route grammar has no room
  for (`[\w]+` and an optional `if` is the whole of it).

An app route with no registration is perfectly legal: it is reachable from another
screen and never appears on the home grid, which is all a "page" ever needed to be. A
registration with **no route** is reported by name in `mast.runtime.log` and left off
the PADD &mdash; almost always a typo, or a `//gui/tab` that was never migrated.

!!! warning "If it used to be a `//gui/tab`, rebuild both"
    The app table lives in the library and the routes live in a mastlib. A library that
    reads the new table beside a mastlib still declaring `//gui/tab/cargo` gives you a
    tile that does nothing when pressed. Rebuild the `.sbslib` **and** the `.mastlib`.

### Scoping a tile

`consoles` takes a comma list, or `"*"` for every **ship** console. Names are matched
after normalization, so `"engineering"` matches the engine's `normal_engi`.

```
gui_app_register("airwing", title="Airwing", icon="epadd.airwing",
                 consoles="hangar", group="Ship", sort=40,
                 description="Craft, pilots, sortie board")
```

`"*"` deliberately does **not** include the crew console. A boarding party is not everywhere
on the ship, it is somewhere else entirely, and a landing party has no use for the cargo
hold. An app opts in with `boarding=True`, or names `consoles="boarding"` to go there and
nowhere else.

### Groups and order

`group` is the heading a tile files under. `Ship`, `Mission` and `Systems` render in
that order and anything else lands after them alphabetically; `sort` orders within a
group, low first, ties breaking on title.

The convention LegendaryMissions follows: **Ship** is what this hull is telling you
(status, messages, cargo, upgrades), **Mission** is what outlives the hull (quests,
lore, help), **Systems** is tooling.

### A live badge

`status` is a string or a callable, called at build time:

```
gui_app_register("messages", title="Messages", icon="epadd.messages",
                 group="Ship", sort=3, description="From the crew, and from home",
                 status=lm_epadd_unread, boarding=True)
```

Anything the callable raises is swallowed and costs only its own badge &mdash; a badge
must never be able to take the home screen down with it.

### Icons

`icon` is a name for `gui_icon_name`, never a sheet index, so a mod can re-point a name
at its own art and every tile follows. An unknown name draws nothing and says so once,
so an app can be registered before anyone has drawn its glyph.

**Namespace them.** The icon registry is one flat namespace and a registration is a
claim on it: a bare `brain` takes over the built-in glyph for everything else that draws
it. LegendaryMissions claims `epadd.*` from its own sheet:

```
gui_icon_add_atlas_grid(media_shared("epadd/icons"), 4, 6, cell=128, names=[
    "epadd.cargo", "epadd.fabricate", "epadd.upgrades", "epadd.quests", ...])
```

---

## Writing an app's screen

An app screen is an ordinary GUI screen. Two helpers give it the PADD's chrome, and both
are optional &mdash; a list/detail screen that wants the whole sheet reads better
without them.

```
=== cargo_screen
    gui_tab_back(CONSOLE_SELECT)
    gui_app_chrome("Cargo", "what the hold is carrying")
    gui_section(style="area: 0, 109px, 100, 100;")
    ...
    await gui()
```

- `gui_app_chrome(title, subtitle=None)` draws the title bar in its own band and returns
  the subtitle widget, so a live screen can update that line in place. Pass `""` for a
  line that is empty now but will have text later &mdash; the widget is created either
  way.
- `gui_app_subnav(["brain", "mast"])`, called straight after the chrome, puts this app's
  other screens on the right-hand end of the same bar.

**The PADD keeps no history.** The one Back in the game is the console's, on the tab
bar, which every PADD screen declares with `gui_tab_back(CONSOLE_SELECT)` like any other
screen. There is no HOME button on the chrome either: the strip's status region already
opens the home screen.

`gui_app_open("cargo")` opens an app from code &mdash; the same two lines a tab click
runs, so an app opened from the PADD arrives exactly as a tab would have.

---

## The home screen

A mission reaches the PADD by declaring the shell route. `sbs_utils` ships no `.mast` of
its own, so this stub is what turns it on; LegendaryMissions carries it in
`consoles/epadd.mast`:

```
//gui/app/epadd
    jump epadd_home_screen

=== epadd_home_screen
    gui_tab_back(CONSOLE_SELECT)
    gui_app_home(ship_name=ship.name)
    on change gui_app_revision():
        jump epadd_home_screen
    on change mission_elapsed_text():
        gui_app_home_tick()
    await gui()
    ->END
```

Two details in there are load-bearing:

- **A signal does not wake `await gui()`.** Without the `on change gui_app_revision()`
  the home screen is frozen at whatever it said when it was opened: mail arriving never
  moves the Messages badge, and an app whose route condition turns on never appears.
- **The mission clock moves the widget, not the page.** A repaint a second is every tile
  on the sheet over the wire, per console, forever, so `gui_app_home_tick()` updates that
  one widget and touches nothing else.

The grid **falls back to a scrolling list when the tiles do not fit** &mdash; a grid does
not scroll and the engine does not clip. The decision reads the client's real height, so
it is about the screen and not a count: thirty apps is a list at 1024x768 and a grid at
1920x1080. Columns follow the client's aspect ratio, and a console carrying more than a
dozen apps goes dense (six columns, descriptions dropped).

!!! note "The PADD is always on"
    It used to be opt-in, behind a setting, and that went when apps became their own
    route kind. Switching it off does not fall back to the classic strip &mdash; apps are
    not on the tab bar at all, so it leaves them with no way in. Declaring the
    `//gui/app/epadd` route **is** the opt-in.

---

## The identity badge

Above the ship data panel, on every console, the PADD draws who is sitting there and how
much is waiting: `Lt Marek (2)`. The count is **apps with something to say**, not
messages &mdash; "how many of these should I open" is the number a crew member cannot get
any other way. `gui_app_identity_text()` is what it draws, and it answers `None` when
there is nothing worth a line, so a mission using none of this gets no empty box.

There is **no badge on the main screen**. It names the person at a console, and the main
screen is the room's.

---

## Messages

The Messages app is the one most missions will touch, because two different things arrive
in the same inbox on purpose:

- **Crew to crew.** Helm texts Engineering. It is a bridge simulator with people sat at
  separate screens who cannot see each other, and passing a note is half of what they
  would do if they could.
- **From content.** A mission, a quest beat or a map sends a letter from a character.

```
message_send("All hands: contact in ten minutes.", sender="The Captain")
message_mail("Made it to the outer colonies. Mum sends her love.",
             to="helm", sender="Your brother")
```

**A letter wears its sender's face.** Pass `face=` with a face string, or leave it out:
when a lifeform exists with the sender's name (`lifeform_spawn("Admiral Harkin", ...)`),
its face is used. The face is kept on the message, so it still shows after that
character has left the story. The reading pane then leads with the face beside
"From <name>"; a message with no face reads exactly as before.

**Addressed to a console, not to a person.** A console is what the PADD knows, what a
client is sitting at, and what survives a player disconnecting and coming back; a crew
name does none of those. `to="*"` is everyone and is the default. Read state is per
console too, kept beside the messages rather than on the client, because consoles get
reassigned and an inbox that forgot what it had read every time somebody swapped seats
would be worse than not tracking it at all.

A message can **ask a question**. `choices` are `amd_choice` dicts, capped at four, and
answering settles the choice, applies its outcomes and posts the reply back into the
thread &mdash; which is what makes it read as a conversation rather than a form that was
filled in. Two consoles pressing in the same frame cannot both apply the outcome: the
arbitration token moves *before* the outcomes run.

### Mail written in AMD

A mission's letters belong in an `.amd` file a writer can be handed without reading any
code. One heading per message:

```
## [Nan says hello](mail_nan)
---
From: Mum
To: helm
After: 90
---
Your nan has learned what a subspace relay is and now believes she can be heard by
everyone on the ship at once, so she has started saying hello to all of them.

- [Tell her hello back](reply) ; signal nan_answered
- [Pretend you were on shift](dodge)
```

- `From:` is who it is from; a message without one is ignored.
- `To:` is a console, a comma list, or `*` (the default).
- `After:` is how many seconds into the mission it arrives. Spread them out &mdash; mail
  that all lands at once is a document, not a message.
- A `- [label](target) ; outcomes` line is a reply the crew can send, up to four.

Load it once, from the top level, and run a pump to deliver what is due:

```
default shared MAIL_LOADED = False
if not MAIL_LOADED:
    shared MAIL_LOADED = True
    message_load_amd(document_get_amd_file(None, "Messages",
                     content=media_read_relative_file("messages.amd")))
    task_schedule(mail_pump)

== mail_pump ==
--- pump
    await delay_sim(15)
    message_deliver_due()
    jump pump
```

Keep message bodies ASCII and under about 600 characters: the engine draws no curly
quotes, no em-dashes and no emoji, and a `^` is a line break to it.

---

## The boarding party

The PADD is the boarding party's console. `boarding=True` on a registration means the landing
party carries that app down with them, and the boarding scene mirrors each beat into the
inbox, so a party reads its story in the same place it reads its mail.

That is also what retired the separate crew console for PADD missions: the crew carry
the screen with them, and whatever job apps a mission adds sit beside it. See
[Boarding parties](boarding-parties.md).

!!! note "A PADD mission's main screen shows nothing about the boarding mission"
    The shared view is driven by the older `boarding_begin` path, which PADD missions do not
    emit. The PADD model has no answer for a *shared* surface &mdash; the same fact as
    "no badge on the main screen".

---

## See also

- [Story & NPC messages](messages.md) &mdash; the ship's log, and the other place text
  reaches a crew.
- [Player ships & consoles](players-consoles.md) &mdash; the tab strip the PADD replaces.
- [Icons by name](../cosmos/gui_icons.md) &mdash; how `icon=` resolves.
- API: [gui](../api/procedural/gui.md#the-epadd), [messages](../api/procedural/messages.md).
