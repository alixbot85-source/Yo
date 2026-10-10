#!/usr/bin/env python3
"""yo-cleaner: targeted, reversible disk-space reclamation.

Design rule that never changes: nothing is deleted unless the run is
explicitly armed, the target is inside an allowed root, and no path
matches a protected pattern. The default mode is a dry-run report.

Usage:
    python3 yo_cleaner.py scan            # report only, deletes nothing
    python3 yo_cleaner.py clean --apply   # actually delete (still guarded)
    python3 yo_cleaner.py undo <log>      # restore files deleted by a run

Exit codes:
    0 success, 1 refused by a safety guard, 2 usage/argument error,
    3 runtime error (permission, missing path, ...)
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import shutil
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

VERSION = "1.0.0"

# --------------------------------------------------------------------------
# Safety layer
# --------------------------------------------------------------------------

# Directories and names that are never touched, whatever the user asks for.
PROTECTED_NAMES = {
    "windows",
    "system32",
    "syswow64",
    "boot",
    "program files",
    "program files (x86)",
    "programdata",
    ".git",
    ".ssh",
    ".gnupg",
    "appdata",
    "documents",
    "desktop",
    "pictures",
    "videos",
    "music",
    "downloads",
    "$recycle.bin",
    "system volume information",
}

# Glob patterns treated as untouchable anywhere in the tree.
PROTECTED_PATTERNS = (
    "*.exe",
    "*.dll",
    "*.sys",
    "*.drv",
    "*.msi",
    "ntldr",
    "bootmgr",
    "*.sam",
    "*.vhd",
    "*.vhdx",
    "id_rsa",
    "id_ed25519",
    "*.pem",
    "*.pfx",
    "*.key",
)

# Roots a run is allowed to operate under. Anything outside is refused.
def default_allowed_roots() -> list[Path]:
    home = Path.home()
    roots = [home]
    for var in ("TEMP", "TMP"):
        value = os.environ.get(var)
        if value:
            roots.append(Path(value))
    # Deduplicate, keep order, drop nothing silently.
    seen: set[Path] = set()
    out: list[Path] = []
    for root in roots:
        try:
            resolved = root.resolve()
        except OSError:
            continue
        if resolved not in seen:
            seen.add(resolved)
            out.append(resolved)
    return out


class SafetyRefusal(Exception):
    """Raised when a guard blocks the operation. Never swallowed."""


@dataclass(frozen=True)
class Guard:
    """Decides whether a single path may be deleted."""

    allowed_roots: tuple[Path, ...]
    protected_names: frozenset[str] = frozenset(PROTECTED_NAMES)
    protected_patterns: tuple[str, ...] = PROTECTED_PATTERNS

    def _under_allowed_root(self, path: Path) -> bool:
        return any(
            path == root or root in path.parents for root in self.allowed_roots
        )

    def check(self, path: Path) -> None:
        """Raise SafetyRefusal with a reason, or return None if allowed."""
        if not self._under_allowed_root(path):
            raise SafetyRefusal(
                f"{path} is outside the allowed roots "
                f"({', '.join(str(r) for r in self.allowed_roots)})"
            )
        for part in path.parts:
            if part.lower() in self.protected_names:
                raise SafetyRefusal(f"{path} is inside protected directory {part!r}")
        name = path.name.lower()
        for pattern in self.protected_patterns:
            if fnmatch.fnmatch(name, pattern):
                raise SafetyRefusal(f"{path} matches protected pattern {pattern!r}")

    def is_allowed(self, path: Path) -> bool:
        try:
            self.check(path)
        except SafetyRefusal:
            return False
        return True


# --------------------------------------------------------------------------
# Target selection
# --------------------------------------------------------------------------

DEFAULT_TARGETS: dict[str, list[str]] = {
    "Python bytecode caches": ["__pycache__", "*.pyc"],
    "Node install/build output": ["node_modules", ".next", ".turbo"],
    "Test / lint caches": [".pytest_cache", ".mypy_cache", ".ruff_cache"],
    "Editor scratch": [".vscode/ipch", "*.swp", "*.swo"],
}


@dataclass
class Candidate:
    path: Path
    kind: str  # "dir" or "file"
    bytes: int
    reason: str

    def as_dict(self) -> dict:
        return {
            "path": str(self.path),
            "kind": self.kind,
            "bytes": self.bytes,
            "reason": self.reason,
        }


@dataclass
class Stats:
    scanned: int = 0
    candidates: int = 0
    bytes_reclaimable: int = 0
    deleted: int = 0
    bytes_freed: int = 0
    skipped: int = 0
    errors: int = 0

    def as_dict(self) -> dict:
        return {
            "scanned": self.scanned,
            "candidates": self.candidates,
            "bytes_reclaimable": self.bytes_reclaimable,
            "deleted": self.deleted,
            "bytes_freed": self.bytes_freed,
            "skipped": self.skipped,
            "errors": self.errors,
        }


def human(n: int) -> str:
    value = float(n)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} TiB"  # pragma: no cover


def dir_size(path: Path) -> int:
    total = 0
    stack = [path]
    while stack:
        current = stack.pop()
        try:
            entries = list(os.scandir(current))
        except OSError:
            continue
        for entry in entries:
            try:
                if entry.is_dir(follow_symlinks=False):
                    stack.append(Path(entry.path))
                elif entry.is_file(follow_symlinks=False):
                    total += entry.stat(follow_symlinks=False).st_size
            except OSError:
                continue
    return total


def matches_any(name: str, patterns: Iterable[str]) -> str | None:
    lowered = name.lower()
    for pattern in patterns:
        if fnmatch.fnmatch(lowered, pattern.lower()) or lowered == pattern.lower():
            return pattern
    return None


def find_candidates(
    roots: list[Path],
    patterns: list[str],
    guard: Guard,
    stats: Stats,
    max_depth: int = 25,
) -> list[Candidate]:
    """Walk roots and collect deletable candidates. Guarded path by path."""
    found: list[Candidate] = []
    seen: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        stack: list[tuple[Path, int]] = [(root, 0)]
        while stack:
            current, depth = stack.pop()
            if depth > max_depth:
                continue
            try:
                entries = list(os.scandir(current))
            except OSError:
                stats.errors += 1
                continue
            for entry in entries:
                path = Path(entry.path)
                stats.scanned += 1
                hit = matches_any(path.name, patterns)
                if hit:
                    try:
                        is_dir = entry.is_dir(follow_symlinks=False)
                    except OSError:
                        stats.errors += 1
                        continue
                    if path in seen:
                        continue
                    seen.add(path)
                    size = dir_size(path) if is_dir else _file_size(path)
                    found.append(
                        Candidate(
                            path=path,
                            kind="dir" if is_dir else "file",
                            bytes=size,
                            reason=f"matched {hit!r}",
                        )
                    )
                    stats.candidates += 1
                    stats.bytes_reclaimable += size
                    # Do not descend into a directory we will delete wholesale.
                    continue
                try:
                    if entry.is_dir(follow_symlinks=False):
                        stack.append((path, depth + 1))
                except OSError:
                    stats.errors += 1
    found.sort(key=lambda c: c.bytes, reverse=True)
    return found


def _file_size(path: Path) -> int:
    try:
        return path.stat(follow_symlinks=False).st_size
    except OSError:
        return 0


# --------------------------------------------------------------------------
# Actions
# --------------------------------------------------------------------------

@dataclass
class RunResult:
    mode: str
    armed: bool
    started_at: float
    finished_at: float = field(default=0.0)
    log_path: str | None = None
    stats: Stats = field(default_factory=Stats)
    deletions: list[dict] = field(default_factory=list)
    refusals: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "version": VERSION,
            "mode": self.mode,
            "armed": self.armed,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "log_path": self.log_path,
            "stats": self.stats.as_dict(),
            "deletions": self.deletions,
            "refusals": self.refusals,
        }


def execute(
    candidates: list[Candidate],
    guard: Guard,
    apply: bool,
    confirm_token: str | None,
    log_dir: Path,
    require_confirmation: bool = True,
) -> RunResult:
    """Dry-run by default. Deleting needs --apply AND the confirmation token."""
    result = RunResult(mode="clean", armed=apply, started_at=time.time())

    if apply:
        if require_confirmation and confirm_token != "DELETE":
            raise SafetyRefusal(
                "refusing to delete: pass --confirm DELETE to arm the run"
            )
        log_dir.mkdir(parents=True, exist_ok=True)
        result.log_path = str(log_dir / f"run-{uuid.uuid4().hex[:12]}.json")

    for candidate in candidates:
        try:
            guard.check(candidate.path)
        except SafetyRefusal as refusal:
            result.refusals.append(f"{candidate.path}: {refusal}")
            result.stats.skipped += 1
            continue

        if not apply:
            continue

        if candidate.kind == "file":
            record = _delete_file(candidate)
        else:
            record = _delete_dir(candidate)
        if record is None:
            result.stats.errors += 1
            continue
        result.deletions.append(record)
        result.stats.deleted += 1
        result.stats.bytes_freed += record["bytes"]

    if apply and result.log_path:
        _write_log(result)
    result.finished_at = time.time()
    return result


def _delete_file(candidate: Candidate) -> dict | None:
    path = candidate.path
    try:
        data = path.read_bytes()
        mode = path.stat(follow_symlinks=False).st_mode
        path.unlink()
    except OSError:
        return None
    return {
        "path": str(path),
        "kind": "file",
        "bytes": len(data),
        "content_base64": _b64(data),
        "mode": mode,
    }


def _delete_dir(candidate: Candidate) -> dict | None:
    path = candidate.path
    entries: list[dict] = []
    sizes = dir_size(path)
    for file_path in _walk_files(path):
        try:
            data = file_path.read_bytes()
            entries.append(
                {
                    "path": str(file_path.relative_to(path)),
                    "bytes": len(data),
                    "content_base64": _b64(data),
                }
            )
        except OSError:
            continue
    try:
        shutil.rmtree(path)
    except OSError:
        return None
    return {
        "path": str(path),
        "kind": "dir",
        "bytes": sizes,
        "files": entries,
    }


def _walk_files(root: Path) -> list[Path]:
    out: list[Path] = []
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            entries = list(os.scandir(current))
        except OSError:
            continue
        for entry in entries:
            path = Path(entry.path)
            if entry.is_dir(follow_symlinks=False):
                stack.append(path)
            elif entry.is_file(follow_symlinks=False):
                out.append(path)
    return sorted(out)


UNDO_INLINE_LIMIT = 8 * 1024 * 1024  # keep the undo log from exploding


def _b64(data: bytes) -> str:
    import base64

    if len(data) > UNDO_INLINE_LIMIT:
        return ""
    return base64.b64encode(data).decode("ascii")


def _write_log(result: RunResult) -> None:
    assert result.log_path
    Path(result.log_path).write_text(
        json.dumps(result.as_dict(), indent=2), encoding="utf-8"
    )


def undo(log_path: Path) -> dict:
    """Reverse one recorded run. Files come back, directories are recreated."""
    payload = json.loads(log_path.read_text(encoding="utf-8"))
    import base64

    restored = 0
    failed = 0
    for record in reversed(payload.get("deletions", [])):
        target = Path(record["path"])
        try:
            if record.get("kind") == "file":
                target.parent.mkdir(parents=True, exist_ok=True)
                content = record.get("content_base64") or ""
                target.write_bytes(base64.b64decode(content) if content else b"")
                if record.get("mode"):
                    os.chmod(target, record["mode"] & 0o7777)
                restored += 1
            else:
                for entry in record.get("files", []):
                    dest = target / entry["path"]
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    content = entry.get("content_base64") or ""
                    dest.write_bytes(base64.b64decode(content) if content else b"")
                    restored += 1
                if not record.get("files"):
                    target.mkdir(parents=True, exist_ok=True)
        except OSError:
            failed += 1
    return {"restored": restored, "failed": failed, "log": str(log_path)}


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _collect_patterns(args: argparse.Namespace) -> list[str]:
    if args.pattern:
        return list(args.pattern)
    flat: list[str] = []
    for group in DEFAULT_TARGETS.values():
        flat.extend(group)
    return flat


def _roots_for(args: argparse.Namespace, guard_roots: list[Path]) -> list[Path]:
    if args.root:
        return [Path(r) for r in args.root]
    return guard_roots


def _guard_roots(defaults: list[Path], requested: list[Path]) -> tuple[Path, ...]:
    """Allowed roots = defaults plus anything the user explicitly asked to scan.

    Adding a root only widens *where* we may look. The protected names and
    patterns stay in force inside it, so --root C:\\ still cannot eat Windows.
    """
    combined = list(defaults) + [Path(r).resolve() for r in requested]
    seen: set[Path] = set()
    out: list[Path] = []
    for root in combined:
        if root not in seen:
            seen.add(root)
            out.append(root)
    return tuple(out)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="yo-cleaner",
        description="Targeted, reversible disk-space reclamation. Dry-run by default.",
    )
    parser.add_argument("--version", action="version", version=f"yo-cleaner {VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--root", action="append", help="scan this root instead of home")
        p.add_argument(
            "--pattern", action="append", help="glob to treat as junk (repeatable)"
        )
        p.add_argument("--json", action="store_true", help="emit machine-readable JSON")
        p.add_argument("--limit", type=int, default=25, help="report top N candidates")

    scan = sub.add_parser("scan", help="report what would be reclaimed; delete nothing")
    add_common(scan)

    clean = sub.add_parser("clean", help="reclaim space (needs --apply to delete)")
    add_common(clean)
    clean.add_argument("--apply", action="store_true", help="actually delete")
    clean.add_argument("--confirm", help="must be DELETE when --apply is used")
    clean.add_argument(
        "--log-dir", default=".yo-cleaner-logs", help="where undo logs are written"
    )

    restore = sub.add_parser("undo", help="restore files removed by a recorded run")
    restore.add_argument("log", help="path to the run JSON produced by clean --apply")
    restore.add_argument("--json", action="store_true", help="emit machine-readable JSON")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "undo":
        try:
            outcome = undo(Path(args.log))
        except (OSError, json.JSONDecodeError) as error:
            print(f"ERROR: {error}", file=sys.stderr)
            return 3
        if args.json:
            print(json.dumps(outcome, indent=2))
        else:
            print(
                f"restored {outcome['restored']} file(s), "
                f"failed {outcome['failed']}, log {outcome['log']}"
            )
        return 0 if outcome["failed"] == 0 else 3

    allowed = default_allowed_roots()
    requested = [Path(r) for r in (args.root or [])]
    guard = Guard(allowed_roots=_guard_roots(allowed, requested))

    try:
        patterns = _collect_patterns(args)
        roots = _roots_for(args, allowed)
        stats = Stats()
        candidates = find_candidates(roots, patterns, guard, stats)

        if args.command == "scan":
            if args.json:
                print(
                    json.dumps(
                        {"mode": "scan", "stats": stats.as_dict(),
                         "candidates": [c.as_dict() for c in candidates[: args.limit]]},
                        indent=2,
                    )
                )
            else:
                print(f"scanned {stats.scanned} entries")
                print(
                    f"{stats.candidates} candidate(s), "
                    f"{human(stats.bytes_reclaimable)} reclaimable"
                )
                for candidate in candidates[: args.limit]:
                    print(f"  {human(candidate.bytes):>10}  {candidate.path}")
                print("\nnothing was deleted (scan mode)")
            return 0

        result = execute(
            candidates,
            guard,
            apply=args.apply,
            confirm_token=args.confirm,
            log_dir=Path(args.log_dir),
        )
        if args.json:
            print(json.dumps(result.as_dict(), indent=2))
        else:
            verb = "deleted" if args.apply else "would delete"
            print(f"{verb} {result.stats.deleted} item(s), "
                  f"{human(result.stats.bytes_freed)}")
            if not args.apply:
                print("dry-run: pass --apply --confirm DELETE to delete")
            if result.log_path:
                print(f"undo log: {result.log_path}")
            for refusal in result.refusals[:10]:
                print(f"refused: {refusal}")
        return 0

    except SafetyRefusal as refusal:
        print(f"REFUSED: {refusal}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
