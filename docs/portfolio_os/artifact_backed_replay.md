# Artifact-Backed Replay

Hermes keeps exact raw blobs for audit while replaying bounded summaries for old
large content. This preserves prompt-cache stability and tool-call validity while
removing raw replay bloat.

## Storage

- `artifacts`: exact raw blobs keyed by SHA-256.
- `message_artifacts`: message-to-artifact links.
- `messages.replay_content`: bounded replay payload.
- `messages.search_content`: full-text-search payload.
- `messages.content_sha256`: exact content fingerprint.
- `prompt_blocks` and `session_prompt_blocks`: content-addressed system prompt
  blocks. `sessions.system_prompt` remains exact until byte-identical
  reconstruction is proven.

## Replay Rules

- Small recent messages replay exactly.
- Current turn and the latest relevant tool-call group replay exactly.
- Older large tool/file/web/terminal outputs replay as typed summary plus artifact
  pointer.
- Assistant tool-call/tool-result pairing stays valid.
- Codex reasoning fields are preserved when present.
- FTS searches `search_content`, so artifact-backed raw content remains findable.

## Cache Safety

The system prompt is not regenerated during a session. Prompt blocks are
content-addressed for future reconstruction, but the byte-identical
`sessions.system_prompt` column remains authoritative.

## Migration And Rollback

Schema version 7 adds artifact and prompt-block tables plus replay/search content
columns. The migration is additive and backfills existing message rows with exact
content as replay/search content.

Rollback is a data-retention decision: before dropping v7 columns or tables,
export `artifacts`, `message_artifacts`, and any rows where
`messages.content_artifacted = 1`. Dropping the tables without export preserves
the bounded replay text but loses exact raw audit blobs.
