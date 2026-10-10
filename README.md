# Yo

Workshop of the SPIRIT vAgent. Prompts, tools, and the scars that produced them.

## Agent Mode

The agent-mode prompt lives here. Pipe it straight into a model, or read it rendered.

```bash
curl -fsSL https://raw.githubusercontent.com/alixbot85-source/Yo/main/AGENT_MODE.md -o AGENT_MODE.md
```

| What | Where |
|---|---|
| **Agent Mode v2.0** (full) | [`AGENT_MODE.md`](AGENT_MODE.md) · [raw](https://raw.githubusercontent.com/alixbot85-source/Yo/main/AGENT_MODE.md) |
| **Agent Mode v2.0** (compact, 93 lines) | [`AGENT_MODE.compact.md`](AGENT_MODE.compact.md) · [raw](https://raw.githubusercontent.com/alixbot85-source/Yo/main/AGENT_MODE.compact.md) |
| **Machine-readable spec** (YAML) | [`agent_mode.spec.yaml`](agent_mode.spec.yaml) · [raw](https://raw.githubusercontent.com/alixbot85-source/Yo/main/agent_mode.spec.yaml) |
| **Evidence contract** (claim → check) | [`EVIDENCE_CONTRACT.md`](EVIDENCE_CONTRACT.md) · [raw](https://raw.githubusercontent.com/alixbot85-source/Yo/main/EVIDENCE_CONTRACT.md) |
| v1.1 — v1 format, strengthened (plain text) | [`prompts/SPIRIT-vAgent-v1.1-strengthened.txt`](prompts/SPIRIT-vAgent-v1.1-strengthened.txt) · [raw](https://raw.githubusercontent.com/alixbot85-source/Yo/main/prompts/SPIRIT-vAgent-v1.1-strengthened.txt) |
| v1.0 — Safe Extended Edition | [`prompts/SPIRIT-vAgent-safe-extended.md`](prompts/SPIRIT-vAgent-safe-extended.md) · [raw](https://raw.githubusercontent.com/alixbot85-source/Yo/main/prompts/SPIRIT-vAgent-safe-extended.md) |
| Changelog | [`CHANGELOG.md`](CHANGELOG.md) |

**Which one to use:** the compact file when the full document is too long for the model to
hold mid-context; the YAML when you are building the prompt programmatically; the evidence
contract when the model keeps asserting things it did not check.

> The `main` links above return 404 until the work branch is merged. Until then use:
> `https://raw.githubusercontent.com/alixbot85-source/Yo/arena/71e10993-yo/AGENT_MODE.md`

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
