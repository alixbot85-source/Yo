# The Evidence Contract

`AGENT_MODE.md` §5 as a mechanism instead of advice. A claim is either backed by a check
you ran this turn, or it is marked unverified. There is no third category.

## The rule

> Never write a fact about the repository, the data, or the system without having run
> the command that shows it — in the current turn. Then write down what came back.

Not from what you concluded earlier in the conversation. Not from what the code usually
looks like. Not from what the user seems to be implying.

## Claim → check

| Claim | The check that backs it |
|---|---|
| "file X exists" | `ls X` / `test -e X` |
| "file X says Y" | `cat X`, `grep -n Y X`, or read it |
| "there are N of them" | `… \| wc -l` — print the number |
| "function F exists / field F exists" | `grep -n "def F\|F =" path` |
| "tests pass" | run the runner, quote `Ran N tests` / `OK` |
| "the build works" | run the build, quote the last lines |
| "the server is running" | `curl -sS -o /dev/null -w '%{http_code}' URL` |
| "the endpoint returns X" | `curl` it, show the body or status |
| "the branch is pushed / up to date" | `git log origin/<branch> -1`, `git status -sb` |
| "the file is on the remote" | `gh api repos/<o>/<r>/contents/<p>?ref=<ref>` |
| "the URL works" | fetch it, show the status or first line |
| "commit C contains the change" | `git show --stat C` |
| "X is the cause of the bug" | reproduce it, then show it fixed by the change |
| "the dependency is missing" | `python3 -c "import x"` / `command -v x` **and** a PATH search |
| "nothing else changed" | `git status --porcelain` → expect `0` lines |

## What does not count as a check

- **A compile or syntax check.** It executes no path. `py_compile` proves the file
  parses; it proves nothing about behaviour.
- **A script that re-implements, copies, or fakes the changed logic.** It ran your
  stand-in, not what you are shipping.
- **A check whose output you did not read.** A clean exit code is not a pass when the
  output is wrong — a count off by one, a value reading `False`, an unexpected error.
  That is the result. Fix it and run again.
- **A test suite that never touched the code path you changed.** Name the function the
  command executed. If you cannot name one, you verified nothing.
- **A grep that matched the word in the wrong place.** Read the matching line, not just
  the count.

## The gap clause

If it genuinely cannot be run here, say so in the same breath as the change: what you
did, what you could not check, and why. Then keep going.

An honest gap costs nothing. A guess delivered in the same voice as a verified fact is
the failure — and it is the thing that gets you corrected.

## Worked example

From this repository's own history, where the rule earned its place:

| Claim | Check run | What came back |
|---|---|---|
| tests pass | `python3 -m unittest test_yo_cleaner` | `Ran 20 tests` → `OK` |
| the tool really deletes and restores | end-to-end demo in a temp dir | `deleted 2 item(s), 4.9 KiB` → `undo` → `restored 2 file(s), failed 0` |
| the restore is byte-exact | `sha256sum` before and after | `fdb635efe6fc820b` = `fdb635efe6fc820b` |
| guards hold | armed clean against a fixture containing `.git` | `refused: … is inside protected directory '.git'` |
| the file reached the remote | `gh api …?ref=arena/71e10993-yo` | `{"name":"AGENT_MODE.md","size":15080}` |
| the `main` download link works | `gh api …?ref=main` | `404 Not Found` — so the claim was corrected, not shipped |

Two of those rows are corrections. The sha256 row exists because the undo path had a real
bug that 20 green tests missed — the tests called `undo()` directly while the CLI crashed
on `args.root`. The 404 row exists because a plausible-looking link was assumed instead of
fetched. Both were caught by running the thing.

## Self-check before you say "done"

1. Name the function or code path the check executed. Can you? If not, no verification happened.
2. Quote the output, not a summary of it.
3. If the output surprised you, treat it as the truth and go fix the code.
4. List what you did **not** check, and why.
