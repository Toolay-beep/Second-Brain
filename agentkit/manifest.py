"""Deterministic codebase manifest with content hashing.

The manifest lists every tracked file with its SHA-256 digest and size, plus
per-directory digests and a single root digest. Output is byte-for-byte stable
for identical inputs: paths are POSIX-normalised and sorted, JSON keys are
sorted, and no timestamps or absolute paths are recorded.

Agents use it to (a) know what exists without reading every file, (b) detect
drift between what they were told and what is on disk, and (c) pin the exact
input state of a pipeline run.

CLI:
    python -m agentkit.manifest build  [ROOT] [-o MANIFEST]
    python -m agentkit.manifest verify [ROOT] [-m MANIFEST]
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import sys
from pathlib import Path, PurePosixPath

MANIFEST_NAME = "agent-manifest.json"
IGNORE_FILE = ".manifestignore"
DEFAULT_IGNORES = [".git/", "__pycache__/", "*.pyc", ".pytest_cache/", MANIFEST_NAME]
CHUNK = 1 << 16


def _load_ignores(root: Path) -> list[str]:
    patterns = list(DEFAULT_IGNORES)
    f = root / IGNORE_FILE
    if f.is_file():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                patterns.append(line)
    return patterns


def _ignored(rel: str, is_dir: bool, patterns: list[str]) -> bool:
    name = PurePosixPath(rel).name
    for p in patterns:
        if p.endswith("/"):
            if is_dir and (fnmatch.fnmatch(name, p[:-1]) or fnmatch.fnmatch(rel, p[:-1])):
                return True
        elif fnmatch.fnmatch(name, p) or fnmatch.fnmatch(rel, p):
            return True
    return False


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def iter_files(root: Path):
    patterns = _load_ignores(root)
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root).as_posix()
        rel_dir = "" if rel_dir == "." else rel_dir
        dirnames[:] = sorted(
            d for d in dirnames
            if not _ignored(f"{rel_dir}/{d}".lstrip("/"), True, patterns)
        )
        for fn in sorted(filenames):
            rel = f"{rel_dir}/{fn}".lstrip("/")
            if not _ignored(rel, False, patterns):
                yield rel


def _digest_lines(lines: list[str]) -> str:
    return hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()


def build(root: Path) -> dict:
    root = root.resolve()
    files = {}
    for rel in iter_files(root):
        p = root / rel
        files[rel] = {"sha256": hash_file(p), "bytes": p.stat().st_size}

    # Directory digests: hash of the sorted "<sha256>  <path>\n" lines beneath each dir.
    dir_lines: dict[str, list[str]] = {}
    for rel in sorted(files):
        line = f"{files[rel]['sha256']}  {rel}\n"
        parts = PurePosixPath(rel).parts[:-1]
        for i in range(len(parts) + 1):
            dir_lines.setdefault("/".join(parts[:i]) or ".", []).append(line)
    dirs = {d: _digest_lines(lines) for d, lines in sorted(dir_lines.items())}

    return {
        "schema": "agentkit.manifest/1",
        "algorithm": "sha256",
        "root_digest": dirs.get(".", _digest_lines([])),
        "file_count": len(files),
        "dirs": dirs,
        "files": files,
    }


def dumps(manifest: dict) -> str:
    return json.dumps(manifest, indent=2, sort_keys=True) + "\n"


def diff(expected: dict, actual: dict) -> dict:
    e, a = expected["files"], actual["files"]
    return {
        "added": sorted(set(a) - set(e)),
        "removed": sorted(set(e) - set(a)),
        "modified": sorted(k for k in set(e) & set(a) if e[k]["sha256"] != a[k]["sha256"]),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="agentkit.manifest", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="write the manifest")
    b.add_argument("root", nargs="?", default=".")
    b.add_argument("-o", "--output", default=None, help=f"default: ROOT/{MANIFEST_NAME}; '-' for stdout")
    v = sub.add_parser("verify", help="exit 1 if the tree drifted from the manifest")
    v.add_argument("root", nargs="?", default=".")
    v.add_argument("-m", "--manifest", default=None)
    args = ap.parse_args(argv)

    root = Path(args.root)
    if args.cmd == "build":
        text = dumps(build(root))
        if args.output == "-":
            sys.stdout.write(text)
        else:
            out = Path(args.output) if args.output else root / MANIFEST_NAME
            out.write_text(text, encoding="utf-8")
            print(f"wrote {out} ({json.loads(text)['file_count']} files)", file=sys.stderr)
        return 0

    mpath = Path(args.manifest) if args.manifest else root / MANIFEST_NAME
    expected = json.loads(mpath.read_text(encoding="utf-8"))
    actual = build(root)
    if expected["root_digest"] == actual["root_digest"]:
        print(f"OK root_digest={actual['root_digest']}")
        return 0
    d = diff(expected, actual)
    for kind in ("added", "removed", "modified"):
        for path in d[kind]:
            print(f"{kind.upper():9} {path}")
    print(f"DRIFT expected={expected['root_digest']} actual={actual['root_digest']}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
