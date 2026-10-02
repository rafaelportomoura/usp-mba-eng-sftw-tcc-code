"""Diff unificado entre o workspace inicial (cópia) e o final; sem git, sem dependências."""

import difflib
from pathlib import Path

IGNORED_PARTS = {"__pycache__"}


def _files(root):
    root = Path(root)
    return {p.relative_to(root).as_posix(): p for p in sorted(root.rglob("*"))
            if p.is_file() and not (set(p.relative_to(root).parts) & IGNORED_PARTS)
            and p.suffix != ".pyc"}


def _text(path):
    data = path.read_bytes()
    if b"\0" in data:
        return None
    return data.decode("utf-8", errors="replace").splitlines(keepends=True)


def workspace_diff(before, after):
    a, b = _files(before), _files(after)
    out = []
    for rel in sorted(set(a) | set(b)):
        pa, pb = a.get(rel), b.get(rel)
        if pa and pb and pa.read_bytes() == pb.read_bytes():
            continue
        ta = _text(pa) if pa else []
        tb = _text(pb) if pb else []
        if ta is None or tb is None:
            out.append(f"Binary files a/{rel} and b/{rel} differ\n")
            continue
        for line in difflib.unified_diff(ta, tb, fromfile=f"a/{rel}" if pa else "/dev/null",
                                         tofile=f"b/{rel}" if pb else "/dev/null"):
            out.append(line if line.endswith("\n") else line + "\n\\ No newline at end of file\n")
    return "".join(out)
