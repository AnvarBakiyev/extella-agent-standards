#!/usr/bin/env python3
"""Gate: the English mirror under en/ must not silently fall behind the Russian source.

WHY. The corpus is written in Russian; English readers need the same documents. Two copies
of a text diverge the moment one is edited — we already lost a day on outreach texts where
the "approved" file turned out to be the previous week's edition. So every English file
carries a stamp of the exact Russian source it was translated from, and this gate fails
the moment the source changes without the translation following.

How it works:

    en/MANIFEST.yaml lists pairs {ru: <path>, en: <path>} that are in scope.
    Each in-scope en file starts with a stamp line:
        <!-- source: <ru path> sha256:<64 hex> -->
    The gate recomputes sha256 of the current ru file and compares.

    python3 tools/check_en_sync.py              # check everything in the manifest
    python3 tools/check_en_sync.py --stamp AGENT_BUILD_GUIDE.md en/AGENT_BUILD_GUIDE.md
                                                 # (re)write the stamp after translating
    python3 tools/check_en_sync.py --coverage   # also list Russian .md files not yet in scope
    python3 tools/check_en_sync.py --selftest

Exit codes: 0 — every in-scope translation matches its source, 1 — at least one is missing,
unstamped or stale, 2 — nothing to check (manifest missing or empty).

Documents outside the manifest are reported with --coverage but never fail the gate: the
mirror is built up in batches, and a gate that fails on "not yet translated" would have to be
switched off, which is the same as not having it.
"""

import hashlib
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "en" / "MANIFEST.yaml"
STAMP = re.compile(r"^<!--\s*source:\s*(\S+)\s+sha256:([0-9a-f]{64})\s*-->\s*$")


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_manifest():
    if not MANIFEST.exists():
        return None
    import yaml  # CI installs pyyaml; same dependency as the registry gate
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8")) or {}
    docs = data.get("docs") or []
    return [(str(d["ru"]), str(d["en"])) for d in docs if "ru" in d and "en" in d]


def read_stamp(en_path: pathlib.Path):
    try:
        first = en_path.read_text(encoding="utf-8").splitlines()[0]
    except (IndexError, FileNotFoundError):
        return None
    m = STAMP.match(first.strip())
    return (m.group(1), m.group(2)) if m else None


def check(pairs):
    problems = []
    for ru, en in pairs:
        ru_p, en_p = ROOT / ru, ROOT / en
        if not ru_p.exists():
            problems.append(f"{en}: source {ru} does not exist — fix the manifest")
            continue
        if not en_p.exists():
            problems.append(f"{en}: translation missing for {ru}")
            continue
        st = read_stamp(en_p)
        if st is None:
            problems.append(f"{en}: no stamp line; run --stamp {ru} {en} after translating")
            continue
        if st[0] != ru:
            problems.append(f"{en}: stamp says source is {st[0]}, manifest says {ru}")
            continue
        if st[1] != sha256(ru_p):
            problems.append(f"{en}: STALE — {ru} changed since translation; retranslate, then --stamp")
    return problems


def stamp(ru: str, en: str):
    ru_p, en_p = ROOT / ru, ROOT / en
    if not ru_p.exists() or not en_p.exists():
        print(f"cannot stamp: {ru} or {en} does not exist")
        return 1
    lines = en_p.read_text(encoding="utf-8").splitlines()
    line = f"<!-- source: {ru} sha256:{sha256(ru_p)} -->"
    if lines and STAMP.match(lines[0].strip()):
        lines[0] = line
    else:
        lines = [line, ""] + lines
    en_p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"stamped {en} ← {ru}")
    return 0


def coverage(pairs):
    in_scope = {ru for ru, _ in pairs}
    skip = {"CHANGELOG.md"}
    ru_docs = sorted(str(p.relative_to(ROOT)) for p in ROOT.glob("*.md") if p.name not in skip)
    for d in ("rules", "docs", "checklists", "skills", "templates"):
        ru_docs += sorted(str(p.relative_to(ROOT)) for p in (ROOT / d).rglob("*.md"))
    missing = [d for d in ru_docs if d not in in_scope and not d.startswith("en/")]
    print(f"in scope: {len(in_scope)} · not yet translated: {len(missing)}")
    for d in missing:
        print(f"  - {d}")


def selftest():
    import tempfile
    tmp = pathlib.Path(tempfile.mkdtemp())
    ru = tmp / "a.md"; en = tmp / "a.en.md"
    ru.write_text("# А\n", encoding="utf-8"); en.write_text("# A\n", encoding="utf-8")
    global ROOT
    ROOT = tmp
    assert check([("a.md", "a.en.md")]) and "no stamp" in check([("a.md", "a.en.md")])[0]
    assert stamp("a.md", "a.en.md") == 0
    assert check([("a.md", "a.en.md")]) == []
    ru.write_text("# А изменён\n", encoding="utf-8")
    assert "STALE" in check([("a.md", "a.en.md")])[0]
    print("selftest: ok")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["--selftest"]:
        sys.exit(selftest())
    if args[:1] == ["--stamp"] and len(args) == 3:
        sys.exit(stamp(args[1], args[2]))
    pairs = load_manifest()
    if not pairs:
        print("en/MANIFEST.yaml missing or empty — nothing to check")
        sys.exit(2)
    if args[:1] == ["--coverage"]:
        coverage(pairs)
    problems = check(pairs)
    for p in problems:
        print("FAIL " + p)
    print(f"en sync: {len(pairs) - len(problems)}/{len(pairs)} translations match their source")
    sys.exit(1 if problems else 0)
