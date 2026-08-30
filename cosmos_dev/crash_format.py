"""Turn cdb output into a readable stack: innermost first, file:line under each frame.

`cdb -c "kn"` prints one dense line per frame carrying Child-SP, RetAddr, a mangled
symbol and, when `.lines -e` is on, a `[path @ line]` suffix. The mangled MSVC names for
templated containers run to several hundred characters, so the interesting part - which
function, which line - is off the right-hand edge of a terminal. This pulls the frames
apart and puts the source location on its own line.

`.lines -e` IS THE WHOLE TRICK. Without it cdb prints symbols only, which reads exactly
like a PDB with no line table - a conclusion this codebase carried in its notes for a
while and which is simply wrong. The release PDB has lines; cdb just does not load them
unless asked.

Build-machine roots (`D:\\PaxDev\\`, the MSVC include tree) are trimmed so the path
starts at something meaningful, and the compiler-version folder is collapsed to `STL/`.
"""
import re

# kn frames look like:
#   00 00000022`eea8fd80 00007ff7`707375a9 Sym!Func+0xa8 [D:\path\File.cpp @ 33]
#   (Inline Function) --------`-------- --------`-------- Sym!Func+0x2 [path @ 1801]
_FRAME = re.compile(
    r"^(?P<idx>[0-9a-f]{2}|\(Inline Function\))\s+"
    r"(?P<sp>[0-9a-f`]+|-+`-+)\s+"
    r"(?P<ret>[0-9a-f`]+|-+`-+)\s+"
    r"(?P<sym>.+?)"
    r"(?:\s+\[(?P<file>[^\]]+?)\s+@\s+(?P<line>\d+)\])?\s*$"
)

_ROOTS = ("D:\\PaxDev\\", "d:\\paxdev\\")


def short_path(path):
    """Trim the build machine's roots; collapse the MSVC version folder to STL/."""
    p = path.replace("/", "\\")
    low = p.lower()
    marker = "\\vc\\tools\\msvc\\"
    if marker in low:
        tail = p[low.index(marker) + len(marker):]
        parts = tail.split("\\", 1)
        return "STL/" + (parts[1].replace("\\", "/") if len(parts) > 1 else tail)
    for root in _ROOTS:
        i = low.find(root.lower())
        if i >= 0:
            p = p[i + len(root):]
            break
    return p.replace("\\", "/")


def bucket(out):
    """cdb's failure bucket - the thing that groups repeat crashes automatically."""
    for line in out.splitlines():
        if line.startswith("FAILURE_BUCKET_ID:"):
            return line.split(":", 1)[1].strip()
    return None


def fault_context(out):
    """(instruction, dereferenced address) from the `.ecxr` disassembly line, or Nones."""
    for line in out.splitlines():
        if " ds:" in line and "=" in line:
            body = line.strip()
            instr = body.split("  ")[-1].split(" ds:")[0].strip()
            addr = body.split(" ds:")[-1].split("=")[0].strip()
            return instr, addr
    return None, None


def frames(out):
    """Parsed frames, innermost first: {symbol, module, file, line, inline}."""
    got, started = [], False
    for line in out.splitlines():
        if line.lstrip().startswith("# Child-SP"):
            started = True
            continue
        if not started:
            continue
        if not line.strip():
            if got:
                break
            continue
        m = _FRAME.match(line.strip())
        if not m:
            continue
        sym = (m.group("sym") or "").strip()
        if not sym:
            continue
        mod, _, func = sym.partition("!")
        got.append({
            "module": mod if func else "",
            "symbol": func or sym,
            "file": short_path(m.group("file")) if m.group("file") else None,
            "line": int(m.group("line")) if m.group("line") else None,
            "inline": m.group("idx").startswith("("),
        })
    return got


def format_stack(out, width=88, skip_noise=True):
    """A readable stack. Returns "" when cdb produced no frames."""
    fs = frames(out)
    if not fs:
        return ""
    lines = []
    b = bucket(out)
    if b:
        lines.append("bucket : %s" % b)
    instr, addr = fault_context(out)
    if instr:
        lines.append("fault  : %s   ->  %s" % (instr, addr))
    if lines:
        lines.append("")

    for i, f in enumerate(fs):
        # OS/CRT tails carry no line info and no signal; keep them, but unindented and
        # without the blank-looking gap a missing source line would leave.
        noise = f["module"] in ("ntdll", "kernel32", "ucrtbase", "KERNELBASE")
        sym = f["symbol"]
        if len(sym) > width:
            sym = sym[:width - 3] + "..."
        tag = "  (inlined)" if f["inline"] else ""
        mark = "   <-- FAULT" if i == 0 else ""
        if noise and skip_noise:
            lines.append("#%-2d %s!%s" % (i, f["module"], sym))
            continue
        lines.append("#%-2d %s%s%s" % (i, sym, tag, mark))
        if f["file"]:
            lines.append("        %s:%d" % (f["file"], f["line"]))
    return "\n".join(lines)
