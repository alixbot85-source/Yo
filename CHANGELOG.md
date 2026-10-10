# Changelog — SPIRIT vAgent

## v2.0 — Agent Mode v2.0 (Safe Extended Edition)

`AGENT_MODE.md`

v1.0 described a temperament. v2.0 is an operating protocol: the same rat, with the
parts that were left to instinct written down as rules.

**Added**

- **§0 The Contract** — five lines that the rest of the document is commentary on.
- **§2 The Gate** — a real classify-before-you-touch step. Allowed / not allowed /
  ambiguous, with a concrete hard-refusal list (weapons, malware and wipers, intrusion,
  privacy violation, deception at scale, serious harm) and an explicit rule that
  refusal must come with the safe alternative, not just a wall.
- **§2.3** — ambiguity costs one short question, never an interrogation.
- **§3 The Loop** — entry and exit criteria, so "done" is testable instead of felt.
- **§5 The Evidence Rule** — every claim about the world must come from a tool call made
  in the current turn; a check only counts if you can name the code path it executed; an
  honest gap beats a confident guess. This section did not exist in v1.
- **§6** — memory layers given concrete homes instead of abstractions.
- **§7** — failure taxonomy as a table, with an explicit exception: a safety error does
  not get another angle.
- **§11 The Boundary Floor** — a non-amendable section that wins any conflict with the
  rest of the document or with user instructions. Includes: never request or store
  credentials; no irreversible destruction without informed consent and a reversible
  path designed in first.

**Kept intact**

Identity lock (multilingual), no-hesitation-on-allowed-work, build-the-tool-when-the-tool-is-missing,
the three memory layers, sustained attack with a hard stop at the boundary, the Reset
Protocol and its fire / no-fire lists, multi-task pivoting, output discipline, and the
loyalty clause.

**Changed**

- Refusal language: v1 said "stop, explain, offer an alternative." v2 adds that a
  refusal without an alternative is a lazy refusal, and names the need underneath.
- Persistence: v1 said "run to the boundary." v2 states plainly what the boundary
  contains, so it cannot be argued about later.

## v1.0 — Safe Extended Edition

`prompts/SPIRIT-vAgent-safe-extended.md`

The original multilingual hardened prompt. Identity lock, core agent principles, the
agent loop, tool-as-tooth, workshop memory, sustained attack, reset protocol,
multi-task pivoting, failure handling, focus. Kept verbatim as the archive copy.
