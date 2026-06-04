# Output Contract (Compact By Default)

Hermes now runs with a compact output contract by default to reduce output token
waste while preserving the evidence required to continue work.

## Default behavior

- Default response envelope:
  - sentence cap: `7`
  - character cap: `1200`
  - paragraph cap: `2`
- If the user does not ask for expansion, responses are compacted before being
  emitted and a compacted suffix is appended:
  - `[Response compacted. Reply with "expand" for a longer version.]`
- A response with explicit depth request is not compacted.

## Expansion triggers

Expansion is enabled when the user message contains any of:

- `expand`
- `more detail`
- `full detail`
- `verbose`
- `complete response`
- `unabridged`

Use an explicit request when you need:

- a full diagnostic write-up
- step-by-step implementation detail
- longer prose for product/design rationale

## Runtime configuration

Output limits can be set through config/env and applied across CLI, gateway,
ACP/Telegram/Slack (API-server), and paperclip handoff:

- `output.max_sentences`
- `output.max_chars`
- `HERMES_OUTPUT_MAX_SENTENCES`
- `HERMES_OUTPUT_MAX_CHARS`

The same settings are forwarded from Paperclip adapter execution to Hermes so
sessions stay consistent across entry points.

## Practical effect

- Keeps outputs concise by default in user-facing channels.
- Preserves tool-call and error recovery context.
- Adds low-friction control: one word (`expand`) to unlock fuller detail only when
  needed.
