# OSC control panels (TouchOSC) - experimental

!!! warning "Experimental"
    New in v1.4.0 and still settling. The addresses may change, the generated TouchOSC
    layouts have only been tried on the helm so far, and some controls the consoles have
    are out of reach (see [What a panel cannot do](#what-a-panel-cannot-do)). Try it,
    and report what works and what does not.

A tablet running [TouchOSC](https://hexler.net/touchosc) (or any app that speaks Open
Sound Control) can sit beside a console as an extra control panel: a throttle lever, a
red-alert button, power faders, a torpedo fire button, and live gauges for shields,
energy and heat.

It adds to the consoles; it does not replace them. Some controls cannot be driven from
script at all (see [What a panel cannot do](#what-a-panel-cannot-do)).

## Turning it on

The listener runs **inside the game server** - there is nothing extra to launch.

**LegendaryMissions** - launch with the ready-made profile:

```
Artemis3-x64-release.exe profile=osc
```

or turn it on in `settings.yaml` (or your own profile):

```yaml
OSC:
    enable: true
    port: 8000            # tablets send here
    feedback_port: 9000   # the ship's state is sent back to each tablet on this port
    allow: []             # e.g. ["192.168.1."] to accept only your own network
```

It starts when a game starts, on the server, and stops with the mission.

**Any other mission** - call it once on the server, for example from a
`//shared/signal/game_started` route:

```
osc_listen(8000, feedback_port=9000)
```

Then point the tablet at the **server machine's** address, port 8000, and set its
receive port to 9000. The game logic runs on the server, so the tablet always talks to
the server, never to a console PC.

!!! warning "It opens a network port"
    OSC has no passwords. Anyone who can reach the port can fly the ship. It is off by
    default; keep it on your own network, and use `allow` to name it. The first time it
    runs, Windows may ask whether to let Artemis through the firewall - allow it on
    private networks only.

## What a panel can send

A **button** sends 1 when pressed and 0 when released, so a button only acts on the
press. Where a button needs a choice (which torpedo, which target), the choice is part
of the address: `/weapons/fire/Nuke`, not `/weapons/fire "Nuke"`.

| Address | Control | What it does |
|---|---|---|
| `/helm/impulse` | fader | impulse 0 to 1, like the game's throttle bar - keeps reverse, drops out of warp |
| `/helm/reverse` | toggle | reverse (1) or forward (0) at the same power |
| `/helm/warp/<n>` | button | warp 1-4; `/helm/warp/0` drops back to full impulse |
| `/helm/throttle` | fader | the raw throttle: -1 reverse, 0 stop, 1 full impulse, 2-5 warp 1-4 |
| `/helm/stop` | button | all stop |
| `/helm/heading` | fader | steer to a compass heading in degrees (0 = +Z, 90 = +X) |
| `/helm/shields` | toggle | shields up (1) or down (0) |
| `/helm/red_alert` | toggle | red alert on (1) or off (0) |
| `/helm/dock` | button | dock at the nearest friendly station |
| `/helm/undock` | button | undock |
| `/weapons/target/nearest` | button | target the nearest hostile |
| `/weapons/target/next`, `/prev` | button | step through hostiles by distance |
| `/weapons/target/clear` | button | drop the weapons target |
| `/weapons/fire/<type>` | button | fire one torpedo of that type (`Homing`, `Nuke`, `EMP`...) at the target |
| `/science/target/nearest`, `/next`, `/prev` | button | pick a science target, as a click on it would |
| `/comms/target/nearest`, `/next`, `/prev` | button | pick a comms target, as a click on it would |
| `/comms/button/<n>` | button | press comms button *n* (0 is the first) |
| `/eng/power/<system>` | fader | power to a system, 0 to 3 (1 = 100%) - `beam`, `torp`, `impulse`, `warp`, `maneuver`, `sensors`, `front_shield`, `rear_shield` |
| `/eng/coolant/<n>` | fader | coolant on system 0-3, capped by what is available |

**Which ship.** A tablet drives the first player ship unless told otherwise:

- `/bind 2` - everything from this tablet now goes to player ship 2.
- `/ship/2/helm/throttle 0.5` - one message aimed at ship 2.

## What comes back

Every tablet heard from in the last 30 seconds is sent the ship's state about five times
a second, and only the values that changed:

| Address | Value |
|---|---|
| `/state/shields/front`, `/state/shields/rear` | 0..1 |
| `/state/energy` | the ship's energy |
| `/state/heat/0` .. `/3` | heat per system |
| `/state/torps/<type>` | torpedoes left, e.g. `/state/torps/homing` |
| `/state/docked` | 1 when docked |
| `/state/warp` | the warp factor, 0 at impulse |
| `/state/target/weapons`, `/science`, `/comms` | the target's name |

The controls' own addresses come back too - `/helm/throttle`, `/helm/shields`,
`/helm/impulse`, `/helm/reverse`, `/helm/red_alert`, `/eng/power/<system>`, `/eng/coolant/<n>` - so when someone moves the
throttle at the helm console, the tablet's throttle fader moves with it.

## Testing without a tablet

`sbs osc` sends and listens from the command line:

```
sbs osc send /helm/throttle 0.5
sbs osc send /weapons/fire/Homing 1
sbs osc monitor              # prints what the game sends back, on port 9000
```

**Ready-made TouchOSC panels** - one per console, already bound to the addresses above:

```
sbs osc layout helm -o helm.tosc
sbs osc layout all -o my_panels/        # helm, weapons, science, comms, engineering
```

!!! note "Experimental"
    The generated `.tosc` files have not been opened in TouchOSC by the author yet. Open
    one in the TouchOSC editor before relying on it, and report back if it does not load.
    `--xml` also writes the plain XML beside it, which is what to attach to a report.

`monitor` only receives once the game has heard from this machine, so send something
first. In Git Bash, prefix the command with `MSYS_NO_PATHCONV=1` - otherwise Git Bash
rewrites `/helm/throttle` into a Windows path before it reaches `sbs`.

## What a panel cannot do

These have no script-side control in the engine yet, so no panel can drive them:

- load or unload a torpedo tube, or choose which type a tube holds
- fire beams on demand (beams fire on their own at the weapons target)
- set the beam frequency
- start a science scan
- jump
- the engineering presets

## Cost

The listener never waits: each game update it collects whatever packets have arrived
and returns. Measured in the engine, that costs about 0.03 ms an update, and a control
reaches the ship within one update - about 35 ms on average.
