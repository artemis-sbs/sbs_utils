"""Overnight ENGINE soak: relaunch Cosmos until it crashes, and say what crashed.

Why this exists alongside `overnight_runner`
--------------------------------------------
`overnight_runner` soaks the mockgui, which is the right tool for mission logic. It
cannot find the crash this was written for: the recurring `ObjectDataBlob` crash-to-
desktop is engine C++, and the mock is *kinder* than the engine in exactly the places
that matter (`create_new_sim()` clears `hull_map_objects`; there is no Simulation::Tick
to corrupt). Measured: the mock ran the same mission clean while the engine died.

So this drives the REAL exe, under autoplay, and treats each launch as a trial.

What it captures per launch, because the evidence is destroyed by the next one
-----------------------------------------------------------------------------
  * exit code (`-1073741819` / 3221225477 is 0xC0000005) and wall-clock uptime
  * any NEW minidump, symbolized to `function +delta` using the shipping PDB - the
    fault RVA is the only reliable way to tell one crash site from another, and it is
    only comparable WITHIN one build, so the PE timestamp is recorded too
  * `mast.compile.log`, `mast.runtime.log` and `debug.log`, copied aside - all three are
    opened mode="w" per run, so without this the crashing run's logs are erased by the
    relaunch that follows
  * completed games, read from `game_results.yaml`, so "died on game N" is answerable

Everything lands under `soak_out/` as one folder per launch plus a cumulative
`summary.json`, and the console line per launch is meant to be readable in the morning
without opening anything.

Usage (from data/missions):
    python -m cosmos_dev.engine_soak --hours 8
    python -m cosmos_dev.engine_soak --launches 5 --minutes 6
    python -m cosmos_dev.engine_soak --mission LegendaryMissions --map siege --profile autoplay7
"""
import argparse
import datetime
import glob
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import time

COSMOS = r"E:\a\Cosmos-dev"
EXE = os.path.join(COSMOS, "Artemis3-x64-release.exe")
PDB = os.path.join(COSMOS, "Artemis3-x64-release.pdb")
DUMPS = os.path.expandvars(r"%LOCALAPPDATA%\CrashDumps")
MISSIONS = os.path.join(COSMOS, "data", "missions")
# ProcDump, launched as a DEBUGGER around the engine.
#
# WER cannot be relied on here. Measured 2026-08-29: three crashes in one day produced
# ZERO dumps and ZERO Application Error events, while an identical-signature crash the
# day before produced both. The exe calls SetUnhandledExceptionFilter and has no
# dbghelp/MiniDumpWriteDump of its own, so its handler is swallowing the fault and
# exiting with 0xC0000005 as an EXIT CODE rather than faulting through to WER.
#
# procdump -e sees the exception first, because it is the debugger. -ma makes it a FULL
# memory dump rather than WER's minidump, which is what lets a bad `this` pointer be
# examined (freed heap vs never-constructed). Dumps land in the launch folder, so they
# need no pid matching at all.
PROCDUMP = os.path.join(COSMOS, "tools", "procdump64.exe")

# cdb.exe ships INSIDE the WinDbg MSIX (`winget install Microsoft.WinDbg`) - it is not on
# PATH and not where the classic SDK put it, which makes it very easy to conclude it is
# "not installed" and go looking for another package. It is not: check here first.
CDB_GLOBS = [
    r"C:\Program Files\WindowsApps\Microsoft.WinDbg_*_x64__8wekyb3d8bbwe\amd64\cdb.exe",
    r"C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\cdb.exe",
    r"C:\Program Files\Windows Kits\10\Debuggers\x64\cdb.exe",
]


# ----------------------------------------------------------------- dump reading
def _streams(buf):
    n, rva = struct.unpack_from("<II", buf, 8)
    out = {}
    for i in range(n):
        t, size, r = struct.unpack_from("<III", buf, rva + i * 12)
        out[t] = (size, r)
    return out


def _publics():
    """(rva, name) for every S_PUB32 in the shipping PDB, sorted. [] if unavailable."""
    try:
        exe = open(EXE, "rb").read()
        pe = struct.unpack_from("<I", exe, 0x3C)[0]
        n_sec = struct.unpack_from("<H", exe, pe + 6)[0]
        opt = struct.unpack_from("<H", exe, pe + 20)[0]
        secs = []
        for i in range(n_sec):
            o = pe + 24 + opt + i * 40
            _vs, va, _rs, _rp = struct.unpack_from("<IIII", exe, o + 8)
            secs.append(va)
        pdb = open(PDB, "rb").read()
        bs, _f, _nb, dirbytes, _u, blockmap = struct.unpack_from("<IIIIII", pdb, 0x20)

        def blocks(idxs, size):
            b = bytearray()
            for i in idxs:
                b += pdb[i * bs:(i + 1) * bs]
            return bytes(b[:size])

        ndb = (dirbytes + bs - 1) // bs
        d = blocks(struct.unpack_from("<%dI" % ndb, pdb, blockmap * bs), dirbytes)
        ns = struct.unpack_from("<I", d, 0)[0]
        sizes = struct.unpack_from("<%dI" % ns, d, 4)
        pos, streams = 4 + 4 * ns, []
        for s in sizes:
            nb = 0 if s in (0, 0xFFFFFFFF) else (s + bs - 1) // bs
            idxs = struct.unpack_from("<%dI" % nb, d, pos) if nb else ()
            pos += 4 * nb
            streams.append(blocks(idxs, s if s != 0xFFFFFFFF else 0))
        syms = streams[struct.unpack_from("<H", streams[3], 20)[0]]
        pubs, off = [], 0
        while off + 4 <= len(syms):
            ln = struct.unpack_from("<H", syms, off)[0]
            if ln < 2:
                break
            if struct.unpack_from("<H", syms, off + 2)[0] == 0x110E:
                _fl, soff, seg = struct.unpack_from("<IIH", syms, off + 4)
                end = syms.find(b"\0", off + 14)
                if 0 < seg <= len(secs):
                    pubs.append((secs[seg - 1] + soff,
                                 syms[off + 14:end].decode("latin1", "replace")))
            off += ln + 2
        pubs.sort()
        return pubs
    except Exception as e:                                      # noqa: BLE001
        print("[soak] no symbols (%r)" % (e,))
        return []


def _find_cdb():
    """Locate cdb.exe, including inside the WinDbg MSIX.

    `glob` CANNOT find the MSIX copy: `C:\\Program Files\\WindowsApps` is ACL-restricted,
    so expanding a wildcard there needs list permission the soak does not have - it comes
    back empty and reads exactly like "cdb is not installed". Opening a known FULL path
    under it works fine, so ask the package manager for the version and build the path,
    and only fall back to globbing for the classic SDK locations.
    """
    for pat in CDB_GLOBS:
        if "*" not in pat and os.path.isfile(pat):
            return pat
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-AppxPackage -Name 'Microsoft.WinDbg*' | "
             "Select-Object -First 1).InstallLocation"],
            capture_output=True, text=True, timeout=60).stdout.strip()
        if out:
            cand = os.path.join(out, "amd64", "cdb.exe")
            if os.path.isfile(cand):
                return cand
    except Exception:                                           # noqa: BLE001
        pass
    for pat in CDB_GLOBS:
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[-1]
    return None


def cdb_stack(path, cdb):
    """A REAL unwound stack, via cdb and the shipping PDB.

    Worth the subprocess: an x64 unwind needs the exe's .pdata/UNWIND_INFO, and a stack
    SCAN cannot do it. The scan reported `ObjectDataBlob::Set` as the caller here; cdb
    showed the actual caller is `ObjectDataBlob::Get`, INLINED - so it has no frame to
    find and no scan could ever have seen it. It also names the inline chain
    (operator[] -> _Try_emplace -> _Find_lower_bound), which is what shows a *read* path
    inserting into the map.
    """
    try:
        out = subprocess.run(
            [cdb, "-z", path, "-y", COSMOS, "-i", COSMOS,
             "-c", ".symfix; .reload; !analyze -v; kb; q"],
            capture_output=True, text=True, timeout=300).stdout
    except Exception as e:                                      # noqa: BLE001
        return {"cdb_error": repr(e)}
    frames, bucket = [], None
    for line in out.splitlines():
        if "Artemis3" in line and "!" in line:
            frag = line.split(":")[-1].strip()
            if frag and frag not in frames:
                frames.append(frag[:160])
        if line.startswith("BUGCHECK_STR:") or line.startswith("FAILURE_BUCKET_ID:"):
            bucket = line.strip()
    return {"raw": out, "frames": frames[:12], "bucket": bucket}


def analyze_dump(path, pubs):
    """Exception, fault RVA and symbol for one minidump."""
    try:
        buf = open(path, "rb").read()
    except Exception as e:                                      # noqa: BLE001
        return {"error": repr(e)}
    st = _streams(buf)
    info = {"dump": os.path.basename(path)}
    mods = []
    if 4 in st:
        _s, rva = st[4]
        for i in range(struct.unpack_from("<I", buf, rva)[0]):
            o = rva + 4 + i * 108
            base, size, _c, ts, nrva = struct.unpack_from("<QIIII", buf, o)
            ln = struct.unpack_from("<I", buf, nrva)[0]
            name = buf[nrva + 4:nrva + 4 + ln].decode("utf-16-le", "replace")
            mods.append((base, size, ts, name.split("\\")[-1]))
    if 6 in st:
        _s, rva = st[6]
        code, _fl, _r, addr, _np = struct.unpack_from("<IIQQI", buf, rva + 8)
        params = struct.unpack_from("<15Q", buf, rva + 40)
        info["exception"] = "0x%08X" % code
        info["access"] = {0: "read", 1: "write", 8: "execute"}.get(params[0], params[0])
        info["bad_address"] = "0x%016X" % params[1]
        for base, size, ts, name in mods:
            if base <= addr < base + size:
                info["module"] = name
                info["build_pe_timestamp"] = "0x%X" % ts
                info["fault_rva"] = "0x%X" % (addr - base)
                if pubs and name.lower().endswith(".exe"):
                    import bisect
                    addrs = [p[0] for p in pubs]
                    i = bisect.bisect_right(addrs, addr - base) - 1
                    if i >= 0:
                        info["symbol"] = pubs[i][1][:150]
                        info["symbol_delta"] = "0x%X" % ((addr - base) - pubs[i][0])
                break
    return info


# ----------------------------------------------------------------- soak
def _games_between(t0, t1):
    """Games completed inside a launch window, by TIMESTAMP.

    A before/after count delta looked obvious and reported 0 for 28 straight launches
    while 35 games were demonstrably being recorded. There are FOUR game_results.yaml in
    the tree (data/, data/missions/, data/missions_amd/, data/missions_mast/ - `sbs swap`
    territory) and the engine's write timing is its own business, so sampling a count
    around a subprocess is not something to trust. Each record carries its own time; ask
    the records instead.
    """
    lo = t0.strftime("%Y-%m-%d %H:%M:%S")
    hi = t1.strftime("%Y-%m-%d %H:%M:%S")
    seen = 0
    for cand in (os.path.join(MISSIONS, "game_results.yaml"),
                 os.path.join(COSMOS, "data", "game_results.yaml")):
        try:
            with open(cand, encoding="utf-8", errors="replace") as f:
                for line in f:
                    m = re.match(r'^- time: "([\d\-]+ [\d:]+)"', line)
                    if m and lo <= m.group(1) <= hi:
                        seen += 1
        except Exception:                                       # noqa: BLE001
            continue
        if seen:
            break                                               # first file that answers
    return seen


def _snapshot_dumps():
    try:
        return set(glob.glob(os.path.join(DUMPS, "*.dmp")))
    except Exception:                                           # noqa: BLE001
        return set()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mission", default="LegendaryMissions")
    ap.add_argument("--map", default="siege")
    ap.add_argument("--profile", default="autoplay7",
                    help="launch profile; autoplay7 gives AUTO_START + AUTO_PLAY so the "
                         "mission plays itself to victory and loops - which is the "
                         "game-end boundary this is hunting")
    ap.add_argument("--hours", type=float, default=8.0)
    ap.add_argument("--launches", type=int, default=0, help="0 = unlimited within --hours")
    ap.add_argument("--minutes", type=float, default=45.0,
                    help="kill and relaunch a run that lasts this long without crashing")
    ap.add_argument("--out", default=os.path.join(MISSIONS, "soak_out"))
    ap.add_argument("--no-procdump", action="store_true",
                    help="launch the engine directly and rely on WER (which has been "
                         "observed to miss these crashes entirely)")
    args = ap.parse_args(argv)

    os.makedirs(args.out, exist_ok=True)
    pubs = _publics()
    cdb = _find_cdb()
    print("[soak] %d symbols loaded; cdb: %s" % (len(pubs), cdb or "NOT FOUND (parser only)"))
    print("[soak] procdump: %s" % (PROCDUMP if os.path.isfile(PROCDUMP) else "NOT FOUND - relying on WER"))

    deadline = time.time() + args.hours * 3600.0
    summary = {"started": datetime.datetime.now().isoformat(timespec="seconds"),
               "exe": EXE, "mission": args.mission, "map": args.map,
               "profile": args.profile, "launches": []}
    n = 0
    while time.time() < deadline and (not args.launches or n < args.launches):
        n += 1
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        run_dir = os.path.join(args.out, "launch-%03d-%s" % (n, stamp))
        os.makedirs(run_dir, exist_ok=True)
        before_dumps = _snapshot_dumps()
        t_start = datetime.datetime.now()

        engine_cmd = [EXE, "autostartserver", "defaultmission=" + args.mission]
        if args.map:
            engine_cmd.append("map=" + args.map)
        if args.profile:
            engine_cmd.append("profile=" + args.profile)
        use_procdump = (not args.no_procdump) and os.path.isfile(PROCDUMP)
        if use_procdump:
            # -x launches the target under procdump, so monitoring starts before the
            # first instruction - the 13-second startup crashes are inside that window.
            cmd = [PROCDUMP, "-accepteula", "-ma", "-e", "-x", run_dir] + engine_cmd
        else:
            cmd = engine_cmd

        t0 = time.time()
        print("[soak] launch %d: %s" % (n, " ".join(cmd[1:])))
        with open(os.path.join(run_dir, "stdout.txt"), "wb") as out:
            proc = subprocess.Popen(cmd, cwd=COSMOS, stdout=out,
                                    stderr=subprocess.STDOUT)
            killed = False
            try:
                proc.wait(timeout=args.minutes * 60.0)
            except subprocess.TimeoutExpired:
                killed = True
                # /T kills the tree. Killing procdump alone would leave the engine
                # running and the next launch would fight it for the network port.
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                               capture_output=True)
                try:
                    proc.wait(timeout=60)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
        uptime = time.time() - t0

        # The engine truncates all three of these on the next launch.
        mdir = os.path.join(MISSIONS, args.mission)
        for src in (os.path.join(mdir, "mast.runtime.log"),
                    os.path.join(mdir, "mast.compile.log"),
                    os.path.join(COSMOS, "debug.log")):
            try:
                if os.path.isfile(src):
                    shutil.copy2(src, run_dir)
            except Exception:                                   # noqa: BLE001
                pass

        # Attribute by PID, not just by "appeared since we started". A dump is named
        # Artemis3-x64-release.exe.<pid>.dmp, and WER can take a moment to finish writing
        # it - so wait briefly, then prefer the one carrying THIS launch's pid. Anything
        # else that appeared is kept separately rather than blamed on this launch.
        appeared = sorted(_snapshot_dumps() - before_dumps)
        if proc.returncode not in (0, 1) and not appeared:
            time.sleep(10)                       # WER is still writing
            appeared = sorted(_snapshot_dumps() - before_dumps)
        local = sorted(glob.glob(os.path.join(run_dir, "*.dmp")))
        mine = local or [d for d in appeared if (".%d.dmp" % proc.pid) in os.path.basename(d)]
        others = [d for d in appeared if d not in mine]
        if local:
            others = []          # procdump dumps are unambiguous - no attribution needed
        new_dumps = mine or appeared
        rec = {"launch": n, "when": stamp, "uptime_sec": round(uptime, 1),
               "exit_code": proc.returncode, "killed_by_soak": killed,
               "games_completed": _games_between(t_start, datetime.datetime.now()),
               "pid": proc.pid,
               "dumps": [analyze_dump(d, pubs) for d in new_dumps],
               "cdb": ([cdb_stack(d, cdb) for d in new_dumps] if cdb else []),
               "dump_matched_pid": bool(mine),
               "other_dumps_seen": [os.path.basename(d) for d in others]}
        summary["launches"].append(rec)
        with open(os.path.join(args.out, "summary.json"), "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        for i, c in enumerate(rec.get("cdb") or []):
            raw = c.pop("raw", None)
            if raw:
                with open(os.path.join(run_dir, "cdb-%d.txt" % i), "w",
                          encoding="utf-8", errors="replace") as f:
                    f.write(raw)
        with open(os.path.join(run_dir, "result.json"), "w", encoding="utf-8") as f:
            json.dump(rec, f, indent=2)

        verdict = "killed at limit" if killed else ("exit %s" % proc.returncode)
        if rec["dumps"]:
            d = rec["dumps"][0]
            verdict = "CRASH %s %s of %s at %s %s+%s" % (
                d.get("exception"), d.get("access"), d.get("bad_address"),
                d.get("fault_rva"), (d.get("symbol") or "?")[:60],
                d.get("symbol_delta"))
        print("[soak]   %s | %.0fs | %d game(s) | %s"
              % (verdict, uptime, rec["games_completed"], run_dir))
        time.sleep(3)

    crashes = [l for l in summary["launches"] if l["dumps"]]
    print("\n[soak] %d launch(es), %d crash(es). %s"
          % (len(summary["launches"]), len(crashes),
             os.path.join(args.out, "summary.json")))
    for c in crashes:
        d = c["dumps"][0]
        print("   launch %d after %ss: %s +%s (%s)"
              % (c["launch"], c["uptime_sec"], (d.get("symbol") or "?")[:70],
                 d.get("symbol_delta"), d.get("fault_rva")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
