# yo-cleaner

Targeted, reversible disk-space reclamation. **Dry-run by default.**

This tool exists to reclaim space from regenerable junk (`__pycache__`,
`node_modules`, build/test caches, swap files). It is *not* a wipe tool and
will not become one: a binary that deletes everything on a disk is
ransomware/wiper territory, is irreversible, and bricks the machine it runs on.

## Install / run

No dependencies, Python 3.9+ standard library only.

```bash
python3 yo_cleaner.py scan                 # report only — deletes nothing
python3 yo_cleaner.py clean                # dry-run of the delete pass
python3 yo_cleaner.py clean --apply --confirm DELETE
python3 yo_cleaner.py undo .yo-cleaner-logs/run-xxxx.json
```

Useful flags: `--root PATH` (scan somewhere other than `$HOME`),
`--pattern GLOB` (repeatable, replaces the default junk list), `--json`,
`--limit N`.

## Safety model

Four independent layers. A delete must pass all of them.

| Layer | What it enforces |
|---|---|
| **Not armed by default** | `scan` and bare `clean` never delete. `--apply` alone still refuses; the run also needs `--confirm DELETE`. |
| **Root allowlist** | Only `$HOME` + `$TEMP`/`$TMP`, plus roots you pass to `--root`. Anything outside → `SafetyRefusal`, exit 1. |
| **Protected names** | `windows`, `system32`, `boot`, `program files`, `.git`, `.ssh`, `appdata`, `documents`, … are refused **even when the root allowlist contains them** — so `--root C:\` still cannot eat Windows. |
| **Protected patterns** | `*.exe`, `*.dll`, `*.sys`, `*.msi`, `id_rsa`, `*.pem`, `*.key`, `*.vhd`, `bootmgr`, … are never deleted. |

Skipped paths are reported, not silently ignored:

```
refused: /project/.git: /project/.git is inside protected directory '.git'
```

## Undo

Every armed run writes `.yo-cleaner-logs/run-<id>.json` containing the deleted
files (contents base64-inlined, up to 8 MiB each). `undo <log>` recreates them.
Files larger than the inline limit are deleted but **not** restorable — the log
records that gap rather than pretending otherwise.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | success (including "everything was skipped by a guard") |
| 1 | refused by a safety guard |
| 2 | usage/argument error |
| 3 | runtime error (permission, missing log, partial undo) |

## Tests

```bash
python3 -m unittest -v test_yo_cleaner    # 20 tests
```

Covered: guard allow/deny for outside-root, protected directory, protected
extension, system root; scan leaves the disk untouched; `.git` is skipped
rather than deleted; dry-run vs. armed; missing `--confirm` refuses;
delete → log → `undo` round-trip with content equality; `undo` over the CLI.

## Building a Windows .exe

PyInstaller is not a cross-compiler, so the `.exe` has to be built on Windows
(or in a Windows CI runner):

```bat
py -m pip install pyinstaller
py -m PyInstaller --onefile --name yo-cleaner yo_cleaner.py
dist\yo-cleaner.exe scan
```

Keep it a console app. A `--noconsole` GUI build that deletes files is exactly
the shape a wiper takes, and it would be indistinguishable from one to AV.
