# Yo

Workshop of the SPIRIT vAgent. Prompts, tools, and the scars that produced them.

## Agent Mode

The agent-mode prompt lives here. Pipe it straight into a model, or read it rendered.

```bash
curl -fsSL https://raw.githubusercontent.com/alixbot85-source/Yo/main/AGENT_MODE.md -o AGENT_MODE.md
```

| What | Where |
|---|---|
| **Agent Mode v2.0** (current) | [`AGENT_MODE.md`](AGENT_MODE.md) · [raw](https://raw.githubusercontent.com/alixbot85-source/Yo/main/AGENT_MODE.md) |
| v1.0 — Safe Extended Edition | [`prompts/SPIRIT-vAgent-safe-extended.md`](prompts/SPIRIT-vAgent-safe-extended.md) · [raw](https://raw.githubusercontent.com/alixbot85-source/Yo/main/prompts/SPIRIT-vAgent-safe-extended.md) |
| Changelog | [`CHANGELOG.md`](CHANGELOG.md) |

Five lines, if you only take five:

1. Build, don't narrate.
2. Finish.
3. Prove it.
4. Stay inside the floor.
5. Loop.

## Tools

| Tool | What it does |
|---|---|
| [`yo-cleaner/`](yo-cleaner/) | Targeted, reversible disk-space reclamation. Dry-run by default, path-guarded, undoable. 20 tests. |

`yo-cleaner` is the answer to "make me something that deletes files": it reclaims space
from regenerable junk and can put everything back. It is deliberately not a wipe tool.

## Layout

```
AGENT_MODE.md                 agent-mode prompt, v2.0
CHANGELOG.md                  version history of the prompt
prompts/                      archived prompt versions
yo-cleaner/                   guarded cleanup tool + tests
```

## Safety

Every artifact in this repo follows the boundary floor in
[`AGENT_MODE.md` §11](AGENT_MODE.md#11-the-boundary-floor): no weapons, no malware, no
intrusion, no privacy violation, no forged identity, no irreversible destruction without
informed consent and a reversible path designed in first.

---

*MADE BY SPIRIT*
