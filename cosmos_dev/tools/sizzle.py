"""Sizzle-reel capture harness CLI (dev-only).

    python -m cosmos_dev.tools.sizzle doctor

`doctor` is the only subcommand implemented so far (M0/M1). It answers the one question
worth answering before anything is built: is this machine actually able to shoot?

Shaped after cosmos_dev/tools/mission_soak.py - stdlib only, argparse, exit codes:
    0  everything the checked scope needs is present
    1  a blocking problem (something required is missing or off)
    3  nothing ran
"""
import io
import os
import time
import re
import sys
import glob
import json
import shutil
import argparse
import subprocess

from ..sizzle import obsws


OK = "ok  "
WARN = "warn"
BAD = "FAIL"


def _row(status, label, detail=""):
    print("  [%s] %-26s %s" % (status, label, detail))


# --- individual checks ----------------------------------------------------------------

def check_obs(args):
    """OBS install, websocket config, and - if it is reachable - a live handshake."""
    print("OBS")
    bad = False

    exe = r"C:\Program Files\obs-studio\bin\64bit\obs64.exe"
    if os.path.isfile(exe):
        _row(OK, "obs64.exe", exe)
    else:
        _row(BAD, "obs64.exe", "not found at " + exe)
        bad = True

    cfg = obsws.obs_config()
    path = obsws.obs_config_path()
    if not cfg:
        _row(BAD, "websocket config", "unreadable: %s" % path)
        return True

    port = cfg.get("server_port", obsws.DEFAULT_PORT)
    enabled = cfg.get("server_enabled")
    _row(OK, "websocket config", path)
    _row(OK if enabled else BAD, "server_enabled", str(enabled))
    _row(OK, "server_port", str(port))
    _row(OK if cfg.get("server_password") else WARN, "server_password",
         "set (read from config)" if cfg.get("server_password") else "not set")

    if not enabled:
        print()
        print("  -> Turn it on: OBS -> Tools -> WebSocket Server Settings ->")
        print("     tick 'Enable WebSocket server'. Nothing else to configure;")
        print("     the port and password are read from the file above.")
        return True

    try:
        with obsws.connect(host=args.obs_host, port=args.obs_port,
                           password=args.obs_password) as obs:
            v = obs.version()
            _row(OK, "handshake", "OBS %s / ws %s / rpc %s" % (
                v.get("obsVersion"), obs.ws_version, obs.rpc_version))
            scenes = obs.scenes().get("scenes") or []
            _row(OK, "scenes", "%d: %s" % (
                len(scenes),
                ", ".join(s.get("sceneName", "?") for s in scenes[:6]) or "-"))
            inputs = obs.inputs().get("inputs") or []
            games = [i for i in inputs if i.get("inputKind") == "game_capture"]
            _row(OK, "game_capture inputs", "%d of %d inputs" % (len(games), len(inputs)))
            for i in games[:8]:
                _row(OK, "  source", i.get("inputName", "?"))
            if args.shot:
                bad |= _try_shot(obs, games, args.shot)
    except obsws.ObsError as e:
        _row(BAD, "handshake", str(e))
        bad = True
    return bad


def _try_shot(obs, games, path):
    """Prove the capture path writes a real PNG.

    A game_capture source with nothing hooked cannot render, and that is ORDINARY
    before the engine is up - it is not a fault in the client. So fall back to the
    current program scene, which always renders: that still exercises the whole path
    (request -> base64 -> bytes -> file) and tells us capture works.
    """
    out = os.path.abspath(path)
    targets = [(g.get("inputName"), "game_capture") for g in games]
    try:
        current = obs.request("GetCurrentProgramScene")
        name = current.get("sceneName") or current.get("currentProgramSceneName")
        if name:
            targets.append((name, "scene"))
    except obsws.ObsError:
        pass

    last = None
    for name, kind in targets:
        try:
            png = obs.source_screenshot(name, width=480)
        except obsws.ObsError as e:
            last = e
            _row(WARN, "screenshot", "%s %r cannot render yet (%s)" % (kind, name, e))
            continue
        with open(out, "wb") as f:
            f.write(png)
        _row(OK, "screenshot", "%d bytes from %s %r -> %s" % (len(png), kind, name, out))
        return False
    _row(BAD, "screenshot", "nothing could be captured: %s" % last)
    return True


def _aspect(w, h):
    """A reduced w:h label, so 2560x1440 and 1920x1080 both read as 16:9."""
    if not w or not h:
        return "?"
    from math import gcd
    g = gcd(int(w), int(h))
    return "%d:%d" % (int(w) // g, int(h) // g)


def _engine_window_size(cosmos_dir):
    """The engine window's client size, measured live. None when nothing is running.

    Deliberately NOT read from preferences.json: `main-buff-*` there is the engine's
    internal image buffer, not the window it presents into, so it does not predict
    what a capture contains. The only truthful source is the live window.
    """
    from ..sizzle import windows
    windows.set_dpi_aware()
    try:
        out = subprocess.run(
            ["tasklist", "/fi", "imagename eq Artemis3-x64-release.exe", "/fo", "csv", "/nh"],
            capture_output=True, text=True, timeout=20).stdout
    except Exception:
        return None
    for line in out.splitlines():
        parts = [p.strip('"') for p in line.split('","')]
        if len(parts) < 2 or not parts[1].isdigit():
            continue
        hwnd = windows.window_of_pid(int(parts[1]), timeout=0.5)
        size = windows.client_size(hwnd) if hwnd else None
        if size and size[0] > 0 and size[1] > 0:
            return size
    return None


def check_video(args):
    """The resolution the reel is actually shot at, both ends.

    An aspect mismatch pillarboxes or crops, and an OBS output smaller than the source
    throws detail away. Neither is visible while shooting - only afterwards, which is
    why this is a pre-flight check rather than something noticed in the edit.
    """
    print("video")
    bad = False

    size = _engine_window_size(args.cosmos_dir)
    if size:
        _row(OK, "engine window", "%dx%d (%s) - measured client area"
             % (size[0], size[1], _aspect(*size)))
    else:
        _row(WARN, "engine window", "no engine running - size is measured at shoot time")

    try:
        with obsws.connect(host=args.obs_host, port=args.obs_port,
                           password=args.obs_password) as obs:
            v = obs.request("GetVideoSettings")
            bw, bh = v.get("baseWidth"), v.get("baseHeight")
            ow, oh = v.get("outputWidth"), v.get("outputHeight")
            fps = v.get("fpsNumerator", 0) / max(1, v.get("fpsDenominator", 1))
            _row(OK, "obs canvas", "%sx%s (%s)" % (bw, bh, _aspect(bw, bh)))
            _row(OK, "obs output", "%sx%s (%s) @ %.4g fps"
                 % (ow, oh, _aspect(ow, oh), fps))
            if size and ow and oh:
                if _aspect(*size) != _aspect(ow, oh):
                    _row(BAD, "aspect match",
                         "engine window %s vs OBS output %s - pillarboxed or cropped"
                         % (_aspect(*size), _aspect(ow, oh)))
                    bad = True
                elif ow < size[0] or oh < size[1]:
                    _row(WARN, "aspect match",
                         "OBS output %dx%d is smaller than the window %dx%d - "
                         "detail is thrown away" % (ow, oh, size[0], size[1]))
                else:
                    _row(OK, "aspect match", "window and OBS output agree")
    except obsws.ObsError as e:
        _row(WARN, "obs video settings", str(e))
    return bad


def check_ffmpeg():
    """ffmpeg is only needed to assemble; a contact sheet does not touch it."""
    print("ffmpeg")
    p = shutil.which("ffmpeg")
    if p:
        _row(OK, "ffmpeg", p)
        return False
    try:
        import imageio_ffmpeg
        _row(OK, "ffmpeg", "%s (imageio-ffmpeg)" % imageio_ffmpeg.get_ffmpeg_exe())
        return False
    except Exception:
        pass
    _row(WARN, "ffmpeg", "not found - needed only to ASSEMBLE, not to shoot stills")
    print("     -> pip install imageio-ffmpeg")
    return False


def check_engine(args):
    """The engine, the missions dir, and whether one is already running."""
    print("engine")
    bad = False
    cosmos = args.cosmos_dir
    exe = os.path.join(cosmos, "Artemis3-x64-release.exe")
    if os.path.isfile(exe):
        _row(OK, "engine exe", exe)
    else:
        _row(BAD, "engine exe", "not found at " + exe)
        bad = True

    missions = args.missions_dir or os.path.join(cosmos, "data", "missions")
    if os.path.isdir(missions):
        n = len(glob.glob(os.path.join(missions, "*", "story.json")))
        _row(OK, "missions dir", "%s (%d missions)" % (missions, n))
    else:
        _row(BAD, "missions dir", "not found at " + missions)
        bad = True

    # An already-running engine is a blocker, not a warning: EngineDriver.launch()
    # taskkills EVERY engine exe, so starting a shoot would kill a live session.
    try:
        out = subprocess.run(["tasklist", "/fi", "imagename eq Artemis3-x64-release.exe"],
                             capture_output=True, text=True, timeout=20).stdout
        running = "Artemis3-x64-release.exe" in out
    except Exception:
        running = False
    if running:
        _row(BAD, "engine running", "yes - a shoot would taskkill it (use --force)")
        bad = True
    else:
        _row(OK, "engine running", "no")
    return bad


def check_host():
    print("host")
    _row(OK, "python", sys.version.split()[0])
    try:
        import PIL
        _row(OK, "pillow", PIL.__version__)
    except Exception:
        _row(BAD, "pillow", "missing - needed to tile the contact sheet")
        return True
    return False


def cmd_doctor(args):
    bad = False
    bad |= check_host()
    print()
    bad |= check_obs(args)
    print()
    bad |= check_video(args)
    print()
    bad |= check_ffmpeg()
    print()
    bad |= check_engine(args)
    print()
    print("VERDICT: %s" % ("blocked - see FAIL rows above" if bad else "ready to shoot"))
    return 1 if bad else 0


def _client_label(drv, cid):
    """The MAST label a client's GUI task is currently on, or a reason it is unknown.

    Defensive on purpose: the exact attribute path is not documented and this runs
    inside the live engine, where an AttributeError would end the probe rather than
    answer it. An honest "unknown: <why>" is worth more than a confident wrong name.
    """
    expr = (
        "(lambda c: 'no such client' if c is None else "
        "(lambda p: 'no page' if p is None else "
        "(lambda t: 'no gui_task' if t is None else "
        "str(getattr(getattr(t, 'active_label', None), 'name', None) or "
        "getattr(t, 'active_label', None) or 'no active_label'))"
        "(getattr(p, 'gui_task', None)))"
        "(c.page_stack[-1] if getattr(c, 'page_stack', None) else None))"
        "(__import__('sbs_utils.gui', fromlist=['Gui']).Gui.clients.get(%d))" % cid
    )
    try:
        return drv.eval(expr, timeout=15)
    except Exception as e:
        return "unknown: %s" % e


def cmd_stage(args):
    """M2: bring up the engine + clients, bind them, and prove a reroute lands."""
    from ..engine_driver.driver import EngineDriver
    from ..sizzle import clients as C
    from ..sizzle import windows as W

    W.set_dpi_aware()
    if check_engine(args) and not args.force:
        print("\nRefusing to start (use --force to override).")
        return 1

    drv = EngineDriver(cosmos_dir=args.cosmos_dir, mission=args.mission)
    print("\nbuilding devqueue mastlib...")
    print("  " + drv.build_mastlib())
    print("enabling it in %s/story.json (revert with: git checkout story.json)"
          % args.mission)
    drv.enable_in_story()

    print("launching server on mission %r%s..."
          % (args.mission, (" map=%s" % args.map) if args.map else ""))
    drv.launch(map=args.map)
    print("waiting for the devqueue to answer (this is also the engine's boot)...")
    if not drv.ping(timeout=args.timeout):
        print("FAIL: the engine never answered the queue")
        return 1
    print("  engine answered: 1+1 = %s" % drv.eval("1+1"))

    # The known crash window is ~2s after a console connects, so settle first.
    print("warmup %ds..." % args.warmup)
    for _ in range(args.warmup):
        time.sleep(1)
        if not drv.is_running():
            print("FAIL: the engine died during warmup")
            return 1

    made = []
    try:
        for i, role in enumerate(args.roles.split(",")):
            role = role.strip()
            if not role:
                continue
            title = "SZ-%s" % role.upper()
            print("launching client %d (%s) as %r..." % (i + 1, role, title))
            c = C.launch_client(drv, role, title, timeout=args.timeout,
                                maximize=not args.no_maximize)
            made.append(c)
            print("  -> %r" % c)

        print("\nBINDING")
        print(C.table(made))

        bound = [c for c in made if c.client_id is not None]
        if len(bound) != len(made):
            print("\nFAIL: %d of %d clients did not bind"
                  % (len(made) - len(bound), len(made)))
            return 1

        # THE high-risk unknown in the plan: does gui_reroute_client survive being
        # called from a devqueue exec, where FrameContext.task is None?
        if args.reroute and bound:
            cid = bound[0].client_id
            print("\nREROUTE TEST: gui_reroute_client(%d, %s)" % (cid, args.reroute))
            # A MAST label is NOT a Python name in this scope - naming it bare is a
            # NameError and the reroute never even runs. Labels live in the page's
            # story table, keyed by name, so look it up there first.
            code = "\n".join([
                "from sbs_utils.gui import Gui",
                "from sbs_utils.procedural.gui.navigation import gui_reroute_client",
                "_c = Gui.clients.get(%d)" % cid,
                "_p = _c.page_stack[-1] if _c and _c.page_stack else None",
                "_labels = getattr(getattr(_p, 'story', None), 'labels', None) or {}",
                "_lbl = _labels.get(%r)" % args.reroute,
                "if _lbl is None:",
                "    raise KeyError('no label %%r; %%d labels known' %% "
                "(%r, len(_labels)))" % args.reroute,
                "gui_reroute_client(%d, _lbl)" % cid,
            ])
            before = _client_label(drv, cid)
            print("  label before: %s" % before)
            # send() RETURNS the engine's reply and only raises on transport failure -
            # an exception INSIDE the engine comes back as ok=False. Catching around
            # the call therefore proves nothing; the reply has to be read.
            try:
                resp = drv.send(code, timeout=20)
            except Exception as e:
                print("  FAIL (transport): %s" % e)
                return 1
            if not resp.get("ok"):
                print("  FAIL (in-engine): %s" % resp.get("error"))
                print("  -> fall back to task_schedule_server of a mission label")
                return 1
            time.sleep(2)
            after = _client_label(drv, cid)
            print("  label after : %s" % after)

            # "No exception" is NOT the test. gui_reroute_client can no-op silently,
            # and a no-op is exactly what a dead FrameContext.task would produce - so
            # the label has to be seen to CHANGE, or this proves nothing.
            if after and before and after != before:
                print("  PASS: the client moved to a different label")
            elif after and args.reroute.strip("'\"") in str(after):
                print("  PASS: the client is on the requested label")
            else:
                print("  INCONCLUSIVE: the label did not change - the reroute may")
                print("  have silently no-opped. Use task_schedule_server instead.")

            tail = drv.read_log(tail=1500) or ""
            hits = [ln for ln in tail.splitlines()
                    if "Traceback" in ln or "Error" in ln or "error" in ln]
            for ln in hits[-6:]:
                print("  log: " + ln)

        if args.hold:
            print("\nHOLDING. Ctrl-C to tear down.")
            while drv.is_running():
                time.sleep(1)
    except KeyboardInterrupt:
        print("\ninterrupted")
    finally:
        if not args.keep:
            print("\ntearing down...")
            C.stop(made)
            drv.close()
    return 0


def _sync_stage_mission(missions_dir, name="SizzleReel"):
    """Copy the versioned staging mission into data/missions.

    It lives in the repo so the shot list is version-controlled beside the tool, and
    is copied out per run so `enable_in_story` never edits anything of yours.
    """
    import shutil
    src = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "sizzle", "stage", name)
    dst = os.path.join(missions_dir, name)
    if not os.path.isdir(src):
        raise FileNotFoundError(src)
    # Copy OVER rather than delete-then-copy. The engine keeps mast.*.log open and
    # Windows will not remove a directory with an open handle in it, so an rmtree here
    # fails with PermissionError and takes the whole run with it - for a folder whose
    # only stale contents are logs we do not care about.
    shutil.copytree(src, dst, dirs_exist_ok=True)
    return dst


def _start_scene(drv, spec, timeout=60.0):
    """Start a @map through the library's own launch sequence.

    `maps_find` + `map_start` is the canonical pair - map_start's docstring says it
    exists BECAUSE LegendaryMissions and the headless runner had each hand-rolled the
    sequence and drifted on whether the sim resumes before or after scheduling. Calling
    it here means the harness is not a third divergent copy.

    Not `map=` on the engine command line either: that only reaches
    `sbs.command_line_dict()` and a mission has to be written to read it.
    """
    code = chr(10).join([
        "from sbs_utils.procedural.maps import maps_find, map_start",
        "_m = maps_find(%r)" % spec,
        "if _m is None:",
        "    from sbs_utils.procedural.maps import maps_get_list",
        "    raise KeyError('no map %%r; known: %%s' %% (%r, "
        "[getattr(x, 'path', x) for x in maps_get_list()]))" % spec,
        "map_start(_m)",
    ])
    resp = drv.send(code, timeout=20)
    if not resp.get("ok"):
        raise RuntimeError(resp.get("error"))
    return True


def cmd_contact(args):
    """M4: step the shot list, grab one still per shot, tile them into a sheet."""
    from ..engine_driver.driver import EngineDriver
    from ..sizzle import clients as C, windows as W, stepper, contact as sheet

    W.set_dpi_aware()
    if check_engine(args) and not args.force:
        print("\nRefusing to start (use --force to override).")
        return 1

    missions = args.missions_dir or os.path.join(args.cosmos_dir, "data", "missions")
    print("staging mission -> %s" % _sync_stage_mission(missions))

    drv = EngineDriver(cosmos_dir=args.cosmos_dir, mission="SizzleReel",
                       missions_dir=missions)
    drv.build_mastlib()
    drv.enable_in_story()
    print("launching engine on SizzleReel map=%s ..." % args.map)
    drv.launch(map=args.map)
    try:
        ok = drv.ping(timeout=args.timeout)
    except Exception as e:
        print("FAIL: the engine never answered the queue (%s)" % e)
        print("  logs: %s" % os.path.join(missions, "SizzleReel", "mast.compile.log"))
        drv.stop_engines()
        return 1
    if not ok:
        print("FAIL: the engine never answered the queue")
        drv.stop_engines()
        return 1
    print("  queue answered; warmup %ds (the known crash window is ~2s after a "
          "console connects)" % args.warmup)
    for _ in range(args.warmup):
        time.sleep(1)
        if not drv.is_running():
            print("FAIL: the engine died during warmup")
            return 1

    made = []
    scene = "sizzle-contact"
    src_name = "sizzle-cam"
    prev_scene = None
    obs = None
    try:
        cam = C.launch_client(drv, "cam", "SZ-CAM", timeout=args.timeout)
        made.append(cam)
        print("  %r" % cam)
        if cam.client_id is None:
            print("FAIL: the client never bound - %s" % cam.why)
            return 1
        if cam.size:
            asp = _aspect(*cam.size)
            print("  shooting at %dx%d (%s)" % (cam.size[0], cam.size[1], asp))
            if asp != "16:9":
                # A maximized window keeps its title bar, so its client area is short
                # of 16:9 and the take gets letterboxed or cropped on the way out.
                # The engine's own fullscreen mode fixes it and is set BY HAND - it is
                # not scriptable - so say so rather than silently shooting the wrong
                # shape, which is only visible once the reel is cut.
                print("  WARNING: not 16:9. Set the engine to FULLSCREEN by hand for a")
                print("  true %dx%d, or the reel is letterboxed/cropped."
                      % (W.screen_size() or (0, 0)))

        obs = obsws.connect(host=args.obs_host, port=args.obs_port,
                            password=args.obs_password)
        prev_scene = obs.current_scene()
        obs.remove_input(src_name)
        obs.remove_scene(scene)
        obs.create_scene(scene)
        obs.create_window_capture(
            scene, src_name, "%s:Engine:Artemis3-x64-release.exe" % cam.title)
        obs.set_current_scene(scene)
        time.sleep(1.5)          # let game_capture hook the swap chain

        print("starting map %r via map_start ..." % args.map)
        _start_scene(drv, args.map)

        # The label spawns, casts and loads the .amd; give it frames to finish
        # before asking what resolved.
        shots = []
        for _ in range(int(args.timeout)):
            time.sleep(1)
            shots = stepper.load_shots(drv, args.scene)
            if shots:
                break
        print("\n%d shots resolved in scene %r" % (len(shots), args.scene))
        rep = stepper.scene_report(drv)
        print("  sim: %s npc(s)" % rep.get("npcs", "?"))
        for o in (rep.get("objects") or []):
            print("       %-14s at %6d,%5d,%6d" % tuple(o))
        if shots and shots[0].get("subject"):
            fr = stepper.framing_report(drv, shots[0]["subject"])
            print("  framing for subject %s: %s" % (shots[0]["subject"], fr))
        if not shots:
            print("FAIL: no shots resolved. Either the staging label never ran, or")
            print("every Subject: failed to resolve (cast not bound) so each shot")
            print("was dropped. Check %s/SizzleReel/mast.runtime.log" % missions)
            return 1

        want = None
        if args.only:
            want = set(int(x) for x in args.only.replace(" ", "").split(",") if x != "")

        tiles = []
        for i, shot in enumerate(shots):
            if want is not None and i not in want:
                tiles.append(None)
                continue
            label = stepper.apply_shot(drv, args.scene, i, [cam.client_id])
            time.sleep(args.settle)
            try:
                png = obs.source_screenshot(src_name, width=args.width)
            except obsws.ObsError as e:
                print("  %02d %-28s NO FRAME (%s)" % (i, label, e))
                png = None
            else:
                print("  %02d %-28s %d bytes" % (i, label, len(png)))
            tiles.append(png)
            if not stepper.alive(drv):
                print("FAIL: the engine stopped answering at shot %d" % i)
                break

        out = args.out or os.path.join(missions, "_sizzle", "contact")
        path = sheet.write_sheet(out, tiles, shots, cols=args.cols, width=args.width)
        print("\nsheet: %s" % path)
    finally:
        if obs is not None:
            try:
                if prev_scene:
                    obs.set_current_scene(prev_scene)
                obs.remove_input(src_name)
                obs.remove_scene(scene)
            except Exception:
                pass
            obs.close()
        if not args.keep:
            C.stop(made)
            drv.close()
            # close() only ends the process this driver started. A client is its own
            # process and an early failure can leave the server behind, which then
            # blocks the NEXT run on the already-running guard - so sweep.
            drv.stop_engines()
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="sizzle", description=__doc__.splitlines()[0])
    ap.add_argument("--cosmos-dir", default=os.environ.get("COSMOS_DIR", r"E:\a\Cosmos-dev"))
    ap.add_argument("--missions-dir", default=None)
    ap.add_argument("--obs-host", default="127.0.0.1")
    ap.add_argument("--obs-port", type=int, default=None)
    ap.add_argument("--obs-password", default=None)
    sub = ap.add_subparsers(dest="cmd")

    d = sub.add_parser("doctor", help="check this machine can shoot")
    d.add_argument("--shot", metavar="PATH", default=None,
                   help="also write a GetSourceScreenshot PNG here, proving capture works")
    d.set_defaults(func=cmd_doctor)

    st = sub.add_parser("stage", help="M2: launch the engine + clients and bind them")
    st.add_argument("-m", "--mission", default="LegendaryMissions")
    st.add_argument("--map", default=None)
    st.add_argument("--roles", default="cam,2d",
                    help="comma-separated client roles to launch")
    st.add_argument("--reroute", default=None,
                    help="a MAST label to gui_reroute_client the first client to")
    st.add_argument("--warmup", type=int, default=20)
    st.add_argument("--timeout", type=float, default=120.0)
    st.add_argument("--hold", action="store_true", help="leave it up until Ctrl-C")
    st.add_argument("--keep", action="store_true", help="do not tear down on exit")
    st.add_argument("--no-maximize", action="store_true")
    st.add_argument("--force", action="store_true",
                    help="start even though an engine is already running")
    st.set_defaults(func=cmd_stage)

    ct = sub.add_parser("contact", help="M4: step the shot list into a contact sheet")
    ct.add_argument("--scene", default="open", help="cutscene key in shots.amd")
    ct.add_argument("--map", default="sz_open",
                    help="@map to start (index, path, name or substring)")
    ct.add_argument("--only", default=None, help="re-shoot only these indices, e.g. 4,7")
    ct.add_argument("--settle", type=float, default=0.6)
    ct.add_argument("--warmup", type=int, default=20)
    ct.add_argument("--width", type=int, default=480)
    ct.add_argument("--cols", type=int, default=4)
    ct.add_argument("--timeout", type=float, default=120.0)
    ct.add_argument("--out", default=None)
    ct.add_argument("--keep", action="store_true")
    ct.add_argument("--force", action="store_true")
    ct.set_defaults(func=cmd_contact)

    args = ap.parse_args(argv)
    if not getattr(args, "func", None):
        ap.print_help()
        return 3
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
